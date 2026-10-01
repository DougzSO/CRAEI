"""COMANDO 18-D Actions 3-4.

Action 3: on the SAME PWM-converged series sampled in COMANDO 18-C
(`fd_pwm_vs_pearson3_sample.csv`), refit log-logistic by MLE (not PWM) and
compare F_D against PWM's own F_D on the identical data -- isolates the
distribution-family effect (log-logistic vs. Pearson III) from the
estimator-type effect (moments/PWM vs. maximum likelihood), since this
comparison keeps the family fixed (log-logistic both times) and only
changes the estimator.

Action 4: two-parameter log-logistic (origin fixed at 0, `floc=0.0`) as an
alternative fallback on the series where the production 3-parameter PWM
estimator fails (`spei.parquet`'s `distribution == "pearson3"` rows --
COMANDO 17-C already found this essentially never converges on this
project's earlier failure set; re-measured here directly against the
committed 55/56 D45/D46-consistent numbers). Sampled, not full population,
same reasoning as COMANDO 18-C (Pearson III/MLE cost). Read-only.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from craei.config import load_params, load_paths
from craei.hazards import spei

SAMPLE_PER_STRATUM = 200
SEED = 11


def _loglogistic_mle_fit_fn(values: np.ndarray):
    values = values[np.isfinite(values)]
    if len(values) < spei.MIN_FIT_SAMPLES:
        return None, None
    params = spei._fit_group_mle(values, stats.fisk, floc=None)
    if params is None:
        return None, None
    return {"shape": params[0], "loc": params[1], "scale": params[2]}, "loglogistic"


def _loglogistic_2param_fit_fn(values: np.ndarray):
    """2-parameter (floc=0) log-logistic MLE -- Action 4, with the support
    check `_fit_group_mle` does NOT do on its own.

    Found while running this: `stats.fisk.fit(values, floc=0.0)` does not
    raise or return non-finite output when `values` has entries below 0
    (fisk's support with loc=0 is `[0, inf)`) -- it silently converges to a
    numerically degenerate near-delta-function fit instead (observed:
    `scale` ~1e-26 on a real failing sample with 37% negative D values, a
    garbage fit that still passes a bare `finite and scale > 0` check and
    produces an absurd F_D, ~60-75%, when standardized). This is exactly
    the same support-violation failure mode COMANDO 17-D already found and
    fixed for the 3-parameter PWM path (`loc <= min(sample)`); the
    2-parameter MLE path needs the identical guard, which the first version
    of this audit script did not have. Fixed here: refuse the fit outright
    if any value is below `floc` (0), and additionally reject a degenerate
    `scale` (< 1e-6, several orders below any real D_acc12 magnitude) as a
    second guard in case scipy's optimizer degenerates for another reason.
    """
    values = values[np.isfinite(values)]
    if len(values) < spei.MIN_FIT_SAMPLES:
        return None, None
    if values.min() < 0.0:  # fisk support [loc, inf) with loc fixed at 0
        return None, None
    params = spei._fit_group_mle(values, stats.fisk, floc=0.0)
    if params is None:
        return None, None
    if params[2] < 1e-6:  # degenerate scale, a second guard
        return None, None
    return {"shape": params[0], "loc": params[1], "scale": params[2]}, "loglogistic"


def action3(processed_dir: Path, threshold: float, clip_bound: float) -> None:
    sample = pd.read_csv(processed_dir / "fd_pwm_vs_pearson3_sample.csv")
    print(f"Action 3: reusing COMANDO 18-C's {len(sample)}-series PWM-converged sample")

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"

    results = []
    for bucket_group, wb_path, window, is_cell in [
        (["hydro_reservoir", "hydro_run_of_river"], catchment_path, 12, False),
        (["hydro_run_of_river_spei3"], catchment_path, 3, False),
        (["thermal_water_dependent"], cell_path, 12, True),
    ]:
        sub = sample[sample["bucket"].isin(bucket_group)]
        if not len(sub):
            continue
        for model in sub["model"].unique():
            model_sub = sub[sub["model"] == model]
            ids = set(model_sub["id"])
            wb = pd.read_parquet(wb_path, filters=[("model", "=", model)])
            if is_cell:
                wb = wb.copy()
                wb["id"] = wb["cell_lat"].astype(str) + "_" + wb["cell_lon"].astype(str)
            wb = wb[wb["id"].isin(ids)]
            if not len(wb):
                del wb
                continue
            group_cols = ["id", "model"]
            value_col = "D"
            acc = spei.accumulate(wb[[*group_cols, "scenario", "period", "month", value_col]], window=window, value_col=value_col)
            acc_col = f"{value_col}_acc{window}"
            baseline_acc = acc[(acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]

            fitted = spei.fit_baseline(baseline_acc, acc_col, group_cols, _loglogistic_mle_fit_fn)
            std = spei.standardize(baseline_acc, acc_col, fitted, group_cols, clip_bound, "SPEI_MLE")
            fd = spei.severe_drought_frequency(std, "SPEI_MLE", threshold, group_cols)
            fd["model"] = model
            fd = fd.rename(columns={"F_D": "f_d_loglogistic_mle"})
            results.append(fd[["id", "model", "f_d_loglogistic_mle"]])
            del wb, acc, baseline_acc, fitted, std
            gc.collect()

    mle_fd = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=["id", "model", "f_d_loglogistic_mle"])
    merged = sample.merge(mle_fd, on=["id", "model"], how="inner")
    merged["gap_mle_vs_pwm_pp"] = (merged["f_d_loglogistic_mle"] - merged["f_d_pwm"]) * 100

    print("\n=== Action 3: log-logistic MLE vs. PWM, same family, same data ===")
    for (bucket, country), g in merged.groupby(["bucket", "country"]):
        pos = (g["gap_mle_vs_pwm_pp"] > 0).sum()
        neg = (g["gap_mle_vs_pwm_pp"] < 0).sum()
        print(
            f"{bucket:24s} {country}: n={len(g):4d}  median={g['gap_mle_vs_pwm_pp'].median():+.3f}pp  "
            f"P5={g['gap_mle_vs_pwm_pp'].quantile(0.05):+.3f}pp  P95={g['gap_mle_vs_pwm_pp'].quantile(0.95):+.3f}pp  "
            f"sign: {pos} pos / {neg} neg"
        )
    merged.to_csv(processed_dir / "fd_loglogistic_mle_vs_pwm.csv", index=False)


def action4(processed_dir: Path, threshold: float, clip_bound: float) -> None:
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class", "hydro_type"])
    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"])
    hydro = plants[plants["tech_class"] == "hydro"]
    thermal_water = plants[plants["tech_class"] == "thermal_water_dependent"]
    hydro_id_country = hydro[["plant_uid", "country"]].rename(columns={"plant_uid": "id"})
    tw = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
    tw["id"] = tw["cell_lat"].astype(str) + "_" + tw["cell_lon"].astype(str)
    cell_id_country = tw[["id", "country"]].drop_duplicates(subset="id")

    spei_cols = ["id", "model", "period", "SPEI_12", "distribution"]
    catchment = pd.read_parquet(processed_dir / "spei.parquet", columns=spei_cols, filters=[("scale", "=", "catchment")])
    fail_catchment = catchment[(catchment["period"] == "baseline") & (catchment["distribution"] == "pearson3")][["id", "model"]].drop_duplicates()
    del catchment
    gc.collect()

    cell = pd.read_parquet(processed_dir / "spei.parquet", columns=spei_cols, filters=[("scale", "=", "cell")])
    fail_cell = cell[(cell["period"] == "baseline") & (cell["distribution"] == "pearson3")][["id", "model"]].drop_duplicates()
    del cell
    gc.collect()

    def sample_strata(candidates, id_country, bucket_name):
        c = candidates.merge(id_country, on="id", how="inner")
        c["bucket"] = bucket_name
        rng = np.random.default_rng(SEED)
        parts = []
        for country, g in c.groupby("country"):
            n = min(SAMPLE_PER_STRATUM, len(g))
            idx = rng.choice(g.index.to_numpy(), size=n, replace=False)
            parts.append(g.loc[idx])
        return pd.concat(parts, ignore_index=True) if parts else c.iloc[0:0]

    sample_hydro = sample_strata(fail_catchment[fail_catchment["id"].isin(hydro["plant_uid"])], hydro_id_country, "hydro")
    sample_thermal = sample_strata(fail_cell, cell_id_country, "thermal_water_dependent")

    print(f"\nAction 4: sampled PWM-failure (pearson3-fallback) population -- hydro {len(sample_hydro)}, thermal {len(sample_thermal)}")

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    results = []
    for sample, wb_path, is_cell, label in [
        (sample_hydro, catchment_path, False, "hydro"),
        (sample_thermal, cell_path, True, "thermal_water_dependent"),
    ]:
        if not len(sample):
            continue
        for model in sample["model"].unique():
            model_sub = sample[sample["model"] == model]
            ids = set(model_sub["id"])
            wb = pd.read_parquet(wb_path, filters=[("model", "=", model)])
            if is_cell:
                wb = wb.copy()
                wb["id"] = wb["cell_lat"].astype(str) + "_" + wb["cell_lon"].astype(str)
            wb = wb[wb["id"].isin(ids)]
            if not len(wb):
                del wb
                continue
            group_cols = ["id", "model"]
            acc = spei.accumulate(wb[[*group_cols, "scenario", "period", "month", "D"]], window=12, value_col="D")
            baseline_acc = acc[(acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]

            fitted = spei.fit_baseline(baseline_acc, "D_acc12", group_cols, _loglogistic_2param_fit_fn)
            n_months_total = len(fitted)
            n_months_ok = int(fitted["fit_ok"].sum())
            std = spei.standardize(baseline_acc, "D_acc12", fitted, group_cols, clip_bound, "SPEI_2P")
            fd = spei.severe_drought_frequency(std, "SPEI_2P", threshold, group_cols)
            fd["model"] = model
            fd["bucket"] = label
            fd["n_months_fit_ok"] = n_months_ok
            fd["n_months_total"] = n_months_total
            results.append(fd)
            del wb, acc, baseline_acc, fitted, std
            gc.collect()

    combined = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    if not len(combined):
        print("Action 4: no results (empty sample)")
        return

    id_country_all = pd.concat([hydro_id_country, cell_id_country], ignore_index=True)
    combined = combined.merge(id_country_all, on="id", how="left")

    total_months_attempted = combined["n_months_total"].sum()
    total_months_ok = combined["n_months_fit_ok"].sum()
    print(
        f"\n=== Action 4: 2-parameter log-logistic (floc=0) fallback, calendar-month fit rate ==="
    )
    print(
        f"{total_months_ok}/{total_months_attempted} calendar-month fits succeed "
        f"({100*total_months_ok/total_months_attempted:.3f}%) among sampled PWM-3-param failures"
    )
    # A group only gets a usable F_D if ALL 12 of its calendar months converged
    # (severe_drought_frequency's F_D would otherwise mix NaN-standardized months in).
    converged_groups = combined[combined["n_months"] > 0]
    print(f"(id, model) groups with >=1 valid standardized month: {len(converged_groups)}/{len(combined)}")
    if len(converged_groups):
        print("\nF_D (%) by country among the (rare) fully-converged 2-param subset:")
        fd_pct = converged_groups.copy()
        fd_pct["F_D_pct"] = fd_pct["F_D"] * 100
        print(fd_pct.groupby("country")["F_D_pct"].agg(["mean", "count"]))
    combined.to_csv(processed_dir / "fd_2param_loglogistic_fallback.csv", index=False)


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    threshold = float(params["drought_spei_threshold"]["value"])
    clip_bound = float(params["spei_clip_bound"]["value"])

    action3(processed_dir, threshold, clip_bound)
    action4(processed_dir, threshold, clip_bound)


if __name__ == "__main__":
    main()
