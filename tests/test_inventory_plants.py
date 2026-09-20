import pandas as pd

from craei.inventory import plants as inv


def _row(**overrides):
    base = {
        "Country/area": "Brazil",
        "Plant / Project name": "Plant A",
        "Capacity (MW)": 100.0,
        "Status": "operating",
        "Type": "hydropower",
        "Technology": "run-of-river",
        "Latitude": -10.0,
        "Longitude": -50.0,
    }
    base.update(overrides)
    return base


def _synthetic_gem() -> pd.DataFrame:
    rows = [
        _row(),  # unit 1 of Plant A, kept, operating hydro run-of-river
        _row(),  # unit 2 of Plant A, same name/lat/lon -> aggregates with unit 1
        _row(
            **{
                "Plant / Project name": "Plant B",
                "Status": "construction",
                "Type": "coal",
                "Technology": "subcritical",
                "Latitude": -15.0,
                "Longitude": -47.0,
            }
        ),  # planned_adv thermal water-dependent
        _row(
            **{
                "Plant / Project name": "Plant C",
                "Country/area": "India",
                "Status": "announced",
                "Type": "oil/gas",
                "Technology": "gas turbine",
                "Latitude": 20.0,
                "Longitude": 78.0,
            }
        ),  # planned_early thermal air-only
        _row(
            **{
                "Plant / Project name": "Plant D",
                "Country/area": "Portugal",
                "Status": "retired",
                "Type": "coal",
                "Technology": "subcritical",
                "Latitude": 39.0,
                "Longitude": -8.0,
            }
        ),  # status excluded
        _row(
            **{
                "Plant / Project name": "Plant E",
                "Status": "operating",
                "Type": "wind",
                "Technology": "unknown",
                "Latitude": -12.0,
                "Longitude": -48.0,
            }
        ),  # technology excluded (D04)
        _row(
            **{
                "Plant / Project name": "Plant F",
                "Status": "operating",
                "Capacity (MW)": float("nan"),
            }
        ),  # no_capacity
        _row(
            **{
                "Plant / Project name": "Plant G",
                "Status": "operating",
                "Latitude": float("nan"),
            }
        ),  # no_coordinate
        _row(
            **{
                "Plant / Project name": "Plant H",
                "Country/area": "Canada",
            }
        ),  # out of scope (country filter)
        _row(
            **{
                "Plant / Project name": "Plant I",
                "Country/area": "Portugal",
                "Status": "operating",
                "Type": "coal",
                "Technology": "subcritical",
                "Latitude": 38.72,
                "Longitude": -27.07,
            }
        ),  # Azores -- non_mainland_excluded (D40)
        _row(
            **{
                "Plant / Project name": "Plant J",
                "Country/area": "Portugal",
                "Status": "operating",
                "Type": "coal",
                "Technology": "subcritical",
                "Latitude": 32.65,
                "Longitude": -16.97,
            }
        ),  # Madeira -- non_mainland_excluded (D40)
    ]
    return pd.DataFrame(rows)


def test_kept_plus_discarded_equals_scoped_input():
    gem = _synthetic_gem()
    plants, discarded, n_units_in_scope = inv.build_inventory(gem)
    kept_units = n_units_in_scope - len(discarded)
    assert kept_units + len(discarded) == n_units_in_scope
    # 10 rows are Brazil/India/Portugal (all but Plant H); Plant A has 2 units.
    assert n_units_in_scope == 10


def test_units_aggregate_to_one_plant_by_name_lat_lon():
    gem = _synthetic_gem()
    plants, _discarded, _n = inv.build_inventory(gem)
    plant_a = plants[plants["plant_uid"] == inv.plant_uid("Plant A", -10.0, -50.0)]
    assert len(plant_a) == 1
    assert plant_a.iloc[0]["capacity_mw"] == 200.0


def test_no_duplicate_plant_uid():
    gem = _synthetic_gem()
    plants, _discarded, _n = inv.build_inventory(gem)
    assert plants["plant_uid"].duplicated().sum() == 0


def test_discard_reasons():
    gem = _synthetic_gem()
    _plants, discarded, _n = inv.build_inventory(gem)
    reasons = dict(discarded["reason"].value_counts())
    assert reasons == {
        "status_excluded": 1,
        "technology_excluded": 1,
        "no_capacity": 1,
        "no_coordinate": 1,
        "non_mainland_excluded": 2,
    }


def test_azores_madeira_excluded_from_continental_scope():
    gem = _synthetic_gem()
    plants, discarded, _n = inv.build_inventory(gem)
    non_mainland = discarded[discarded["reason"] == "non_mainland_excluded"]
    assert set(non_mainland["Plant / Project name"]) == {"Plant I", "Plant J"}
    assert inv.plant_uid("Plant I", 38.72, -27.07) not in set(plants["plant_uid"])
    assert inv.plant_uid("Plant J", 32.65, -16.97) not in set(plants["plant_uid"])


def test_fleet_and_tech_class_mapping():
    gem = _synthetic_gem()
    plants, _discarded, _n = inv.build_inventory(gem)
    by_name = plants.set_index("plant_uid")
    a = by_name.loc[inv.plant_uid("Plant A", -10.0, -50.0)]
    assert a["fleet"] == "operating"
    assert a["tech_class"] == "hydro"
    assert a["hydro_type"] == "run-of-river"
    assert bool(a["water_dependent"]) is True

    b = by_name.loc[inv.plant_uid("Plant B", -15.0, -47.0)]
    assert b["fleet"] == "planned_adv"
    assert b["tech_class"] == "thermal_water_dependent"

    c = by_name.loc[inv.plant_uid("Plant C", 20.0, 78.0)]
    assert c["fleet"] == "planned_early"
    assert c["tech_class"] == "thermal_air_only"
    assert bool(c["water_dependent"]) is False
