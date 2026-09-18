"""Plant inventory (Spec §1.2, §3 Step 1; COMANDO 13).

Filters the GEM Global Integrated Power Tracker to the 3 study countries and
the fleets defined in D16, aggregates units to plants, classifies technology
per D15, and computes distance to coast (D24: azimuthal equidistant CRS
centered on each country, per Spec §3 Step 1) with 2/5/10 km coastal flags.
"""

import hashlib
from pathlib import Path

import geopandas as gpd
import pandas as pd

COUNTRY_NAMES = {"BRA": "Brazil", "IND": "India", "PRT": "Portugal"}

# D16: GEM Status -> fleet.
_STATUS_TO_FLEET = {
    "operating": "operating",
    "construction": "planned_adv",
    "pre-construction": "planned_adv",
    "announced": "planned_early",
}
_STATUS_EXCLUDED = {
    "shelved",
    "shelved - inferred 2 y",
    "cancelled",
    "cancelled - inferred 4 y",
    "mothballed",
    "retired",
}

# D15: GEM Type -> technology class ("excluded" types are dropped, not counted
# as a fleet). Type "hydropower"/coal/oil-gas/bioenergy/nuclear resolve via
# _classify below since they also need the Technology field.
_TYPE_EXCLUDED = {"wind", "geothermal"}
_THERMAL_TYPES = {"coal", "oil/gas", "bioenergy", "nuclear"}
_AIR_ONLY_TECHNOLOGIES = {"gas turbine", "internal combustion"}
_RUN_OF_RIVER_TECHNOLOGIES = {"run-of-river", "conventional and run-of-river"}
_PUMPED_STORAGE_TECHNOLOGIES = {"pumped storage", "conventional and pumped storage"}

COASTAL_BUFFER_KM_DEFAULT = (2, 5, 10)


def _norm(value: object) -> str:
    return str(value).strip().lower() if pd.notna(value) else ""


def _classify(gem_type: str, technology: str) -> tuple[str, bool, str | None]:
    """Return (tech_class, water_dependent, hydro_type) per D15."""
    if gem_type == "hydropower":
        if technology in _RUN_OF_RIVER_TECHNOLOGIES:
            hydro_type = "run-of-river"
        elif technology in _PUMPED_STORAGE_TECHNOLOGIES:
            hydro_type = "pumped storage"
        else:
            hydro_type = "reservoir"  # D11: missing/unknown type -> reservoir
        return "hydro", True, hydro_type
    if gem_type in _THERMAL_TYPES:
        if gem_type != "nuclear" and technology in _AIR_ONLY_TECHNOLOGIES:
            return "thermal_air_only", False, None
        return "thermal_water_dependent", True, None
    if gem_type == "utility-scale solar":
        return "solar_pv", False, None
    return "other", False, None


def plant_uid(name: str, lat: float, lon: float) -> str:
    key = f"{name}|{lat:.6f}|{lon:.6f}"
    return hashlib.blake2s(key.encode("utf-8")).hexdigest()


def load_gem(gem_path: Path, sheet_name: str = "Power facilities") -> pd.DataFrame:
    return pd.read_excel(gem_path, sheet_name=sheet_name)


def build_inventory(
    gem: pd.DataFrame, countries: dict[str, str] = COUNTRY_NAMES
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Filter, classify and aggregate GEM units into plants.

    Returns (plants, discarded, n_units_in_scope): `discarded` has one row
    per dropped unit with a `reason` column, `plants` has one row per
    plant_uid (units aggregated), and `n_units_in_scope` is the unit-level
    count for the 3 study countries before any row is dropped — the
    reference total for `kept units + discarded units == n_units_in_scope`.
    """
    df = gem.copy()
    iso_by_name = {v: k for k, v in countries.items()}
    df = df[df["Country/area"].isin(countries.values())].copy()
    df["iso3"] = df["Country/area"].map(iso_by_name)

    reason = pd.Series(pd.NA, index=df.index, dtype="object")
    reason[df["Latitude"].isna() | df["Longitude"].isna()] = "no_coordinate"
    reason[reason.isna() & df["Capacity (MW)"].isna()] = "no_capacity"

    status_norm = df["Status"].map(_norm)
    type_norm = df["Type"].map(_norm)
    reason[reason.isna() & status_norm.isin(_STATUS_EXCLUDED)] = "status_excluded"
    reason[reason.isna() & ~status_norm.isin(_STATUS_TO_FLEET)] = "status_excluded"
    reason[reason.isna() & type_norm.isin(_TYPE_EXCLUDED)] = "technology_excluded"

    df["_reason"] = reason
    discarded = df[df["_reason"].notna()][
        ["Country/area", "Plant / Project name", "Status", "Type", "_reason"]
    ].rename(columns={"_reason": "reason"})

    kept = df[df["_reason"].isna()].copy()
    kept["fleet"] = kept["Status"].map(_norm).map(_STATUS_TO_FLEET)
    classified = kept.apply(
        lambda r: _classify(_norm(r["Type"]), _norm(r["Technology"])), axis=1, result_type="expand"
    )
    kept[["tech_class", "water_dependent", "hydro_type"]] = classified
    kept["plant_uid"] = kept.apply(
        lambda r: plant_uid(str(r["Plant / Project name"]), r["Latitude"], r["Longitude"]), axis=1
    )

    plants = (
        kept.groupby("plant_uid", as_index=False)
        .agg(
            country=("iso3", "first"),
            fleet=("fleet", lambda s: s.mode().iat[0]),
            tech_class=("tech_class", lambda s: s.mode().iat[0]),
            water_dependent=("water_dependent", lambda s: s.mode().iat[0]),
            hydro_type=("hydro_type", lambda s: s.mode().iat[0] if s.notna().any() else None),
            capacity_mw=("Capacity (MW)", "sum"),
            lat=("Latitude", "first"),
            lon=("Longitude", "first"),
        )
    )
    return plants, discarded, len(df)


def add_coastal_distance(
    plants: pd.DataFrame,
    coastline_path: Path,
    bboxes: dict[str, list[float]],
    buffer_deg: float = 2.0,
    flag_km: tuple[float, ...] = COASTAL_BUFFER_KM_DEFAULT,
) -> pd.DataFrame:
    """Add `dist_coast_km` and `coastal_{n}km` flags, D24 (per-country aeqd CRS)."""
    coastline = gpd.read_file(coastline_path)
    plants = plants.copy()
    plants["dist_coast_km"] = pd.NA

    out_parts = []
    for iso, group in plants.groupby("country"):
        west, east, south, north = bboxes[iso]
        clip_box = (west - buffer_deg, south - buffer_deg, east + buffer_deg, north + buffer_deg)
        coast_clip = gpd.clip(coastline, clip_box)

        lat0, lon0 = group["lat"].mean(), group["lon"].mean()
        aeqd = f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +units=m +datum=WGS84"

        pts = gpd.GeoDataFrame(
            group, geometry=gpd.points_from_xy(group["lon"], group["lat"]), crs="EPSG:4326"
        ).to_crs(aeqd)
        coast_proj = coast_clip.to_crs(aeqd)

        joined = gpd.sjoin_nearest(pts, coast_proj[["geometry"]], distance_col="_dist_m")
        joined = joined[~joined.index.duplicated(keep="first")]
        group = group.copy()
        group["dist_coast_km"] = joined["_dist_m"] / 1000.0
        out_parts.append(group)

    plants = pd.concat(out_parts, ignore_index=True)
    for km in flag_km:
        plants[f"coastal_{km}km"] = plants["dist_coast_km"] <= km
    return plants


def write_plants(plants: pd.DataFrame, discarded: pd.DataFrame, processed_dir: Path) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "plants.parquet"
    plants.to_parquet(out_path, index=False)
    discarded.to_csv(processed_dir / "plants_discarded.csv", index=False)
    return out_path
