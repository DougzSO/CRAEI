"""Brazil fleet table by technology, fuel and fleet, from plant_units (C29).

Pure functions over the unit-level table (D78, D80, D81). No hazards involved.
"""

import pandas as pd

FLEETS = ["operating", "planned_adv", "planned_early"]
IN_SCOPE_TECH = ("hydro", "thermal_air_only", "thermal_water_dependent")
KEYS = ["tech_class", "fuel_class", "hydro_type", "bio_subtype", "fleet"]


def scope_units(units: pd.DataFrame, country: str = "BRA") -> pd.DataFrame:
    """Units of one country in the article scope (hydro and thermal only)."""
    keep = (units["country"] == country) & units["tech_class"].isin(IN_SCOPE_TECH)
    return units[keep].copy()


def apply_foreign_share(
    units: pd.DataFrame, uids: set, total_mw: float, foreign_mw: float
) -> pd.DataFrame:
    """Scale the unit capacities of `uids` so the plant keeps total - foreign MW.

    Raises ValueError if the current plant capacity differs from `total_mw`.
    The input table is not modified.
    """
    out = units.copy()
    mask = out["plant_uid"].isin(list(uids))
    current = float(out.loc[mask, "capacity_mw"].sum())
    if abs(current - total_mw) > 1e-6:
        raise ValueError(f"plant capacity {current} MW differs from expected {total_mw} MW")
    factor = (total_mw - foreign_mw) / total_mw
    out.loc[mask, "capacity_mw"] = out.loc[mask, "capacity_mw"] * factor
    return out


def fleet_table(units: pd.DataFrame) -> pd.DataFrame:
    """Long table: units, plants and capacity by KEYS (missing subtypes become '-')."""
    d = units.copy()
    for col in ("hydro_type", "bio_subtype"):
        d[col] = d[col].where(d[col].notna(), "-")
    g = d.groupby(KEYS, as_index=False).agg(
        units=("capacity_mw", "size"),
        plants=("plant_uid", "nunique"),
        capacity_mw=("capacity_mw", "sum"),
    )
    g["capacity_gw"] = g["capacity_mw"] / 1000
    return g