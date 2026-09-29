"""COMANDO 17: SPEI-12, SPEI-3 and SPI-12 (Spec §1.4 H2, §3 Step 6).

Reads COMANDO 16's monthly water balance (`water_balance_catchment.parquet`
for hydro at catchment scale, `water_balance_cell.parquet` for
water-dependent thermal at cell scale). For each group (plant/cell x model),
D = P - PET is 12-month accumulated (also 3-month for run-of-river hydro
plants); the log-logistic distribution is fit per calendar month on
1985-2014 baseline data only and applied to both periods (SPEI). SPI-12
does the same with a gamma fit on P alone. Processed one country/model at a
time with explicit memory release, per COMANDOS 15/16 (`docs/DECISIONS.md`
D41) -- required here too (COMANDO 17 Action 1), not optional: an earlier
version of this script loaded and processed the full water-balance tables in
one call and `MemoryError`'d on this ~6 GB machine (see `craei.rolling` and
`docs/DECISIONS.md` for the accompanying `accumulate()` vectorization fix;
this per-(model, country) chunking is the second, independent half of that
fix -- it bounds each `fit_baseline`/`standardize` call's group count even
though those no longer concat per group).  Each `model` is read from parquet
with a predicate-pushdown filter (`filters=[("model", "=", model)]`), so a
chunk's data is never resident for other models; each `country` subsets
in-memory via a small id/cell membership set built once from `plants.parquet`
and `cells_with_catchments_by_country`, not a further parquet read.
"""

import gc
from pathlib import Path

import pandas as pd
from scipy import stats

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.loading import cells_with_catchments_by_country

SEVERE_THRESHOLD = None  # set from params.yaml in main()
CLIP_BOUND = None  # set from params.yaml in main()
TRUNCATED_CELLS_WEIGHT_FLAG_THRESHOLD = 0.2  # Action 4: named-basin cutoff (spec-stated value)


def _fit_and_standardize(acc, acc_col, group_cols, fit_fn, dist, out_col, clip_bound):
    baseline_acc = acc[
        (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    fitted = spei.fit_baseline(baseline_acc, acc_col, group_cols, fit_fn)
    out = spei.standardize(acc, acc_col, fitted, group_cols, dist, clip_bound, out_col)
    failures = spei.fit_failure_summary(fitted, group_cols)
    return out, failures


def process_hydro(water_balance_catchment: pd.DataFrame, run_of_river_ids: set[str], clip_bound: float):
    group_cols = ["id", "model"]
    d_cols = [*group_cols, "scenario", "period", "month", "D"]

    # `accumulate` infers its grouping columns as "every column but month and
    # value_col" -- passing P/PET along unselected would make every row its
    # own group (they vary month to month) and silently NaN every
    # accumulation (COMANDO 17 follow-up: caught only after fixing the
    # memory crash that had masked it, since the run never got this far
    # before). Each `accumulate` call below is given exactly its grouping
    # columns plus the one value column it accumulates.
    acc12 = spei.accumulate(water_balance_catchment[d_cols], window=12, value_col="D")
    spei12, fail12 = _fit_and_standardize(
        acc12, "D_acc12", group_cols, spei.loglogistic_fit_fn, stats.fisk, "SPEI_12", clip_bound
    )

    acc_p12 = spei.accumulate(
        water_balance_catchment.rename(columns={"P": "P_for_acc"})[
            [*group_cols, "scenario", "period", "month", "P_for_acc"]
        ],
        window=12,
        value_col="P_for_acc",
    )
    spi12, _ = _fit_and_standardize(
        acc_p12, "P_for_acc_acc12", group_cols, spei.gamma_fit_fn, stats.gamma, "SPI_12", clip_bound
    )

    ror = water_balance_catchment.loc[water_balance_catchment["id"].isin(run_of_river_ids), d_cols]
    acc3 = spei.accumulate(ror, window=3, value_col="D")
    spei3, fail3 = _fit_and_standardize(
        acc3, "D_acc3", group_cols, spei.loglogistic_fit_fn, stats.fisk, "SPEI_3", clip_bound
    )

    out = spei12[["id", "model", "scenario", "period", "month", "SPEI_12"]].merge(
        spi12[["id", "model", "scenario", "period", "month", "SPI_12"]],
        on=["id", "model", "scenario", "period", "month"],
        how="left",
    )
    out = out.merge(
        spei3[["id", "model", "scenario", "period", "month", "SPEI_3"]],
        on=["id", "model", "scenario", "period", "month"],
        how="left",
    )
    out["scale"] = "catchment"
    return out, fail12, fail3


def process_thermal_cell(water_balance_cell: pd.DataFrame, clip_bound: float):
    d = water_balance_cell.copy()
    d["id"] = d["cell_lat"].astype(str) + "_" + d["cell_lon"].astype(str)
    group_cols = ["id", "model"]

    acc12 = spei.accumulate(d[[*group_cols, "scenario", "period", "month", "D"]], window=12, value_col="D")
    spei12, fail12 = _fit_and_standardize(
        acc12, "D_acc12", group_cols, spei.loglogistic_fit_fn, stats.fisk, "SPEI_12", clip_bound
    )
    out = spei12[["id", "model", "scenario", "period", "month", "SPEI_12"]].copy()
    out["SPI_12"] = pd.NA
    out["SPEI_3"] = pd.NA
    out["scale"] = "cell"
    return out, fail12


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])

    clip_bound = float(params["spei_clip_bound"]["value"])
    severe_threshold = float(params["drought_spei_threshold"]["value"])

    plants = pd.read_parquet(
        processed_dir / "plants.parquet",
        columns=["plant_uid", "country", "tech_class", "hydro_type"],
    )
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    run_of_river_ids = set(hydro_plants.loc[hydro_plants["hydro_type"] == "run-of-river", "plant_uid"])
    print(f"hydro plants: {len(hydro_plants)}; run-of-river (SPEI-3 also reported): {len(run_of_river_ids)}")

    hydro_ids_by_country = {
        country: set(hydro_plants.loc[hydro_plants["country"] == country, "plant_uid"])
        for country in STUDY_COUNTRIES
    }
    cells_by_country = {
        country: set(zip(cells["cell_lat"], cells["cell_lon"]))
        for country, cells in cells_with_catchments_by_country(processed_dir).items()
    }

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())

    hydro_out_parts, hydro_fail12_parts, hydro_fail3_parts = [], [], []
    thermal_out_parts, thermal_fail12_parts = [], []

    for model in models:
        catchment_model = pd.read_parquet(catchment_path, filters=[("model", "=", model)])
        cell_model = pd.read_parquet(cell_path, filters=[("model", "=", model)])

        for country in STUDY_COUNTRIES:
            country_ids = hydro_ids_by_country[country]
            catchment_chunk = catchment_model[catchment_model["id"].isin(country_ids)]
            if len(catchment_chunk):
                h_out, h_fail12, h_fail3 = process_hydro(
                    catchment_chunk, run_of_river_ids, clip_bound
                )
                hydro_out_parts.append(h_out)
                hydro_fail12_parts.append(h_fail12)
                hydro_fail3_parts.append(h_fail3)
            del catchment_chunk

            cell_mask = list(zip(cell_model["cell_lat"], cell_model["cell_lon"]))
            cell_mask = pd.Series(cell_mask, index=cell_model.index).isin(cells_by_country[country])
            cell_chunk = cell_model[cell_mask]
            if len(cell_chunk):
                t_out, t_fail12 = process_thermal_cell(cell_chunk, clip_bound)
                thermal_out_parts.append(t_out)
                thermal_fail12_parts.append(t_fail12)
            del cell_chunk

            print(f"{model}/{country}: done")

        del catchment_model, cell_model
        gc.collect()

    hydro_out = pd.concat(hydro_out_parts, ignore_index=True)
    hydro_fail12 = pd.concat(hydro_fail12_parts, ignore_index=True)
    hydro_fail3 = pd.concat(hydro_fail3_parts, ignore_index=True)
    thermal_out = pd.concat(thermal_out_parts, ignore_index=True)
    thermal_fail12 = pd.concat(thermal_fail12_parts, ignore_index=True)
    del hydro_out_parts, hydro_fail12_parts, hydro_fail3_parts
    del thermal_out_parts, thermal_fail12_parts
    gc.collect()

    out = pd.concat([hydro_out, thermal_out], ignore_index=True)
    out_path = processed_dir / "spei.parquet"
    out.to_parquet(out_path, index=False)
    print(f"\nwrote {out_path}: {len(out)} rows")

    # Action 3: F_D baseline distribution per model (hydro catchment scale).
    baseline = hydro_out[hydro_out["period"] == "baseline"]
    fd = spei.severe_drought_frequency(baseline, "SPEI_12", severe_threshold, group_cols=["id", "model"])
    print(f"\n=== Action 3: F_D baseline distribution (SPEI-12 <= {severe_threshold}) per model ===")
    print(
        fd.groupby("model")["F_D"].describe(percentiles=[0.05, 0.5, 0.95])[
            ["50%", "5%", "95%"]
        ].rename(columns={"50%": "median", "5%": "P5", "95%": "P95"})
    )

    # Action 4: weight of truncated-PET cells (51 India cells, COMANDO 16) per basin.
    weights = pd.read_parquet(processed_dir / "catchment_weights.parquet")
    truncated_cells_path = processed_dir / "truncated_pet_cells.parquet"
    print("\n=== Action 4: truncated-PET-cell weight per basin ===")
    if truncated_cells_path.exists():
        truncated_cells = pd.read_parquet(truncated_cells_path)
        hit = weights.merge(truncated_cells[["cell_lat", "cell_lon"]].drop_duplicates(), on=["cell_lat", "cell_lon"])
        per_plant = hit.groupby("plant_uid", as_index=False)["weight"].sum()
        per_plant = per_plant.merge(plants[["plant_uid", "country"]], on="plant_uid")
        print(f"max weight sum: {per_plant['weight'].max():.4f}; median: {per_plant['weight'].median():.4f}")
        flagged = per_plant[per_plant["weight"] > TRUNCATED_CELLS_WEIGHT_FLAG_THRESHOLD]
        print(f"plants above {TRUNCATED_CELLS_WEIGHT_FLAG_THRESHOLD}: {len(flagged)}")
        print(flagged.to_string(index=False))
    else:
        print(
            f"{truncated_cells_path} not found -- rerun scripts/audit_tx_tn_and_pet_truncation.py "
            "with its truncated-cell list persisted to this path before this action can be reported."
        )

    # Action 5: fit failures.
    print("\n=== Action 5: baseline fit failures ===")
    for label, fail in (("SPEI-12 (hydro catchment)", hydro_fail12), ("SPEI-3 (run-of-river)", hydro_fail3),
                         ("SPEI-12 (thermal cell)", thermal_fail12)):
        n_failed_groups = int((fail["n_months_failed"] > 0).sum())
        total_failed_months = int(fail["n_months_failed"].sum())
        print(
            f"{label}: {n_failed_groups}/{len(fail)} groups with >=1 failed calendar-month fit, "
            f"{total_failed_months} total failed (group, calendar-month) fits -- left as NaN, not substituted"
        )

    # Action 6: first valid date per period.
    print("\n=== Action 6: first valid SPEI-12 date per period (hydro catchment) ===")
    for period, g in hydro_out.dropna(subset=["SPEI_12"]).groupby("period"):
        print(f"period={period}: first month={g['month'].min()}, last month={g['month'].max()}")


if __name__ == "__main__":
    main()
