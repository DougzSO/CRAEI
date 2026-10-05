"""Tests for craei.geo.state_assignment (pure functions, synthetic geometry)."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

from craei.geo.state_assignment import add_macro_region, assign_state


def _admin1():
    # Two adjacent 1x1 degree squares: A at x in [0,1], B at x in [1,2].
    return gpd.GeoDataFrame(
        {"name": ["State A", "State B"], "postal": ["AA", "BB"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)],
        crs="EPSG:4326",
    )


def test_assign_state_inside_polygons():
    df = pd.DataFrame({
        "plant_uid": ["p1", "p2"],
        "lat": [0.5, 0.5],
        "lon": [0.5, 1.5],
    })
    out = assign_state(df, _admin1())
    assert out.set_index("plant_uid").loc["p1", "state_postal"] == "AA"
    assert out.set_index("plant_uid").loc["p2", "state_postal"] == "BB"
    assert not out["nearest_fallback"].any()


def test_assign_state_nearest_fallback():
    # Point just outside both squares (x = 2.05, inside neither): nearest is B.
    df = pd.DataFrame({"plant_uid": ["p3"], "lat": [0.5], "lon": [2.05]})
    out = assign_state(df, _admin1())
    row = out.set_index("plant_uid").loc["p3"]
    assert row["state_postal"] == "BB"
    assert row["nearest_fallback"]


def test_assign_state_no_nan_raises_never_hit_on_valid_input():
    df = pd.DataFrame({"plant_uid": ["p1"], "lat": [0.5], "lon": [0.5]})
    out = assign_state(df, _admin1())
    assert out["state_name"].notna().all()


def test_add_macro_region():
    df = pd.DataFrame({"plant_uid": ["p1", "p2"], "state_postal": ["AA", "BB"]})
    out = add_macro_region(df, {"AA": "Region1", "BB": "Region2"})
    assert out.loc[out["plant_uid"] == "p1", "macro_region"].iloc[0] == "Region1"


def test_add_macro_region_missing_raises():
    df = pd.DataFrame({"plant_uid": ["p1"], "state_postal": ["ZZ"]})
    try:
        add_macro_region(df, {"AA": "Region1"})
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
