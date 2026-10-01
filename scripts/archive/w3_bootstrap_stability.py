"""W3d stability check (read-only): percentiles vs seed and number of draws."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_bootstrap as hb
from craei.exposure import heat_fuel as hf

sys.stdout.reconfigure(encoding="utf-8")

KEY = ["group", "fleet", "scenario"]
RUNS = ((2000, 86), (2000, 1), (2000, 2), (5000, 86), (5000, 7))
MIN_CELLS = 10
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
    runs = {}
    for n, seed in RUNS:
        parts = [
            hb.cell_bootstrap(df, cells, g, (30,), n, seed)[0]
            for g in ("fuel_class", "tech_class", None)
        ]
        runs[(n, seed)] = pd.concat(parts, ignore_index=True).set_index(KEY)
    ref = runs[RUNS[0]]
    keep = (ref["n_cells_fleet"] >= MIN_CELLS) & (ref["nan_frac"] == 0)
    log(f"reference n_boot={RUNS[0][0]} seed={RUNS[0][1]}; rows compared: {int(keep.sum())}")
    for k in RUNS[1:]:
        r = runs[k].loc[ref.index]
        for col in ("boot_p025", "boot_p975"):
            d = (r[col] - ref[col]).abs()[keep]
            log(f"n_boot={k[0]} seed={k[1]} {col}: max |diff| {d.max():.2f} pp "
                f"(row {d.idxmax()}), median {d.median():.2f} pp")

    audit = Path(paths["outputs_audit_dir"]) / "w3d_stability"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()