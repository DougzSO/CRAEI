"""Table 3 (article layout): 4x4 cross-tab main (operating, SSP5-8.5) and supplementary.

Source: table3_coexposure.csv (canonical pools, see table3_coexposure_crosstab.py).
Writes table3_crosstab_main.{csv,md} and table3_crosstab_supplementary.md.
"""

import pandas as pd
from _common import SCEN_LABEL, out_dir, write_csv, write_text
from table3_coexposure_crosstab import canonical

CLASSES = ["low", "medium", "high", "extreme"]
FLEET = {"operating": "Operating", "planned_all": "Planned"}
DESC = "Rows = heat class, columns = drought class. Cell = median % capacity (median GW)."
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
             "| heat \ drought | " + " | ".join(CLASSES) + " |", "|---|---|---|---|---|"]
    for h in CLASSES:
        cells = [f"{x.loc[(h, d), 'pct_median']:.1f}% ({x.loc[(h, d), 'gw_median']:.1f} GW)"
                 for d in CLASSES]
        lines.append(f"| **{h}** | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    t = canonical()
    d = out_dir("tables")
    main_csv = pd.concat([
        t[(t.group == g) & (t.fleet == f) & (t.scenario == s)]
        .assign(group=CSV_GROUP[g])
        .sort_values(["heat_class", "drought_class"])
        [["group", "heat_class", "drought_class", "pct_median", "gw_median"]]
        for g, f, s in MAIN], ignore_index=True)
    write_csv(main_csv, d / "table3_crosstab_main.csv")
    write_text(d / "table3_crosstab_main.md",
               "\n\n".join(block(t, g, f, s, MAIN_TITLE[g]) for g, f, s in MAIN) + "\n")
    write_text(d / "table3_crosstab_supplementary.md",
               "\n\n".join(block(t, g, f, s, SUPP_TITLE[g]) for g, f, s in SUPP) + "\n")


if __name__ == "__main__":
    main()
