"""Read-only: are exposed plant sets nested across GCMs (k>=1 equals the max GCM)?"""
from pathlib import Path

import pandas as pd

from craei.config import load_paths


def main():
    proc = Path(load_paths()["processed_dir"])
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    h = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                        filters=[("hazard", "==", "TX35")])
    print("plant level, all thermal plants with TX35 (no capacity weighting)")
    for th in (20, 30, 40):
        for scen, g in h.groupby("scenario"):
            flag = g["delta"] >= th
            e = flag.groupby([g["plant_uid"], g["model"]]).any().unstack("model")
            per = e.sum()
            best, worst = per.idxmax(), per.idxmin()
            union = int(e.any(axis=1).sum())
            not_in_best = int((e.any(axis=1) & ~e[best]).sum())
            worst_not_all = int((e[worst] & ~e.all(axis=1)).sum())
            print(f"th={th} {scen}: plants={len(e)} union={union} "
                  f"best={best}({int(per[best])}) union_not_in_best={not_in_best} "
                  f"worst={worst}({int(per[worst])}) worst_not_in_all={worst_not_all}")


if __name__ == "__main__":
    main()