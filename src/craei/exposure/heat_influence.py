"""Leave-one-cell-out influence on heat exposure shares (W3c, O19). Pure functions.

The hazard is defined per 0.5-degree cell, so plants in one cell share the same delta.
Dropping one cell at a time shows how much a group's share depends on a single cell.
"""
from __future__ import annotations

import pandas as pd

KEYS = ["group", "fleet", "scenario"]
CELL = ["cell_lat", "cell_lon"]
TOP_RENAME = {
    "cell_lat": "top_cell_lat",
    "cell_lon": "top_cell_lon",
    "shift_pp": "top_shift_pp",
    "cell_gw_pct": "top_cell_gw_pct",
}


def leave_one_cell_out(
    df: pd.DataFrame, cells: pd.DataFrame, group_col: str | None, threshold: int = 30
) -> pd.DataFrame:
    """Median-over-GCM share of GW exposed, with each occupied cell removed in turn."""
    key = cells[["plant_uid", *CELL]].drop_duplicates("plant_uid")
    base = df.merge(key, on="plant_uid", how="left", validate="many_to_one")
    if base[CELL].isna().any().any():
        raise ValueError("some plants have no cell")
    group = base[group_col] if group_col else "all_thermal"
    exposed = base["capacity_mw"].where(base["delta"] >= threshold, 0.0)
    base = base.assign(group=group, mw_e=exposed)

    per = base.groupby([*KEYS, "model", *CELL], as_index=False).agg(
        mw=("capacity_mw", "sum"), mw_e=("mw_e", "sum")
    )
    tot = per.groupby([*KEYS, "model"], as_index=False).agg(
        mw_all=("mw", "sum"), e_all=("mw_e", "sum")
    )
    per = per.merge(tot, on=[*KEYS, "model"], validate="many_to_one")
    rest = (per["mw_all"] - per["mw"]).where(lambda s: s > 1e-9)
    per["pct_loo"] = 100.0 * (per["e_all"] - per["mw_e"]) / rest
    tot["pct"] = 100.0 * tot["e_all"] / tot["mw_all"]
    med = tot.groupby(KEYS)["pct"].median().rename("pct_median").reset_index()

    loo = per.groupby([*KEYS, *CELL], as_index=False).agg(
        pct_loo=("pct_loo", "median"), mw_cell=("mw", "first")
    )
    loo = loo.merge(med, on=KEYS, validate="many_to_one")
    loo["shift_pp"] = loo["pct_loo"] - loo["pct_median"]
    loo["abs_shift"] = loo["shift_pp"].abs()
    loo["cell_gw_pct"] = 100.0 * loo["mw_cell"] / loo.groupby(KEYS)["mw_cell"].transform("sum")

    agg = loo.groupby(KEYS, as_index=False).agg(
        n_cells=("mw_cell", "size"),
        gw_total=("mw_cell", "sum"),
        loo_min=("pct_loo", "min"),
        loo_max=("pct_loo", "max"),
    )
    agg["gw_total"] = agg["gw_total"] / 1000.0
    order = loo.sort_values(
        ["abs_shift", *CELL], ascending=[False, True, True], na_position="last"
    )
    top = order.groupby(KEYS, as_index=False).head(1)
    top = top[[*KEYS, *CELL, "shift_pp", "cell_gw_pct"]].rename(columns=TOP_RENAME)
    out = agg.merge(med, on=KEYS, validate="one_to_one")
    out = out.merge(top, on=KEYS, validate="one_to_one")
    out["threshold"] = threshold
    return out