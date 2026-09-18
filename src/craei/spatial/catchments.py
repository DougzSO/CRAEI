"""Upstream catchment delineation and grid-cell area weights (Spec §1.3, §3 Step 3; COMANDO 14).

HydroBASINS level 6: each basin's `NEXT_DOWN` points to the next basin
downstream (0 = terminal/coastal outlet). The upstream catchment of the
basin containing a hydro plant is every basin that reaches it by following
`NEXT_DOWN`, found by reversing that edge and doing a BFS from the plant's
basin. `UP_AREA` is HydroSHEDS' own precomputed accumulated upstream area,
used to sanity-check the BFS: sum(SUB_AREA of upstream set) should match it
within 1%.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

# World Cylindrical Equal Area: for area/intersection computations regardless
# of catchment size (from small Portuguese basins to the Amazon).
EQUAL_AREA_CRS = "EPSG:6933"


def load_hydrobasins(zip_path: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(f"zip://{zip_path}")


def basin_containing_point(basins: gpd.GeoDataFrame, lat: float, lon: float) -> int | None:
    point = gpd.GeoSeries([gpd.points_from_xy([lon], [lat])[0]], crs="EPSG:4326")
    hit = basins[basins.contains(point.iloc[0])]
    if hit.empty:
        # Point falls on a shared boundary/coastline edge; fall back to nearest basin.
        hit = basins.iloc[[basins.distance(point.iloc[0]).idxmin()]]
    return int(hit.iloc[0]["HYBAS_ID"])


def upstream_basin_ids(basins: gpd.GeoDataFrame, basin_id: int) -> set[int]:
    """BFS over the reversed NEXT_DOWN graph, from `basin_id`."""
    reverse: dict[int, list[int]] = {}
    for hybas_id, next_down in zip(basins["HYBAS_ID"], basins["NEXT_DOWN"], strict=True):
        if next_down != 0:
            reverse.setdefault(int(next_down), []).append(int(hybas_id))

    seen = {basin_id}
    frontier = [basin_id]
    while frontier:
        next_frontier = []
        for b in frontier:
            for upstream in reverse.get(b, []):
                if upstream not in seen:
                    seen.add(upstream)
                    next_frontier.append(upstream)
        frontier = next_frontier
    return seen


def validate_upstream_area(
    basins: gpd.GeoDataFrame, basin_id: int, upstream_ids: set[int]
) -> float:
    """Percent difference between sum(SUB_AREA) of `upstream_ids` and UP_AREA of `basin_id`."""
    summed = basins.loc[basins["HYBAS_ID"].isin(upstream_ids), "SUB_AREA"].sum()
    reference = basins.loc[basins["HYBAS_ID"] == basin_id, "UP_AREA"].iloc[0]
    return abs(summed - reference) / reference * 100.0


def cell_weights(catchment_geom, cells: pd.DataFrame, cell_res_deg: float) -> pd.DataFrame:
    """Area-intersection weight of each land `cells` row with `catchment_geom`, summing to 1.

    Cells with no overlap are dropped; if the catchment extends beyond the
    country's cropped ISIMIP bbox (so no cell falls in that part), the
    remaining in-bbox cells are renormalized to sum to 1 (L12).
    """
    half = cell_res_deg / 2
    boxes = gpd.GeoDataFrame(
        cells,
        geometry=gpd.points_from_xy(cells["cell_lon"], cells["cell_lat"]).buffer(half, cap_style=3),
        crs="EPSG:4326",
    ).to_crs(EQUAL_AREA_CRS)
    catchment = gpd.GeoSeries([catchment_geom], crs="EPSG:4326").to_crs(EQUAL_AREA_CRS).iloc[0]

    boxes["overlap_area"] = boxes.geometry.intersection(catchment).area
    overlapping = boxes[boxes["overlap_area"] > 0].copy()
    total = overlapping["overlap_area"].sum()
    overlapping["weight"] = overlapping["overlap_area"] / total
    return overlapping[["cell_lat", "cell_lon", "weight"]].reset_index(drop=True)


def build_catchment_weights(
    hydro_plants: pd.DataFrame,
    basins_by_region: dict[str, gpd.GeoDataFrame],
    region_by_country: dict[str, str],
    cells_by_country: dict[str, pd.DataFrame],
    cell_res_deg: float = 0.5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (catchment_weights, validation) for every row in `hydro_plants`.

    `validation` has one row per plant: basin_id, n_upstream_basins,
    pct_diff_up_area (see `validate_upstream_area`).
    """
    weight_parts, val_rows = [], []
    for _, plant in hydro_plants.iterrows():
        region = region_by_country[plant["country"]]
        basins = basins_by_region[region]
        basin_id = basin_containing_point(basins, plant["lat"], plant["lon"])
        upstream_ids = upstream_basin_ids(basins, basin_id)
        pct_diff = validate_upstream_area(basins, basin_id, upstream_ids)

        catchment_geom = basins.loc[basins["HYBAS_ID"].isin(upstream_ids), "geometry"].union_all()
        w = cell_weights(catchment_geom, cells_by_country[plant["country"]], cell_res_deg)
        w.insert(0, "plant_uid", plant["plant_uid"])
        weight_parts.append(w)

        val_rows.append(
            {
                "plant_uid": plant["plant_uid"],
                "basin_id": basin_id,
                "n_upstream_basins": len(upstream_ids),
                "pct_diff_up_area": pct_diff,
            }
        )

    weights = pd.concat(weight_parts, ignore_index=True) if weight_parts else pd.DataFrame(
        columns=["plant_uid", "cell_lat", "cell_lon", "weight"]
    )
    validation = pd.DataFrame(val_rows)
    return weights, validation
