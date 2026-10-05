"""Assign Brazilian state and macro-region to plant points (W3h; D88 M10).

Natural Earth admin1 has no macro-region field; the IBGE mapping (tier 1,
official, 5 regions) is supplied externally (config/params.yaml,
brazil_macroregion_map). Pure functions; no hazard computation here.
"""

import geopandas as gpd
import pandas as pd

from craei.spatial.catchments import EQUAL_AREA_CRS


def assign_state(df, admin1, lat_col="lat", lon_col="lon", uid_col="plant_uid"):
    """Attach state_name/state_postal/nearest_fallback by point-in-polygon join.

    Points outside every polygon fall back to the nearest polygon (equal-area
    CRS for the distance); nearest_fallback flags those rows. Raises if any
    row ends up without a state (should not happen after the fallback).
    """
    pts = gpd.GeoDataFrame(
        df[[uid_col]].copy(),
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    admin1 = admin1[["name", "postal", "geometry"]]
    joined = gpd.sjoin(pts, admin1, how="left", predicate="within")
    joined = joined.drop_duplicates(subset=uid_col)
    missing = joined["name"].isna()
    if missing.any():
        pts_eq = pts[missing].to_crs(EQUAL_AREA_CRS)
        admin1_eq = admin1.to_crs(EQUAL_AREA_CRS)
        nearest = gpd.sjoin_nearest(pts_eq, admin1_eq)
        nearest = nearest.drop_duplicates(subset=uid_col).set_index(uid_col)
        joined = joined.set_index(uid_col)
        joined.loc[nearest.index, ["name", "postal"]] = nearest[["name", "postal"]]
        joined = joined.reset_index()
    joined["nearest_fallback"] = missing.values
    out = df.merge(
        joined[[uid_col, "name", "postal", "nearest_fallback"]].rename(
            columns={"name": "state_name", "postal": "state_postal"}),
        on=uid_col, how="left",
    )
    if out["state_name"].isna().any():
        raise ValueError("some points could not be assigned to any state")
    return out


def add_macro_region(df, macro_map, postal_col="state_postal"):
    """Attach macro_region from an explicit {postal: region} mapping (IBGE, tier 1)."""
    out = df.copy()
    out["macro_region"] = out[postal_col].map(macro_map)
    if out["macro_region"].isna().any():
        missing = sorted(out.loc[out["macro_region"].isna(), postal_col].unique())
        raise ValueError(f"postal codes without macro_region mapping: {missing}")
    return out
