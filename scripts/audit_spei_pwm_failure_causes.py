"""COMANDO 17-C: root cause of the log-logistic PWM fit failures found by
COMANDO 17-B (`scripts/audit_spei_fit_diagnostics.py`) -- 32%/14%/29% of
baseline (group, calendar-month) fits fail even though every one of them has
the full 30-sample baseline and zero missing months. Measure only (Action 5
tests a 2-parameter variant; nothing here is adopted).

Action 1: the estimator is the closed-form PWM estimator from
Vicente-Serrano et al. (2010) (`spei._fit_loglogistic_pwm`), not an
iterative optimizer -- it never "fails to converge" in the numerical-solver
sense. `_classify_loglogistic` in COMANDO 17-B's audit script labeled every
non-`None` return "not_converged", which was a misnomer carried over from
the SPI/gamma classifier (gamma MLE, an actual iterative fit); for the PWM
estimator, a `None` return means one of its closed-form validity conditions
was violated (beta <= 0, a non-finite Gamma-function evaluation, alpha <= 0,
or a non-finite loc) -- see the pasted `_fit_loglogistic_pwm` body below.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special, stats

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_paths
from craei.hazards import spei
from craei.hazards.loading import cells_with_catchments_by_country

ESTIMATOR_SOURCE = '''\
def _fit_loglogistic_pwm(values: np.ndarray):
    """Three-parameter log-logistic fit via unbiased PWMs (Vicente-Serrano et al. 2010, Eq. 3-8)."""
    x = np.sort(values)
    n = len(x)
    i = np.arange(1, n + 1)
    w0 = x.mean()
    w1 = np.sum(x * (n - i) / (n - 1)) / n
    w2 = np.sum(x * (n - i) * (n - i - 1) / ((n - 1) * (n - 2))) / n

    denom = 6 * w1 - w0 - 6 * w2
    if denom == 0:
        return None
    beta = (2 * w1 - w0) / denom
    if not np.isfinite(beta) or beta <= 0:
        return None

    g1 = special.gamma(1 + 1 / beta)
    g2 = special.gamma(1 - 1 / beta)
    if not (np.isfinite(g1) and np.isfinite(g2)) or g1 * g2 == 0:
        return None

    alpha = (w0 - 2 * w1) * beta / (g1 * g2)
    if not np.isfinite(alpha) or alpha <= 0:
        return None
    loc = w0 - alpha * g1 * g2
    if not np.isfinite(loc):
        return None
    return (beta, loc, alpha)  # (c, loc, scale) in scipy.stats.fisk order
'''  # Spec §1.4 H2; source: src/craei/hazards/spei.py


def pwm_diagnostic(values: np.ndarray) -> dict:
    """Recomputes `_fit_loglogistic_pwm` step by step, keeping every intermediate value.

    `reason` matches the 4 buckets COMANDO 17-C Action 2 asks for, in the
    order the estimator itself would hit them: `beta_nonpositive`,
    `gamma_domain_invalid` (the Gamma-function evaluation is non-finite or
    zero -- Action 2's "argumento fora do dominio da funcao gama"),
    `loc_above_sample_min` (a check `_fit_loglogistic_pwm` itself does NOT
    make -- log-logistic support requires `loc <= min(x)`; a `loc` above the
    sample minimum is a support violation even when every other condition
    passes, so this can also flag a currently-"successful" fit as invalid),
    or `other` (denom == 0, alpha <= 0, or a non-finite loc after passing
    the Gamma check -- rare enough Action 2 groups them together).
    """
    x = np.sort(values)
    n = len(x)
    i = np.arange(1, n + 1)
    w0 = x.mean()
    w1 = np.sum(x * (n - i) / (n - 1)) / n
    w2 = np.sum(x * (n - i) * (n - i - 1) / ((n - 1) * (n - 2))) / n
    denom = 6 * w1 - w0 - 6 * w2

    out = {
        "w0": w0, "w1": w1, "w2": w2, "denom": denom,
        "beta": np.nan, "alpha": np.nan, "loc": np.nan,
    }
    if denom == 0:
        return {**out, "reason": "other"}
    beta = (2 * w1 - w0) / denom
    out["beta"] = beta
    if not np.isfinite(beta) or beta <= 0:
        return {**out, "reason": "beta_nonpositive"}

    g1 = special.gamma(1 + 1 / beta)
    g2 = special.gamma(1 - 1 / beta)
    if not (np.isfinite(g1) and np.isfinite(g2)) or g1 * g2 == 0:
        return {**out, "reason": "gamma_domain_invalid"}

    alpha = (w0 - 2 * w1) * beta / (g1 * g2)
    out["alpha"] = alpha
    if not np.isfinite(alpha) or alpha <= 0:
        return {**out, "reason": "other"}
    loc = w0 - alpha * g1 * g2
    out["loc"] = loc
    if not np.isfinite(loc):
        return {**out, "reason": "other"}
    if loc > x.min():
        return {**out, "reason": "loc_above_sample_min"}
    return {**out, "reason": "ok"}


def two_param_recovers(values: np.ndarray) -> bool:
    """Action 5: does fixing loc=0 (2-parameter log-logistic MLE) let a failing sample fit?"""
    try:
        c, loc, scale = stats.fisk.fit(values, floc=0.0)
    except Exception:
        return False
    return np.isfinite(c) and np.isfinite(scale) and scale > 0


def diagnose(
    acc: pd.DataFrame, acc_col: str, group_cols: list[str], id_country: dict
) -> pd.DataFrame:
    baseline_acc = acc[
        (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    d = baseline_acc.dropna(subset=[acc_col]).copy()
    d["cal_month"] = d["month"].dt.month
    rows = []
    for keys, g in d.groupby(group_cols + ["cal_month"], sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        values = g[acc_col].to_numpy(dtype=float)
        diag = pwm_diagnostic(values)
        row = dict(zip(group_cols + ["cal_month"], keys))
        row.update(diag)
        row["n"] = len(values)
        row["mean"] = values.mean()
        row["std"] = values.std(ddof=1)
        row["cv"] = row["std"] / abs(row["mean"]) if row["mean"] != 0 else np.inf
        row["country"] = id_country.get(row["id"])
        if diag["reason"] != "ok":
            row["two_param_recovers"] = two_param_recovers(values)
        rows.append(row)
    return pd.DataFrame(rows)


def _report(label: str, diag: pd.DataFrame) -> None:
    print(f"\n{'=' * 10} {label} (n={len(diag)} group/calendar-month combos) {'=' * 10}")

    print("\n--- Action 2: failure-cause counts ---")
    print(diag.loc[diag["reason"] != "ok", "reason"].value_counts().to_string())
    beta_bad = diag[diag["reason"] == "beta_nonpositive"]
    if len(beta_bad):
        print(
            f"beta_nonpositive: beta range "
            f"[{beta_bad['beta'].min():.4f}, {beta_bad['beta'].max():.4f}]"
        )

    print("\n--- Action 3: failure rate by calendar month x country ---")
    diag["failed"] = diag["reason"] != "ok"
    rate = diag.groupby(["country", "cal_month"])["failed"].mean().unstack("cal_month")
    print(rate.round(2).to_string())

    print("\n--- Action 4: D_acc statistics, failing vs. passing ---")
    groups = (("failing", diag[diag["failed"]]), ("passing", diag[~diag["failed"]]))
    for cause_label, subset in groups:
        if len(subset) == 0:
            print(f"{cause_label}: no rows")
            continue
        finite_cv = subset["cv"].replace([np.inf, -np.inf], np.nan)
        print(
            f"{cause_label} (n={len(subset)}): mean(D_acc) median={subset['mean'].median():.2f}, "
            f"std(D_acc) median={subset['std'].median():.2f}, "
            f"|CV| median={finite_cv.abs().median():.3f}"
        )

    if "two_param_recovers" in diag.columns:
        failing = diag[diag["failed"]]
        n_recovered = int(failing["two_param_recovers"].sum())
        print(f"\n--- Action 5: 2-parameter (loc=0) MLE, {len(failing)} failing combos ---")
        print(f"now fit: {n_recovered}/{len(failing)} ({n_recovered / len(failing):.1%})")


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])

    print("=== Action 1: estimator in src/craei/hazards/spei.py ===")
    print(ESTIMATOR_SOURCE)
    print(
        "This is a closed-form estimator (no iteration, no solver, no convergence loop) -- "
        "COMANDO 17-B's audit script labeled every non-None-returning failure 'not_converged', "
        "which was carried over from the SPI/gamma classifier (an actual iterative MLE) and is "
        "a misnomer here. What it actually marks: beta <= 0 or non-finite (Action 2's "
        "'beta negativo ou proximo de zero'), a non-finite or zero Gamma-function evaluation "
        "('argumento fora do dominio da funcao gama'), or (checked separately below, since "
        "_fit_loglogistic_pwm itself does not check it) loc above the sample minimum -- a "
        "log-logistic support violation ('gama acima do minimo da amostra')."
    )

    plant_cols = ["plant_uid", "country", "tech_class", "hydro_type"]
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=plant_cols)
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    is_ror = hydro_plants["hydro_type"] == "run-of-river"
    run_of_river_ids = set(hydro_plants.loc[is_ror, "plant_uid"])
    hydro_id_country = dict(zip(hydro_plants["plant_uid"], hydro_plants["country"]))
    hydro_ids_by_country = {
        country: set(hydro_plants.loc[hydro_plants["country"] == country, "plant_uid"])
        for country in STUDY_COUNTRIES
    }
    cells_by_country_df = cells_with_catchments_by_country(processed_dir)
    cells_by_country = {
        country: set(zip(cells["cell_lat"], cells["cell_lon"]))
        for country, cells in cells_by_country_df.items()
    }
    cell_id_country = {}
    for country, cells in cells_by_country_df.items():
        for lat, lon in zip(cells["cell_lat"], cells["cell_lon"]):
            cell_id_country[f"{lat}_{lon}"] = country

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())

    hydro12_parts, hydro3_parts, thermal12_parts = [], [], []

    for model in models:
        catchment_model = pd.read_parquet(catchment_path, filters=[("model", "=", model)])
        cell_model = pd.read_parquet(cell_path, filters=[("model", "=", model)])

        for country in STUDY_COUNTRIES:
            country_ids = hydro_ids_by_country[country]
            catchment_chunk = catchment_model[catchment_model["id"].isin(country_ids)]
            if len(catchment_chunk):
                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(catchment_chunk[d_cols], window=12, value_col="D")
                hydro12_parts.append(diagnose(acc12, "D_acc12", ["id", "model"], hydro_id_country))

                ror = catchment_chunk.loc[catchment_chunk["id"].isin(run_of_river_ids), d_cols]
                if len(ror):
                    acc3 = spei.accumulate(ror, window=3, value_col="D")
                    hydro3_parts.append(diagnose(acc3, "D_acc3", ["id", "model"], hydro_id_country))
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
                thermal12_parts.append(
                    diagnose(acc12_cell, "D_acc12", ["id", "model"], cell_id_country)
                )
                del acc12_cell
            del cell_chunk

            print(f"{model}/{country}: done")

        del catchment_model, cell_model
        gc.collect()

    _report("SPEI-12 hydro catchment", pd.concat(hydro12_parts, ignore_index=True))
    _report("SPEI-3 run-of-river", pd.concat(hydro3_parts, ignore_index=True))
    _report("SPEI-12 thermal cell", pd.concat(thermal12_parts, ignore_index=True))


if __name__ == "__main__":
    main()
