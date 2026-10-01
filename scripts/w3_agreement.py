"""W3b (axis 1): GW exposed in at least k of the GCMs, Brazilian thermal fleet."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_agreement as ha
from craei.exposure import heat_fuel as hf

sys.stdout.reconfigure(encoding="utf-8")

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
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz))
    parts = [ha.agreement_gw(df, g, hf.THRESHOLDS) for g in ("fuel_class", "tech_class", None)]
    out = pd.concat(parts, ignore_index=True)
    tables = Path(paths["outputs_tables_dir"])
    out.to_csv(tables / "w3_heat_agreement.csv", index=False)

    chk = out[(out["group"] == "all_thermal") & (out["fleet"] == "operating")]
    log("all thermal operating GW (compare with 47.67 of the fleet table): "
        + str(chk["gw_total"].round(2).unique()))
    log("")
    log("Operating fleet, threshold 30 d: % of group GW exposed in >= k of 5 GCMs")
    head = out[(out["fleet"] == "operating") & (out["threshold"] == 30)]
    head = head[head["k_min"].isin([1, 3, 5])]
    tab = head.pivot_table(index=["group", "scenario"], columns="k_min", values="pct_gw")
    tab.columns = [f"pct_k{c}" for c in tab.columns]
    size = head.groupby(["group", "scenario"])[["gw_total", "n_plants"]].first()
    log(tab.join(size).round(1).to_string())

    audit = Path(paths["outputs_audit_dir"]) / "w3b"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("tables:", tables)
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()