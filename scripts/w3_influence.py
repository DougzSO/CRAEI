"""W3c (axis 1, O19): leave-one-cell-out influence on the thermal heat shares."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf
from craei.exposure import heat_influence as hi

sys.stdout.reconfigure(encoding="utf-8")

THRESHOLDS = (20, 30, 40)
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def main() -> None:
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    cells = pd.read_parquet(
        proc / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz))
    parts = [
        hi.leave_one_cell_out(df, cells, g, t)
        for g in ("fuel_class", "tech_class", None)
        for t in THRESHOLDS
    ]
    out = pd.concat(parts, ignore_index=True)
    tables = Path(paths["outputs_tables_dir"])
    out.to_csv(tables / "w3_heat_influence.csv", index=False)

    log("Leave-one-cell-out at threshold 30 d, operating and planned_all fleets.")
    log("pct_median = median over GCMs; loo_* = range of that median dropping one cell;")
    log("top_* = most influential cell (shift in pp; share of the group GW in the cell).")
    sel = out[(out["threshold"] == 30) & out["fleet"].isin(["operating", "planned_all"])]
    show = ["group", "fleet", "scenario", "n_cells", "gw_total", "pct_median", "loo_min",
            "loo_max", "top_cell_lat", "top_cell_lon", "top_shift_pp", "top_cell_gw_pct"]
    log(sel[show].sort_values(["group", "fleet", "scenario"]).round(2).to_string(index=False))

    audit = Path(paths["outputs_audit_dir"]) / "w3c"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("tables:", tables)
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()