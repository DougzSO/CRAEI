"""W3f-5 (O27): TX40 exposure on its own threshold grid, checked against W3f-4."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf

GRID = (1, 2, 5, 10, 20, 30)
SHARED = (10, 20, 30)
GROUPS = ("fuel_class", "tech_class", None)
STATS = ["pct_min", "pct_median", "pct_max"]


def violations(summ):
    n = 0
    for _, g in summ.groupby(["group", "fleet", "scenario"]):
        g = g.sort_values("threshold")
        for c in STATS:
            n += int((g[c].diff() > 1e-9).sum())
    return n


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    tables = Path(paths["outputs_tables_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                          filters=[("hazard", "==", "TX40")])
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz, "TX40"))
    curves = [hf.exposure_curves(df, g, GRID) for g in GROUPS]
    summ = hf.summarise_gcms(pd.concat(curves, ignore_index=True))
    old = pd.read_csv(tables / "w3_heat_sensitivity.csv")
    old = old[old["choice"] == "metric_TX40"]
    alt = old[hf.KEY + [c + "_alt" for c in STATS]]
    m = summ.merge(alt, on=hf.KEY, validate="one_to_one")
    n_shared = int(summ["threshold"].isin(SHARED).sum())
    d = max(float((m[c] - m[c + "_alt"]).abs().max()) for c in STATS)
    viol = violations(summ)
    print(f"rows {len(summ)}; shared with W3f-4 {len(m)}/{n_shared}; max |diff| {d:.2e}")
    print(f"monotone violations: {viol}")
    if not (len(m) == n_shared and d <= 1e-6 and viol == 0):
        print("ABORT: consistency failed; nothing written")
        sys.exit(1)
    summ = summ.assign(bootstrap="not_computed", metric="TX40")
    summ.to_csv(tables / "w3_tx40_curves.csv", index=False)
    print("written: w3_tx40_curves.csv")
    sel = summ[(summ["group"] == "all_thermal")
               & summ["fleet"].isin(["operating", "planned_all"])]
    print("\nTX40, all thermal: threshold:median[min-max] % over GCMs")
    for (fleet, scen), g in sel.groupby(["fleet", "scenario"]):
        g = g.sort_values("threshold")
        cells = [f"{r.threshold}:{r.pct_median:.0f}[{r.pct_min:.0f}-{r.pct_max:.0f}]"
                 for r in g.itertuples()]
        print(f"{fleet:11s} {scen}", " ".join(cells))


if __name__ == "__main__":
    main()