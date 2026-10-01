"""W3f-1: Table 1 of Axis 1, joining existing W3 tables (no new estimation).

Bootstrap bounds follow the O25 rule: reported only if the fleet has at least
MIN_CELLS cells and nan_frac is 0; otherwise the row is labelled descriptive.
"""

import numpy as np
import pandas as pd

KEY = ["group", "fleet", "scenario", "threshold"]
MIN_CELLS = 10
K_SHOW = (1, 3, 5)
THRESHOLDS = (20, 30, 40)
SUMMARY_COLS = KEY + [
    "gw_total", "n_units", "n_plants", "n_gcm", "pct_min", "pct_median",
    "pct_max", "gw_min", "gw_median", "gw_max",
]
INFLUENCE_COLS = KEY + ["n_cells", "top_cell_gw_pct", "loo_min", "loo_max"]


def pivot_agreement(agr, k_show=K_SHOW):
    """Wide agreement table: share and GW exposed in >= k of the GCMs."""
    sub = agr[agr["k_min"].isin(k_show)]
    wide = sub.pivot_table(
        index=KEY, columns="k_min", values=["pct_gw", "gw_exposed"], aggfunc="first"
    )
    wide.columns = [f"{v}_k{k}" for v, k in wide.columns]
    return wide.reset_index()


def apply_o25(boot, min_cells=MIN_CELLS):
    """Keep bootstrap bounds (whole pp) only where the O25 rule allows."""
    out = boot.copy()
    nan_frac = pd.to_numeric(out["nan_frac"], errors="coerce")
    ok = (out["n_cells_fleet"] >= min_cells) & (nan_frac == 0)
    out["boot_reported"] = ok
    for col in ("boot_p025", "boot_p975"):
        out[col + "_pp"] = np.where(ok, out[col].round(0), np.nan)
    keep = KEY + ["n_cells_fleet", "boot_reported", "boot_p025_pp", "boot_p975_pp"]
    return out[keep]


def build_table1(summary, agreement, influence, boot, thresholds=THRESHOLDS,
                 min_cells=MIN_CELLS):
    """One row per group, fleet, scenario and threshold (left join on summary)."""
    base = summary[summary["threshold"].isin(thresholds)][SUMMARY_COLS]
    tab = base.merge(pivot_agreement(agreement), on=KEY, how="left")
    tab = tab.merge(influence[INFLUENCE_COLS], on=KEY, how="left")
    tab = tab.merge(apply_o25(boot, min_cells), on=KEY, how="left")
    if len(tab) != len(base):
        raise ValueError("merge changed the row count (duplicated keys?)")
    tab["boot_reported"] = tab["boot_reported"].eq(True)
    tab["label"] = np.where(tab["boot_reported"], "range_reported", "descriptive")
    return tab.sort_values(KEY).reset_index(drop=True)