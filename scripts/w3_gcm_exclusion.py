"""W3f-6: GCM-exclusion sensitivity of Axis 1 (tables only, no hazard recomputation).

Checks that the 5-GCM case reproduces w3_heat_summary and w3_heat_planned_vs_operating
(abort before writing otherwise). Writes w3_gcm_exclusion*.csv.
"""

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.hazards import gcm_exclusion as gx

TOL = 1e-9


def compare(a, b, keys, col):
    m = a[keys + [col]].merge(b[keys + [col]], on=keys, how="outer",
                              suffixes=("", "_t"), indicator=True)
    both = int((m["_merge"] == "both").sum())
    d = float((m[col] - m[col + "_t"]).abs().max())
    return both, len(a), len(b), d


def fmt(r):
    return f"{r.pct_median:.1f} [{r.pct_min:.1f}-{r.pct_max:.1f}] n={int(r.n_gcm)}"


def main():
    tab = Path(load_paths()["outputs_tables_dir"])
    by_gcm = pd.read_csv(tab / "w3_heat_curves_by_gcm.csv")
    summ_t = pd.read_csv(tab / "w3_heat_summary.csv")
    pvo_t = pd.read_csv(tab / "w3_heat_planned_vs_operating.csv")
    sets = gx.exclusion_sets(by_gcm["model"].unique())
    summ = gx.summarize_exclusions(by_gcm, sets)
    con = gx.contrast_exclusions(by_gcm, sets)
    rank = gx.fuel_ranking(summ)

    r1 = compare(summ[summ["exclusion"] == gx.REF], summ_t, gx.KEYS, "pct_median")
    r2 = compare(con[con["exclusion"] == gx.REF], pvo_t, gx.CKEYS, "diff_median")
    print(f"check summary: both {r1[0]} / mine {r1[1]} / table {r1[2]}; max|diff| {r1[3]:.2e}")
    print(f"check contrast: both {r2[0]} / mine {r2[1]} / table {r2[2]}; max|diff| {r2[3]:.2e}")
    if not (r1[0] == r1[2] and r1[3] < TOL and r2[0] == r2[2] and r2[3] < TOL):
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("checks vs W3a/W3d tables: PASS")

    summ.to_csv(tab / "w3_gcm_exclusion.csv", index=False)
    con.to_csv(tab / "w3_gcm_exclusion_contrast.csv", index=False)
    rank.to_csv(tab / "w3_gcm_exclusion_rank.csv", index=False)
    print(f"written: summary {len(summ)}, contrast {len(con)}, rank {len(rank)} rows")

    hs = summ[(summ["group"] == "all_thermal") & (summ["fleet"] == "operating")
              & (summ["threshold"] == 30)]
    print("\nall thermal, operating, 30 d: median [min-max] over kept GCMs (%)")
    for name in sets:
        cells = [fmt(hs[(hs["exclusion"] == name) & (hs["scenario"] == sc)].iloc[0])
                 for sc in sorted(hs["scenario"].unique())]
        print(f"{name:28s} " + " | ".join(cells))

    hc = con[(con["group"] == "all_thermal") & (con["planned_fleet"] == "planned_all")
             & (con["threshold"] == 30)]
    print("\nplanned_all - operating, all thermal, 30 d: median pp, n_pos/n_gcm, sign changed")
    for name in sets:
        cells = []
        for sc in sorted(hc["scenario"].unique()):
            r = hc[(hc["exclusion"] == name) & (hc["scenario"] == sc)].iloc[0]
            cells.append(f"{r.diff_median:.2f} {int(r.n_pos)}/{int(r.n_gcm)} {r.sign_changed}")
        print(f"{name:28s} " + " | ".join(cells))

    nonref = con[con["exclusion"] != gx.REF]
    fl = nonref[nonref["sign_changed"]]
    print(f"\nsign flips (all thresholds): {len(fl)} of {len(nonref)} rows")
    f30 = fl[fl["threshold"] == 30]
    cols = ["group", "planned_fleet", "scenario", "exclusion", "ref_diff_median", "diff_median"]
    print(f"sign flips at 30 d: {len(f30)}")
    print(f30[cols].round(2).head(40).to_string(index=False))

    rn = rank[rank["exclusion"] != gx.REF]
    print(f"\nfuel-order changes (all thresholds): {int(rn['order_changed'].sum())} of {len(rn)}")
    r30 = rn[(rn["threshold"] == 30) & (rn["fleet"] == "operating") & rn["order_changed"]]
    print(f"fuel-order changes, operating, 30 d: {len(r30)}")
    print(r30[["scenario", "exclusion", "ref_order", "order"]].head(20).to_string(index=False))
    bo = rank[(rank["fleet"] == "operating") & (rank["threshold"] == 30)]
    print("\nbioenergy > gas, operating, 30 d (count of True over exclusion sets):")
    print(bo.groupby("scenario")["bio_gt_gas"].agg(["sum", "count"]).to_string())


if __name__ == "__main__":
    main()