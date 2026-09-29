"""Extreme precipitation daily indices (Spec §1.4 H4, §3 Step 4; COMANDO 15).

Wet-day (pr >= 1 mm) 95th percentile is estimated once per group on the
baseline period only (Rule 4, CLAUDE.md): `wet_day_p95` filters internally
to `period_col == baseline_label` before computing the percentile, so it
cannot see (and cannot be affected by) future-period rows even if the
caller passes a combined baseline+future frame. Exceedance frequency and
Rx5day are then computed for both periods against that fixed threshold.
"""

import numpy as np
import pandas as pd

from craei.rolling import rolling_sum_by_group

WET_DAY_THRESHOLD_MM = 1.0  # Spec §1.4 H4, wet-day definition


def wet_day_p95(
    daily: pd.DataFrame,
    percentile: float,
    value_col: str = "pr_mm",
    period_col: str = "period",
    baseline_label: str = "baseline",
) -> pd.DataFrame:
    """Baseline-only wet-day percentile threshold, per group (e.g. cell, model)."""
    baseline = daily[daily[period_col] == baseline_label]
    group_cols = [c for c in baseline.columns if c not in ("date", value_col, period_col)]
    wet = baseline[baseline[value_col] >= WET_DAY_THRESHOLD_MM]
    return wet.groupby(group_cols, as_index=False).agg(
        p95_mm=(value_col, lambda s: np.percentile(s, percentile))
    )


def wet_day_count(
    daily: pd.DataFrame,
    value_col: str = "pr_mm",
    period_col: str = "period",
    baseline_label: str = "baseline",
) -> pd.DataFrame:
    """Baseline-only count of wet days (pr >= 1 mm), per group (e.g. cell, model).

    The sample size `wet_day_p95`'s percentile is estimated from -- a small
    count makes that threshold, and everything H4 derives from it, noisy.
    """
    baseline = daily[daily[period_col] == baseline_label]
    group_cols = [c for c in baseline.columns if c not in ("date", value_col, period_col)]
    wet = baseline[baseline[value_col] >= WET_DAY_THRESHOLD_MM]
    return wet.groupby(group_cols, as_index=False).agg(n_wet_days=(value_col, "size"))


def exceedance_frequency(
    daily: pd.DataFrame, p95: pd.DataFrame, value_col: str = "pr_mm"
) -> pd.DataFrame:
    """Fraction of wet days exceeding each group's baseline P95, pooled over `daily`'s period.

    Spec H4: baseline exceedance frequency is ~5% of wet days "by construction"
    -- a single ratio over the whole baseline (like F_D for drought, Spec H2),
    not an average of per-year ratios. A per-year average is biased at cells
    with few wet days per year (many 0/0-adjacent years dominate the mean),
    so this pools counts across every row `daily` provides before dividing.
    Call separately per scenario/period to get baseline vs future frequency.

    `daily` may cover any subset of dates; `p95` (from `wet_day_p95`) is
    joined on every one of its columns except `p95_mm`, so the same
    baseline threshold is applied regardless of which period `daily` is.
    """
    join_cols = [c for c in p95.columns if c != "p95_mm"]
    d = daily.merge(p95, on=join_cols, how="left")
    wet = d[d[value_col] >= WET_DAY_THRESHOLD_MM].copy()
    wet["exceeds"] = wet[value_col] > wet["p95_mm"]

    out = wet.groupby(join_cols, as_index=False).agg(
        n_wet=(value_col, "size"), n_exceed=("exceeds", "sum")
    )
    out["exceedance_frequency"] = out["n_exceed"] / out["n_wet"]
    return out


def annual_rx5day(daily: pd.DataFrame, value_col: str = "pr_mm") -> pd.DataFrame:
    """Annual maximum 5-day precipitation total, per group.

    Uses `craei.rolling.rolling_sum_by_group` (vectorized cumsum), not
    `groupby(...).transform(...)` -- see that module's docstring: the naive
    `transform` pattern risks the same `MemoryError` found in COMANDO 17's
    SPEI accumulation on data with many groups, even though this call has
    not itself crashed (COMANDOS 15/16's per-country/model/scenario chunking
    kept each call's group count small enough).
    """
    group_cols = [c for c in daily.columns if c not in ("date", value_col)]
    d = daily.sort_values(group_cols + ["date"]).reset_index(drop=True)
    d["roll5"] = rolling_sum_by_group(d, group_cols, "date", value_col, window=5)
    d["year"] = d["date"].dt.year
    return d.groupby(group_cols + ["year"], as_index=False).agg(value=("roll5", "max"))
