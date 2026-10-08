"""W4a: null false-positive rate of R_D >= 2 (blocks 12/24/36/60, AR(1), white noise).

Reproduces c23d (seed 23, same stream) for block 12 and white noise and aborts
before writing if the pool or the two reference rates do not match. Writes
w4_null_rates.csv (long format). The AR(1) check against c23c is informative only.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.countries import iso as country_iso
from craei.hazards import null_model as nm

SEED, N_SIM, N_MONTHS, CANON_BLOCK = 23, 2000, 360, 12
OTHER_BLOCKS = (24, 36, 60)
SPEI_TH, RD_TH = (-1.0, -1.5, -2.0), (1.5, 2.0, 3.0)
EXPECT_POOL, REF_BB12, REF_WN = 1110, 18.88, 1.80
REF_AR1, REF_PHI = 26.12, 0.9291


def load_pool(proc):
    plants = pd.read_parquet(proc / "plants.parquet", columns=["plant_uid", "country"])
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
    bra = set(plants.loc[plants["country"] == country_iso(), "plant_uid"])
    hyd = haz[haz["bucket"].isin(["hydro_reservoir", "hydro_run_of_river"])]
    ids = set(hyd["plant_uid"]) & bra
    cols = ["id", "model", "period", "scale", "month", "SPEI_12"]
    flt = [("scale", "==", "catchment"), ("period", "==", "baseline")]
    spei = pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)
    pool, keys = nm.build_series_pool(spei, ids, N_MONTHS)
    return pool, keys, len(ids)


def prod_point(base, fut):
    t = nm.null_rate_table(base, fut, [-1.5], [2.0])
    return float(t["pct_rd_ge"].iloc[0]), int(t["n_rd_defined"].iloc[0])


def tag(tab, null, block, phi, seed):
    tab = tab.assign(null=null, block_months=block, phi=phi, seed=seed)
    tab["is_production_point"] = (tab["spei_threshold"] == -1.5) & (tab["rd_threshold"] == 2.0)
    return tab


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    out = Path(paths["outputs_tables_dir"])
    pool, keys, n_ids = load_pool(proc)
    n_models = len({k[1] for k in keys})
    print(f"pool: {len(pool)} series ({n_ids} hydro BRA ids in hazards; {n_models} models)")
    phi = nm.estimate_phi(pool)
    print(f"phi (mean lag-1 of pool) = {phi:.4f}  [c23c reference {REF_PHI}]")

    rng = np.random.default_rng(SEED)
    bb12 = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, CANON_BLOCK, rng)
    wn = nm.simulate_white_noise(N_SIM, N_MONTHS, CANON_BLOCK, rng)
    p_bb, d_bb = prod_point(*bb12)
    p_wn, d_wn = prod_point(*wn)
    print(f"check block 12: {p_bb:.4f}% (n defined {d_bb}) vs {REF_BB12}")
    print(f"check white noise: {p_wn:.4f}% (n defined {d_wn}) vs {REF_WN}")
    ok = (len(pool) == EXPECT_POOL and abs(p_bb - REF_BB12) < 0.005 and abs(p_wn - REF_WN) < 0.005)
    if not ok:
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("checks vs c23d: PASS")

    parts = [
        tag(nm.null_rate_table(*bb12, SPEI_TH, RD_TH), "block_bootstrap", CANON_BLOCK,
            np.nan, f"{SEED} (c23d stream)"),
        tag(nm.null_rate_table(*wn, SPEI_TH, RD_TH), "white_noise_ms12", CANON_BLOCK,
            np.nan, f"{SEED} (c23d stream)"),
    ]
    for b in OTHER_BLOCKS:
        sims = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, b, np.random.default_rng([SEED, b]))
        parts.append(tag(nm.null_rate_table(*sims, SPEI_TH, RD_TH), "block_bootstrap", b,
                         np.nan, f"{SEED},{b}"))
    ar = nm.simulate_ar1(N_SIM, N_MONTHS, phi, np.random.default_rng([SEED, 1]))
    parts.append(tag(nm.null_rate_table(*ar, SPEI_TH, RD_TH), "ar1", 0, phi, f"{SEED},1"))
    res = pd.concat(parts, ignore_index=True)
    res.to_csv(out / "w4_null_rates.csv", index=False)
    print(f"written: w4_null_rates.csv ({len(res)} rows)")

    pp = res[res["is_production_point"]]
    cols = ["null", "block_months", "n_sim", "n_rd_defined", "n_rd_undefined", "pct_rd_ge"]
    print("\nproduction point (SPEI <= -1.5, R_D >= 2):")
    print(pp[cols].round(2).to_string(index=False))
    ar_p = float(pp.loc[pp["null"] == "ar1", "pct_rd_ge"].iloc[0])
    print(f"\nAR(1) soft check: {ar_p:.2f}% vs c23c {REF_AR1}% (200 series; informative only)")
    print("\nsensitivity grid, pct_rd_ge (rows: null/block; cols: spei/rd):")
    grid = res.pivot_table(index=["null", "block_months"], columns=["spei_threshold", "rd_threshold"],
                           values="pct_rd_ge")
    print(grid.round(2).to_string())


if __name__ == "__main__":
    main()