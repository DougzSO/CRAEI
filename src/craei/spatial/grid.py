"""ISIMIP 0.5° land grid and nearest-cell assignment (Spec §1.3, §3 Step 3; COMANDO 14).

ISIMIP3b bias-adjusted tasmax/tasmin/pr carry no ocean NaN mask in the
country-cropped files (verified: 0 NaN over open-ocean cells inside the
Brazil bbox) so "nearest land cell" per Spec §3 Step 1 needs an external
land mask; see D25 for the choice (GADM level-0 country polygon).
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from sklearn.neighbors import BallTree

GRID_RES_DEG = 0.5
EARTH_RADIUS_KM = 6371.0088


def land_cells(nc_path: Path, gadm_path: Path, admin_layer: str = "ADM_ADM_0") -> pd.DataFrame:
    """Cell centers of `nc_path`'s grid whose 0.5° box intersects the GADM country polygon."""
    ds = xr.open_dataset(nc_path)
    lats, lons = ds["lat"].values, ds["lon"].values
    ds.close()

    country = gpd.read_file(gadm_path, layer=admin_layer)
    country_geom = country.union_all()

    half = GRID_RES_DEG / 2
    lat_grid, lon_grid = np.meshgrid(lats, lons, indexing="ij")
    cells = gpd.GeoDataFrame(
        {"cell_lat": lat_grid.ravel(), "cell_lon": lon_grid.ravel()},
        geometry=gpd.points_from_xy(lon_grid.ravel(), lat_grid.ravel()).buffer(half, cap_style=3),
        crs="EPSG:4326",
    )
    is_land = cells.intersects(country_geom)
    return cells.loc[is_land, ["cell_lat", "cell_lon"]].reset_index(drop=True)


def nearest_cell(plants: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    """For each plant, the nearest land cell (haversine, km) among `cells`."""
    cell_rad = np.radians(cells[["cell_lat", "cell_lon"]].to_numpy())
    tree = BallTree(cell_rad, metric="haversine")
    plant_rad = np.radians(plants[["lat", "lon"]].to_numpy())
    dist_rad, idx = tree.query(plant_rad, k=1)

    matched = cells.iloc[idx.ravel()].reset_index(drop=True)
    out = plants[["plant_uid"]].reset_index(drop=True).copy()
    out["cell_lat"] = matched["cell_lat"].to_numpy()
    out["cell_lon"] = matched["cell_lon"].to_numpy()
    out["dist_to_cell_km"] = dist_rad.ravel() * EARTH_RADIUS_KM
    return out


def build_plant_cell(
    plants: pd.DataFrame,
    nc_paths_by_country: dict[str, Path],
    gadm_paths_by_country: dict[str, Path],
) -> pd.DataFrame:
    """Run `nearest_cell` per country (each has its own cropped ISIMIP grid)."""
    parts = []
    for iso, group in plants.groupby("country"):
        cells = land_cells(nc_paths_by_country[iso], gadm_paths_by_country[iso])
        parts.append(nearest_cell(group, cells))
    return pd.concat(parts, ignore_index=True)
