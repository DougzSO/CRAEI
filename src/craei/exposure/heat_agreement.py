"""Plant-level GCM agreement on heat exposure (W3b). Pure functions, no I/O.

For each plant, k is the number of GCMs in which its delta is >= the threshold.
GW exposed in at least k GCMs is a range that needs no median: k = 1 is the upper
end (any GCM) and k = n_gcm the lower end (all GCMs), as asked by D85.
"""
from __future__ import annotations

import pandas as pd

IDS = ["group", "fleet", "scenario"]


def agreement_gw(
    df: pd.DataFrame, group_col: str | None, thresholds: tuple[int, ...] = (30,)
) -> pd.DataFrame:
    """GW and share of GW exposed in at least k_min GCMs, per group, fleet, scenario."""
    group = df[group_col] if group_col else "all_thermal"
    base = df.assign(group=group)
    n_gcm = base["model"].nunique()
    parts = []
    for t in thresholds:
        flagged = base.assign(flag=base["delta"] >= t)
        per = flagged.groupby([*IDS, "plant_uid", "model"], as_index=False).agg(
            mw=("capacity_mw", "sum"), flag=("flag", "max")
        )
        plant = per.groupby([*IDS, "plant_uid"], as_index=False).agg(
            mw=("mw", "max"), k=("flag", "sum"), n=("model", "nunique")
        )
        if (plant["n"] != n_gcm).any():
            raise ValueError("a plant is missing some GCMs")
        for k_min in range(1, n_gcm + 1):
            tmp = plant.assign(mw_exp=plant["mw"].where(plant["k"] >= k_min, 0.0))
            g = tmp.groupby(IDS, as_index=False).agg(
                mw_total=("mw", "sum"),
                mw_exp=("mw_exp", "sum"),
                n_plants=("plant_uid", "size"),
            )
            parts.append(g.assign(threshold=t, k_min=k_min))
    out = pd.concat(parts, ignore_index=True)
    out["gw_total"] = out.pop("mw_total") / 1000.0
    out["gw_exposed"] = out.pop("mw_exp") / 1000.0
    out["pct_gw"] = 100.0 * out["gw_exposed"] / out["gw_total"]
    out["n_gcm"] = n_gcm
    return out