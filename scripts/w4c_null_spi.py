"""W4c Step 3: null false-positive rate of R_D >= 2 using SPI-12 (O18/D108 item 3).

Structural clone of scripts/w4_null.py with SPEI_12 replaced by SPI_12. The
REF_BB12/REF_WN reproduction checks from w4_null.py do not apply here (this is
the first time this null rate is computed under SPI-12; there is no prior
reference to reproduce). Validity is structural only: pool size must equal
1,110 (hydro BRA, same universe as w4_null.py) and no NaN may leak into the
simulated arrays. Output: w4c_null_rates_spi.csv.
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
EXPECT_POOL = 1110
VALUE_COL = "SPI_12"


def load_pool(proc):
    plants = pd.read_parquet(proc / "plants.parquet", columns=["plant_uid", "country"])
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
    bra = set(plants.loc[plants["country"] == country_iso(), "plant_uid"])
    hyd = haz[haz["bucket"].isin(["hydro_reservoir", "hydro_run_of_river"])]
    ids = set(hyd["plant_uid"]) & bra
    cols = ["id", "model", "period", "scale", "month", VALUE_COL]
    flt = [("scale", "==", "catchment"), ("period", "==", "baseline")]
    spi = pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)
    pool, keys = nm.build_series_pool(spi, ids, N_MONTHS, value_col=VALUE_COL)
    return pool, keys, len(ids)


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

    any_nan = any(np.isnan(x).any() for x in pool)
    ok_pool = (len(pool) == EXPECT_POOL) and not any_nan
    print(f"check pool size: {len(pool)} (expect {EXPECT_POOL}); any NaN in pool: {any_nan} "
          f"-> {'PASS' if ok_pool else 'FAIL'}")
    if not ok_pool:
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("check: PASS")

    phi = nm.estimate_phi(pool)
    print(f"phi (mean lag-1 of SPI-12 pool) = {phi:.4f}  [informative only, no reference]")

    rng = np.random.default_rng(SEED)
    bb12 = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, CANON_BLOCK, rng)
    wn = nm.simulate_white_noise(N_SIM, N_MONTHS, CANON_BLOCK, rng)

    parts = [
        tag(nm.null_rate_table(*bb12, SPEI_TH, RD_TH), "block_bootstrap", CANON_BLOCK,
            np.nan, f"{SEED} (SPI stream)"),
        tag(nm.null_rate_table(*wn, SPEI_TH, RD_TH), "white_noise_ms12", CANON_BLOCK,
            np.nan, f"{SEED} (SPI stream)"),
    ]
    for b in OTHER_BLOCKS:
        sims = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, b, np.random.default_rng([SEED, b]))
        parts.append(tag(nm.null_rate_table(*sims, SPEI_TH, RD_TH), "block_bootstrap", b,
                         np.nan, f"{SEED},{b}"))
    ar = nm.simulate_ar1(N_SIM, N_MONTHS, phi, np.random.default_rng([SEED, 1]))
    parts.append(tag(nm.null_rate_table(*ar, SPEI_TH, RD_TH), "ar1", 0, phi, f"{SEED},1"))
    res = pd.concat(parts, ignore_index=True)
    res.to_csv(out / "w4c_null_rates_spi.csv", index=False)
    print(f"written: w4c_null_rates_spi.csv ({len(res)} rows)")

    pp = res[res["is_production_point"]]
    cols = ["null", "block_months", "n_sim", "n_rd_defined", "n_rd_undefined", "pct_rd_ge"]
    print("\nproduction point (SPI <= -1.5, R_D >= 2):")
    print(pp[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
