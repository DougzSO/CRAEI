"""Table 2: leave-one-out sensitivity, 5 largest hydro plants (D113, O19).

Source: w4d_leave_one_out.csv.
"""

from _common import SCEN_LABEL, md_table, out_dir, read_csv, write_csv, write_text

BUCKET = {"hydro_reservoir": "Hydro (reservoir)", "hydro_run_of_river": "Hydro (run-of-river)"}
COLS = ["Bucket", "Scenario", "Plant Removed", "Capacity (MW)", "Share Full Fleet (%)",
        "Share Leave-One-Out (%)", "Delta (pp)"]
NOTE = (
    "**Note:** Delta (pp) = share with the plant removed minus share with the full fleet "
    "(TX35 exposure, percentage points). Source: w4d_leave_one_out.csv (D113, O19 closed). "
    "Baseline 1985-2014, future 2041-2070.")


def main():
    t = read_csv("w4d_leave_one_out.csv")
    assert len(t) == 15, len(t)
    assert t["bucket"].isin(BUCKET).all() and t["scenario"].isin(SCEN_LABEL).all()
    df = t.assign(
        Bucket=t["bucket"].map(BUCKET), Scenario=t["scenario"].map(SCEN_LABEL),
        **{"Plant Removed": t["plant_removed"], "Capacity (MW)": t["capacity_mw"],
           "Share Full Fleet (%)": t["share_full_pct"].round(2),
           "Share Leave-One-Out (%)": t["share_loo_pct"].round(2),
           "Delta (pp)": t["delta_pp"].round(2)})[COLS]
    d = out_dir("tables")
    write_csv(df, d / "table2_leave_one_out.csv")
    md = df.assign(**{
        "Capacity (MW)": df["Capacity (MW)"].map("{:.0f}".format),
        "Share Full Fleet (%)": df["Share Full Fleet (%)"].map("{:.2f}".format),
        "Share Leave-One-Out (%)": df["Share Leave-One-Out (%)"].map("{:.2f}".format),
        "Delta (pp)": df["Delta (pp)"].map("{:+.2f}".format)})
    write_text(d / "table2_leave_one_out.md",
               "# Table 2 -- Leave-One-Out Sensitivity, 5 Largest Hydro Plants\n\n"
               + md_table(md) + "\n\n" + NOTE + "\n")


if __name__ == "__main__":
    main()
