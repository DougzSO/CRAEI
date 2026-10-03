"""Relative (baseline-percentile) heat threshold, TH1 (D91). Pure functions.

Unlike TX35/TX40 (fixed 35/40 degC, craei.hazards.heat), TH1 asks whether the
main H1 results are an artifact of the absolute threshold: per cell and GCM,
the threshold is the 95th percentile of daily tasmax pooled over every day of
the baseline (1985-2014, no calendar-day window); the same fixed threshold
then counts days at or above it in the baseline and in 2041-2070 of every
scenario of that GCM. Never an operating limit.
"""

import pandas as pd


def baseline_percentile_threshold(
    daily_baseline: pd.DataFrame, percentile: float, group_cols: list[str],
    value_col: str = "tasmax_c",
) -> pd.DataFrame:
    """Per `group_cols` (e.g. cell_lat, cell_lon, model), the `percentile` of
    `value_col` pooled over every day of `daily_baseline` (no day-of-year window).
    """
    return (
        daily_baseline.groupby(group_cols)[value_col]
        .quantile(percentile / 100.0)
        .rename("threshold_c")
        .reset_index()
    )


def annual_days_at_or_above(
    daily: pd.DataFrame, thresholds: pd.DataFrame, group_cols: list[str],
    value_col: str = "tasmax_c",
) -> pd.DataFrame:
    """Annual count of days with `value_col` >= the group's threshold.

    `thresholds` has one row per `group_cols` (e.g. cell_lat, cell_lon,
    model); `daily` may carry extra constant columns (scenario, period).
    Raises if any row has no matching threshold.
    """
    d = daily.merge(thresholds, on=group_cols, how="left")
    if d["threshold_c"].isna().any():
        raise ValueError("rows without a matching threshold")
    d["year"] = d["date"].dt.year
    out_group = [c for c in d.columns if c not in ("date", value_col, "threshold_c")]
    d["exceed"] = (d[value_col] >= d["threshold_c"]).astype(int)
    out = d.groupby(out_group, as_index=False)["exceed"].sum()
    return out.rename(columns={"exceed": "value"})


def baseline_exceedance_fraction(
    daily_baseline: pd.DataFrame, thresholds: pd.DataFrame, group_cols: list[str],
    value_col: str = "tasmax_c",
) -> pd.DataFrame:
    """Fraction of baseline days at or above the threshold, per `group_cols`."""
    d = daily_baseline.merge(thresholds, on=group_cols, how="left")
    if d["threshold_c"].isna().any():
        raise ValueError("rows without a matching threshold")
    d["exceed"] = (d[value_col] >= d["threshold_c"]).astype(int)
    out = d.groupby(group_cols, as_index=False)["exceed"].mean()
    return out.rename(columns={"exceed": "fraction"})