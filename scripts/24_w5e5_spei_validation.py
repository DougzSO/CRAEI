"""COMANDO 22-D: SPEI-12 derived directly from W5E5 observations (not the
ISIMIP3b bias-adjusted models in `spei.parquet`), for Spec Sec1.7/Fig.5
validation against ONS ENA (Brazil, national) and REN IPH (Portugal).

METHODS_SPEC.md line 115/405 requires SPEI-12 "computed from W5E5
observations", distinct from the model-based SPEI-12 already produced by
scripts/07_water_balance.py + scripts/08_spei.py (bias-adjusted ISIMIP3b
GCM historical runs). That W5E5-native derivation had never been run --
the raw W5E5 NetCDFs were acquired (D59) but never passed through PET /
water balance / SPEI fitting. This script does that, restricted to the
hydro catchment cells of Brazil's 222 and Portugal's 41 hydro plants only
(not the full country cell set used for the production pipeline), since
this is a validation-only derivation, not a reprocessing of the hazard
results.

Writes `data/processed/water_balance_catchment_w5e5.parquet` and
`data/processed/spei_w5e5.parquet` -- new files, the production
`water_balance_*`/`spei.parquet` outputs are untouched.
"""

import gc
from pathlib import Path

import pandas as pd
import xarray as xr

from craei.config import load_datasets, load_paths
from craei.hazards import pet, spei
from craei.hazards.pet import KELVIN_OFFSET_C

PR_FLUX_TO_MM_PER_DAY = 86400.0
COUNTRIES = ["BRA", "PRT"]  # India excluded (Spec line 115: "India is not validated")


def bbox_token(bbox: list[float]) -> str:
    west, east, south, north = bbox
    return f"lon{west}to{east}lat{south}to{north}"


def find_files(raw_dir: Path, var: str, bbox: list[float]) -> list[Path]:
    token = bbox_token(bbox)
    files = sorted((raw_dir / "climate" / "w5e5v2.0" / var).glob(f"{var}_W5E5v2.0_*_{token}.nc"))
    if not files:
        raise FileNotFoundError(f"no W5E5 {var} files found for bbox token {token}")
    return files


def load_cell_series_multi(
    nc_paths: list[Path], cells: pd.DataFrame, value_col: str, start_year: int, end_year: int
) -> pd.DataFrame:
    with xr.open_mfdataset(nc_paths, combine="by_coords") as ds:
        variable = next(iter(ds.data_vars))
        lat_sel = xr.DataArray(cells["cell_lat"].to_numpy(), dims="cell")
        lon_sel = xr.DataArray(cells["cell_lon"].to_numpy(), dims="cell")
        time_ok = (ds["time.year"] >= start_year) & (ds["time.year"] <= end_year)
        selected = (
            ds[variable]
            .sel(lat=lat_sel, lon=lon_sel, method="nearest")
            .isel(time=time_ok.values)
            .load()
        )
    df = selected.to_dataframe(name=value_col).reset_index()
    df["cell_lat"] = cells["cell_lat"].to_numpy()[df["cell"].to_numpy()]
    df["cell_lon"] = cells["cell_lon"].to_numpy()[df["cell"].to_numpy()]
    df.rename(columns={"time": "date"}, inplace=True)
    return df[["date", "cell_lat", "cell_lon", value_col]]


def hydro_catchment_cells_and_weights(processed_dir: Path, country: str):
    plants = pd.read_parquet(
        processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class"]
    )
    hydro = plants[(plants["country"] == country) & (plants["tech_class"] == "hydro")]
    weights = pd.read_parquet(processed_dir / "catchment_weights.parquet")
    weights_country = weights.merge(hydro[["plant_uid"]], on="plant_uid")
    cells = weights_country[["cell_lat", "cell_lon"]].drop_duplicates().reset_index(drop=True)
    return cells, weights_country, len(hydro)


def main() -> None:
    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])

    start_year = int(datasets_cfg["w5e5"]["years"]["start"])  # 1984
    end_year = int(datasets_cfg["w5e5"]["years"]["end"])  # 2019

    catchment_frames = []

    for country in COUNTRIES:
        cells, weights_country, n_hydro = hydro_catchment_cells_and_weights(processed_dir, country)
        print(f"{country}: {n_hydro} hydro plants, {len(cells)} catchment cells")
        bbox = datasets_cfg["bboxes"][country]

        tasmax_files = find_files(raw_dir, "tasmax", bbox)
        tasmin_files = find_files(raw_dir, "tasmin", bbox)
        pr_files = find_files(raw_dir, "pr", bbox)

        tasmax = load_cell_series_multi(tasmax_files, cells, "tasmax_c", start_year, end_year)
        tasmax["tasmax_c"] -= KELVIN_OFFSET_C
        tasmin = load_cell_series_multi(tasmin_files, cells, "tasmin_c", start_year, end_year)
        tasmin["tasmin_c"] -= KELVIN_OFFSET_C
        temps = tasmax.merge(tasmin, on=["date", "cell_lat", "cell_lon"])
        del tasmax, tasmin
        gc.collect()

        tx_tn = pet.count_tx_below_tn(temps)
        n_days = int(tx_tn["n_days"].sum())
        n_bad = int(tx_tn["n_tx_below_tn"].sum())
        print(f"{country}: TX<TN on {n_bad}/{n_days} days ({n_bad / n_days:.4%}) before treatment")

        pet_df = pet.daily_pet(temps)
        n_truncated = int(pet_df["pet_truncated"].sum())
        print(f"{country}: {n_truncated} PET-truncated days")
        del temps
        gc.collect()

        pr = load_cell_series_multi(pr_files, cells, "pr_mm", start_year, end_year)
        pr["pr_mm"] *= PR_FLUX_TO_MM_PER_DAY

        daily = pet_df[["date", "cell_lat", "cell_lon", "pet_mm"]].merge(
            pr[["date", "cell_lat", "cell_lon", "pr_mm"]], on=["date", "cell_lat", "cell_lon"]
        )
        daily = daily.rename(columns={"pr_mm": "p_mm"})
        daily["model"] = "w5e5"
        daily["scenario"] = "w5e5"
        daily["period"] = "baseline"  # spei.fit_baseline_single filters period=="baseline"
        del pet_df, pr
        gc.collect()

        cell_balance = pet.monthly_water_balance(daily)
        del daily
        gc.collect()

        balance_cols = ["cell_lat", "cell_lon", "model", "scenario", "period", "month", "P", "PET"]
        catchment_balance = pet.catchment_water_balance(
            cell_balance[balance_cols],
            weights_country,
        )
        catchment_balance["country"] = country
        catchment_frames.append(catchment_balance)
        del cell_balance
        gc.collect()

    water_balance_catchment_w5e5 = pd.concat(catchment_frames, ignore_index=True)
    out_wb = processed_dir / "water_balance_catchment_w5e5.parquet"
    water_balance_catchment_w5e5.to_parquet(out_wb, index=False)
    print(f"\nwrote {out_wb}: {len(water_balance_catchment_w5e5)} rows")

    # --- SPEI-12: full history (1984-2019) fit on baseline-window subset only ---
    # `period` was set to "baseline" above for every row so `monthly_water_balance`/
    # `catchment_water_balance` group correctly; the 1985-2014 restriction Rule 4
    # requires is applied here explicitly before fitting, then the fit is applied
    # to every row (1984-2019) via `standardize`, exactly like `fit_baseline_single`'s
    # documented contract (COMANDO 18-G).
    group_cols = ["id", "model"]
    d_cols = [*group_cols, "scenario", "period", "month", "D"]
    wb = water_balance_catchment_w5e5.copy()
    in_baseline = wb["month"].dt.year.between(spei.BASELINE_START_YEAR, spei.BASELINE_END_YEAR)
    wb["period"] = in_baseline.map({True: "baseline", False: "observed"})

    acc12 = spei.accumulate(wb[d_cols], window=12, value_col="D")
    baseline_acc = acc12[
        (acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    fitted = spei.fit_baseline_single(
        baseline_acc, "D_acc12", group_cols, spei.fit_spei_distribution
    )
    out = spei.standardize(
        acc12, "D_acc12", fitted, group_cols, clip_bound=3.0, out_col="SPEI_12"
    )

    id_country = water_balance_catchment_w5e5[["id", "country"]].drop_duplicates()
    out = out.merge(id_country, on="id", how="left")

    out_spei = processed_dir / "spei_w5e5.parquet"
    out.to_parquet(out_spei, index=False)
    print(f"wrote {out_spei}: {len(out)} rows")

    fail = spei.fit_failure_summary(fitted, group_cols)
    n_failed = int((fail["n_months_failed"] > 0).sum())
    print(f"fit failures: {n_failed}/{len(fail)} (id, model) series with >=1 failed month")
    print(f"SPEI_12 NaN rows: {int(out['SPEI_12'].isna().sum())}/{len(out)}")
    print(f"first month={out['month'].min()}, last month={out['month'].max()}")


if __name__ == "__main__":
    main()
