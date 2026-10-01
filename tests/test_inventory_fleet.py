import pandas as pd
import pytest

from craei.inventory import fleet as F

COLS = ["plant_uid", "country", "tech_class", "fuel_class", "hydro_type",
        "bio_subtype", "fleet", "capacity_mw"]


def _units() -> pd.DataFrame:
    rows = [
        ("h1", "BRA", "hydro", "hydro", "reservoir", None, "operating", 700.0),
        ("h1", "BRA", "hydro", "hydro", "reservoir", None, "operating", 700.0),
        ("t1", "BRA", "thermal_water_dependent", "gas", None, None, "operating", 100.0),
        ("t1", "BRA", "thermal_air_only", "gas", None, None, "planned_early", 50.0),
        ("b1", "BRA", "thermal_water_dependent", "bioenergy", None,
         "agricultural_waste", "operating", 30.0),
        ("s1", "BRA", "solar_pv", "solar", None, None, "operating", 999.0),
        ("i1", "IND", "hydro", "hydro", "reservoir", None, "operating", 500.0),
    ]
    return pd.DataFrame(rows, columns=COLS)


def test_scope_units_keeps_brazil_hydro_and_thermal_only():
    s = F.scope_units(_units())
    assert len(s) == 5
    assert set(s.country) == {"BRA"}
    assert "solar_pv" not in set(s.tech_class)


def test_fleet_table_conserves_capacity():
    s = F.scope_units(_units())
    t = F.fleet_table(s)
    assert t["capacity_mw"].sum() == pytest.approx(s["capacity_mw"].sum())
    assert t["capacity_gw"].sum() == pytest.approx(1.58)


def test_fleet_table_counts_and_missing_subtypes():
    t = F.fleet_table(F.scope_units(_units()))
    assert len(t) == 4
    h = t[t.tech_class == "hydro"].iloc[0]
    assert (h.units, h.plants, h.capacity_mw) == (2, 1, 1400.0)
    assert h.bio_subtype == "-"
    b = t[t.fuel_class == "bioenergy"].iloc[0]
    assert b.bio_subtype == "agricultural_waste" and b.hydro_type == "-"


def test_apply_foreign_share_scales_and_validates():
    s = F.scope_units(_units())
    shared = F.apply_foreign_share(s, {"h1"}, 1400.0, 700.0)
    assert shared[shared.plant_uid == "h1"]["capacity_mw"].sum() == pytest.approx(700.0)
    assert shared[shared.plant_uid != "h1"]["capacity_mw"].sum() == pytest.approx(180.0)
    assert s[s.plant_uid == "h1"]["capacity_mw"].sum() == pytest.approx(1400.0)
    with pytest.raises(ValueError):
        F.apply_foreign_share(s, {"h1"}, 1500.0, 700.0)