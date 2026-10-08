"""COMANDO 17/18-G: SPEI-12, SPEI-3 and SPI-12 via per-series temporal
fitting (Spec §1.4 H2, §3 Step 6; docs/DECISIONS.md D54/D55).

SPEI-12 (hydro catchment and thermal cell) is fit once per (id, model)
series over all 360 baseline values, no calendar-month stratification
(`spei.fit_baseline_single`) -- a 12-month accumulation already removes
essentially all seasonality (COMANDO 18-F Action 5: mean standardized SPEI
by calendar month -0.003 to +0.009). SPEI-3 (run-of-river only) is fit per
calendar month using a +/-1 adjacent-month window across all 30 years
(`spei.fit_baseline_windowed`, k=1, n=90) -- measured failure rate 7.4% vs.
14.4% for the unwindowed n=30 fit, k=2 is worse (9.3%, non-monotonic,
mixes seasons). Both use `spei.fit_spei_distribution`'s PWM + Pearson III
MLE fallback (D55: the F_D gap between the two estimators at n=360, on
series where both converge, has median 0.000-0.833pp across every country
and bucket -- well under the 1pp stop threshold, so the fallback is kept,
not replaced). Neither method mixes different (id, model) series -- unlike
the reverted regional pool (D51/D52), each series is still standardized
against its own climatology, not a regional peer group.

SPI-12 is unaffected (gamma on P alone, per (id, model), original n=30
calendar-month fit -- out of this command's scope, D45's original
"unaffected" note carries over).

Processed one country/model at a time with explicit memory release, per
COMANDOS 15/16 (`docs/DECISIONS.md` D41).
"""

import gc
import time
from pathlib import Path

import pandas as pd

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.loading import cells_with_catchments_by_country

SEVERE_THRESHOLD = None  # set from params.yaml in main()
CLIP_BOUND = None  # set from params.yaml in main()
TRUNCATED_CELLS_WEIGHT_FLAG_THRESHOLD = 0.2  # Action 4: named-basin cutoff (spec-stated value)
SPEI3_WINDOW_K = 1  # D54: k=1 (n=90) adopted, k=2 measured worse (COMANDO 18-F)

# docs/LIMITATIONS.md L16, COMANDO 17-C Action 6: Nimoo Bazgo hydroelectric
# plant (India, 45 MW, basin_id 4060623190) has 100% of its catchment weight
# on a single PET-truncated glacial cell (COMANDO 16) -- its SPEI-12 would be
# entirely constructed from a truncation-artifact water balance, not a real
# one. Excluded from H2 entirely (not imputed); the plant itself stays in
# plants.parquet (only H2/spei.parquet drops it).
H2_EXCLUDED_PLANT_IDS = {"5131763b8e53f91a7783faeea1fb15095453fd967630297cac52261097daf54c"}


def _fit_and_standardize(acc, acc_col, group_cols, fit_fn, out_col, clip_bound, fit_kind="calendar"):
    baseline_acc = acc[
        (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    if fit_kind == "single":
        fitted = spei.fit_baseline_single(baseline_acc, acc_col, group_cols, fit_fn)
    elif fit_kind == "windowed":
        fitted = spei.fit_baseline_windowed(baseline_acc, acc_col, group_cols, SPEI3_WINDOW_K, fit_fn)
    else:
        fitted = spei.fit_baseline(baseline_acc, acc_col, group_cols, fit_fn)
    out = spei.standardize(acc, acc_col, fitted, group_cols, clip_bound, out_col)
    failures = spei.fit_failure_summary(fitted, group_cols)
    return out, failures


def process_hydro(water_balance_catchment: pd.DataFrame, run_of_river_ids: set[str], clip_bound: float):
    group_cols = ["id", "model"]
    d_cols = [*group_cols, "scenario", "period", "month", "D"]

    acc12 = spei.accumulate(water_balance_catchment[d_cols], window=12, value_col="D")
    spei12, fail12 = _fit_and_standardize(
        acc12, "D_acc12", group_cols, spei.fit_spei_distribution, "SPEI_12", clip_bound, fit_kind="single"
    )

    acc_p12 = spei.accumulate(
        water_balance_catchment.rename(columns={"P": "P_for_acc"})[
            [*group_cols, "scenario", "period", "month", "P_for_acc"]
        ],
        window=12,
        value_col="P_for_acc",
    )
    spi12, _ = _fit_and_standardize(
        acc_p12, "P_for_acc_acc12", group_cols, spei.gamma_fit_fn, "SPI_12", clip_bound, fit_kind="single"
    )

    ror = water_balance_catchment.loc[water_balance_catchment["id"].isin(run_of_river_ids), d_cols]
    acc3 = spei.accumulate(ror, window=3, value_col="D")
    spei3, fail3 = _fit_and_standardize(
        acc3, "D_acc3", group_cols, spei.fit_spei_distribution, "SPEI_3", clip_bound, fit_kind="windowed"
    )

    out = spei12[["id", "model", "scenario", "period", "month", "SPEI_12", "distribution"]].merge(
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
        acc12, "D_acc12", group_cols, spei.fit_spei_distribution, "SPEI_12", clip_bound, fit_kind="single"
    )

    acc_p12 = spei.accumulate(
        d.rename(columns={"P": "P_for_acc"})[[*group_cols, "scenario", "period", "month", "P_for_acc"]],
        window=12,
        value_col="P_for_acc",
    )
    spi12, _ = _fit_and_standardize(
        acc_p12, "P_for_acc_acc12", group_cols, spei.gamma_fit_fn, "SPI_12", clip_bound, fit_kind="single"
    )

    out = spei12[["id", "model", "scenario", "period", "month", "SPEI_12", "distribution"]].merge(
        spi12[["id", "model", "scenario", "period", "month", "SPI_12"]],
        on=["id", "model", "scenario", "period", "month"],
        how="left",
    )
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
    n_hydro_before_exclusion = len(hydro_plants)
    hydro_plants = hydro_plants[~hydro_plants["plant_uid"].isin(H2_EXCLUDED_PLANT_IDS)]
    print(
        f"hydro plants: {n_hydro_before_exclusion}, {len(H2_EXCLUDED_PLANT_IDS)} excluded from H2 "
        f"(docs/LIMITATIONS.md L16), {len(hydro_plants)} processed"
    )
    run_of_river_ids = set(hydro_plants.loc[hydro_plants["hydro_type"] == "run-of-river", "plant_uid"])
    print(f"run-of-river (SPEI-3 also reported): {len(run_of_river_ids)}")

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
    t_start = time.perf_counter()

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

    elapsed_s = time.perf_counter() - t_start

    out = pd.concat([hydro_out, thermal_out], ignore_index=True)
    out_path = processed_dir / "spei.parquet"
    out.to_parquet(out_path, index=False)
    print(f"\nwrote {out_path}: {len(out)} rows")
    print(f"processing wall time (fit+standardize loop, this run): {elapsed_s:.1f}s")

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
            f"{truncated_cells_path} not found -- rerun scripts/archive/audit_tx_tn_and_pet_truncation.py "
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

    # COMANDO 18-G: per-series temporal fitting (D54/D55) -- final failure
    # rate, distribution split, F_D.
    print("\n=== COMANDO 18-G: per-series temporal fitting results ===")
    spei12_all = out["distribution"].notna() | out["SPEI_12"].notna()
    n_spei12_total = int(spei12_all.sum())
    n_spei12_nan = int(out["SPEI_12"].isna().sum())
    print(
        f"SPEI-12 (hydro catchment + thermal cell combined) final failure rate: "
        f"{n_spei12_nan}/{n_spei12_total} = {n_spei12_nan / n_spei12_total:.4%} "
        f"(both PWM and Pearson III failed, or accumulation itself was NaN)"
    )
    dist_counts = out["distribution"].value_counts(dropna=False)
    print("distribution used, SPEI-12 rows with a successful fit:")
    print((dist_counts / dist_counts.sum()).to_string())

    baseline_all = out[out["period"] == "baseline"].dropna(subset=["SPEI_12"])
    fd_all = spei.severe_drought_frequency(
        baseline_all, "SPEI_12", severe_threshold, group_cols=["id", "model"]
    )
    print(
        f"F_D baseline (SPEI-12 <= {severe_threshold}), hydro+thermal combined, "
        f"mean over (id, model) groups: {fd_all['F_D'].mean():.4%}"
    )


if __name__ == "__main__":
    main()
