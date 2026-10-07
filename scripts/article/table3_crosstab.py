"""Table 3 (article layout): 4x4 cross-tab main (operating, SSP5-8.5) and supplementary (D137).

Source: table3_coexposure_gcm_mean.csv (scripts/w5_table3_gcm_mean.py): MEAN across 5 GCMs per
cell, with min-max across GCMs in GW. Writes table3_crosstab_main.{csv,md} and
table3_crosstab_supplementary.md. The median version is table3_median_reference (see
table3_coexposure_crosstab.py).
"""

import pandas as pd
from _common import SCEN_LABEL, out_dir, read_csv, write_csv, write_text
from table3_coexposure_crosstab import canonical

CLASSES = ["low", "medium", "high", "extreme"]
FLEET = {"operating": "Operating", "planned_all": "Planned"}
DESC = ("Rows = heat class, columns = drought class. Cell = mean % capacity across 5 GCMs "
        "(mean GW) [min-max across GCMs, GW].")
NOTE = ("**Note:** Mean across 5 GCMs, unlike the headline results, which use the median. The 16 "
        "means of each table sum exactly to the fleet total. Heat class = TX35 future; drought "
        "class = F_D future against the block12 null (p50/p90/p99 cuts); both from the same GCM. "
        "Source: table3_coexposure_gcm_mean.csv (D137).")
MAIN = [("hydro", "operating", "ssp585"), ("thermal_water_dependent", "operating", "ssp585")]
SUPP = [(g, f, s) for g in ("hydro", "thermal_water_dependent")
        for f, s in [("operating", "ssp126"), ("operating", "ssp370"),
                     ("planned_all", "ssp126"), ("planned_all", "ssp370"),
                     ("planned_all", "ssp585")]]
CSV_GROUP = {"hydro": "Hydropower", "thermal_water_dependent": "Thermal"}
MAIN_TITLE = {"hydro": "Hydropower (Itaipu Brazil share)",
              "thermal_water_dependent": "Water-Dependent Thermal"}
SUPP_TITLE = {"hydro": "Hydropower", "thermal_water_dependent": "Thermal"}


def block(t, g, f, s, title):
    x = t[(t.group == g) & (t.fleet == f) & (t.scenario == s)].set_index(
        ["heat_class", "drought_class"])
    assert len(x) == 16
    lines = [f"### {title} -- {FLEET[f]} Fleet, {SCEN_LABEL[s]}", "", DESC, "",
             "| heat \\ drought | " + " | ".join(CLASSES) + " |", "|---|---|---|---|---|"]
    for h in CLASSES:
        cells = []
        for d in CLASSES:
            r = x.loc[(h, d)]
            cells.append(f"{r['pct_mean']:.1f}% ({r['gw_mean']:.1f} GW) "
                         f"[{r['gw_min']:.1f}-{r['gw_max']:.1f}]")
        lines.append(f"| **{h}** | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    t = canonical(read_csv("table3_coexposure_gcm_mean.csv"))
    d = out_dir("tables")
    cols = ["group", "heat_class", "drought_class", "pct_mean", "gw_mean", "gw_min", "gw_max"]
    main_csv = pd.concat([
        t[(t.group == g) & (t.fleet == f) & (t.scenario == s)]
        .assign(group=CSV_GROUP[g]).sort_values(["heat_class", "drought_class"])[cols]
        for g, f, s in MAIN], ignore_index=True)
    write_csv(main_csv, d / "table3_crosstab_main.csv")
    write_text(d / "table3_crosstab_main.md",
               "\n\n".join(block(t, g, f, s, MAIN_TITLE[g]) for g, f, s in MAIN)
               + "\n\n" + NOTE + "\n")
    write_text(d / "table3_crosstab_supplementary.md",
               "\n\n".join(block(t, g, f, s, SUPP_TITLE[g]) for g, f, s in SUPP)
               + "\n\n" + NOTE + "\n")


if __name__ == "__main__":
    main()
