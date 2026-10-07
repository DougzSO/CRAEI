"""Table 3 (long form): heat x drought co-exposure 4x4 cross-tab, GW and % (C85, D130).

Source: table3_coexposure.csv, canonical pool/null/cutset (hydro: catchment pool;
thermal: cell pool; block12, p50_p90_p99).
"""

from _common import SCEN_LABEL, md_table, out_dir, read_csv, write_csv, write_text

GROUP = {"hydro": "Hydro", "thermal_water_dependent": "Thermal (water-dependent)"}
FLEET = {"operating": "Operating", "planned_all": "Planned (all stages)"}
NOTE = (
    "**Note:** 192 rows = 12 group/fleet/itaipu/scenario combinations x 16 heat x drought "
    "cells (4x4). Itaipu reported at Brazil's 7,000 MW share for hydro (itaipu=b); not "
    "applicable for thermal. Canonical pool/null/cutset: catchment|cell, block12, "
    "p50_p90_p99. 'Gap (GW)' = gw_total minus the sum of the 16 per-cell gw_median values "
    "for that combination (median is not additive across cells, D80/D96/D97/D99/D106; this "
    "is expected, not an error). Source: table3_coexposure.csv (C85/D130, scope fixed). "
    "Visual cross-tab layout for publication (4x4 grid per combination) still pending -- "
    "this file is the formatted long-form data. Baseline 1985-2014, future 2041-2070.")
POOL = {"hydro": "catchment", "thermal_water_dependent": "cell"}  # D130 canonical pools


def canonical():
    t = read_csv("table3_coexposure.csv")
    t = t[t["canonical"]]
    t = t[t["pool"] == t["group"].map(POOL)]
    assert (t["null"] == "block12").all() and (t["cutset"] == "p50_p90_p99").all()
    assert len(t) == 192, len(t)
    assert t.groupby(["group", "fleet", "scenario"]).size().eq(16).all()
    return t


def main():
    t = canonical()
    t = t.assign(Group=t["group"].map(GROUP), Fleet=t["fleet"].map(FLEET),
                 Scenario=t["scenario"].map(SCEN_LABEL),
                 **{"Heat Class": t["heat_class"].str.capitalize(),
                    "Drought Class": t["drought_class"].str.capitalize()})
    t["g"] = t["group"].map({"hydro": 0, "thermal_water_dependent": 1})
    t["f"] = t["fleet"].map({"operating": 0, "planned_all": 1})
    t = t.sort_values(["g", "f", "scenario", "Heat Class", "Drought Class"])
    df = t.assign(**{"GW Median": t["gw_median"].round(3), "% Median": t["pct_median"].round(2),
                     "Gap (GW)": t["gap_gw"].round(3)})[
        ["Group", "Fleet", "Scenario", "Heat Class", "Drought Class",
         "GW Median", "% Median", "Gap (GW)"]].reset_index(drop=True)
    d = out_dir("tables")
    write_csv(df, d / "table3_coexposure_crosstab.csv")
    md = df.assign(**{"GW Median": df["GW Median"].map("{:.3f}".format),
                      "% Median": df["% Median"].map("{:.2f}".format),
                      "Gap (GW)": df["Gap (GW)"].map("{:.3f}".format)})
    write_text(d / "table3_coexposure_crosstab.md",
               "# Table 3 -- Heat x Drought Co-Exposure Cross-Tab (4x4), GW and %\n\n"
               + md_table(md) + "\n\n" + NOTE + "\n")


if __name__ == "__main__":
    main()
