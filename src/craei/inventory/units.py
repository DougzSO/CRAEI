"""Unit-level plant table (D78, D79, D80; C28).

One row per kept GEM unit, with fleet, fuel_class, bio_subtype and tech_class
assigned per unit instead of per plant (plants.py takes the mode over units
and sums capacity over all units, which mis-assigns mixed plants).

The filtering mirrors inventory.plants.build_inventory exactly (same discards,
same plant_uid); tests/test_inventory_units.py guards against drift.
plants.parquet is neither read nor changed here.
"""

import pandas as pd

from craei.inventory import plants as inv

_OIL_GAS_FUEL = {"gas": "gas", "lng only": "gas", "oil": "oil", "multi fuel": "multi_fuel"}

UNIT_COLUMNS = [
    "plant_uid", "gem_row", "unit_name", "country", "fleet", "fuel_class",
    "bio_subtype", "tech_class", "water_dependent", "hydro_type", "capacity_mw",
]


def oil_gas_class(value) -> str:
    return _OIL_GAS_FUEL.get(inv._norm(value), "oil_gas_unclassified")


def _bio_token(token: str) -> str:
    t = token.strip().lower().replace("bioenergy:", "").strip()
    if t == "agricultural waste (solids)":
        return "agricultural_waste"
    if t == "paper mill wastes":
        return "paper_mill_waste"
    if t.startswith("wood & other biomass"):
        return "wood_biomass"
    return "other_bioenergy"


def bio_subtype(value) -> str:
    """One subtype if all listed fuels map to the same class, else 'bio_mixed'."""
    classes = {_bio_token(x) for x in str(value).split(",") if x.strip()}
    return classes.pop() if len(classes) == 1 else "bio_mixed"


def fuel_class(gem_type: str, oil_gas_value) -> str:
    if gem_type in ("coal", "nuclear", "bioenergy"):
        return gem_type
    if gem_type == "oil/gas":
        return oil_gas_class(oil_gas_value)
    if gem_type == "hydropower":
        return "hydro"
    if gem_type == "utility-scale solar":
        return "solar"
    return "other"


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series(pd.NA, index=df.index, dtype="object")


def _as_text(s: pd.Series) -> pd.Series:
    """Cast to str, keeping missing values missing.

    GEM text columns mix strings and numbers, which parquet cannot store.
    """
    return s.astype(object).where(s.isna(), s.astype(str))


def _kept_units(gem: pd.DataFrame, countries: dict[str, str]) -> pd.DataFrame:
    """Same filter as inventory.plants.build_inventory; returns the kept units."""
    df = gem.copy()
    iso_by_name = {v: k for k, v in countries.items()}
    df = df[df["Country/area"].isin(countries.values())].copy()
    df["iso3"] = df["Country/area"].map(iso_by_name)

    reason = pd.Series(pd.NA, index=df.index, dtype="object")
    reason[df["Latitude"].isna() | df["Longitude"].isna()] = "no_coordinate"
    reason[reason.isna() & df["Capacity (MW)"].isna()] = "no_capacity"

    west, east, south, north = inv._PRT_MAINLAND_BBOX
    is_prt_non_mainland = (df["iso3"] == "PRT") & reason.isna() & (
        (df["Longitude"] < west)
        | (df["Longitude"] > east)
        | (df["Latitude"] < south)
        | (df["Latitude"] > north)
    )
    reason[is_prt_non_mainland] = "non_mainland_excluded"

    status_norm = df["Status"].map(inv._norm)
    type_norm = df["Type"].map(inv._norm)
    reason[reason.isna() & status_norm.isin(inv._STATUS_EXCLUDED)] = "status_excluded"
    reason[reason.isna() & ~status_norm.isin(inv._STATUS_TO_FLEET)] = "status_excluded"
    reason[reason.isna() & type_norm.isin(inv._TYPE_EXCLUDED)] = "technology_excluded"
    return df[reason.isna()].copy()


def build_units(gem: pd.DataFrame, countries: dict[str, str] = inv.COUNTRY_NAMES) -> pd.DataFrame:
    kept = _kept_units(gem, countries)
    type_n = kept["Type"].map(inv._norm)
    tech_n = kept["Technology"].map(inv._norm)
    cls = [inv._classify(t, k) for t, k in zip(type_n, tech_n)]
    oil_gas = _col(kept, "Fuel classification (oil/gas only)")
    bio_fuel = _col(kept, "Fuel (combustion only)")

    uids = [
        inv.plant_uid(str(n), la, lo)
        for n, la, lo in zip(kept["Plant / Project name"], kept["Latitude"], kept["Longitude"])
    ]
    bio = [bio_subtype(b) if t == "bioenergy" else None for t, b in zip(type_n, bio_fuel)]
    cap = pd.to_numeric(kept["Capacity (MW)"], errors="coerce").to_numpy(dtype=float)

    out = pd.DataFrame(
        {
            "plant_uid": uids,
            "gem_row": kept.index.to_numpy(),
            "unit_name": _as_text(_col(kept, "Unit / Phase name")).to_numpy(),
            "country": kept["iso3"].to_numpy(),
            "fleet": kept["Status"].map(inv._norm).map(inv._STATUS_TO_FLEET).to_numpy(),
            "fuel_class": [fuel_class(t, o) for t, o in zip(type_n, oil_gas)],
            "bio_subtype": bio,
            "tech_class": [c[0] for c in cls],
            "water_dependent": [bool(c[1]) for c in cls],
            "hydro_type": [c[2] for c in cls],
            "capacity_mw": cap,
        }
    )
    if "GEM unit/phase ID" in kept.columns:
        out["gem_unit_id"] = _as_text(kept["GEM unit/phase ID"]).to_numpy()
    return out.sort_values(["plant_uid", "gem_row"]).reset_index(drop=True)