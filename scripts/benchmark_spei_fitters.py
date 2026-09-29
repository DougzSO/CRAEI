"""COMANDO 17-E: benchmark PWM vs MLE log-logistic vs GEV vs Pearson III as
SPEI-12/SPEI-3 baseline fitters (Spec Sec 1.4 H2), to ground docs/DECISIONS.md
D45's methodological choice in measured numbers rather than intuition.

Read-only (Action 4): loads the same baseline (1985-2014) accumulated series
COMANDO 17/17-B/17-C already use, but writes nothing to spei.parquet or any
other production artifact -- only this script's own stdout report.

Sampling (disclosed, not silently approximated -- a first version tried to
fit every PWM-failing combo exactly and a pilot run on 200 synthetic combos
measured ~100ms per scipy.stats.genextreme.fit call, ~60ms per fisk MLE
call: at the real ~70,000 PWM-failing combos across the 3 buckets, that is
multiple hours, not viable in this session): per bucket, this draws a
fixed-seed random sample of up to `MAX_FAILING_SAMPLE` PWM-failing combos
and up to `MAX_PASSING_SAMPLE` PWM-passing combos, and reports both sample
sizes next to every number below. Neither stratum is the full population;
treat every percentage as +/- a few points, not exact.
"""

import gc
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.loading import cells_with_catchments_by_country

RNG_SEED = 0
MAX_FAILING_SAMPLE = 800  # per bucket, PWM-failing combos randomly sampled
MAX_PASSING_SAMPLE = 800  # per bucket, PWM-passing combos randomly sampled


def fit_pwm(values: np.ndarray):
    """Baseline: the production closed-form PWM estimator (post-COMANDO 17-D fix)."""
    return spei._fit_loglogistic_pwm(values)


def fit_loglogistic_mle(values: np.ndarray):
    """Alternative 1: 3-parameter log-logistic via numerical MLE, moment-seeded."""
    span = values.max() - values.min()
    loc0 = values.min() - 1e-6 * (span + 1.0)
    scale0 = values.std(ddof=1) or 1.0
    try:
        c, loc, scale = stats.fisk.fit(values, 1.0, loc=loc0, scale=scale0)
    except Exception:
        return None
    if not (np.isfinite(c) and np.isfinite(loc) and np.isfinite(scale)):
        return None
    if scale <= 0 or c <= 0 or loc > values.min():
        return None
    return (c, loc, scale)


def fit_gev(values: np.ndarray):
    """Alternative 2: Generalized Extreme Value via MLE (scipy defaults, no seeding)."""
    try:
        c, loc, scale = stats.genextreme.fit(values)
    except Exception:
        return None
    if not (np.isfinite(c) and np.isfinite(loc) and np.isfinite(scale)) or scale <= 0:
        return None
    return (c, loc, scale)


def fit_pearson3(values: np.ndarray):
    """Alternative 3 (optional): Pearson Type III via MLE (scipy defaults)."""
    try:
        skew, loc, scale = stats.pearson3.fit(values)
    except Exception:
        return None
    if not (np.isfinite(skew) and np.isfinite(loc) and np.isfinite(scale)) or scale <= 0:
        return None
    return (skew, loc, scale)


METHODS = {
    "PWM log-logistic (production)": (fit_pwm, stats.fisk),
    "MLE log-logistic": (fit_loglogistic_mle, stats.fisk),
    "GEV (MLE)": (fit_gev, stats.genextreme),
    "Pearson III (MLE)": (fit_pearson3, stats.pearson3),
}


def collect_baseline_samples(acc: pd.DataFrame, acc_col: str, group_cols: list[str]) -> list[dict]:
    """One record per (group, calendar-month): its 30 baseline values and whether PWM fits it."""
    baseline_acc = acc[
        (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    d = baseline_acc.dropna(subset=[acc_col]).copy()
    d["cal_month"] = d["month"].dt.month
    records = []
    for _keys, g in d.groupby(group_cols + ["cal_month"], sort=False):
        values = g[acc_col].to_numpy(dtype=float)
        records.append({"values": values, "pwm_ok": fit_pwm(values) is not None})
    return records


def _cap(items: list[dict], max_n: int, rng: np.random.Generator) -> list[dict]:
    if len(items) <= max_n:
        return items
    idx = rng.choice(len(items), size=max_n, replace=False)
    return [items[i] for i in idx]


def stratified_sample(records: list[dict], rng: np.random.Generator) -> list[dict]:
    failing = _cap([r for r in records if not r["pwm_ok"]], MAX_FAILING_SAMPLE, rng)
    passing = _cap([r for r in records if r["pwm_ok"]], MAX_PASSING_SAMPLE, rng)
    return failing + passing


def evaluate_method(
    sample: list[dict], fit_fn, dist, clip_bound: float, severe_threshold: float
) -> dict:
    n_total = len(sample)
    n_failed = 0
    n_pwm_failed_in_sample = sum(1 for r in sample if not r["pwm_ok"])
    n_recovered = 0
    standardized_parts = []

    t0 = time.perf_counter()
    for rec in sample:
        values = rec["values"]
        params = fit_fn(values)
        if params is None:
            n_failed += 1
            continue
        if not rec["pwm_ok"]:
            n_recovered += 1
        cdf = np.clip(dist.cdf(values, *params), 1e-10, 1 - 1e-10)
        idx = np.clip(stats.norm.ppf(cdf), -clip_bound, clip_bound)
        standardized_parts.append(idx)
    elapsed = time.perf_counter() - t0

    all_idx = np.concatenate(standardized_parts) if standardized_parts else np.array([])
    f_d = float((all_idx <= severe_threshold).mean()) if len(all_idx) else float("nan")
    recovery_rate = n_recovered / n_pwm_failed_in_sample if n_pwm_failed_in_sample else float("nan")
    return {
        "n_total": n_total,
        "failure_rate": n_failed / n_total if n_total else float("nan"),
        "n_pwm_failed_in_sample": n_pwm_failed_in_sample,
        "recovery_rate_pwm_failed": recovery_rate,
        "F_D": f_d,
        "elapsed_s": elapsed,
    }


def _report(
    label: str,
    records: list[dict],
    rng: np.random.Generator,
    clip_bound: float,
    severe_threshold: float,
) -> None:
    sample = stratified_sample(records, rng)
    n_pwm_failing_total = sum(1 for r in records if not r["pwm_ok"])
    n_failing_sampled = sum(1 for r in sample if not r["pwm_ok"])
    n_passing_sampled = len(sample) - n_failing_sampled
    print(f"\n{'=' * 10} {label} {'=' * 10}")
    print(
        f"population: {len(records)} (group, calendar-month) combos, "
        f"{n_pwm_failing_total} PWM-failing; sample evaluated: {len(sample)} "
        f"({n_failing_sampled}/{n_pwm_failing_total} failing sampled, "
        f"{n_passing_sampled} passing sampled)"
    )
    rows = []
    pwm_time = None
    for method_label, (fit_fn, dist) in METHODS.items():
        result = evaluate_method(sample, fit_fn, dist, clip_bound, severe_threshold)
        if pwm_time is None:
            pwm_time = result["elapsed_s"] or 1e-9
        result["relative_time"] = result["elapsed_s"] / pwm_time
        result["method"] = method_label
        rows.append(result)
    table = pd.DataFrame(rows).set_index("method")
    table = table[
        ["failure_rate", "recovery_rate_pwm_failed", "F_D", "elapsed_s", "relative_time", "n_total"]
    ]
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(table.to_string())


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    clip_bound = float(params["spei_clip_bound"]["value"])
    severe_threshold = float(params["drought_spei_threshold"]["value"])
    rng = np.random.default_rng(RNG_SEED)

    plant_cols = ["plant_uid", "country", "tech_class", "hydro_type"]
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=plant_cols)
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    hydro_plants = hydro_plants[~hydro_plants["plant_uid"].isin(_h2_excluded_ids())]
    is_ror = hydro_plants["hydro_type"] == "run-of-river"
    run_of_river_ids = set(hydro_plants.loc[is_ror, "plant_uid"])
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

    hydro12_records, hydro3_records, thermal12_records = [], [], []

    for model in models:
        catchment_model = pd.read_parquet(catchment_path, filters=[("model", "=", model)])
        cell_model = pd.read_parquet(cell_path, filters=[("model", "=", model)])

        for country in STUDY_COUNTRIES:
            country_ids = hydro_ids_by_country[country]
            catchment_chunk = catchment_model[catchment_model["id"].isin(country_ids)]
            if len(catchment_chunk):
                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(catchment_chunk[d_cols], window=12, value_col="D")
                hydro12_records.extend(collect_baseline_samples(acc12, "D_acc12", ["id", "model"]))

                ror = catchment_chunk.loc[catchment_chunk["id"].isin(run_of_river_ids), d_cols]
                if len(ror):
                    acc3 = spei.accumulate(ror, window=3, value_col="D")
                    hydro3_records.extend(collect_baseline_samples(acc3, "D_acc3", ["id", "model"]))
                del acc12, ror
            del catchment_chunk

            cell_mask = pd.Series(
                list(zip(cell_model["cell_lat"], cell_model["cell_lon"])), index=cell_model.index
            ).isin(cells_by_country[country])
            cell_chunk = cell_model[cell_mask].copy()
            if len(cell_chunk):
                cell_chunk["id"] = (
                    cell_chunk["cell_lat"].astype(str) + "_" + cell_chunk["cell_lon"].astype(str)
                )
                cell_d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12_cell = spei.accumulate(cell_chunk[cell_d_cols], window=12, value_col="D")
                thermal12_records.extend(
                    collect_baseline_samples(acc12_cell, "D_acc12", ["id", "model"])
                )
                del acc12_cell
            del cell_chunk

            print(f"{model}/{country}: collected")

        del catchment_model, cell_model
        gc.collect()

    _report("SPEI-12 hydro catchment", hydro12_records, rng, clip_bound, severe_threshold)
    _report("SPEI-3 run-of-river", hydro3_records, rng, clip_bound, severe_threshold)
    _report("SPEI-12 thermal cell", thermal12_records, rng, clip_bound, severe_threshold)
    sigma = -severe_threshold
    print(f"\nExpected F_D under a correctly-specified fit: ~{sigma:.1f} sigma -> ~6.7%")


def _h2_excluded_ids() -> set[str]:
    return {"5131763b8e53f91a7783faeea1fb15095453fd967630297cac52261097daf54c"}


if __name__ == "__main__":
    main()
