"""W3 inspection 4 (read-only): n35 vs tx35, plants/cells per fuel, top plants."""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths

sys.stdout.reconfigure(encoding="utf-8")

THERMAL = ["gas", "oil", "coal", "nuclear", "bioenergy", "multi_fuel"]
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def check_n35(proc: Path) -> None:
    cols = ["cell_lat", "cell_lon", "model", "scenario", "period", "year", "month",
            "index", "value"]
    df = pd.read_parquet(
        proc / "indices_daily.parquet", columns=cols,
        filters=[("index", "in", ["n35", "tx35"])],
    )
    n35 = df[df["index"] == "n35"]
    tx = df[df["index"] == "tx35"]
    log("n35 calendar months present: " + str(sorted(n35["month"].dt.month.unique())))
    log(f"tx35 rows with null month: {tx['month'].isna().mean():.3f}")
    key = ["cell_lat", "cell_lon", "model", "scenario", "period", "year"]
    s = n35.groupby(key)["value"].sum().rename("n35_sum")
    t = tx.set_index(key)["value"].rename("tx35")
    j = pd.concat([s, t], axis=1)
    both = j.dropna()
    diff = (both["n35_sum"] - both["tx35"]).abs()
    log(f"keys: n35 {len(s)}, tx35 {len(t)}, union {len(j)}, both {len(both)}")
    log(f"max |sum(n35) - tx35|: {diff.max():.6f}; keys with diff > 1e-6: "
        f"{int((diff > 1e-6).sum())}")
    del df, n35, tx, s, t, j, both
    gc.collect()


def main() -> None:
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    log(f"processed_dir: {proc}")
    check_n35(proc)

    units = pd.read_parquet(proc / "plant_units.parquet")
    th = units[(units["country"] == "BRA") & units["fuel_class"].isin(THERMAL)]
    cells = pd.read_parquet(proc / "plant_cell.parquet")
    cells = cells[["plant_uid", "cell_lat", "cell_lon"]].drop_duplicates("plant_uid")
    m = th.merge(cells, on="plant_uid", how="left", validate="many_to_one")
    m["cell"] = m["cell_lat"].astype(str) + "_" + m["cell_lon"].astype(str)
    g = m.groupby(["fuel_class", "fleet"]).agg(
        n_units=("capacity_mw", "size"),
        n_plants=("plant_uid", "nunique"),
        n_cells=("cell", "nunique"),
        gw=("capacity_mw", lambda s: s.sum() / 1000.0),
    )
    log("")
    log("units, plants, cells and GW per fuel x fleet:")
    log(g.round(2).to_string())

    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    op = th[th["fleet"] == "operating"]
    cap = op.groupby(["plant_uid", "fuel_class"], as_index=False)["capacity_mw"].sum()
    cap["gw"] = cap.pop("capacity_mw") / 1000.0
    top = cap.sort_values("gw", ascending=False).head(15)
    sel = haz[haz["plant_uid"].isin(top["plant_uid"]) & haz["scenario"].isin(["ssp126", "ssp585"])]
    wide = sel.pivot_table(index="plant_uid", columns=["scenario", "model"], values="delta")
    wide.columns = [f"{s[3:]}_{mod[:4]}" for s, mod in wide.columns]
    names = op.groupby("plant_uid")["unit_name"].first().rename("name")
    out = top.merge(cells, on="plant_uid").merge(names, on="plant_uid")
    out = out.merge(wide, left_on="plant_uid", right_index=True)
    out["uid"] = out["plant_uid"].str[:8]
    out = out.drop(columns="plant_uid")
    log("")
    log("15 largest operating thermal plants (by fuel): delta TX35 per scenario_GCM:")
    log(out.round(1).to_string(index=False))

    audit = Path(paths["outputs_audit_dir"]) / "w3_inspect4"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()