"""Table 2: leave-one-out sensitivity, 5 largest hydro plants (D113, O19, D135).

Source: w4d_leave_one_out.csv (scripts/w4d_leave_one_out.py). Main table: Itaipu at the
Brazilian share (version b, 7,000 MW, headline D102). The whole-asset version (a,
14,000 MW) is written as table2_sensitivity_itaipu_a.{csv,md}.
"""

from _common import SCEN_LABEL, md_table, out_dir, read_csv, write_csv, write_text

BUCKET = {"hydro_reservoir": "Hydro (reservoir)", "hydro_run_of_river": "Hydro (run-of-river)"}
COLS = ["Bucket", "Scenario", "Plant Removed", "Capacity (MW)", "Share Full Fleet (%)",
        "Share Leave-One-Out (%)", "Delta (pp)"]
NOTE = (
    "**Note:** Share = percentage of the bucket's operating Brazilian hydro capacity with "
    "drought exposure R_D >= 2.0 (future-to-baseline frequency ratio of SPEI-12 <= -1.5), "
    "capacity-weighted, median across 5 GCMs. Raw capacity share, not excess over the null; not "
    "comparable with D102. Delta (pp) = "
    "share with the plant removed minus share with the full fleet. {itaipu} Source: "
    "w4d_leave_one_out.csv (D113, D135, O19 closed). Baseline 1985-2014, future 2041-2070.")
ITAIPU_NOTE = {
    "b": "Itaipu at the Brazilian share (7,000 MW, version b, D102); the whole binational asset "
         "(14,000 MW, version a) is in table2_sensitivity_itaipu_a.",
    "a": "Sensitivity: Itaipu as the whole binational asset (14,000 MW, version a); the headline "
         "table uses the Brazilian share (7,000 MW, version b)."}
TITLE = {"b": "# Table 2 -- Leave-One-Out Sensitivity, 5 Largest Hydro Plants",
         "a": "# Table 2 (sensitivity) -- Leave-One-Out, 5 Largest Hydro Plants, Itaipu Whole "
              "Asset (14,000 MW)"}
STEM = {"b": "table2_leave_one_out", "a": "table2_sensitivity_itaipu_a"}


def build(t, ver):
    t = t[t["itaipu"] == ver]
    assert len(t) == 15, (ver, len(t))
    assert t["bucket"].isin(BUCKET).all() and t["scenario"].isin(SCEN_LABEL).all()
    df = t.assign(
        Bucket=t["bucket"].map(BUCKET), Scenario=t["scenario"].map(SCEN_LABEL),
        **{"Plant Removed": t["plant_removed"], "Capacity (MW)": t["capacity_mw"],
           "Share Full Fleet (%)": t["share_full_pct"].round(2),
           "Share Leave-One-Out (%)": t["share_loo_pct"].round(2),
           "Delta (pp)": t["delta_pp"].round(2)})[COLS]
    d = out_dir("tables")
    write_csv(df, d / (STEM[ver] + ".csv"))
    md = df.assign(**{
        "Capacity (MW)": df["Capacity (MW)"].map("{:.0f}".format),
        "Share Full Fleet (%)": df["Share Full Fleet (%)"].map("{:.2f}".format),
        "Share Leave-One-Out (%)": df["Share Leave-One-Out (%)"].map("{:.2f}".format),
        "Delta (pp)": df["Delta (pp)"].map("{:+.2f}".format)})
    write_text(d / (STEM[ver] + ".md"), TITLE[ver] + "\n\n" + md_table(md) + "\n\n"
               + NOTE.format(itaipu=ITAIPU_NOTE[ver]) + "\n")


def main():
    t = read_csv("w4d_leave_one_out.csv")
    for ver in ("b", "a"):
        build(t, ver)


if __name__ == "__main__":
    main()
