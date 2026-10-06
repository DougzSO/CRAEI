"""Heat exposure of the thermal fleet by fuel (W3, axis 1). Pure functions, no I/O.

Unit of analysis: one generating unit (plant_units), linked to the plant-level hazard
row by plant_uid. A unit is exposed, for one GCM and scenario, when its plant's delta
is >= the threshold. Shares are capacity-weighted and kept per GCM, so the spread
between GCMs is reported next to the median (D85).
"""
from __future__ import annotations

import pandas as pd
from craei.config import load_params

THERMAL_FUELS = ("gas", "oil", "coal", "nuclear", "bioenergy", "multi_fuel")
THRESHOLDS = tuple(int(x) for x in load_params()["heat_sensitivity_grid"]["value"])
POOLED_PLANNED = "planned_all"
PLANNED_FLEETS = (POOLED_PLANNED, "planned_adv", "planned_early")
KEY = ["group", "fleet", "scenario", "threshold"]


def build_unit_hazard(
    units: pd.DataFrame,
    hazards: pd.DataFrame,
    hazard: str = "TX35",
    country: str = "BRA",
) -> pd.DataFrame:
    """Thermal units of one country x hazard rows (one row per unit, GCM, scenario)."""
    sel = units[(units["country"] == country) & units["fuel_class"].isin(THERMAL_FUELS)]
    haz = hazards.loc[
        hazards["hazard"] == hazard, ["plant_uid", "model", "scenario", "delta"]
    ]
    if haz.duplicated(["plant_uid", "model", "scenario"]).any():
        raise ValueError("duplicate (plant_uid, model, scenario) rows in hazards")
    uids = set(sel["plant_uid"])
    absent = uids - set(haz["plant_uid"])
    if absent:
        raise ValueError(f"{len(absent)} plants have no {hazard} row; define the policy first")
    sizes = haz[haz["plant_uid"].isin(uids)].groupby("plant_uid").size()
    if sizes.nunique() != 1:
        raise ValueError("plants differ in number of GCM x scenario rows")
    out = sel.merge(haz, on="plant_uid", how="inner")
    if out["delta"].isna().any():
        raise ValueError("NaN delta among the selected plants")
    return out.reset_index(drop=True)


def add_pooled_planned(df: pd.DataFrame) -> pd.DataFrame:
    """Append a pooled fleet (planned_adv + planned_early) labelled planned_all."""
    planned = df[df["fleet"].str.startswith("planned")]
    if planned.empty:
        return df.copy()
    return pd.concat([df, planned.assign(fleet=POOLED_PLANNED)], ignore_index=True)


def exposure_curves(
    df: pd.DataFrame, group_col: str | None, thresholds: tuple[int, ...] = THRESHOLDS
) -> pd.DataFrame:
    """GW and share of GW with delta >= threshold, per group, fleet, scenario, GCM."""
    group = df[group_col] if group_col else "all_thermal"
    base = df.assign(group=group)
    keys = ["group", "fleet", "scenario", "model"]
    parts = []
    for t in thresholds:
        flag = base["delta"] >= t
        tmp = base.assign(
            mw_exp=base["capacity_mw"].where(flag, 0.0), n_exp=flag.astype(int)
        )
        g = tmp.groupby(keys, dropna=False).agg(
            mw_total=("capacity_mw", "sum"),
            mw_exp=("mw_exp", "sum"),
            n_units=("capacity_mw", "size"),
            n_plants=("plant_uid", "nunique"),
            n_exp=("n_exp", "sum"),
        )
        g = g.reset_index()
        g["threshold"] = t
        parts.append(g)
    out = pd.concat(parts, ignore_index=True)
    out["gw_total"] = out.pop("mw_total") / 1000.0
    out["gw_exposed"] = out.pop("mw_exp") / 1000.0
    out["pct_gw"] = 100.0 * out["gw_exposed"] / out["gw_total"]
    return out


def summarise_gcms(curves: pd.DataFrame) -> pd.DataFrame:
    """Min, median and max over GCMs of the share and of the exposed GW."""
    out = curves.groupby(KEY, dropna=False).agg(
        gw_total=("gw_total", "first"),
        gw_total_min=("gw_total", "min"),
        gw_total_max=("gw_total", "max"),
        n_units=("n_units", "first"),
        n_plants=("n_plants", "first"),
        n_gcm=("model", "nunique"),
        pct_min=("pct_gw", "min"),
        pct_median=("pct_gw", "median"),
        pct_max=("pct_gw", "max"),
        gw_min=("gw_exposed", "min"),
        gw_median=("gw_exposed", "median"),
        gw_max=("gw_exposed", "max"),
    )
    out = out.reset_index()
    if ((out["gw_total_max"] - out["gw_total_min"]).abs() > 1e-9).any():
        raise ValueError("group capacity differs between GCMs")
    return out.drop(columns=["gw_total_min", "gw_total_max"])


def wide_by_gcm(curves: pd.DataFrame) -> pd.DataFrame:
    """Share of GW per GCM, one column per GCM (raises if a key is duplicated)."""
    wide = curves.set_index([*KEY, "model"])["pct_gw"].unstack("model")
    wide.columns = [f"pct_{m}" for m in wide.columns]
    return wide.reset_index()


def leave_one_gcm_out(curves: pd.DataFrame) -> pd.DataFrame:
    """Range of the median share when each GCM is dropped in turn."""
    parts = []
    for m in sorted(curves["model"].unique()):
        sub = curves[curves["model"] != m]
        med = sub.groupby(KEY, dropna=False)["pct_gw"].median()
        parts.append(med.rename("pct_median").reset_index())
    long = pd.concat(parts, ignore_index=True)
    rng = long.groupby(KEY, dropna=False)["pct_median"].agg(loo_min="min", loo_max="max")
    return rng.reset_index()


def planned_vs_operating(
    curves: pd.DataFrame, planned: str = POOLED_PLANNED, operating: str = "operating"
) -> pd.DataFrame:
    """Planned minus operating share (pp) per GCM, summarised over GCMs.

    n_planned_ge counts the GCMs in which the planned share is >= the operating one.
    """
    cols = ["group", "scenario", "threshold"]
    key = [*cols, "model"]
    p = curves[curves["fleet"] == planned].set_index(key)[["pct_gw", "gw_total"]]
    p = p.rename(columns={"pct_gw": "pct_planned", "gw_total": "gw_planned"})
    o = curves[curves["fleet"] == operating].set_index(key)["pct_gw"]
    d = p.join(o.rename("pct_operating"), how="inner").reset_index()
    names = [
        "planned_fleet", *cols, "gw_planned", "n_gcm",
        "diff_min", "diff_median", "diff_max", "n_planned_ge",
    ]
    if d.empty:
        return pd.DataFrame(columns=names)
    d["diff_pp"] = d["pct_planned"] - d["pct_operating"]
    out = d.groupby(cols, dropna=False).agg(
        gw_planned=("gw_planned", "first"),
        n_gcm=("model", "nunique"),
        diff_min=("diff_pp", "min"),
        diff_median=("diff_pp", "median"),
        diff_max=("diff_pp", "max"),
        n_planned_ge=("diff_pp", lambda s: int((s >= 0).sum())),
    )
    out = out.reset_index()
    out.insert(0, "planned_fleet", planned)
    return out