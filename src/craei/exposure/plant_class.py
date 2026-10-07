"""Analytical thermal population: classification by plant-level cooling class (D151).

`plant_units.parquet` carries a unit-level `tech_class`; `plant_hazards.parquet` carries the plant-level
bucket assigned by `consolidate.py::_assign_bucket` from the plant-level class. A few plants hold
water-dependent units while their plant-level class is air-only (mixed cooling). The analyses (D125, D138,
Fig 4, E1, Table 3, Fig 5b) classify a plant as water-dependent only when its plant-level bucket is
`thermal_water_dependent`; the units of the other plants leave the water-dependent population.
"""

WATER_DEPENDENT = "thermal_water_dependent"


def plant_class_filter(units, bucket_by_plant):
    """Return (units without the mixed-cooling plants' water-dependent units, dropped units).

    `units` has `tech_class` and `plant_uid`; `bucket_by_plant` maps plant_uid -> plant-level bucket.
    Only water-dependent units whose plant bucket differs from `thermal_water_dependent` are dropped.
    """
    mixed = (units["tech_class"] == WATER_DEPENDENT) & (units["plant_uid"].map(bucket_by_plant) != WATER_DEPENDENT)
    return units[~mixed], units[mixed]
