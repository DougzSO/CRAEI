"""GCM-exclusion sensitivity (W3f-6). Pure functions over per-GCM exposure shares.

Input columns (w3_heat_curves_by_gcm): group, fleet, scenario, threshold, model, pct_gw.
With 4 GCMs the median is the mean of the two middle values; with 3 it is the middle one.
"""

import numpy as np
import pandas as pd

REF = "all5"
KEYS = ["group", "fleet", "scenario", "threshold"]
CKEYS = ["group", "planned_fleet", "scenario", "threshold"]
RKEYS = ["fleet", "scenario", "threshold"]
FUELS = ("bioenergy", "coal", "gas", "multi_fuel", "nuclear", "oil")


def exclusion_sets(models, pair=("ukesm1-0-ll", "ipsl-cm6a-lr")):
    """name -> kept models: all, drop each one, drop the pair."""
    models = sorted(models)
    if not set(pair) <= set(models):
        raise ValueError("pair must be among the models")
    sets = {REF: models}
    for m in models:
        sets["drop_" + m] = [x for x in models if x != m]
    sets["drop_" + "+".join(pair)] = [x for x in models if x not in pair]
    return sets


def summarize_exclusions(by_gcm, sets):
    """min/median/max of pct_gw over the kept GCMs, per exclusion set."""
    parts = []
    for name, keep in sets.items():
        g = (by_gcm[by_gcm["model"].isin(keep)].groupby(KEYS)["pct_gw"]
             .agg(n_gcm="count", pct_min="min", pct_median="median", pct_max="max")
             .reset_index())
        parts.append(g.assign(exclusion=name))
    out = pd.concat(parts, ignore_index=True)
    ref = out.loc[out["exclusion"] == REF, KEYS + ["pct_median"]]
    ref = ref.rename(columns={"pct_median": "ref_median"})
    out = out.merge(ref, on=KEYS, how="left")
    out["shift_pp"] = out["pct_median"] - out["ref_median"]
    return out


def contrast_exclusions(by_gcm, sets):
    """Paired planned - operating difference per GCM, summarized per exclusion set."""
    op = by_gcm[by_gcm["fleet"] == "operating"]
    op = op[["group", "scenario", "threshold", "model", "pct_gw"]]
    op = op.rename(columns={"pct_gw": "pct_op"})
    pl = by_gcm[by_gcm["fleet"] != "operating"]
    pl = pl.rename(columns={"fleet": "planned_fleet", "pct_gw": "pct_pl"})
    m = pl.merge(op, on=["group", "scenario", "threshold", "model"], how="inner")
    m["diff"] = m["pct_pl"] - m["pct_op"]
    m["pos"] = m["diff"] > 0
    m["neg"] = m["diff"] < 0
    parts = []
    for name, keep in sets.items():
        g = (m[m["model"].isin(keep)].groupby(CKEYS)
             .agg(n_gcm=("diff", "count"), diff_min=("diff", "min"),
                  diff_median=("diff", "median"), diff_max=("diff", "max"),
                  n_pos=("pos", "sum"), n_neg=("neg", "sum"))
             .reset_index())
        parts.append(g.assign(exclusion=name))
    out = pd.concat(parts, ignore_index=True)
    ref = out.loc[out["exclusion"] == REF, CKEYS + ["diff_median"]]
    ref = ref.rename(columns={"diff_median": "ref_diff_median"})
    out = out.merge(ref, on=CKEYS, how="left")
    out["sign_changed"] = np.sign(out["diff_median"]) != np.sign(out["ref_diff_median"])
    return out


def fuel_ranking(summary, fuels=FUELS):
    """Order of fuel groups by median share, per fleet/scenario/threshold/exclusion."""
    s = summary[summary["group"].isin(fuels)]
    wide = s.pivot_table(index=RKEYS + ["exclusion"], columns="group",
                         values="pct_median", aggfunc="first").reset_index()
    cols = [f for f in fuels if f in wide.columns]

    def _order(row):
        r = row[cols].astype(float).dropna()
        return " > ".join(r.sort_values(ascending=False, kind="stable").index)

    wide["order"] = wide.apply(_order, axis=1)
    if "bioenergy" in cols and "gas" in cols:
        wide["bio_gt_gas"] = wide["bioenergy"] > wide["gas"]
    ref = wide.loc[wide["exclusion"] == REF, RKEYS + ["order"]]
    ref = ref.rename(columns={"order": "ref_order"})
    wide = wide.merge(ref, on=RKEYS, how="left")
    wide["order_changed"] = wide["order"] != wide["ref_order"]
    return wide