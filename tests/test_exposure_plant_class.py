"""Tests of craei.exposure.plant_class (D151)."""

import pandas as pd

from craei.exposure.plant_class import plant_class_filter


def test_mixed_cooling_units_leave_water_dependent_population():
    units = pd.DataFrame({"plant_uid": ["a", "a", "b", "c"],
                          "tech_class": ["thermal_water_dependent", "thermal_air_only",
                                         "thermal_water_dependent", "hydro"],
                          "capacity_mw": [10.0, 90.0, 5.0, 100.0]})
    bucket = pd.Series({"a": "thermal_air_only", "b": "thermal_water_dependent", "c": "hydro_reservoir"})
    kept, dropped = plant_class_filter(units, bucket)
    assert dropped["capacity_mw"].tolist() == [10.0]
    assert kept["capacity_mw"].sum() == 195.0
    assert len(kept) == 3


def test_plants_missing_from_bucket_table_are_dropped_not_kept():
    units = pd.DataFrame({"plant_uid": ["x"], "tech_class": ["thermal_water_dependent"],
                          "capacity_mw": [1.0]})
    kept, dropped = plant_class_filter(units, pd.Series(dtype=object))
    assert len(kept) == 0 and len(dropped) == 1
