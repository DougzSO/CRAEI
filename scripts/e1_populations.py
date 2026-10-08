"""E1 populations (D140): Brazilian operating hydro (Itaipu b) and water-dependent thermal plants.

Same selection as W4b (hydro) and W4c / Fig 4 (thermal, D138): units of plant_units.parquet by
tech_class and fleet, thermal plants kept only if their plant-level hazard bucket is
thermal_water_dependent. Itaipu at the Brazilian share (7,000 MW, version b, D102). Capacity of a
plant = sum of its selected units; the cell comes from plant_cell.parquet.
Thermal fleets: "operating" (main) and "operating_plus_planned" (secondary, the future insurance).
"""

import pandas as pd

from craei.countries import iso as country_iso
from craei.exposure import heat_levels as hl
from craei.hazards import drought_levels as dl

COUNTRY = country_iso()
ITAIPU_TOTAL_MW = 14000.0  # scripts/th1_fleet_gw.py:73
EXPECT_HYDRO_GW, EXPECT_THERMAL_PLANTS, EXPECT_THERMAL_GW = 102.667, 618, 39.1015  # D102, D125
PLANNED = ["planned_adv", "planned_early"]


def _plants(units, cells):
    g = units.groupby("plant_uid", as_index=False)["capacity_mw"].sum()
    g = g.merge(cells, on="plant_uid", how="left")
    assert g["cell_lat"].notna().all(), "plants without a cell"
    g["cell_id"] = g["cell_lat"].astype(str) + "_" + g["cell_lon"].astype(str)
    return g.reset_index(drop=True)


def load_populations(proc):
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[units["country"] == COUNTRY]
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, COUNTRY, "itaipu", ITAIPU_TOTAL_MW))
    bucket = (pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
              .drop_duplicates("plant_uid").set_index("plant_uid")["bucket"])
    cells = pd.read_parquet(proc / "plant_cell.parquet",
                            columns=["plant_uid", "cell_lat", "cell_lon"]).drop_duplicates("plant_uid")
    hyd = uv[(uv["tech_class"] == "hydro") & (uv["fleet"] == "operating") & (uv["itaipu"] == "b")]
    thm = uv[(uv["tech_class"] == "thermal_water_dependent") & (uv["itaipu"] == "na")]
    thm = thm[thm["plant_uid"].map(bucket) == "thermal_water_dependent"]
    pops = {"hydro": _plants(hyd, cells),
            "operating": _plants(thm[thm["fleet"] == "operating"], cells),
            "operating_plus_planned": _plants(thm[thm["fleet"].isin(["operating", *PLANNED])], cells)}
    assert abs(pops["hydro"]["capacity_mw"].sum() / 1000 - EXPECT_HYDRO_GW) < 1e-3
    assert len(pops["operating"]) == EXPECT_THERMAL_PLANTS, len(pops["operating"])
    assert abs(pops["operating"]["capacity_mw"].sum() / 1000 - EXPECT_THERMAL_GW) < 1e-3
    return pops
