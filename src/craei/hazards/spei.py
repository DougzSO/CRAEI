"""SPEI-12, SPEI-3 and SPI-12 (Spec §1.4 H2, §3 Step 6; COMANDO 17).

The monthly water-balance deficit D = P - PET (SPEI) or precipitation P
alone (SPI) is accumulated over a rolling window (12 or 3 months) per group
(id, model, scenario), then fit per calendar month on the 1985-2014
baseline; the same fitted parameters transform both baseline and future
accumulated values to a standard-normal index via `norm.ppf(cdf(x,
*params))`, clipped to +/- `spei_clip_bound` (config/params.yaml).

SPEI (`fit_spei_distribution`, COMANDO 17-F) is a hybrid: try the
closed-form log-logistic PWM estimator (Vicente-Serrano et al. 2010, the
paper Spec §1.4 H2 cites) first -- fast, and standard in the SPEI
literature -- and fall back to a Pearson III MLE fit only for the ~30% of
(group, calendar-month) baseline samples where PWM's closed-form validity
conditions are not met (COMANDO 17-C: overwhelmingly a shape parameter
sign flip caused by high skewness in a 30-sample D series, not a data
problem -- see `docs/METHODS_SPEC.md` §3 Step 6 note for the full
derivation and `docs/DECISIONS.md` D45 for the decision this closes).
COMANDO 17-E measured this fallback recovering 100% of a large sample of
PWM's failures at ~1.2-1.4x PWM-alone's wall-clock cost. Which
distribution actually fit a given (group, calendar-month) is recorded (the
`distribution` column fed through to `spei.parquet`), since a downstream
consumer computing anything beyond the already-standardized index (e.g. a
tail-shape-sensitive statistic) needs to know it is not one distribution
family throughout.

SPI uses a two-parameter gamma distribution (`scipy.stats.gamma` MLE with
`loc` fixed at 0, since accumulated precipitation is non-negative and gamma
MLE is fast and well-behaved) -- unaffected by the SPEI hybrid above. A
group/calendar-month whose fit does not converge to finite, valid
parameters under BOTH SPEI estimators (COMANDO 17-E: never observed on
real data) or under the SPI gamma fit is left as NaN and counted by the
caller, never silently replaced by a default (COMANDO 17 Action 5).
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import special, stats

from craei.rolling import rolling_sum_by_group

BASELINE_START_YEAR = 1985  # Spec §1.3; the extra 1984 history month feeds accumulation only
BASELINE_END_YEAR = 2014
MIN_FIT_SAMPLES = 8  # below this, a per-calendar-month fit is treated as failed, not attempted

# scipy distribution object per `distribution` name, all with (shape, loc, scale) cdf order.
DIST_BY_NAME = {"loglogistic": stats.fisk, "pearson3": stats.pearson3, "gamma": stats.gamma}


def _fit_loglogistic_pwm(values: np.ndarray) -> tuple[dict | None, str]:
    """Three-parameter log-logistic fit via unbiased PWMs (Vicente-Serrano et al. 2010, Eq. 3-8).

    Returns `(params, status)`. `params` is `{"shape": beta, "loc": gamma,
    "scale": alpha}` (in `scipy.stats.fisk` order: its CDF is
    `1 / (1 + ((x-loc)/scale)^-shape)`) on success, else `None`. `status` is
    one of:

    - `"success"`: beta > 0 and finite, the Gamma-function evaluations in
      the alpha step are finite and nonzero, alpha > 0 and finite, and
      `loc <= min(sample)` (the log-logistic's support is `[loc, inf)`, so a
      `loc` above the sample minimum is a support violation the closed-form
      PWM formula does not rule out on its own -- COMANDO 17-D).
    - `"beta_nonpositive"`: any of the above conditions up to and including
      alpha fails -- overwhelmingly beta <= 0 or non-finite in practice
      (COMANDO 17-C measured 100% of real failures landing here, with beta
      ranging -2.96 to -21,878, i.e. a shape-parameter sign flip from high
      sample skewness, not a near-zero edge case); the PWM denominator
      being exactly zero, a non-finite/zero Gamma-function evaluation, and
      a non-finite or non-positive alpha are folded into this same status
      rather than split further, since COMANDO 17-C found 0/70,808 real
      failures in those specific sub-cases.
    - `"loc_violation"`: beta and alpha are valid but `loc > min(sample)`.
    """
    x = np.sort(values)
    n = len(x)
    i = np.arange(1, n + 1)
    w0 = x.mean()
    w1 = np.sum(x * (n - i) / (n - 1)) / n
    w2 = np.sum(x * (n - i) * (n - i - 1) / ((n - 1) * (n - 2))) / n

    denom = 6 * w1 - w0 - 6 * w2
    if denom == 0:
        return None, "beta_nonpositive"
    beta = (2 * w1 - w0) / denom
    if not np.isfinite(beta) or beta <= 0:
        return None, "beta_nonpositive"

    g1 = special.gamma(1 + 1 / beta)
    g2 = special.gamma(1 - 1 / beta)
    if not (np.isfinite(g1) and np.isfinite(g2)) or g1 * g2 == 0:
        return None, "beta_nonpositive"

    alpha = (w0 - 2 * w1) * beta / (g1 * g2)
    if not np.isfinite(alpha) or alpha <= 0:
        return None, "beta_nonpositive"
    loc = w0 - alpha * g1 * g2
    if not np.isfinite(loc):
        return None, "beta_nonpositive"
    if loc > x[0]:  # log-logistic support restriction: loc <= min(sample)
        return None, "loc_violation"
    return {"shape": beta, "loc": loc, "scale": alpha}, "success"


def _fit_pearson3_mle(values: np.ndarray) -> tuple[dict | None, str]:
    """Pearson Type III fit via MLE -- fallback when PWM log-logistic fails (COMANDO 17-F).

    Pearson III (`scipy.stats.pearson3`, parameterized by skew/loc/scale)
    has support `(-inf, loc + scale/skew]` when `skew > 0` and
    `[loc + scale/skew, inf)` when `skew < 0` -- unlike the log-logistic
    PWM estimator, whose closed form only ever produces a valid fit for one
    sign of skewness, Pearson III's `skew` parameter can take either sign,
    so it can represent the left-skewed shape many of this project's
    D = P - PET baseline samples have where PWM fails (COMANDO 17-C/17-E).
    Fit by numerical MLE (`scipy.stats.pearson3.fit`), far slower than the
    closed-form PWM estimator (COMANDO 17-E measured ~150-290x on this
    project's data) and less standard for SPEI in the literature than
    log-logistic (Vicente-Serrano et al. 2010) -- used only as a fallback,
    not the primary estimator -- but numerically stable under the high
    skewness where PWM fails (Bobee and Robitaille 1977, drought analysis).

    Returns `(params, status)`: `params` is `{"shape": skew, "loc": loc,
    "scale": scale}` on success, else `None`; `status` is `"success"` or
    `"pearson3_failed"` (too few samples, the MLE optimizer raised, or the
    result is non-finite / has `scale <= 0`).
    """
    values = values[np.isfinite(values)]
    if len(values) < MIN_FIT_SAMPLES:
        return None, "pearson3_failed"
    try:
        # `floc=None` (the literal COMANDO 17-F instruction, "no loc fixed")
        # is NOT the same as omitting `floc` -- scipy's `rv_continuous.fit`
        # treats an explicit `floc=None` as "subtract None from the data"
        # internally and raises `TypeError`, rather than leaving loc free
        # the way leaving the kwarg out entirely does. Verified directly
        # against this project's own PWM-failing samples before relying on
        # it. Omitting the kwarg is the correct way to leave loc free.
        skew, loc, scale = stats.pearson3.fit(values)
    except Exception:
        return None, "pearson3_failed"
    if not (np.isfinite(skew) and np.isfinite(loc) and np.isfinite(scale)) or scale <= 0:
        return None, "pearson3_failed"
    return {"shape": skew, "loc": loc, "scale": scale}, "success"


def fit_spei_distribution(
    values: np.ndarray, method: str = "pwm_with_fallback"
) -> tuple[dict | None, str | None, str]:
    """Fit SPEI's baseline distribution for one (group, calendar-month) sample (COMANDO 17-F).

    `method="pwm_with_fallback"` (the only method implemented): try the
    closed-form PWM log-logistic estimator first; if it does not return a
    valid fit (`_fit_loglogistic_pwm` status != `"success"`), fall back to
    a Pearson III MLE fit (`_fit_pearson3_mle`). COMANDO 17-E measured this
    recovering 100% of a large sample of PWM's real failures.

    Returns `(params, distribution, status)`. `distribution` is
    `"loglogistic"` or `"pearson3"`, whichever succeeded, or `None` if
    both failed or the sample was too small (`status` is then
    `"few_valid_values"` or `"both_failed"` respectively) -- COMANDO 17-E's
    benchmark found `"both_failed"` never occurs on this project's real
    data; a warning is raised (not silently swallowed) if it ever does, so
    a future run with different data would surface it immediately.
    """
    if method != "pwm_with_fallback":
        raise ValueError(f"unknown method {method!r}")
    values = values[np.isfinite(values)]
    if len(values) < MIN_FIT_SAMPLES:
        return None, None, "few_valid_values"

    params, status = _fit_loglogistic_pwm(values)
    if status == "success":
        return params, "loglogistic", status

    params, p3_status = _fit_pearson3_mle(values)
    if p3_status == "success":
        return params, "pearson3", p3_status

    warnings.warn(
        f"fit_spei_distribution: both PWM log-logistic ({status}) and Pearson III MLE "
        f"({p3_status}) failed for a sample of size {len(values)} -- left as NaN, not "
        "substituted by a default.",
        stacklevel=2,
    )
    return None, None, "both_failed"


def accumulate(monthly: pd.DataFrame, window: int, value_col: str = "D") -> pd.DataFrame:
    """Rolling `window`-month sum of `value_col`, per group (every column but month/value_col).

    NaN wherever fewer than `window` consecutive months of history precede
    a row within its group (`min_periods=window`) -- e.g. the first 11
    months of `window=12` baseline history (1984) and of each disjoint
    future block (Spec L05) are NaN by construction, not an error.

    CALLER PITFALL: `monthly` must carry only the grouping columns (id,
    model, scenario, period, ...) plus `month` and `value_col` -- any other
    column (e.g. a sibling variable like P or PET that varies every row)
    becomes part of the inferred grouping too, silently making every row its
    own group of size 1 and `NaN`-ing the whole output with no error
    (COMANDO 17 follow-up: this happened in `scripts/08_spei.py`'s first
    `process_hydro` call, masked for a while by the `MemoryError` below,
    which failed first and looked like the only problem). Select down to
    exactly `[*group_cols, "month", value_col]` before calling this.

    Uses `craei.rolling.rolling_sum_by_group` (vectorized cumsum, not
    `groupby(...).transform(...)`) -- see that module's docstring for why:
    the naive `transform` pattern crashed this project's ~6 GB machine with
    a `MemoryError` on this data's tens of thousands of
    id/model/scenario/period groups (COMANDO 17 follow-up).
    """
    group_cols = [c for c in monthly.columns if c not in ("month", value_col)]
    d = monthly.sort_values(group_cols + ["month"]).reset_index(drop=True)
    d[f"{value_col}_acc{window}"] = rolling_sum_by_group(d, group_cols, "month", value_col, window)
    return d


def _fit_group_mle(values: np.ndarray, dist: stats.rv_continuous, floc: float | None):
    """MLE fit of `dist` to `values`; None if too few samples, the fit raises, or degenerates."""
    values = values[np.isfinite(values)]
    if len(values) < MIN_FIT_SAMPLES:
        return None
    try:
        params = dist.fit(values, floc=floc) if floc is not None else dist.fit(values)
    except Exception:
        return None
    if not all(np.isfinite(p) for p in params) or params[-1] <= 0:
        return None
    return params


def loglogistic_fit_fn(values: np.ndarray):
    """`fit_fn` for `fit_baseline`: PWM-only log-logistic fit (no Pearson III fallback).

    Superseded in production by `fit_spei_distribution` (COMANDO 17-F);
    kept for tests and diagnostics that want the original PWM-only
    behavior in isolation. Returns `(params, "loglogistic")` or
    `(None, None)`, matching `fit_baseline`'s `fit_fn` contract.
    """
    values = values[np.isfinite(values)]
    if len(values) < MIN_FIT_SAMPLES:
        return None, None
    params, status = _fit_loglogistic_pwm(values)
    return (params, "loglogistic") if status == "success" else (None, None)


def gamma_fit_fn(values: np.ndarray):
    """`fit_fn` for `fit_baseline`: gamma MLE with `loc` fixed at 0 (SPI, Spec §3 Step 6).

    Returns `(params, "gamma")` or `(None, None)`, matching `fit_baseline`'s
    `fit_fn` contract; unaffected by the SPEI hybrid (COMANDO 17-F).
    """
    params = _fit_group_mle(values, stats.gamma, floc=0.0)
    if params is None:
        return None, None
    return {"shape": params[0], "loc": params[1], "scale": params[2]}, "gamma"


def fit_baseline(acc: pd.DataFrame, acc_col: str, group_cols: list[str], fit_fn) -> pd.DataFrame:
    """Apply `fit_fn` per (group_cols, calendar month) on baseline data only.

    `fit_fn(values: np.ndarray) -> (params: dict | None, distribution: str | None)`
    (extra return values, e.g. `fit_spei_distribution`'s trailing `status`,
    are ignored -- only the first two are used) is `fit_spei_distribution`
    or `loglogistic_fit_fn` (SPEI) or `gamma_fit_fn` (SPI). Raises if any
    row's `month` falls outside `[BASELINE_START_YEAR, BASELINE_END_YEAR]`
    (Rule 4, CLAUDE.md; COMANDO 17 Action 2) -- the caller restricts `acc`
    to `period == "baseline"` and drops the extra pre-baseline history year
    before calling this.
    """
    d = acc.dropna(subset=[acc_col]).copy()
    years = d["month"].dt.year
    if len(d) and ((years < BASELINE_START_YEAR).any() or (years > BASELINE_END_YEAR).any()):
        raise ValueError(
            f"fit_baseline received data outside {BASELINE_START_YEAR}-{BASELINE_END_YEAR}: "
            f"years {years.min()}-{years.max()}"
        )
    d["cal_month"] = d["month"].dt.month

    rows = []
    for keys, g in d.groupby(group_cols + ["cal_month"], sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        result = fit_fn(g[acc_col].to_numpy(dtype=float))
        params, distribution = result[0], result[1]
        row = dict(zip(group_cols + ["cal_month"], keys))
        row["fit_ok"] = params is not None
        row["fit_params"] = params
        row["distribution"] = distribution
        rows.append(row)
    return pd.DataFrame(rows)


def standardize(
    acc: pd.DataFrame,
    acc_col: str,
    fitted: pd.DataFrame,
    group_cols: list[str],
    clip_bound: float,
    out_col: str,
) -> pd.DataFrame:
    """Apply `fitted` per-(group, calendar-month) params to every row of `acc`.

    Rows whose group+calendar-month fit failed (`fit_ok` False, or absent
    from `fitted`, or a NaN accumulation) get NaN in `out_col` -- never a
    substituted default (COMANDO 17 Action 5); the caller counts these.

    No single `dist` is passed in (COMANDO 17-F): each row's distribution
    family comes from `fitted`'s own `distribution` column (`"loglogistic"`,
    `"pearson3"` or `"gamma"`, via `DIST_BY_NAME`), since the SPEI hybrid
    fallback means different (group, calendar-month) rows within the same
    call can use different families. `dist.cdf` is still called once per
    distribution family on that family's whole valid slice (array
    parameters, broadcasting elementwise against `x`), not once per row --
    this runs over tens of millions of rows (every cell/plant x model x
    scenario x month), where a per-row Python-level `dist.cdf` call would be
    prohibitively slow.
    """
    d = acc.copy()
    d["cal_month"] = d["month"].dt.month
    merged = d.merge(fitted, on=group_cols + ["cal_month"], how="left")

    acc_vals = merged[acc_col].to_numpy(dtype=float)
    ok = merged["fit_ok"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    valid = ok & np.isfinite(acc_vals)

    values = np.full(len(merged), np.nan)
    if valid.any():
        param_dicts = merged.loc[valid, "fit_params"].tolist()
        shapes = np.array([p["shape"] for p in param_dicts], dtype=float)
        locs = np.array([p["loc"] for p in param_dicts], dtype=float)
        scales = np.array([p["scale"] for p in param_dicts], dtype=float)
        dist_names = merged.loc[valid, "distribution"].to_numpy()
        valid_x = acc_vals[valid]

        cdf = np.full(len(param_dicts), np.nan)
        for name, dist in DIST_BY_NAME.items():
            mask = dist_names == name
            if mask.any():
                cdf[mask] = dist.cdf(valid_x[mask], shapes[mask], locs[mask], scales[mask])
        cdf = np.clip(cdf, 1e-10, 1 - 1e-10)
        values[valid] = stats.norm.ppf(cdf)

    merged[out_col] = np.clip(values, -clip_bound, clip_bound)
    return merged.drop(columns=["fit_params", "fit_ok", "cal_month"])


def fit_failure_summary(fitted: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Per-group count of calendar months (out of 12) whose baseline fit failed."""
    d = fitted.copy()
    return d.groupby(group_cols, as_index=False).agg(
        n_months_fit=("fit_ok", "size"), n_months_failed=("fit_ok", lambda s: (~s).sum())
    )


def severe_drought_frequency(
    df: pd.DataFrame, index_col: str, threshold: float, group_cols: list[str]
) -> pd.DataFrame:
    """F_D: fraction of non-NaN months with `index_col` <= `threshold`, per group."""
    d = df.dropna(subset=[index_col])
    out = d.groupby(group_cols, as_index=False).agg(
        n_months=(index_col, "size"),
        n_severe=(index_col, lambda s: (s <= threshold).sum()),
    )
    out["F_D"] = out["n_severe"] / out["n_months"]
    return out
