"""Extreme heat daily indices (Spec §1.4 H1, §3 Step 4; COMANDO 15).

TX35 = (1/30) * sum_y sum_d 1[TX_{y,d} >= 35C], reported per year (the /30
normalisation is applied later, at the exposure-aggregation stage, not
here); TX40 is the same count at 40C. N35 is the same count aggregated
monthly instead of annually (used by the compound metric, Spec §1.6).

Inputs are degrees Celsius; ISIMIP tasmax arrives in Kelvin and must be
converted by the caller (`pet.KELVIN_OFFSET_C`).
"""

import pandas as pd


def annual_hot_day_counts(
    daily: pd.DataFrame, threshold_c: float, value_col: str = "tasmax_c"
) -> pd.DataFrame:
    """Annual count of days with `value_col` >= threshold_c.

    Grouped by every column except `date`/`value_col` (e.g. cell_lat,
    cell_lon, model, scenario, period). Used for TX35 (threshold_c=35) and
    TX40 (threshold_c=40).
    """
    group_cols = [c for c in daily.columns if c not in ("date", value_col)]
    d = daily.copy()
    d["year"] = d["date"].dt.year
    return d.groupby(group_cols + ["year"], as_index=False).agg(
        value=(value_col, lambda s: int((s >= threshold_c).sum()))
    )


def monthly_hot_day_counts(
    daily: pd.DataFrame, threshold_c: float, value_col: str = "tasmax_c"
) -> pd.DataFrame:
    """Monthly count of days with `value_col` >= threshold_c (N35 at threshold_c=35)."""
    group_cols = [c for c in daily.columns if c not in ("date", value_col)]
    d = daily.copy()
    d["month"] = d["date"].values.astype("datetime64[M]")
    return d.groupby(group_cols + ["month"], as_index=False).agg(
        value=(value_col, lambda s: int((s >= threshold_c).sum()))
    )
