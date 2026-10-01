"""W3f-3: paired scenario contrast with cell bootstrap, checked against W3a and W3d."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf
from craei.exposure import heat_scenario as hs

THRESHOLDS = (20, 30, 40)
N_BOOT = 2000
SEED = 86
SHOW = ["group", "fleet", "pair", "obs_median_diff", "obs_min_diff", "obs_max_diff",
        "n_gcm_pos", "boot_p025_pp", "boot_p975_pp", "prob_diff_gt0", "loo_min",
        "loo_max", "label"]


def check_gcm(by_gcm, tables):
    cv = pd.read_csv(tables / "w3_heat_curves_by_gcm.csv")
    cv = cv[cv["threshold"].isin(THRESHOLDS)]
    piv = cv.pivot_table(index=["group", "fleet", "model", "threshold"],
                         columns="scenario", values="pct_gw")
    refs = []
    for a, b in hs.PAIRS:
        d = (piv[a] - piv[b]).rename("ref").reset_index()
        refs.append(d.assign(pair=f"{a}-{b}"))
    key = ["group", "fleet", "pair", "model", "threshold"]
    m = by_gcm.merge(pd.concat(refs), on=key, how="inner")
    dmax = float((m["diff_obs"] - m["ref"]).abs().max())
    print(f"check per-GCM diff vs W3a curves: {len(m)}/{len(by_gcm)} rows, max {dmax:.2e}")
    return len(m) == len(by_gcm) and dmax <= 1e-6


def check_ref(ref, tables):
    w3d = pd.read_csv(tables / "w3_heat_bootstrap_shares.csv")
    key = ["group", "fleet", "scenario", "threshold"]
    cols = key + ["boot_p025", "boot_p975"]
    m = ref.merge(w3d[cols], on=key, suffixes=("", "_w3d"), validate="one_to_one")
    d = max(float((m[c] - m[c + "_w3d"]).abs().max()) for c in ("boot_p025", "boot_p975"))
    nan_same = bool((m["boot_p025"].isna() == m["boot_p025_w3d"].isna()).all())
    print(f"check draws vs W3d shares: {len(m)}/{len(ref)} rows, max {d:.2e}, "
          f"NaN pattern equal: {nan_same}")
    return len(m) == len(ref) and d <= 1e-6 and nan_same


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    tables = Path(paths["outputs_tables_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                          filters=[("hazard", "==", "TX35")])
    cells = pd.read_parquet(proc / "plant_cell.parquet",
                            columns=["plant_uid", "cell_lat", "cell_lon"])
    df = hf.add_pooled_planned(hf.build_unit_hazard(units, haz))
    res = [hs.scenario_contrast(df, cells, g, THRESHOLDS, N_BOOT, SEED)
           for g in ("fuel_class", "tech_class", None)]
    con = pd.concat([r[0] for r in res], ignore_index=True)
    gcm = pd.concat([r[1] for r in res], ignore_index=True)
    ref = pd.concat([r[2] for r in res], ignore_index=True)
    print(f"n_boot={N_BOOT} seed={SEED} rows: contrast {len(con)}, by_gcm {len(gcm)}")
    if not (check_gcm(gcm, tables) and check_ref(ref, tables)):
        print("ABORT: consistency failed; nothing written")
        sys.exit(1)
    con.to_csv(tables / "w3_heat_scenario_contrast.csv", index=False)
    gcm.to_csv(tables / "w3_heat_scenario_by_gcm.csv", index=False)
    print("label counts:", con["label"].value_counts().to_dict())
    print("written: w3_heat_scenario_contrast.csv, w3_heat_scenario_by_gcm.csv")
    sel = con[(con["threshold"] == 30)
              & con["group"].isin(["all_thermal", "bioenergy", "gas"])
              & con["fleet"].isin(["operating", "planned_all"])]
    print("\nHeadline, 30 d, median over GCMs of the per-GCM difference (pp):")
    print(sel[SHOW].round(2).to_string(index=False))


if __name__ == "__main__":
    main()