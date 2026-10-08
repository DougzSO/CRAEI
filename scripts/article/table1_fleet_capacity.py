"""Table 1: fleet and capacity by technology and fuel, Brazil (D131).

Source: plant_units.parquet (BRA). Itaipu at the Brazilian share (version b,
7,000 MW) through `hl.with_itaipu_versions`, consistent with D102.
"""

import pandas as pd
from _common import md_table, out_dir, processed_dir, write_csv, write_text

from craei.countries import iso as country_iso
from craei.exposure import heat_levels as hl
from craei.hazards import drought_levels as dl

COUNTRY = country_iso()
TECH = {"hydro": "Hydro", "solar_pv": "Solar PV",
        "thermal_water_dependent": "Thermal (water-dependent)",
        "thermal_air_only": "Thermal (air-cooled)"}
FUEL = {"hydro": "Hydro", "solar": "Solar", "bioenergy": "Bioenergy", "gas": "Natural gas",
        "coal": "Coal", "nuclear": "Nuclear", "multi_fuel": "Multi-fuel", "oil": "Oil"}
FLEET = {"operating": "Operating", "planned_adv": "Planned (all stages)",
         "planned_early": "Planned (all stages)"}
NOTE = (
    "**Note:** Itaipu hydroelectric plant is reported at Brazil's contractual share "
    "(7,000 MW of 14,000 MW total binational capacity), consistent with the D102 headline "
    "result (hydro operating, itaipu=b, 102.667 GW). The full binational asset (itaipu=a, "
    "14,000 MW) is used only in sensitivity analyses, not in this table. 'Planned (all "
    "stages)' aggregates advanced-stage and early-stage GEM status categories. Source: "
    "plant_units.parquet (BRA only), GEM inventory cutoff 2026-08-09. This table counts units "
    "(inventory). Analyses classify thermal plants by plant-level cooling class; 3 operating "
    "plants with mixed cooling (Guarani, Atlântico, Termo Norte; 0.668 GW of water-dependent "
    "units) are treated as air-cooled, so the analytical water-dependent operating population "
    "is 39.10 GW vs 39.77 GW here. Likewise 2 planned plants (Termopecém, Azulão; 2.432 GW "
    "of water-dependent units) are treated as air-cooled, so the analytical planned "
    "water-dependent population is 41.15 GW vs 43.58 GW here.")


def main():
    proc = processed_dir()
    plants = pd.read_parquet(proc / "plants.parquet")
    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[units["country"] == COUNTRY]
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, COUNTRY, "itaipu", 14000.0))
    uv = uv[uv["itaipu"].isin(["na", "b"])].copy()
    assert len(uv) == len(units)
    uv["Fleet"] = uv["fleet"].map(FLEET)
    uv["Technology"] = uv["tech_class"].map(TECH)
    uv["Fuel"] = uv["fuel_class"].map(FUEL)
    assert not uv[["Fleet", "Technology", "Fuel"]].isna().any().any()
    g = (uv.groupby(["Fleet", "Technology", "Fuel"], as_index=False)
         .agg(Units=("capacity_mw", "size"), cap=("capacity_mw", "sum")))
    g["Capacity (GW)"] = (g["cap"] / 1000).round(3)
    g["fleet_order"] = g["Fleet"].map({"Operating": 0, "Planned (all stages)": 1})
    g = g.sort_values(["fleet_order", "cap"], ascending=[True, False])
    df = g[["Fleet", "Technology", "Fuel", "Units", "Capacity (GW)"]].reset_index(drop=True)
    hyd = df[(df.Fleet == "Operating") & (df.Technology == "Hydro")]["Capacity (GW)"].iloc[0]
    assert abs(hyd - 102.667) < 1e-3, hyd  # D102 regression
    d = out_dir("tables")
    write_csv(df, d / "table1_fleet_capacity.csv")
    md = df.assign(**{"Capacity (GW)": df["Capacity (GW)"].map("{:.3f}".format)})
    write_text(d / "table1_fleet_capacity.md",
               "# Table 1 -- Fleet and Capacity by Technology and Fuel (Brazil)\n\n"
               + md_table(md) + "\n\n" + NOTE + "\n")


if __name__ == "__main__":
    main()
