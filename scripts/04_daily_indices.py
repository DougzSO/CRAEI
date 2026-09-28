"""COMANDO 15: daily heat and precipitation indices (Spec §3 Step 4).

For each model x scenario x country, loads the cropped tasmax/pr files
(COMANDO 11/12), selects only the unique 0.5deg cells actually used by a
plant (COMANDO 14's plant_cell.parquet), and computes TX35/TX40 (annual),
N35 (monthly), wet-day P95 baseline threshold + exceedance frequency, and
Rx5day (annual). Writes `indices_daily.parquet`.

This machine has ~6 GB RAM (not the 32 GB the Spec's Step 4 time estimate
assumes), and a country's daily tasmax/pr at its full ~1,000-cell set is
tens of millions of rows once exploded to a long frame. Each (model,
scenario, variable) daily frame is therefore built, reduced to its (much
smaller) annual/monthly aggregate immediately, and freed (`del` + a
targeted `gc.collect()`) before the next one -- peak memory is one
daily frame, not the whole country/model/scenario cross product.
"""

import gc
from pathlib import Path

import pandas as pd
import xarray as xr

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_datasets, load_params, load_paths
from craei.hazards import heat, precip
from craei.hazards.pet import KELVIN_OFFSET_C

PR_FLUX_TO_MM_PER_DAY = 86400.0  # kg m-2 s-1 -> mm d-1


def unique_cells_by_country(processed_dir: Path) -> dict[str, pd.DataFrame]:
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country"])
    plant_cell = pd.read_parquet(
        processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    merged = plants.merge(plant_cell, on="plant_uid")
    cells = merged[["country", "cell_lat", "cell_lon"]].drop_duplicates()
    return {
        country: g[["cell_lat", "cell_lon"]].reset_index(drop=True)
        for country, g in cells.groupby("country")
    }


def load_cell_series(
    nc_path: Path, cells: pd.DataFrame, value_col: str, scenario: str, datasets_cfg: dict
) -> pd.DataFrame:
    """Point-select `cells` from `nc_path`, filtered to the scenario's study period.

    Returns only (date, cell_lat, cell_lon, value_col) -- no model/scenario/
    period columns, so this frame stays as small as the raw grid selection
    itself; the caller attaches those constant labels after aggregating.
    """
    period_key = "baseline" if scenario == "historical" else "future"
    span = datasets_cfg["periods"][period_key]

    with xr.open_dataset(nc_path) as ds:
        variable = next(iter(ds.data_vars))
        lat_sel = xr.DataArray(cells["cell_lat"].to_numpy(), dims="cell")
        lon_sel = xr.DataArray(cells["cell_lon"].to_numpy(), dims="cell")
        time_ok = (ds["time.year"] >= span["start"]) & (ds["time.year"] <= span["end"])
        selected = (
            ds[variable]
            .sel(lat=lat_sel, lon=lon_sel, method="nearest")
            .isel(time=time_ok.values)
            .load()
        )

    df = selected.to_dataframe(name=value_col).reset_index()
    df["cell_lat"] = cells["cell_lat"].to_numpy()[df["cell"].to_numpy()]
    df["cell_lon"] = cells["cell_lon"].to_numpy()[df["cell"].to_numpy()]
    return df[["time", "cell_lat", "cell_lon", value_col]].rename(columns={"time": "date"})


def with_labels(df: pd.DataFrame, model: str, scenario: str, period: str) -> pd.DataFrame:
    out = df.copy()
    out["model"], out["scenario"], out["period"] = model, scenario, period
    return out


def melt_indices(df: pd.DataFrame, index_name: str, has_month: bool = False, has_year: bool = True) -> pd.DataFrame:
    out = df.copy()
    out["index"] = index_name
    if has_month:
        out["year"] = out["month"].values.astype("datetime64[Y]").astype(int) + 1970
    else:
        out["month"] = pd.NaT
    if not has_year:
        out["year"] = pd.NA  # period-level index (e.g. pooled P95 exceedance frequency), not annual
    return out[["cell_lat", "cell_lon", "model", "scenario", "period", "index", "year", "month", "value"]]


def tasmax_daily(
    nc_path: Path, cells: pd.DataFrame, scenario: str, datasets_cfg: dict
) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "tasmax_c", scenario, datasets_cfg)
    df["tasmax_c"] -= KELVIN_OFFSET_C
    return df


def pr_daily(nc_path: Path, cells: pd.DataFrame, scenario: str, datasets_cfg: dict) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "pr_mm", scenario, datasets_cfg)
    df["pr_mm"] *= PR_FLUX_TO_MM_PER_DAY
    return df


def main() -> None:
    paths = load_paths()
    params = load_params()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])
    climate_dir = raw_dir / "climate" / "isimip3b"

    tx35_c = params["heat_tx35_threshold_c"]["value"]
    tx40_c = params["heat_tx40_threshold_c"]["value"]
    p95_pct = params["wet_day_p95_percentile"]["value"]

    cells_by_country = unique_cells_by_country(processed_dir)

    all_frames = []
    for country in STUDY_COUNTRIES:
        cells = cells_by_country[country]
        print(f"{country}: {len(cells)} unique cells")

        for model in datasets_cfg["models"]:
            # Pass 1: baseline-only pr, to get each cell's wet-day P95 threshold.
            hist_pr_path = climate_dir / model / "historical" / "pr" / f"{model}_historical_pr_{country}.nc"
            hist_pr = pr_daily(hist_pr_path, cells, "historical", datasets_cfg)
            hist_pr["period"] = "baseline"
            p95 = precip.wet_day_p95(hist_pr, p95_pct)
            del hist_pr
            gc.collect()

            for scenario in datasets_cfg["scenarios"]:
                period = "baseline" if scenario == "historical" else "future"

                tasmax_path = climate_dir / model / scenario / "tasmax" / f"{model}_{scenario}_tasmax_{country}.nc"
                tasmax = tasmax_daily(tasmax_path, cells, scenario, datasets_cfg)
                tx35 = with_labels(heat.annual_hot_day_counts(tasmax, tx35_c), model, scenario, period)
                tx40 = with_labels(heat.annual_hot_day_counts(tasmax, tx40_c), model, scenario, period)
                n35 = with_labels(heat.monthly_hot_day_counts(tasmax, tx35_c), model, scenario, period)
                del tasmax
                gc.collect()

                pr = pr_daily(climate_dir / model / scenario / "pr" / f"{model}_{scenario}_pr_{country}.nc", cells, scenario, datasets_cfg)
                exceed = precip.exceedance_frequency(pr, p95).rename(columns={"exceedance_frequency": "value"})
                exceed = with_labels(exceed, model, scenario, period)
                rx5day = with_labels(precip.annual_rx5day(pr), model, scenario, period)
                del pr
                gc.collect()

                all_frames.append(melt_indices(tx35, "tx35"))
                all_frames.append(melt_indices(tx40, "tx40"))
                all_frames.append(melt_indices(n35, "n35", has_month=True))
                all_frames.append(melt_indices(exceed, "p95_exceedance_frequency", has_year=False))
                all_frames.append(melt_indices(rx5day, "rx5day"))

                print(f"{country}/{model}/{scenario}: done")

    indices = pd.concat(all_frames, ignore_index=True)
    out_path = processed_dir / "indices_daily.parquet"
    indices.to_parquet(out_path, index=False)
    print(f"wrote {out_path}: {len(indices)} rows")

    baseline_exceed = indices[
        (indices["index"] == "p95_exceedance_frequency") & (indices["period"] == "baseline")
    ]
    per_cell_model = baseline_exceed.groupby(["cell_lat", "cell_lon", "model"])["value"].mean()
    print(f"baseline P95 exceedance frequency: min={per_cell_model.min():.4f} max={per_cell_model.max():.4f}")
    ok = per_cell_model.between(0.045, 0.055).all()
    print(f"all cells/models within [4.5%, 5.5%]: {ok}")


if __name__ == "__main__":
    main()
