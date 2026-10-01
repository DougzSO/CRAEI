"""W3f-2: plotting table for the threshold curves, checked against W3a and Table 1."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_curves as hc
from craei.exposure.heat_fuel import KEY

NAMES = ["w3_heat_summary", "w3_heat_agreement", "w3_heat_influence",
         "w3_heat_bootstrap_shares"]
CMP = ["pct_min", "pct_median", "pct_max", "pct_gw_k3", "pct_gw_k5"]


def main():
    tdir = Path(load_paths()["outputs_tables_dir"])
    t = {n: pd.read_csv(tdir / (n + ".csv")) for n in NAMES}
    tab = hc.curve_table(*(t[n] for n in NAMES))
    n_sum = len(t["w3_heat_summary"])
    t1 = pd.read_csv(tdir / "w3_table1.csv")
    m = tab.merge(t1, on=KEY, suffixes=("", "_t1"), validate="one_to_one")
    d = max(float((m[c] - m[c + "_t1"]).abs().max()) for c in CMP)
    same_label = bool((m["label"] == m["label_t1"]).all())
    viol = hc.monotone_violations(tab)
    print(f"rows: {len(tab)} (summary {n_sum}); shared with Table 1: {len(m)}/{len(t1)}")
    print(f"max |diff| vs Table 1: {d:.2e}; labels equal: {same_label}")
    print(f"monotone violations: {viol}")
    print("labels:", tab["label"].value_counts().to_dict())
    ok = (len(tab) == n_sum and len(m) == len(t1) and d <= 1e-9
          and same_label and viol == 0)
    if not ok:
        print("ABORT: consistency failed; nothing written")
        sys.exit(1)
    tab.to_csv(tdir / "w3_curves_plot.csv", index=False)
    print("written: w3_curves_plot.csv")
    sel = tab[(tab["group"] == "all_thermal")
              & tab["fleet"].isin(["operating", "planned_all"])]
    print("\nall thermal: threshold:median[min-max] % over GCMs")
    for (fleet, scen), g in sel.groupby(["fleet", "scenario"]):
        g = g.sort_values("threshold")
        cells = [f"{r.threshold}:{r.pct_median:.0f}[{r.pct_min:.0f}-{r.pct_max:.0f}]"
                 for r in g.itertuples()]
        print(f"{fleet:11s} {scen}", " ".join(cells))


if __name__ == "__main__":
    main()