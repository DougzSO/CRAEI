"""W3f-2: plotting table for the threshold curves (Fig. 3); no new estimation.

Extends Table 1 to the full threshold grid. Bootstrap bounds and cell counts exist only
at the thresholds computed in W3d (20, 30, 40 d); elsewhere the label says so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from craei.exposure.heat_fuel import THRESHOLDS
from craei.exposure.heat_table1 import build_table1

BOOT_THRESHOLDS = (20, 30, 40)
MONO_COLS = ("pct_min", "pct_median", "pct_max", "pct_gw_k1", "pct_gw_k3", "pct_gw_k5")


def curve_table(summary, agreement, influence, boot, thresholds=THRESHOLDS,
                boot_thresholds=BOOT_THRESHOLDS):
    """Table 1 logic on the full grid, with an explicit label where no bootstrap exists."""
    tab = build_table1(summary, agreement, influence, boot, thresholds=thresholds)
    has_boot = tab["threshold"].isin(boot_thresholds)
    tab["label"] = np.where(has_boot, tab["label"], "bootstrap_not_computed")
    return tab


def monotone_violations(tab, cols=MONO_COLS):
    """Count increases with the threshold; a share above a threshold cannot increase."""
    n = 0
    for _, g in tab.groupby(["group", "fleet", "scenario"]):
        g = g.sort_values("threshold")
        for c in cols:
            n += int((g[c].diff() > 1e-9).sum())
    return n