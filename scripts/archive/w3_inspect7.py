"""Read-only: nesting of exposed sets across GCMs, Brazil thermal, GW-weighted."""
import inspect
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf

THRESHOLDS = (20, 30, 40)


def one(g, th, fleet, scen):
    t = g.groupby(["plant_uid", "model"]).agg(
        cap=("capacity_mw", "sum"), delta=("delta", "first")).reset_index()
    d = t.pivot(index="plant_uid", columns="model", values="delta")
    cap = t.groupby("plant_uid")["cap"].first().reindex(d.index)
    e = d >= th
    gw = e.mul(cap, axis=0).sum() / 1000.0
    best, worst = gw.idxmax(), gw.idxmin()
    uni, inter = e.any(axis=1), e.all(axis=1)
    out_best = uni & ~e[best]
    in_worst_not_all = e[worst] & ~inter
    tot = cap.sum() / 1000.0
    print(f"{fleet:11s} {scen} th={th}: plants={len(d)} GW={tot:.2f} "
          f"max={gw.max():.2f}({best[:4]}) union={cap[uni].sum() / 1000:.2f} "
          f"union_not_in_best={cap[out_best].sum() / 1000:.3f}GW/{int(out_best.sum())}pl "
          f"min={gw.min():.2f}({worst[:4]}) "
          f"worst_not_in_all={cap[in_worst_not_all].sum() / 1000:.3f}GW/"
          f"{int(in_worst_not_all.sum())}pl")


def main():
    proc = Path(load_paths()["processed_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                          filters=[("hazard", "==", "TX35")])
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz))
    print("columns:", df.columns.tolist())
    if "country" in df.columns:
        print("countries:", df["country"].unique().tolist())
    for fleet in ("operating", "planned_all"):
        for scen in sorted(df["scenario"].unique()):
            g = df[(df["fleet"] == fleet) & (df["scenario"] == scen)]
            for th in THRESHOLDS:
                one(g, th, fleet, scen)
    print("\nheat_fuel public functions:")
    for name, fn in inspect.getmembers(hf, inspect.isfunction):
        if fn.__module__ == hf.__name__ and not name.startswith("_"):
            print(" ", name, inspect.signature(fn))


if __name__ == "__main__":
    main()