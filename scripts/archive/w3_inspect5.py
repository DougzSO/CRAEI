"""Read-only: curve grid, fleets and median curves for the O17 proposal."""
from pathlib import Path

import pandas as pd

from craei.config import load_paths


def main():
    paths = load_paths()
    tdir = Path(paths["outputs_tables_dir"])
    c = pd.read_csv(tdir / "w3_heat_curves_by_gcm.csv")
    print("thresholds:", sorted(c["threshold"].unique()))
    groups = sorted(c["group"].unique())
    print("groups:", groups)
    print("fleets:", sorted(c["fleet"].unique()))
    print("scenarios:", sorted(c["scenario"].unique()))
    print("\ngw_total by group and fleet:")
    print(c.groupby(["group", "fleet"])["gw_total"].first().round(2).to_string())
    want = ("all_thermal", "thermal", "gas", "bioenergy")
    sel = [g for g in groups if g in want] or groups[:3]
    sub = c[c["group"].isin(sel)]
    agg = sub.groupby(["group", "fleet", "scenario", "threshold"])["pct_gw"]
    stats = agg.agg(["min", "median", "max"]).round(1)
    print("\nmedian pct_gw over GCMs:", sel)
    print(stats["median"].unstack("threshold").to_string())
    width = (stats["max"] - stats["min"]).unstack("threshold")
    print("\nGCM range width (max-min, pp), operating:")
    print(width.xs("operating", level="fleet").to_string())
    pv = pd.read_csv(tdir / "w3_heat_planned_vs_operating.csv")
    print("\nplanned_vs_operating columns:", pv.columns.tolist())
    ph = Path(paths["processed_dir"]) / "plant_hazards.parquet"
    haz = pd.read_parquet(ph, columns=["hazard"])["hazard"].unique()
    print("hazards in plant_hazards:", sorted(haz))


if __name__ == "__main__":
    main()