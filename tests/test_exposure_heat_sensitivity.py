import pandas as pd

from craei.exposure import heat_fuel as hf
from craei.exposure import heat_sensitivity as hs


def _df():
    rows = []
    for uid, cap, delta in (("p1", 100.0, 40.0), ("p1", 300.0, 40.0), ("p2", 100.0, 10.0)):
        rows.append({"plant_uid": uid, "fleet": "operating", "scenario": "ssp126",
                     "model": "m1", "fuel_class": "gas", "capacity_mw": cap,
                     "delta": delta})
    return pd.DataFrame(rows)


def _summ(lo, med, hi):
    return pd.DataFrame([{"group": "g", "fleet": "operating", "scenario": "ssp126",
                          "threshold": 30, "pct_min": lo, "pct_median": med,
                          "pct_max": hi}])


def test_plant_weighting_counts_each_plant_once():
    df = _df()
    gw = hf.exposure_curves(df, "fuel_class", (30,))
    pw = hf.exposure_curves(hs.plant_weighted(df, "fuel_class"), "fuel_class", (30,))
    assert gw["pct_gw"].iloc[0] == 80.0
    assert pw["pct_gw"].iloc[0] == 50.0
    assert pw["gw_total"].iloc[0] == 2.0


def test_compare_difference_and_overlap():
    ref = _summ(10.0, 20.0, 30.0)
    far = hs.compare(ref, _summ(35.0, 40.0, 50.0), "x")
    near = hs.compare(ref, _summ(25.0, 27.0, 60.0), "x")
    assert far["diff_median_pp"].iloc[0] == 20.0
    assert not far["ranges_overlap"].iloc[0]
    assert near["diff_median_pp"].iloc[0] == 7.0
    assert near["ranges_overlap"].iloc[0]
    assert far["choice"].iloc[0] == "x"


def test_plant_weighted_keeps_fleets_and_groups():
    base = _df().iloc[[0]]
    rows = pd.concat([base, base.assign(fleet="planned_all"),
                      base.assign(fuel_class="oil")])
    assert len(hs.plant_weighted(rows, None)) == 2
    assert len(hs.plant_weighted(rows, "fuel_class")) == 3