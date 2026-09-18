import pandas as pd

from craei.spatial import grid


def test_nearest_cell_picks_closest_and_reports_distance():
    cells = pd.DataFrame({"cell_lat": [-10.0, -10.5, 0.0], "cell_lon": [-50.0, -50.5, 0.0]})
    plants = pd.DataFrame({"plant_uid": ["p1"], "lat": [-10.05], "lon": [-50.05]})

    out = grid.nearest_cell(plants, cells)

    assert out.loc[0, "cell_lat"] == -10.0
    assert out.loc[0, "cell_lon"] == -50.0
    assert 0 < out.loc[0, "dist_to_cell_km"] < 20


def test_nearest_cell_exact_match_has_zero_distance():
    cells = pd.DataFrame({"cell_lat": [5.25], "cell_lon": [-3.75]})
    plants = pd.DataFrame({"plant_uid": ["p1", "p2"], "lat": [5.25, 5.25], "lon": [-3.75, -3.75]})

    out = grid.nearest_cell(plants, cells)

    assert (out["dist_to_cell_km"] < 1e-6).all()
    assert len(out) == 2
