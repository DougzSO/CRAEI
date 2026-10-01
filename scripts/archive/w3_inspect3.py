"""W3 inspection 3 (read-only): index names, plant_cell, tech_class, TX35 levels."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
THERMAL = ["gas", "oil", "coal", "nuclear", "bioenergy", "multi_fuel"]
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

    pf = pq.ParquetFile(proc / "indices_daily.parquet")
    parts = []
    for b in pf.iter_batches(batch_size=1_000_000, columns=["index", "period", "year"]):
        d = b.to_pandas()
        parts.append(d.groupby(["index", "period"])["year"].agg(["min", "max", "size"]))
    tab = pd.concat(parts).groupby(level=[0, 1]).agg(
        {"min": "min", "max": "max", "size": "sum"}
    )
    log("indices_daily, index x period: year min, year max, rows")
    log(tab.to_string())

    pc_path = proc / "plant_cell.parquet"
    log("")
    log("plant_cell schema:")
    for fld in pq.ParquetFile(pc_path).schema_arrow:
        log(f"  {fld.name}: {fld.type}")
    cells = pd.read_parquet(pc_path)
    log(cells.head(3).to_string())

    units = pd.read_parquet(proc / "plant_units.parquet")
    th = units[(units["country"] == "BRA") & units["fuel_class"].isin(THERMAL)]
    log("")
    log("BRA thermal tech_class (units): "
        + str(th["tech_class"].value_counts(dropna=False).to_dict()))
    log("BRA thermal water_dependent (units): "
        + str(th["water_dependent"].value_counts(dropna=False).to_dict()))

    need = {"plant_uid", "cell_lat", "cell_lon"}
    if need <= set(cells.columns):
        log("plant_cell plant_uid unique: " + str(cells["plant_uid"].is_unique))
        key = cells[sorted(need)].drop_duplicates("plant_uid")
        m = th.merge(key, on="plant_uid", how="left")
        log("thermal units without cell: " + str(int(m["cell_lat"].isna().sum())))
        by = m.groupby(["cell_lat", "cell_lon"])["capacity_mw"].sum() / 1000.0
        by = by.sort_values(ascending=False)
        log(f"distinct cells: {len(by)}; thermal GW total (all fleets): {by.sum():.2f}")
        log("top 5 cells, GW: " + str(by.head(5).round(2).to_dict()))
        log(f"top 5 cells share of GW: {100 * by.head(5).sum() / by.sum():.1f}%")
    else:
        log(f"NOTE: plant_cell lacks {sorted(need - set(cells.columns))}; join key unknown")

    cols = ["plant_uid", "model", "scenario", "hazard", "baseline_value", "future_value"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    tx = haz[haz["plant_uid"].isin(set(th["plant_uid"]))]
    q = [0.1, 0.5, 0.9, 1.0]
    log("")
    log("TX35 baseline_value quantiles (ssp126 rows), by model:")
    log(tx[tx["scenario"] == "ssp126"].groupby("model")["baseline_value"].quantile(q)
        .unstack().round(1).to_string())
    log("TX35 future_value quantiles, by scenario and model:")
    log(tx.groupby(["scenario", "model"])["future_value"].quantile(q)
        .unstack().round(1).to_string())

    out = data / "outputs" / "audit" / "w3_inspect3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("report:", out / "report.md")


if __name__ == "__main__":
    main()