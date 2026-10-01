"""W3d (axis 1, D86): cell bootstrap and paired planned-minus-operating difference."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_bootstrap as hb
from craei.exposure import heat_fuel as hf

sys.stdout.reconfigure(encoding="utf-8")

THRESHOLDS = (20, 30, 40)
N_BOOT = 2000
SEED = 86
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def consistency(shares: pd.DataFrame, paired: pd.DataFrame, tables: Path) -> bool:
    """The observed statistics must reproduce the W3a tables exactly."""
    summ = pd.read_csv(tables / "w3_heat_summary.csv")
    key = ["group", "fleet", "scenario", "threshold"]
    a = shares.merge(summ[[*key, "pct_median"]], on=key, validate="one_to_one")
    d1 = (a["obs_median"] - a["pct_median"]).abs().max()
    pvo = pd.read_csv(tables / "w3_heat_planned_vs_operating.csv")
    key2 = ["planned_fleet", "group", "scenario", "threshold"]
    b = paired.merge(
        pvo[[*key2, "diff_median", "n_planned_ge"]], on=key2, validate="one_to_one"
    )
    d2 = (b["obs_median_diff"] - b["diff_median"]).abs().max()
    same_n = bool((b["n_planned_ge_obs"] == b["n_planned_ge"]).all())
    log(f"consistency shares: {len(a)}/{len(shares)} rows, max |diff| {d1:.2e}")
    log(f"consistency paired: {len(b)}/{len(paired)} rows, max |diff| {d2:.2e}, "
        f"n_planned_ge equal: {same_n}")
    return bool(
        len(a) == len(shares) and len(b) == len(paired)
        and d1 <= 1e-6 and d2 <= 1e-6 and same_n
    )


def main() -> None:
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    tables = Path(paths["outputs_tables_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    cells = pd.read_parquet(
        proc / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz))
    res = [
        hb.cell_bootstrap(df, cells, g, THRESHOLDS, N_BOOT, SEED)
        for g in ("fuel_class", "tech_class", None)
    ]
    shares = pd.concat([r[0] for r in res], ignore_index=True)
    paired = pd.concat([r[1] for r in res], ignore_index=True)
    shares = shares.assign(n_boot=N_BOOT, seed=SEED)
    paired = paired.assign(n_boot=N_BOOT, seed=SEED)
    log(f"n_boot={N_BOOT} seed={SEED} thresholds={THRESHOLDS}")
    if not consistency(shares, paired, tables):
        sys.exit("ABORT: observed statistics differ from the W3a tables; nothing written")
    shares.to_csv(tables / "w3_heat_bootstrap_shares.csv", index=False)
    paired.to_csv(tables / "w3_heat_bootstrap_paired.csv", index=False)

    log("")
    log("Cell bootstrap at 30 d: GCM-median share (%) with the 2.5-97.5 percentile range.")
    log("This is a sensitivity to fleet composition, not a confidence interval.")
    s30 = shares[(shares["threshold"] == 30)
                 & shares["fleet"].isin(["operating", "planned_all"])]
    show = ["group", "fleet", "scenario", "n_cells", "obs_median", "boot_p025",
            "boot_p50", "boot_p975", "nan_frac"]
    log(s30[show].sort_values(["group", "fleet", "scenario"]).round(2).to_string(index=False))

    log("")
    log("Paired planned_all minus operating at 30 d (pp, median over GCMs):")
    p30 = paired[(paired["threshold"] == 30) & (paired["planned_fleet"] == "planned_all")]
    pshow = ["group", "scenario", "n_cells", "n_cells_planned", "obs_median_diff",
             "n_planned_ge_obs", "boot_p025", "boot_p50", "boot_p975", "prob_diff_gt0",
             "nan_frac", "loo_min", "loo_max"]
    log(p30[pshow].sort_values(["group", "scenario"]).round(2).to_string(index=False))

    log("")
    log("All thermal, 30 d, the three planned-fleet definitions (O17):")
    a30 = paired[(paired["threshold"] == 30) & (paired["group"] == "all_thermal")]
    pshow2 = ["planned_fleet", *pshow[1:]]
    log(a30[pshow2].sort_values(["planned_fleet", "scenario"]).round(2).to_string(index=False))

    audit = Path(paths["outputs_audit_dir"]) / "w3d"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("tables:", tables)
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()