"""W3 inspection 2 (read-only): hazard coverage, duplicates, TX35 delta quantiles."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
THERMAL = ["gas", "oil", "coal", "nuclear", "bioenergy", "multi_fuel"]
QUANTS = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def find_data() -> Path:
    for cand in (ROOT.parent / "data", ROOT / "data"):
        if (cand / "processed" / "plant_units.parquet").exists():
            return cand
    sys.exit("ABORT: plant_units.parquet not found under ../data or ./data")


def main() -> None:
    data = find_data()
    proc = data / "processed"
    log(f"data root used: {data}")
    units = pd.read_parquet(proc / "plant_units.parquet")
    bra = units[(units["country"] == "BRA") & units["fuel_class"].isin(THERMAL)]
    ids = set(bra["plant_uid"])
    log(f"BRA thermal units: {len(bra)}; plants: {len(ids)}")

    haz = pd.read_parquet(proc / "plant_hazards.parquet")
    log("hazard rows: " + str(haz["hazard"].value_counts().to_dict()))
    log("models: " + str(sorted(haz["model"].unique())))
    log("scenarios: " + str(sorted(haz["scenario"].unique())))
    key = ["plant_uid", "model", "scenario", "hazard"]
    log("rows sharing the key (plant_uid, model, scenario, hazard): "
        + str(int(haz.duplicated(key, keep=False).sum())))

    tx = haz[(haz["hazard"] == "TX35") & haz["plant_uid"].isin(ids)]
    per_plant = tx.groupby("plant_uid").size()
    log("TX35 rows per BRA thermal plant (rows: n plants): "
        + str(per_plant.value_counts().to_dict()))
    log("BRA thermal plants with no TX35 row: " + str(len(ids - set(per_plant.index))))
    log("TX35 rows with NaN delta (BRA thermal): " + str(int(tx["delta"].isna().sum())))
    log("TX35 buckets, n plants: "
        + str(tx.groupby("bucket")["plant_uid"].nunique().to_dict()))

    log("")
    log("TX35 delta quantiles per plant (unweighted), by scenario and model:")
    tab = tx.groupby(["scenario", "model"])["delta"].quantile(QUANTS).unstack()
    log(tab.round(1).to_string())
    ge30 = (tx["delta"] >= 30).groupby([tx["scenario"], tx["model"]]).mean()
    log("")
    log("fraction of plants with delta >= 30 (unweighted):")
    log(ge30.round(3).to_string())

    path = proc / "indices_daily.parquet"
    if path.exists():
        pf = pq.ParquetFile(path)
        log("")
        log(f"indices_daily: {pf.metadata.num_rows} rows")
        for fld in pf.schema_arrow:
            log(f"  {fld.name}: {fld.type}")
    else:
        log("indices_daily.parquet not found")

    out = data / "outputs" / "audit" / "w3_inspect2"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("report:", out / "report.md")


if __name__ == "__main__":
    main()