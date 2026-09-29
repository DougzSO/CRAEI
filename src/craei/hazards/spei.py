"""SPEI-12, SPEI-3 and SPI-12 (Spec §1.4 H2, §3 Step 6; COMANDO 17).

The monthly water-balance deficit D = P - PET (SPEI) or precipitation P
alone (SPI) is accumulated over a rolling window (12 or 3 months) per group
(id, model, scenario). A three-parameter log-logistic distribution (SPEI)
is fit per calendar month on the 1985-2014 baseline via unbiased
probability-weighted moments (PWMs) -- the closed-form L-moment estimator
from Vicente-Serrano et al. (2010), the paper Spec §1.4 H2 cites for SPEI,
not numerical MLE: `scipy.stats.fisk.fit`'s general-purpose 3-parameter MLE
is both far slower (a per-group numerical optimizer over ~192k
cell/model/calendar-month groups for the thermal fleet alone) and less
standard for this distribution than the PWM method the original SPEI
method uses. SPI uses a two-parameter gamma distribution (`scipy.stats.gamma`
MLE with `loc` fixed at 0, since accumulated precipitation is non-negative
and gamma MLE is fast and well-behaved). The same fitted parameters
transform both baseline and future accumulated values to a standard-normal
index via `norm.ppf(cdf(x, *params))`, clipped to +/- `spei_clip_bound`
(config/params.yaml). A group/calendar-month whose fit does not converge to
finite, valid parameters is left as NaN and counted by the caller, never
silently replaced by a default (COMANDO 17 Action 5).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import special, stats

from craei.rolling import rolling_sum_by_group

BASELINE_START_YEAR = 1985  # Spec §1.3; the extra 1984 history month feeds accumulation only
BASELINE_END_YEAR = 2014
MIN_FIT_SAMPLES = 8  # below this, a per-calendar-month fit is treated as failed, not attempted


def _fit_loglogistic_pwm(values: np.ndarray):
    """Three-parameter log-logistic fit via unbiased PWMs (Vicente-Serrano et al. 2010, Eq. 3-8).

    Returns `(c, loc, scale)` in `scipy.stats.fisk` order (its CDF,
    `1 / (1 + ((x-loc)/scale)^-c)`, matches the paper's with
    `c=beta`, `scale=alpha`, `loc=gamma`), or None if the sample is too
    small or the closed-form estimate is degenerate (beta <= 0, alpha <= 0,
    or a non-finite Gamma-function evaluation).
    """
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
    return (beta, loc, alpha)


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
    """`fit_fn` for `fit_baseline`: PWM log-logistic fit, gated by `MIN_FIT_SAMPLES`."""
    values = values[np.isfinite(values)]
    if len(values) < MIN_FIT_SAMPLES:
        return None
    return _fit_loglogistic_pwm(values)


def gamma_fit_fn(values: np.ndarray):
    """`fit_fn` for `fit_baseline`: gamma MLE with `loc` fixed at 0 (SPI, Spec §3 Step 6)."""
    return _fit_group_mle(values, stats.gamma, floc=0.0)


def fit_baseline(acc: pd.DataFrame, acc_col: str, group_cols: list[str], fit_fn) -> pd.DataFrame:
    """Apply `fit_fn` per (group_cols, calendar month) on baseline data only.

    `fit_fn(values: np.ndarray) -> params tuple | None` is `loglogistic_fit_fn`
    (SPEI) or `gamma_fit_fn` (SPI). Raises if any row's `month` falls outside
    `[BASELINE_START_YEAR, BASELINE_END_YEAR]` (Rule 4, CLAUDE.md; COMANDO 17
    Action 2) -- the caller restricts `acc` to `period == "baseline"` and
    drops the extra pre-baseline history year before calling this.
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
        params = fit_fn(g[acc_col].to_numpy(dtype=float))
        row = dict(zip(group_cols + ["cal_month"], keys))
        row["fit_ok"] = params is not None
        row["fit_params"] = params
        rows.append(row)
    return pd.DataFrame(rows)


def standardize(
    acc: pd.DataFrame,
    acc_col: str,
    fitted: pd.DataFrame,
    group_cols: list[str],
    dist: stats.rv_continuous,
    clip_bound: float,
    out_col: str,
) -> pd.DataFrame:
    """Apply `fitted` per-(group, calendar-month) params to every row of `acc`.

    Rows whose group+calendar-month fit failed (`fit_ok` False, or absent
    from `fitted`, or a NaN accumulation) get NaN in `out_col` -- never a
    substituted default (COMANDO 17 Action 5); the caller counts these.
    Params are expanded into their own columns and `dist.cdf` is called once
    on the whole valid slice with array parameters (broadcasting elementwise
    against `x`), not once per row -- this runs over tens of millions of
    rows (every cell/plant x model x scenario x month), where a per-row
    Python-level `dist.cdf` call would be prohibitively slow.
    """
    d = acc.copy()
    d["cal_month"] = d["month"].dt.month
    merged = d.merge(fitted, on=group_cols + ["cal_month"], how="left")

    acc_vals = merged[acc_col].to_numpy(dtype=float)
    ok = merged["fit_ok"].astype("boolean").fillna(False).to_numpy(dtype=bool)
    valid = ok & np.isfinite(acc_vals)

    values = np.full(len(merged), np.nan)
    if valid.any():
        params_arr = np.array(merged.loc[valid, "fit_params"].tolist(), dtype=float)
        cdf = dist.cdf(acc_vals[valid], params_arr[:, 0], params_arr[:, 1], params_arr[:, 2])
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
