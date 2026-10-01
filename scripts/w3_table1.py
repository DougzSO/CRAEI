"""W3f-1: build Table 1 (Axis 1) from the W3 tables; no new estimation."""

from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure.heat_table1 import KEY, THRESHOLDS, build_table1

NAMES = ["w3_heat_summary", "w3_heat_agreement", "w3_heat_influence",
         "w3_heat_bootstrap_shares"]
SHOW = ["group", "fleet", "scenario", "gw_total", "pct_min", "pct_median", "pct_max",
        "pct_gw_k1", "pct_gw_k5", "n_cells", "top_cell_gw_pct", "boot_p025_pp",
        "boot_p975_pp", "label"]
HEAD_GROUPS = ["all_thermal", "bioenergy", "gas", "coal", "oil", "nuclear"]


def main():
    tdir = Path(load_paths()["outputs_tables_dir"])
    t = {n: pd.read_csv(tdir / (n + ".csv")) for n in NAMES}
    tab = build_table1(*(t[n] for n in NAMES))
    summ = t["w3_heat_summary"]
    expect = int(summ["threshold"].isin(THRESHOLDS).sum())
    print("rows:", len(tab), "expected from summary:", expect)
    miss = tab.isna().sum()
    print("missing by column (only non-zero):")
    print(miss[miss > 0].to_string())
    print("label counts:", tab["label"].value_counts().to_dict())
    chk = summ.merge(t["w3_heat_influence"], on=KEY, suffixes=("", "_i"))
    print("gw_total summary vs influence, max |diff|:",
          float((chk["gw_total"] - chk["gw_total_i"]).abs().max()))
    out = tdir / "w3_table1.csv"
    tab.to_csv(out, index=False)
    print("written:", out)
    sel = tab[(tab["threshold"] == 30) & tab["group"].isin(HEAD_GROUPS)
              & tab["fleet"].isin(["operating", "planned_all"])]
    print("\nHeadline rows, threshold 30 d:")
    print(sel[SHOW].round(1).to_string(index=False))


if __name__ == "__main__":
    main()