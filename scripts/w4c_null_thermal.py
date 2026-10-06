"""W4c/O43: null false-positive rate of R_D>=2 for thermal_water_dependent
plants, cell-scale, SPEI-12 and SPI-12 (follow-up to O18/D123 merge bug, D125).

Structural clone of scripts/w4_null.py and scripts/w4c_null_spi.py, generalized
to the THERMAL pool: BRA thermal_water_dependent plants' assigned cells
(cell-scale, not catchment -- hydro and thermal use different spatial scales
by construction, see consolidate.py::compute_drought_hazards). This null did
not exist before; scripts/w4c_spi_vs_spei.py (C77/D123) incorrectly applied
the HYDRO null (catchment, 1,110-series pool) to thermal rows via a merge
keyed only on `hazard`, not `(group, hazard)`. This script builds the correct
thermal null; the merge bug is fixed separately in w4c_spi_vs_spei.py (D125).

No regression check applies (first time computed; no prior reference).
Validity is structural only: pool size reported (not asserted against an
invented number), zero NaN required.

Output: w4c_null_rates_thermal.csv (same schema as w4_null_rates.csv /
w4c_null_rates_spi.csv, plus a `hazard` column since SPEI_12 and SPI_12 are
both computed here).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.hazards import null_model as nm

COUNTRY = "BRA"
SEED, N_SIM, N_MONTHS, CANON_BLOCK = 23, 2000, 360, 12
OTHER_BLOCKS = (24, 36, 60)
SPEI_TH, RD_TH = (-1.0, -1.5, -2.0), (1.5, 2.0, 3.0)
VALUE_COLS = {"spei": "SPEI_12", "spi": "SPI_12"}


def thermal_cell_ids(proc):
    plants = pd.read_parquet(proc / "plants.parquet",
                              columns=["plant_uid", "country", "tech_class"])
    haz_bucket = pd.read_parquet(proc / "plant_hazards.parquet",
                                  columns=["plant_uid", "bucket"]).drop_duplicates("plant_uid")
    valid_uids = set(haz_bucket.loc[haz_bucket["bucket"] == "thermal_water_dependent", "plant_uid"])
    tw = plants[(plants["country"] == COUNTRY)
                & (plants["tech_class"] == "thermal_water_dependent")
                & plants["plant_uid"].isin(valid_uids)]
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                          columns=["plant_uid", "cell_lat", "cell_lon"])
    tw_cells = tw.merge(pc, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
    n_before, n_after = tw["plant_uid"].nunique(), tw_cells["plant_uid"].nunique()
    if n_after != n_before:
        print(f"WARNING: {n_before - n_after} thermal_water_dependent plants have no assigned cell")
    ids = set(tw_cells["cell_lat"].astype(str) + "_" + tw_cells["cell_lon"].astype(str))
    return ids, n_after


def load_pool(proc, ids, value_col):
    cols = ["id", "model", "period", "scale", "month", value_col]
    flt = [("scale", "==", "cell"), ("period", "==", "baseline")]
    df = pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)
    return nm.build_series_pool(df, ids, N_MONTHS, value_col=value_col)


def tag(tab, hazard, null, block, phi, seed):
    tab = tab.assign(hazard=hazard, null=null, block_months=block, phi=phi, seed=seed)
    tab["is_production_point"] = (tab["spei_threshold"] == -1.5) & (tab["rd_threshold"] == 2.0)
    return tab


def run_hazard(proc, ids, hazard, value_col):
    pool, keys = load_pool(proc, ids, value_col)
    n_models = len({k[1] for k in keys})
    any_nan = any(np.isnan(x).any() for x in pool)
    print(f"[{hazard}] pool: {len(pool)} series ({len(ids)} thermal cells; {n_models} models); any NaN: {any_nan}")
    if any_nan or len(pool) == 0:
        print(f"CHECK FAILED ({hazard}): NaN or empty pool")
        sys.exit(1)

    phi = nm.estimate_phi(pool)
    print(f"[{hazard}] phi (mean lag-1) = {phi:.4f} [informative only, no reference]")

    rng = np.random.default_rng([SEED, 100])
    bb12 = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, CANON_BLOCK, rng)
    wn = nm.simulate_white_noise(N_SIM, N_MONTHS, CANON_BLOCK, rng)
    parts = [
        tag(nm.null_rate_table(*bb12, SPEI_TH, RD_TH), hazard, "block_bootstrap", CANON_BLOCK,
            np.nan, f"{SEED},100 (thermal cell stream)"),
        tag(nm.null_rate_table(*wn, SPEI_TH, RD_TH), hazard, "white_noise_ms12", CANON_BLOCK,
            np.nan, f"{SEED},100 (thermal cell stream)"),
    ]
    for b in OTHER_BLOCKS:
        sims = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, b, np.random.default_rng([SEED, 100, b]))
        parts.append(tag(nm.null_rate_table(*sims, SPEI_TH, RD_TH), hazard, "block_bootstrap", b,
                          np.nan, f"{SEED},100,{b}"))
    ar = nm.simulate_ar1(N_SIM, N_MONTHS, phi, np.random.default_rng([SEED, 100, 1]))
    parts.append(tag(nm.null_rate_table(*ar, SPEI_TH, RD_TH), hazard, "ar1", 0, phi, f"{SEED},100,1"))
    return pd.concat(parts, ignore_index=True)


def main():
    paths = load_paths()
    proc, out = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    ids, n_plants = thermal_cell_ids(proc)
    print(f"thermal_water_dependent BRA plants (valid bucket, with cell): {n_plants}")
    print(f"unique thermal cells (pool population): {len(ids)}")

    results = [run_hazard(proc, ids, hazard, vc) for hazard, vc in VALUE_COLS.items()]
    res = pd.concat(results, ignore_index=True)
    res.to_csv(out / "w4c_null_rates_thermal.csv", index=False)
    print(f"\nwritten: w4c_null_rates_thermal.csv ({len(res)} rows)")

    pp = res[res["is_production_point"]]
    cols = ["hazard", "null", "block_months", "n_sim", "n_rd_defined", "n_rd_undefined", "pct_rd_ge"]
    print("\nproduction point (threshold <= -1.5, R_D >= 2), thermal cell-scale null:")
    print(pp[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
