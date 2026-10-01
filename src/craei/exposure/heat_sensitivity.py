"""W3f-4: sensitivity of the Axis 1 headline to analyst choices (long format, D85).

Pure functions. Each alternative is summarised exactly like the reference (min, median,
max over GCMs) and compared row by row with it. Ranges are structural, not intervals.
"""
from __future__ import annotations

import pandas as pd

from craei.exposure.heat_fuel import KEY

PLANT_KEY = ["plant_uid", "fleet", "scenario", "model"]
STATS = ["pct_min", "pct_median", "pct_max"]
PLANT_WEIGHT_MW = 1000.0


def plant_weighted(df: pd.DataFrame, group_col: str | None) -> pd.DataFrame:
    """One row per plant, fleet, scenario, GCM (and group), each plant weighing 1.

    With capacity_mw = 1000, exposure_curves returns plant counts in the gw columns.
    """
    cols = PLANT_KEY + ([group_col] if group_col else [])
    out = df.drop_duplicates(cols).copy()
    out["capacity_mw"] = PLANT_WEIGHT_MW
    return out


def compare(ref: pd.DataFrame, alt: pd.DataFrame, choice: str) -> pd.DataFrame:
    """Alternative minus reference (median, pp) and overlap of the GCM ranges."""
    m = ref[KEY + STATS].merge(
        alt[KEY + STATS], on=KEY, how="inner", suffixes=("_ref", "_alt"),
        validate="one_to_one",
    )
    m["diff_median_pp"] = m["pct_median_alt"] - m["pct_median_ref"]
    m["ranges_overlap"] = (m["pct_min_alt"] <= m["pct_max_ref"]) & (
        m["pct_min_ref"] <= m["pct_max_alt"]
    )
    m.insert(0, "choice", choice)
    return m