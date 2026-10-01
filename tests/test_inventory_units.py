from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from craei.inventory import plants as inv
from craei.inventory import units as U

_OPT = ["Unit / Phase name", "Fuel (combustion only)", "Fuel classification (oil/gas only)"]


def _row(over: dict) -> dict:
    base = {
        "Country/area": "Brazil", "Plant / Project name": "P", "Unit / Phase name": "u1",
        "Capacity (MW)": 100.0, "Status": "operating", "Type": "hydropower",
        "Technology": "run-of-river", "Latitude": -10.0, "Longitude": -50.0,
        "Fuel (combustion only)": None, "Fuel classification (oil/gas only)": None,
    }
    base.update(over)
    return base


MIXED = "Mixed"


def _gem() -> pd.DataFrame:
    n, la, lo = "Plant / Project name", "Latitude", "Longitude"
    rows = [
        _row({n: MIXED, la: -3.0, lo: -40.0, "Type": "coal", "Technology": "subcritical",
              "Status": "operating", "Capacity (MW)": 100.0, "Unit / Phase name": "c1"}),
        _row({n: MIXED, la: -3.0, lo: -40.0, "Type": "oil/gas", "Technology": "gas turbine",
              "Status": "announced", "Capacity (MW)": 300.0, "Unit / Phase name": "g1",
              "Fuel classification (oil/gas only)": "gas"}),
        _row({n: "Hydro1", "Capacity (MW)": 50.0}),
        _row({n: "Hydro1", "Capacity (MW)": 50.0}),
        _row({n: "Bio1", la: -12.0, lo: -45.0, "Type": "bioenergy", "Technology": "steam turbine",
              "Status": "construction", "Capacity (MW)": 20.0,
              "Fuel (combustion only)": "bioenergy: agricultural waste (solids)"}),
        _row({n: "IndGas", "Country/area": "India", la: 20.0, lo: 78.0, "Type": "oil/gas",
              "Technology": "gas turbine", "Capacity (MW)": 10.0,
              "Fuel classification (oil/gas only)": "oil"}),
        _row({n: "PortoRetired", "Country/area": "Portugal", la: 39.0, lo: -8.0, "Type": "coal",
              "Technology": "subcritical", "Status": "retired"}),
        _row({n: "NoCoord", la: np.nan}),
        _row({n: "NoCap", la: -20.0, lo: -50.0, "Capacity (MW)": np.nan}),
        _row({n: "Wind1", la: -21.0, lo: -50.0, "Type": "wind", "Technology": "onshore"}),
        _row({n: "Azores", "Country/area": "Portugal", la: 38.0, lo: -25.0}),
        _row({n: "Shelved1", la: -22.0, lo: -50.0, "Status": "shelved"}),
    ]
    return pd.DataFrame(rows)


def test_mixed_plant_is_split_by_unit():
    units = U.build_units(_gem())
    plants, _, _ = inv.build_inventory(_gem())
    uid = inv.plant_uid(MIXED, -3.0, -40.0)
    sub = units[units.plant_uid == uid]
    assert len(sub) == 2
    assert sub.groupby("fleet")["capacity_mw"].sum().to_dict() == {"operating": 100.0, "planned_early": 300.0}
    assert sub.set_index("fuel_class")["tech_class"].to_dict() == {
        "coal": "thermal_water_dependent", "gas": "thermal_air_only"}
    pp = plants[plants.plant_uid == uid]
    assert len(pp) == 1 and pp["capacity_mw"].iat[0] == sub["capacity_mw"].sum()


def test_conservation_against_build_inventory():
    gem = _gem()
    plants, discarded, n_scope = inv.build_inventory(gem)
    units = U.build_units(gem)
    assert len(units) + len(discarded) == n_scope
    assert set(units.plant_uid) == set(plants.plant_uid)
    s = units.groupby("plant_uid")["capacity_mw"].sum().sort_index()
    p = plants.set_index("plant_uid")["capacity_mw"].sort_index()
    pd.testing.assert_series_equal(s, p, check_names=False)
    c = units.groupby("plant_uid")["country"].first().sort_index()
    pd.testing.assert_series_equal(c, plants.set_index("plant_uid")["country"].sort_index(), check_names=False)


def test_oil_gas_class_mapping():
    assert U.oil_gas_class("Gas") == "gas"
    assert U.oil_gas_class("LNG only") == "gas"
    assert U.oil_gas_class("oil") == "oil"
    assert U.oil_gas_class("Multi fuel") == "multi_fuel"
    for v in (None, np.nan, "x"):
        assert U.oil_gas_class(v) == "oil_gas_unclassified"


def test_bio_subtype_mapping():
    assert U.bio_subtype("bioenergy: agricultural waste (solids)") == "agricultural_waste"
    assert U.bio_subtype("bioenergy: paper mill wastes") == "paper_mill_waste"
    assert U.bio_subtype("bioenergy: wood & other biomass (solids)") == "wood_biomass"
    assert U.bio_subtype("bioenergy: biogas") == "other_bioenergy"
    assert U.bio_subtype("agricultural waste (solids), agricultural waste (solids)") == "agricultural_waste"
    assert U.bio_subtype("bioenergy: agricultural waste (solids), bioenergy: paper mill wastes") == "bio_mixed"


def test_non_thermal_units_are_labelled():
    units = U.build_units(_gem())
    h = units[units.plant_uid == inv.plant_uid("Hydro1", -10.0, -50.0)]
    assert len(h) == 2
    assert set(h.fuel_class) == {"hydro"} and set(h.tech_class) == {"hydro"}
    assert set(h.hydro_type) == {"run-of-river"} and h.bio_subtype.isna().all()
    b = units[units.plant_uid == inv.plant_uid("Bio1", -12.0, -45.0)]
    assert b.bio_subtype.iat[0] == "agricultural_waste" and b.fleet.iat[0] == "planned_adv"


def test_missing_optional_columns_still_builds():
    gem = _gem().drop(columns=_OPT)
    units = U.build_units(gem)
    assert list(units.columns) == U.UNIT_COLUMNS
    assert units.unit_name.isna().all()
    ind = units[units.country == "IND"]
    assert ind.fuel_class.iat[0] == "oil_gas_unclassified"


def test_plant_units_reference_if_built():
    try:
        from craei.config import load_paths
        path = Path(load_paths()["processed_dir"]) / "plant_units.parquet"
    except Exception:
        path = None
    if path is None or not path.exists():
        pytest.skip("plant_units.parquet not built")
    u = pd.read_parquet(path)
    th = u[(u.country == "BRA") & u.tech_class.str.startswith("thermal")]
    fleet = th.groupby("fleet")["capacity_mw"].sum() / 1000
    assert fleet["operating"] == pytest.approx(47.67, abs=0.015)
    assert fleet["planned_adv"] == pytest.approx(17.31, abs=0.015)
    assert fleet["planned_early"] == pytest.approx(31.04, abs=0.015)
    op = th[th.fleet == "operating"].groupby("fuel_class")["capacity_mw"].sum() / 1000
    for k, v in {"gas": 19.32, "bioenergy": 17.43, "oil": 4.60, "coal": 3.00,
                 "nuclear": 1.99, "multi_fuel": 1.33}.items():
        assert op[k] == pytest.approx(v, abs=0.015)
        