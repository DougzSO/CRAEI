"""Table 3 (long form): heat x drought co-exposure 4x4 cross-tab, mean over 5 GCMs (D137).

Main long-form table: table3_coexposure_crosstab.{csv,md}, from table3_coexposure_gcm_mean.csv
(scripts/w5_table3_gcm_mean.py): mean over 5 GCMs per cell with min-max; the 16 means sum to the
fleet total. Reference table with the per-cell median (C85/D130, not additive, with the gap
column): table3_median_reference.{csv,md}, from table3_coexposure.csv.
Canonical pool/null/cutset: hydro catchment, thermal cell, block12, p50_p90_p99.
"""

from _common import SCEN_LABEL, hydro_context_note, md_table, out_dir, read_csv, write_csv, write_text

GROUP = {"hydro": "Hydro", "thermal_water_dependent": "Thermal (water-dependent)"}
FLEET = {"operating": "Operating", "planned_all": "Planned (all stages)"}
POOL = {"hydro": "catchment", "thermal_water_dependent": "cell"}  # D130 canonical pools
SHARED = (
    "Itaipu reported at Brazil's 7,000 MW share for hydro (itaipu=b); not applicable for "
    "thermal. Canonical pool/null/cutset: catchment|cell, block12, p50_p90_p99. ")
NOTE_MEAN = (
    "**Note:** 192 rows = 12 group/fleet/scenario combinations x 16 heat x drought cells (4x4). "
    "Values are the MEAN across 5 GCMs (GW and % of the group's fleet capacity), with the "
    "minimum and maximum across GCMs in GW; this differs from the headline results, which use "
    "the median. The 16 means of each combination sum exactly to the fleet total, so the table "
    "is additive. " + SHARED + "Source: table3_coexposure_gcm_mean.csv (D137). Baseline "
    "1985-2014, future 2041-2070.")
NOTE_MEDIAN = (
    "**Note:** REFERENCE with the per-cell MEDIAN across 5 GCMs (C85/D130), the version before D137. "
    "192 rows = 12 group/fleet/scenario combinations x 16 cells. " + SHARED + "'Gap (GW)' = "
    "gw_total minus the sum of the 16 per-cell gw_median values for that combination (the median "
    "is not additive across cells, D80/D96/D97/D99/D106; expected, not an error). Source: "
    "table3_coexposure.csv. Baseline 1985-2014, future 2041-2070.")


def canonical(t):
    t = t[t["canonical"]] if "canonical" in t else t
    t = t[t["pool"] == t["group"].map(POOL)]
    assert len(t) == 192, len(t)
    assert t.groupby(["group", "fleet", "scenario"]).size().eq(16).all()
    return t


def labelled(t):
    t = t.assign(Group=t["group"].map(GROUP), Fleet=t["fleet"].map(FLEET),
                 Scenario=t["scenario"].map(SCEN_LABEL),
                 **{"Heat Class": t["heat_class"].str.capitalize(),
                    "Drought Class": t["drought_class"].str.capitalize()})
    t["g"] = t["group"].map({"hydro": 0, "thermal_water_dependent": 1})
    t["f"] = t["fleet"].map({"operating": 0, "planned_all": 1})
    return t.sort_values(["g", "f", "scenario", "Heat Class", "Drought Class"])


def write_pair(df, md_cols, stem, title, note):
    d = out_dir("tables")
    write_csv(df, d / (stem + ".csv"))
    md = df.assign(**{c: df[c].map(f.format) for c, f in md_cols.items()})
    write_text(d / (stem + ".md"), title + "\n\n" + md_table(md) + "\n\n" + note + "\n")


def main():
    base = ["Group", "Fleet", "Scenario", "Heat Class", "Drought Class"]
    mean = labelled(canonical(read_csv("table3_coexposure_gcm_mean.csv")))
    df = mean.assign(**{"GW Mean": mean["gw_mean"].round(3), "% Mean": mean["pct_mean"].round(2),
                        "GW Min": mean["gw_min"].round(3), "GW Max": mean["gw_max"].round(3)})[
        base + ["GW Mean", "% Mean", "GW Min", "GW Max"]].reset_index(drop=True)
    write_pair(df, {"GW Mean": "{:.3f}", "% Mean": "{:.2f}", "GW Min": "{:.3f}",
                    "GW Max": "{:.3f}"}, "table3_coexposure_crosstab",
               "# Table 3 -- Heat x Drought Co-Exposure Cross-Tab (4x4), GW and %, Mean Across "
               "5 GCMs", NOTE_MEAN + "\n\n**Note (hydropower):** " + hydro_context_note()[0])

    med = labelled(canonical(read_csv("table3_coexposure.csv")))
    dm = med.assign(**{"GW Median": med["gw_median"].round(3),
                       "% Median": med["pct_median"].round(2),
                       "Gap (GW)": med["gap_gw"].round(3)})[
        base + ["GW Median", "% Median", "Gap (GW)"]].reset_index(drop=True)
    write_pair(dm, {"GW Median": "{:.3f}", "% Median": "{:.2f}", "Gap (GW)": "{:.3f}"},
               "table3_median_reference",
               "# Table 3 (reference) -- Heat x Drought Co-Exposure Cross-Tab (4x4), Median "
               "Across 5 GCMs", NOTE_MEDIAN)


if __name__ == "__main__":
    main()
