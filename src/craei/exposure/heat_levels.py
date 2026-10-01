"""Level classes of TX35 for thermal and hydro units (W3g; D88, O28). Pure functions."""

import numpy as np
import pandas as pd

from craei.inventory.fleet import apply_foreign_share

LEVEL_CUTS = (10.0, 30.0, 60.0)
LEVEL_LABELS = ("low", "medium", "high", "extreme")
DELTA_CUTS = (10.0, 20.0, 30.0)
DELTA_LABELS = ("d_lt10", "d10_20", "d20_30", "d_ge30")
FUELS = ("gas", "oil", "coal", "nuclear", "bioenergy", "multi_fuel")
TECH_THERMAL = ("thermal_water_dependent", "thermal_air_only")
GROUP_KEYS = ["group", "fleet", "itaipu", "scenario", "model"]
MIN_CELLS = 10


def classify(values, cuts, labels):
    """Exclusive bins: value >= cut goes to the next class. NaN raises."""
    v = np.asarray(values, dtype=float)
    if np.isnan(v).any():
        raise ValueError("NaN in values to classify")
    idx = np.digitize(v, cuts)
    lab = np.asarray(labels, dtype=object)[idx]
    return pd.Categorical(lab, categories=list(labels))


def cell_values(ix):
    """Mean annual TX35 per (cell, model): baseline, future per scenario, delta."""
    k = ["cell_lat", "cell_lon", "model"]
    b = ix[ix["period"] == "baseline"].groupby(k, as_index=False)["value"].mean()
    b = b.rename(columns={"value": "base"})
    f = ix[ix["period"] == "future"].groupby(k + ["scenario"], as_index=False)["value"].mean()
    f = f.rename(columns={"value": "fut"})
    out = f.merge(b, on=k, how="left")
    if out["base"].isna().any():
        raise ValueError("future rows without a baseline")
    out["delta"] = out["fut"] - out["base"]
    return out


def with_itaipu_versions(units, itaipu_uids, total_mw=14000.0, foreign_mw=7000.0):
    """Hydro in two versions (a: whole asset, b: Brazilian share); others labelled na."""
    b = apply_foreign_share(units, set(itaipu_uids), total_mw, foreign_mw)
    hyd = units["tech_class"] == "hydro"
    parts = [units[~hyd].assign(itaipu="na"), units[hyd].assign(itaipu="a"),
             b[hyd].assign(itaipu="b")]
    return pd.concat(parts, ignore_index=True)


def unit_values(units, plant_cell, cvals):
    """Unit x (GCM, scenario) rows with the TX35 values of the plant cell."""
    pc = plant_cell.drop_duplicates("plant_uid")[["plant_uid", "cell_lat", "cell_lon"]]
    u = units.merge(pc, on="plant_uid", how="left")
    if u[["cell_lat", "cell_lon"]].isna().any().any():
        raise ValueError("units without a cell")
    out = u.merge(cvals, on=["cell_lat", "cell_lon"], how="left")
    if out[["base", "fut", "delta"]].isna().any().any():
        raise ValueError("units without TX35 cell values")
    if out.groupby(["uid", "itaipu"]).size().nunique() != 1:
        raise ValueError("units differ in number of GCM x scenario rows")
    return out


def add_classes(df):
    out = df.copy()
    out["level_base"] = classify(out["base"], LEVEL_CUTS, LEVEL_LABELS)
    out["level_fut"] = classify(out["fut"], LEVEL_CUTS, LEVEL_LABELS)
    out["delta_class"] = classify(out["delta"], DELTA_CUTS, DELTA_LABELS)
    return out


def expand_groups(df):
    """Unit rows repeated per group: all_thermal, tech class, fuel, hydro."""
    th = df[df["tech_class"].isin(TECH_THERMAL)]
    parts = [th.assign(group="all_thermal")]
    for t in TECH_THERMAL:
        parts.append(th[th["tech_class"] == t].assign(group=t))
    for f in FUELS:
        parts.append(th[th["fuel_class"] == f].assign(group=f))
    parts.append(df[df["tech_class"] == "hydro"].assign(group="hydro"))
    return pd.concat(parts, ignore_index=True)


def gw_by_gcm(df, class_cols, categories):
    """MW per class (zeros filled) per group, fleet, itaipu, scenario, GCM."""
    keys = GROUP_KEYS + list(class_cols)
    g = df.groupby(keys, observed=True)["capacity_mw"].sum().rename("mw").reset_index()
    for c in class_cols:
        g[c] = g[c].astype(str)
    grid = df[GROUP_KEYS].drop_duplicates()
    for c in class_cols:
        grid = grid.merge(pd.DataFrame({c: list(categories[c])}), how="cross")
    out = grid.merge(g, on=keys, how="left")
    out["mw"] = out["mw"].fillna(0.0)
    tot = df.groupby(GROUP_KEYS)["capacity_mw"].sum().rename("mw_total").reset_index()
    return out.merge(tot, on=GROUP_KEYS, how="left")


def class_sum_gap(t):
    """Max |sum of class MW - total MW| over the GROUP_KEYS cells."""
    s = t.groupby(GROUP_KEYS)["mw"].sum().reset_index()
    s = s.merge(t[GROUP_KEYS + ["mw_total"]].drop_duplicates(), on=GROUP_KEYS)
    return float((s["mw"] - s["mw_total"]).abs().max())


def summarise_gw(t, class_cols):
    """min / median / max over GCMs of GW and share, per class."""
    keys = [k for k in GROUP_KEYS if k != "model"] + list(class_cols)
    t = t.assign(pct=100.0 * t["mw"] / t["mw_total"])
    out = t.groupby(keys).agg(
        n_gcm=("model", "nunique"), gw_total=("mw_total", "first"),
        gw_min=("mw", "min"), gw_median=("mw", "median"), gw_max=("mw", "max"),
        pct_min=("pct", "min"), pct_median=("pct", "median"), pct_max=("pct", "max"),
    ).reset_index()
    for c in ("gw_total", "gw_min", "gw_median", "gw_max"):
        out[c] = out[c] / 1000.0
    return out


def agreement_k(df, class_col, labels=LEVEL_LABELS, ks=(1, 3, 5)):
    """GW of units in a class in at least k GCMs (classes by k are not exclusive)."""
    keys = [k for k in GROUP_KEYS if k != "model"]
    d = df.assign(cls=df[class_col].astype(str))
    cnt = d.groupby(keys + ["uid", "cls"]).agg(
        n=("model", "size"), mw=("capacity_mw", "first")).reset_index()
    tot = d.groupby(keys + ["uid"]).agg(mw=("capacity_mw", "first")).reset_index()
    tot = tot.groupby(keys)["mw"].sum().rename("mw_total").reset_index()
    grid = tot.merge(pd.DataFrame({"cls": list(labels)}), how="cross")
    for k in ks:
        s = cnt[cnt["n"] >= k].groupby(keys + ["cls"])["mw"].sum().rename("mwk")
        grid = grid.merge(s.reset_index(), on=keys + ["cls"], how="left")
        grid["mwk"] = grid["mwk"].fillna(0.0)
        grid[f"gw_k{k}"] = grid["mwk"] / 1000.0
        grid[f"pct_k{k}"] = 100.0 * grid["mwk"] / grid["mw_total"]
        grid = grid.drop(columns="mwk")
    return grid


def level_classes_table(g):
    """Future and baseline level classes with range and agreement k.

    The baseline does not depend on the scenario; ssp370 rows are used for it.
    """
    cats = {"level_base": LEVEL_LABELS, "level_fut": LEVEL_LABELS}
    keys = [k for k in GROUP_KEYS if k != "model"]
    parts = []
    for col, frame, period in (("level_fut", g, "future"),
                               ("level_base", g[g["scenario"] == "ssp370"], "baseline")):
        s = summarise_gw(gw_by_gcm(frame, [col], cats), [col]).rename(columns={col: "class"})
        k = agreement_k(frame, col).rename(columns={"cls": "class"})
        s = s.merge(k.drop(columns="mw_total"), on=keys + ["class"], how="left")
        s["period"] = period
        if period == "baseline":
            s["scenario"] = "baseline"
        parts.append(s)
    return pd.concat(parts, ignore_index=True)


def fleet_meta(g, min_cells=MIN_CELLS):
    """Units, cells and the O25 label per group, fleet, itaipu version."""
    t = g.assign(cell=g["cell_lat"].astype(str) + "_" + g["cell_lon"].astype(str))
    m = t.groupby(["group", "fleet", "itaipu"]).agg(
        n_units=("uid", "nunique"), n_cells=("cell", "nunique")).reset_index()
    m["label"] = np.where(m["n_cells"] >= min_cells, "range_reported", "descriptive")
    return m


def cell_class_table(cvals):
    """Per cell and scenario: class of the median over GCMs and GCMs in that class."""
    c = cvals.copy()
    c["cls"] = np.asarray(classify(c["fut"], LEVEL_CUTS, LEVEL_LABELS)).astype(str)
    keys = ["cell_lat", "cell_lon", "scenario"]
    g = c.groupby(keys).agg(
        n_gcm=("model", "nunique"), base_median=("base", "median"),
        fut_median=("fut", "median"), delta_median=("delta", "median")).reset_index()
    g["class_median"] = np.asarray(
        classify(g["fut_median"], LEVEL_CUTS, LEVEL_LABELS)).astype(str)
    g["base_class_median"] = np.asarray(
        classify(g["base_median"], LEVEL_CUTS, LEVEL_LABELS)).astype(str)
    g["delta_class_median"] = np.asarray(
        classify(g["delta_median"], DELTA_CUTS, DELTA_LABELS)).astype(str)
    m = c.merge(g[keys + ["class_median"]], on=keys)
    m["same"] = m["cls"] == m["class_median"]
    same = m.groupby(keys)["same"].sum().rename("n_gcm_same").reset_index()
    return g.merge(same, on=keys)


def cell_gw(u):
    """GW per cell: thermal and hydro, operating and planned (units with cell columns)."""
    fam = pd.Series(np.where(u["tech_class"] == "hydro", "hydro", "thermal"), index=u.index)
    fl = pd.Series(np.where(u["fleet"] == "operating", "operating", "planned"), index=u.index)
    t = u.assign(col="gw_" + fam + "_" + fl)
    p = t.pivot_table(index=["cell_lat", "cell_lon"], columns="col", values="capacity_mw",
                      aggfunc="sum", fill_value=0.0) / 1000.0
    p.columns.name = None
    return p.reset_index()