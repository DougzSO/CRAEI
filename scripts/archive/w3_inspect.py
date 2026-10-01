"""W3 inspection (read-only): plant_hazards schema; Brazil units without hazard."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "data" / "outputs" / "audit" / "w3_inspect"
LOG: list[str] = []


def log(msg: str = "") -> None:
    LOG.append(msg)
    print(msg)


def main() -> None:
    units = pd.read_parquet(PROC / "plant_units.parquet")
    log(f"plant_units: {len(units)} rows; countries: {sorted(units['country'].unique())}")
    bra = units[units["country"] == "BRA"]
    log(f"BRA units: {len(bra)}; plant_uid dtype: {bra['plant_uid'].dtype}")
    log("BRA fleet counts: " + str(bra["fleet"].value_counts().to_dict()))
    log("BRA fuel_class counts: " + str(bra["fuel_class"].value_counts().to_dict()))

    pf = pq.ParquetFile(PROC / "plant_hazards.parquet")
    log("")
    log(f"plant_hazards: {pf.metadata.num_rows} rows")
    for field in pf.schema_arrow:
        log(f"  {field.name}: {field.type}")
    head = next(pf.iter_batches(batch_size=3)).to_pandas()
    log("head(3):")
    log(head.to_string())

    if "plant_uid" not in pf.schema_arrow.names:
        log("NOTE: plant_hazards has no plant_uid column; join key to be defined")
    else:
        uids = pd.read_parquet(PROC / "plant_hazards.parquet", columns=["plant_uid"])
        uids = uids["plant_uid"].drop_duplicates()
        log("")
        log(f"hazards plant_uid: {len(uids)} unique; dtype {uids.dtype}")
        miss = bra[~bra["plant_uid"].isin(set(uids))]
        log(f"BRA units whose plant_uid is absent from hazards: {len(miss)}")
        if len(miss):
            g = miss.groupby(["fleet", "fuel_class"])["capacity_mw"].agg(["count", "sum"])
            g["GW"] = g["sum"] / 1000.0
            log(g.drop(columns="sum").to_string())
        tot = bra.groupby("fleet")["capacity_mw"].sum() / 1000.0
        log("BRA total GW by fleet (all units): " + str(tot.round(2).to_dict()))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "report.md"
    path.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("report:", path)


if __name__ == "__main__":
    main()