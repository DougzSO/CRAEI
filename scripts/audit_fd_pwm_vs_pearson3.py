"""COMANDO 18-C Action 1/2: is the PWM-vs-Pearson-III F_D gap (L17) a method
artifact or a real climate difference?

For (id, model) baseline series where PWM converges in all 12 calendar
months (`spei.parquet`'s stored SPEI_12/SPEI_3, `distribution ==
"loglogistic"` throughout), refits Pearson III on the SAME raw D
accumulation and compares F_D pairwise on the identical baseline sample --
isolating the estimator's own effect from any real difference in which
series happen to need the fallback. Read-only: never writes to
`spei.parquet` or any other production output (CLAUDE.md Rule 10 -- this is
an audit script, kept separate from the production pipeline).

A fixed-seed stratified sample per (bucket, country) is used (up to
`SAMPLE_PER_STRATUM` series), not the full ~173,000-series PWM-converged
population: refitting Pearson III at production scale was measured at
150-735x PWM's cost (COMANDO 17-E), making a full refit here impractical.
Every reported number states its sample size.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei

SAMPLE_PER_STRATUM = 150
SEED = 42


def _pearson3_fit_fn(values: np.ndarray):
    values = values[np.isfinite(values)]
    if len(values) < spei.MIN_FIT_SAMPLES:
        return None, None
    params, status = spei._fit_pearson3_mle(values)
    return (params, "pearson3") if status == "success" else (None, None)


def _fully_pwm_groups(spei_df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """(id, model) pairs whose baseline `value_col` is 100% loglogistic, non-NaN."""
    baseline = spei_df[(spei_df["period"] == "baseline") & spei_df[value_col].notna()]
    g = baseline.groupby(["id", "model"], as_index=False).agg(
        n=(value_col, "size"), n_loglogistic=("distribution", lambda s: (s == "loglogistic").sum())
    )
    return g[g["n"] == g["n_loglogistic"]][["id", "model"]]


def _sample_strata(candidates: pd.DataFrame, id_country: pd.DataFrame, bucket_name: str) -> pd.DataFrame:
    c = candidates.merge(id_country, on="id", how="inner")
    c["bucket"] = bucket_name
    rng = np.random.default_rng(SEED)
    parts = []
    for country, g in c.groupby("country"):
        n = min(SAMPLE_PER_STRATUM, len(g))
        idx = rng.choice(g.index.to_numpy(), size=n, replace=False)
        parts.append(g.loc[idx])
    return pd.concat(parts, ignore_index=True) if parts else c.iloc[0:0]


def _refit_and_compare(
    sample: pd.DataFrame,
    wb_path: Path,
    window: int,
    value_source_col: str,
    id_col_is_cell: bool,
    clip_bound: float,
    spei_col: str,
) -> pd.DataFrame:
    """For each sampled (id, model), refit Pearson III on its own baseline D
    accumulation and compute F_D under both PWM (already in spei.parquet)
    and the fresh Pearson III refit, plus the raw baseline sample's skew.
    """
    results = []
    models = sample["model"].unique()
    for model in models:
        model_sample = sample[sample["model"] == model]
        ids = set(model_sample["id"])
        wb = pd.read_parquet(wb_path, filters=[("model", "=", model)])
        if id_col_is_cell:
            wb = wb.copy()
            wb["id"] = wb["cell_lat"].astype(str) + "_" + wb["cell_lon"].astype(str)
        wb = wb[wb["id"].isin(ids)]
        if not len(wb):
            del wb
            continue

        group_cols = ["id", "model"]
        d_cols = [*group_cols, "scenario", "period", "month", value_source_col]
        acc = spei.accumulate(wb[d_cols], window=window, value_col=value_source_col)
        acc_col = f"{value_source_col}_acc{window}"
        baseline_acc = acc[
            (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
        ]

        fitted_p3 = spei.fit_baseline(baseline_acc, acc_col, group_cols, _pearson3_fit_fn)
        std_p3 = spei.standardize(baseline_acc, acc_col, fitted_p3, group_cols, clip_bound, "SPEI_P3")
        fd_p3 = spei.severe_drought_frequency(std_p3, "SPEI_P3", THRESHOLD, group_cols)
        fd_p3 = fd_p3.rename(columns={"F_D": "f_d_pearson3", "n_months": "n_months_p3"})

        skew = baseline_acc.dropna(subset=[acc_col]).groupby(group_cols, as_index=False).agg(
            skew=(acc_col, lambda s: float(sps.skew(s)))
        )

        merged = fd_p3.merge(skew, on=group_cols, how="left")
        merged["model"] = model
        results.append(merged[["id", "model", "f_d_pearson3", "n_months_p3", "skew"]])
        del wb, acc, baseline_acc, fitted_p3, std_p3
        gc.collect()

    if not results:
        return pd.DataFrame(columns=["id", "model", "f_d_pearson3", "n_months_p3", "skew"])
    return pd.concat(results, ignore_index=True)


def _pwm_fd(spei_df: pd.DataFrame, sample: pd.DataFrame, spei_col: str) -> pd.DataFrame:
    baseline = spei_df[
        (spei_df["period"] == "baseline")
        & spei_df["id"].isin(set(sample["id"]))
        & spei_df["model"].isin(set(sample["model"]))
    ]
    return spei.severe_drought_frequency(baseline, spei_col, THRESHOLD, ["id", "model"]).rename(
        columns={"F_D": "f_d_pwm", "n_months": "n_months_pwm"}
    )


def _report_gap(df: pd.DataFrame, label: str) -> None:
    print(f"\n--- {label} ---")
    if not len(df):
        print("  no sampled series")
        return
    df = df.copy()
    df["gap"] = df["f_d_pearson3"] - df["f_d_pwm"]
    for (bucket, country), g in df.groupby(["bucket", "country"]):
        pct = g["gap"] * 100  # percentage points
        pos = (pct > 0).sum()
        neg = (pct < 0).sum()
        sign = "pearson3 > pwm" if pos > neg else ("pwm > pearson3" if neg > pos else "tied")
        print(
            f"{bucket:24s} {country}: n={len(g):4d}  median={pct.median():+.3f}pp  "
            f"P5={pct.quantile(0.05):+.3f}pp  P95={pct.quantile(0.95):+.3f}pp  "
            f"sign: {pos} pos / {neg} neg / {len(g) - pos - neg} zero -> {sign}"
        )


def main() -> None:
    global THRESHOLD
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    THRESHOLD = float(params["drought_spei_threshold"]["value"])
    clip_bound = float(params["spei_clip_bound"]["value"])

    plants = pd.read_parquet(
        processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class", "hydro_type"]
    )
    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"])
    hydro = plants[plants["tech_class"] == "hydro"]
    thermal_water = plants[plants["tech_class"] == "thermal_water_dependent"]

    hydro_id_country = hydro[["plant_uid", "country"]].rename(columns={"plant_uid": "id"})
    ror_ids = set(hydro.loc[hydro["hydro_type"] == "run-of-river", "plant_uid"])

    tw_cell = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
    tw_cell["id"] = tw_cell["cell_lat"].astype(str) + "_" + tw_cell["cell_lon"].astype(str)
    cell_id_country = tw_cell[["id", "country"]].drop_duplicates(subset=["id"])

    # Read each scale separately via predicate pushdown, minimal columns,
    # baseline period only -- the full 10-column/28M-row table crashed this
    # 6 GB machine when materialized whole (CLAUDE.md Rule 11); this stays
    # well under that by never holding "catchment" and "cell" at once.
    spei_cols = ["id", "model", "period", "SPEI_12", "SPEI_3", "distribution"]
    catchment = pd.read_parquet(
        processed_dir / "spei.parquet", columns=spei_cols, filters=[("scale", "=", "catchment")]
    )
    full_res = _fully_pwm_groups(catchment[catchment["id"].isin(set(hydro["plant_uid"]) - ror_ids)], "SPEI_12")
    full_ror12 = _fully_pwm_groups(catchment[catchment["id"].isin(ror_ids)], "SPEI_12")
    full_ror3 = _fully_pwm_groups(catchment[catchment["id"].isin(ror_ids)], "SPEI_3")
    del catchment
    gc.collect()

    cell = pd.read_parquet(
        processed_dir / "spei.parquet", columns=spei_cols, filters=[("scale", "=", "cell")]
    )
    full_thermal = _fully_pwm_groups(cell, "SPEI_12")
    del cell
    gc.collect()

    print("Fully PWM-converged (id, model) population sizes (all 12 calendar months loglogistic):")
    print(f"  hydro_reservoir SPEI-12: {len(full_res)}")
    print(f"  hydro_run_of_river SPEI-12: {len(full_ror12)}")
    print(f"  hydro_run_of_river SPEI-3: {len(full_ror3)}")
    print(f"  thermal_water_dependent SPEI-12: {len(full_thermal)}")

    sample_res = _sample_strata(full_res, hydro_id_country, "hydro_reservoir")
    sample_ror12 = _sample_strata(full_ror12, hydro_id_country, "hydro_run_of_river")
    sample_ror3 = _sample_strata(full_ror3, hydro_id_country, "hydro_run_of_river_spei3")
    sample_thermal = _sample_strata(full_thermal, cell_id_country, "thermal_water_dependent")

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"

    p3_res = _refit_and_compare(sample_res, catchment_path, 12, "D", False, clip_bound, "SPEI_12")
    p3_ror12 = _refit_and_compare(sample_ror12, catchment_path, 12, "D", False, clip_bound, "SPEI_12")
    p3_ror3 = _refit_and_compare(sample_ror3, catchment_path, 3, "D", False, clip_bound, "SPEI_3")
    p3_thermal = _refit_and_compare(sample_thermal, cell_path, 12, "D", True, clip_bound, "SPEI_12")

    combined = []
    # Reload spei.parquet once more for PWM-side F_D, filtered to only the
    # sampled ids (a few hundred, not the full 28M-row table).
    sampled_ids = list(
        set(sample_res["id"]) | set(sample_ror12["id"]) | set(sample_thermal["id"])
    )
    spei_df2 = pd.read_parquet(
        processed_dir / "spei.parquet",
        columns=["id", "model", "period", "SPEI_12", "SPEI_3"],
        filters=[("id", "in", sampled_ids)],
    )
    for sample, p3, spei_col, bucket_label in [
        (sample_res, p3_res, "SPEI_12", "hydro_reservoir"),
        (sample_ror12, p3_ror12, "SPEI_12", "hydro_run_of_river"),
        (sample_ror3, p3_ror3, "SPEI_3", "hydro_run_of_river_spei3"),
        (sample_thermal, p3_thermal, "SPEI_12", "thermal_water_dependent"),
    ]:
        if not len(sample):
            continue
        pwm_fd = _pwm_fd(spei_df2, sample, spei_col)
        merged = sample.merge(pwm_fd, on=["id", "model"], how="inner").merge(
            p3, on=["id", "model"], how="inner"
        )
        combined.append(merged)
    del spei_df2
    gc.collect()

    full = pd.concat(combined, ignore_index=True) if combined else pd.DataFrame()
    full.to_csv(processed_dir / "fd_pwm_vs_pearson3_sample.csv", index=False)

    print("\n=== Action 1: paired F_D gap (Pearson III - PWM), fully-PWM-converged series ===")
    _report_gap(full, "All sampled series")

    print("\n=== Action 2: same comparison restricted to the highest-skewness tercile ===")
    high_skew_parts = []
    for (bucket, country), g in full.groupby(["bucket", "country"]):
        cutoff = g["skew"].abs().quantile(2 / 3)
        high_skew_parts.append(g[g["skew"].abs() >= cutoff])
    high_skew = pd.concat(high_skew_parts, ignore_index=True) if high_skew_parts else full.iloc[0:0]
    _report_gap(high_skew, "Top-tercile |skew(D)| subset")

    print("\nDone. Full sample saved to fd_pwm_vs_pearson3_sample.csv")


if __name__ == "__main__":
    main()
