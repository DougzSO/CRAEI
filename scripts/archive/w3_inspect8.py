"""Read-only: dTX40 distribution and its own threshold grid, Brazil thermal."""
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf

GRID = (1, 2, 5, 10, 20, 30, 40, 60)


def main():
    proc = Path(load_paths()["processed_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                          filters=[("hazard", "in", ["TX35", "TX40"])])
    for name in ("TX35", "TX40"):
        df = hf.build_unit_hazard(units, haz, name)
        pl = df.drop_duplicates(["plant_uid", "scenario", "model"])
        q = pl.groupby("scenario")["delta"].quantile([0.5, 0.9, 1.0]).unstack()
        print(f"\n{name}: delta days/yr over plants x GCM (median, p90, max)")
        print(q.round(1).to_string())
        op = df[df["fleet"] == "operating"]
        s = hf.summarise_gcms(hf.exposure_curves(op, None, GRID))
        print(f"{name} operating, share of GW with delta >= threshold, % over GCMs")
        for scen, g in s.groupby("scenario"):
            g = g.sort_values("threshold")
            cells = [f"{r.threshold}:{r.pct_median:.0f}[{r.pct_min:.0f}-{r.pct_max:.0f}]"
                     for r in g.itertuples()]
            print(f"  {scen}", " ".join(cells))


if __name__ == "__main__":
    main()