import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from craei.spatial import catchments as cat


def _synthetic_basins() -> gpd.GeoDataFrame:
    """A 4-basin tree: 3 -> 2 -> 1 (outlet), 4 -> 2. Unit-square geometries
    placed side by side so intersection/area math is easy to check by hand.
    """
    rows = [
        {"HYBAS_ID": 1, "NEXT_DOWN": 0, "SUB_AREA": 100.0, "UP_AREA": 400.0,
         "geometry": box(0, 0, 1, 1)},
        {"HYBAS_ID": 2, "NEXT_DOWN": 1, "SUB_AREA": 100.0, "UP_AREA": 300.0,
         "geometry": box(1, 0, 2, 1)},
        {"HYBAS_ID": 3, "NEXT_DOWN": 2, "SUB_AREA": 100.0, "UP_AREA": 100.0,
         "geometry": box(2, 0, 3, 1)},
        {"HYBAS_ID": 4, "NEXT_DOWN": 2, "SUB_AREA": 100.0, "UP_AREA": 100.0,
         "geometry": box(1, 1, 2, 2)},
    ]
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def test_upstream_bfs_follows_reversed_next_down():
    basins = _synthetic_basins()
    upstream = cat.upstream_basin_ids(basins, 1)
    assert upstream == {1, 2, 3, 4}

    upstream_leaf = cat.upstream_basin_ids(basins, 3)
    assert upstream_leaf == {3}


def test_validate_upstream_area_matches_up_area():
    basins = _synthetic_basins()
    upstream = cat.upstream_basin_ids(basins, 1)
    pct_diff = cat.validate_upstream_area(basins, 1, upstream)
    # sum(SUB_AREA) of {1,2,3,4} = 400 == UP_AREA of basin 1.
    assert pct_diff < 1.0


def test_validate_upstream_area_flags_mismatch():
    basins = _synthetic_basins()
    basins.loc[basins["HYBAS_ID"] == 1, "UP_AREA"] = 1000.0
    upstream = cat.upstream_basin_ids(basins, 1)
    pct_diff = cat.validate_upstream_area(basins, 1, upstream)
    assert pct_diff > 1.0


def test_basin_containing_point():
    basins = _synthetic_basins()
    assert cat.basin_containing_point(basins, lat=0.5, lon=2.5) == 3


def test_cell_weights_single_cell_sums_to_one():
    cells = pd.DataFrame({"cell_lat": [0.5], "cell_lon": [0.5]})
    catchment = box(0, 0, 1, 1)
    weights = cat.cell_weights(catchment, cells, cell_res_deg=1.0)
    assert len(weights) == 1
    assert abs(weights["weight"].iloc[0] - 1.0) < 1e-9


def test_cell_weights_split_evenly_and_sum_to_one():
    cells = pd.DataFrame({"cell_lat": [0.5, 0.5], "cell_lon": [0.5, 1.5]})
    catchment = box(0, 0, 2, 1)
    weights = cat.cell_weights(catchment, cells, cell_res_deg=1.0)
    assert len(weights) == 2
    assert abs(weights["weight"].sum() - 1.0) < 1e-9
    assert all(abs(w - 0.5) < 1e-6 for w in weights["weight"])
