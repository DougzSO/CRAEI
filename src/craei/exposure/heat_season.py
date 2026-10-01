"""Seasonal profile of heat exposure (W3e, O16). Pure functions, no I/O.

Monthly delta N35 (days per month, future minus baseline, mean over years) averaged over
the cells of a group with capacity weights. Summed over the months present it equals the
annual delta TX35 of the same weighted cells (checked in the script against plant_hazards).
"""
from __future__ import annotations

import pandas as pd

CELL = ["cell_lat", "cell_lon"]
BASELINE = "baseline"
FUTURE = "future"


def _year_means(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    g = df.groupby(keys)["value"].agg(["mean", "size"])
    if g["size"].nunique() != 1:
        raise ValueError("cells differ in number of years")
    return g["mean"].rename("v").reset_index()


def monthly_profile(n35: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Capacity-weighted monthly N35 profile per GCM and scenario.

    n35: cell_lat, cell_lon, model, scenario, period, year, month (timestamp), value.
    weights: cell_lat, cell_lon, mw (capacity of the group in the cell).
    """
    w = weights.groupby(CELL, as_index=False)["mw"].sum()
    seen = w.merge(n35[CELL].drop_duplicates(), on=CELL, how="left", indicator=True)
    if (seen["_merge"] != "both").any():
        raise ValueError("weights cells without n35 rows")
    df = n35.merge(w[CELL], on=CELL, how="inner")
    df = df.assign(cal_month=df["month"].dt.month)
    base = df[df["period"] == BASELINE]
    fut = df[df["period"] == FUTURE]
    if base.duplicated([*CELL, "model", "year", "cal_month"]).any():
        raise ValueError("duplicated baseline rows")
    b = _year_means(base, [*CELL, "model", "cal_month"]).rename(columns={"v": "base"})
    f = _year_means(fut, [*CELL, "model", "scenario", "cal_month"])
    f = f.rename(columns={"v": "fut"})
    x = f.merge(b, on=[*CELL, "model", "cal_month"], how="left", validate="many_to_one")
    if x["base"].isna().any():
        raise ValueError("future rows without baseline")
    x = x.merge(w, on=CELL, validate="many_to_one")
    x["delta"] = x["fut"] - x["base"]
    for c in ("base", "fut", "delta"):
        x[f"{c}_w"] = x[c] * x["mw"]
    keys = ["model", "scenario", "cal_month"]
    g = x.groupby(keys, as_index=False).agg(
        mw=("mw", "sum"),
        n_cells=("mw", "size"),
        base_w=("base_w", "sum"),
        fut_w=("fut_w", "sum"),
        delta_w=("delta_w", "sum"),
    )
    out = pd.DataFrame({
        "model": g["model"],
        "scenario": g["scenario"],
        "month": g["cal_month"],
        "gw": g["mw"] / 1000.0,
        "n_cells": g["n_cells"],
        "base_n35": g["base_w"] / g["mw"],
        "fut_n35": g["fut_w"] / g["mw"],
        "delta_n35": g["delta_w"] / g["mw"],
    })
    tot = out.groupby(["model", "scenario"])["delta_n35"].transform("sum")
    out["delta_annual"] = tot
    out["share_of_annual"] = out["delta_n35"] / tot.where(tot.abs() > 1e-9)
    return out


def summarise_gcms(prof: pd.DataFrame) -> pd.DataFrame:
    """Min, median and max over GCMs of the monthly delta and of its annual share."""
    out = prof.groupby(["scenario", "month"]).agg(
        n_gcm=("model", "nunique"),
        base_median=("base_n35", "median"),
        delta_min=("delta_n35", "min"),
        delta_median=("delta_n35", "median"),
        delta_max=("delta_n35", "max"),
        share_min=("share_of_annual", "min"),
        share_median=("share_of_annual", "median"),
        share_max=("share_of_annual", "max"),
    )
    return out.reset_index()