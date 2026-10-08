"""W4g-rev step 1: the emulator code reproduces the stored SPEI_12 (hydro, BRA).

Writes nothing. Aborts (exit 1) if any check fails. Usage: python w4r_emulator_check.py <processed>
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.countries import iso as country_iso
from craei.hazards.null_emulator import accumulate, fd_pct, fit_quiet, standardize_acc

HYDRO_BUCKETS = ["hydro_reservoir", "hydro_run_of_river"]
N_EXPECTED = 1110
TOL_Z, TOL_FD = 1e-3, 0.01


def load_hydro_baseline(proc):
    """Return keys, model array, D (n, 372), stored SPEI_12 (n, 372), stored labels."""
    plants = pd.read_parquet(proc / "plants.parquet", columns=["plant_uid", "country"])
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
    bra = set(plants.loc[plants["country"] == country_iso(), "plant_uid"])
    ids = set(haz.loc[haz["bucket"].isin(HYDRO_BUCKETS), "plant_uid"]) & bra
    sp = pd.read_parquet(
        proc / "spei.parquet",
        filters=[("scale", "==", "catchment"), ("period", "==", "baseline")],
        columns=["id", "model", "month", "SPEI_12", "distribution"])
    sp = sp[sp["id"].isin(ids)].sort_values(["id", "model", "month"])
    stored = {}
    for k, g in sp.groupby(["id", "model"], sort=False):
        stored[k] = (g["SPEI_12"].to_numpy(dtype=float), g["distribution"].iloc[0])
    del sp
    wb = pd.read_parquet(
        proc / "water_balance_catchment.parquet",
        columns=["id", "model", "period", "month", "D"],
        filters=[("period", "==", "baseline")])
    wb = wb[wb["id"].isin(ids)].sort_values(["id", "model", "month"])
    keys, dd, ss, labels = [], [], [], []
    for k, g in wb.groupby(["id", "model"], sort=False):
        if len(g) == 372 and k in stored and len(stored[k][0]) == 372:
            keys.append(k)
            dd.append(g["D"].to_numpy(dtype=float))
            ss.append(stored[k][0])
            labels.append(stored[k][1])
    models = np.array([k[1] for k in keys])
    return keys, models, np.vstack(dd), np.vstack(ss), labels


def main():
    proc = Path(sys.argv[1])
    keys, _, da, st, labels = load_hydro_baseline(proc)
    n_fail = n_label = 0
    max_z = max_fd = 0.0
    for d, s, lab in zip(da, st, labels):
        acc = accumulate(d)
        params, dist, _ = fit_quiet(acc[1:])
        if params is None:
            n_fail += 1
            continue
        z, sv = standardize_acc(acc, dist, params), s[11:]
        n_label += int(dist != lab)
        m = np.abs(sv) < 3.0
        max_z = max(max_z, float(np.abs(z[m] - sv[m]).max()))
        max_fd = max(max_fd, abs(fd_pct(z[1:]) - fd_pct(sv[1:])))
    print(f"series {len(keys)} (expected {N_EXPECTED}) | "
          f"fit failures {n_fail} | label mismatches {n_label}")
    print(f"max |z - stored| {max_z:.2e} (tol {TOL_Z:.0e}) | "
          f"max |dF_D| {max_fd:.4f} pp (tol {TOL_FD:.2f})")
    ok = (len(keys) == N_EXPECTED and n_fail == 0 and n_label == 0
          and max_z <= TOL_Z and max_fd <= TOL_FD)
    print("CHECK:", "PASS" if ok else "ABORT")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()