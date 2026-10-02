"""O37 diagnostic: does anystart reproduce the distribution of 12-month
sums of D?

Read-only: loads the W4r production module (importlib) and the real water-
balance data, draws baselines under year and anystart, computes 12-month
rolling sums of the drawn D series, and compares their variance, mean and
quantiles against the real series.  Prints a table; writes nothing.

Usage: python scripts/o37_anystart_sums.py [n_draws]
  default n_draws = 2000 (fast; increase for tighter estimates).
"""

import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.hazards import null_emulator as ne

N_DEFAULT = 2000
QUANTILES = [0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]


def load_w4r():
    f = Path(__file__).resolve().parent / "archive" / "w4r_null_production.py"
    spec = importlib.util.spec_from_file_location("w4r_prod", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rolling_sum_12(d_monthly):
    """12-month rolling sum of a 1-D monthly array (same as accumulate but raw D)."""
    if len(d_monthly) < 12:
        return np.array([])
    kernel = np.ones(12)
    return np.convolve(d_monthly, kernel, mode="valid")


def real_sums(da):
    """Compute 12-month rolling sums of every real series in the pool."""
    all_sums = []
    for i in range(da.shape[0]):
        s = rolling_sum_12(da[i, 12:])  # skip first 12 months (burn-in)
        all_sums.append(s)
    return np.concatenate(all_sums)


def drawn_sums(da, variant, n_draws, rng):
    """Draw baselines under `variant`, compute 12-month sums of raw D."""
    pool = da[:, 12:]
    all_sums = []
    n_fail = 0
    for _ in range(n_draws):
        i = int(rng.integers(0, pool.shape[0]))
        d_base = ne.resample_months(
            pool[i], ne.N_BASE_BLOCKS, variant, rng
        )
        s = rolling_sum_12(d_base)
        if len(s) == 0:
            n_fail += 1
            continue
        all_sums.append(s)
    return np.concatenate(all_sums), n_fail


def summarise(label, arr):
    """Return a dict with mean, sd, and quantiles."""
    row = {"source": label, "n_values": len(arr),
           "mean": float(np.mean(arr)),
           "sd": float(np.std(arr, ddof=1))}
    for q in QUANTILES:
        row[f"q{q:.2f}"] = float(np.percentile(arr, q * 100))
    return row


def main():
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else N_DEFAULT
    w4r = load_w4r()
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    u = w4r.load_units(proc)
    tw = u.loc[
        u["tech_class"] == "thermal_water_dependent", "plant_uid"
    ].unique()
    hyd = u.loc[u["tech_class"] == "hydro", "plant_uid"].unique()
    cells = w4r.cell_table(proc, tw)

    seeds = np.random.SeedSequence(w4r.SEED).spawn(4)
    rows = []

    idx = 0
    for name, ids in (("catchment", hyd), ("cell", list(cells["id"]))):
        stored = w4r.load_stored(proc, name, ids)
        wb = w4r.load_d(proc, name, cells, ids)
        keys, _, da, _, labels = w4r.assemble(wb, stored)
        print(f"pool {name}: {len(keys)} series, "
              f"da shape {da.shape}")

        r = real_sums(da)
        rows.append(summarise(f"{name}_real", r))

        for variant in ne.VARIANTS:
            idx += 1
            t0 = time.perf_counter()
            d, nf = drawn_sums(
                da, variant, n_draws,
                np.random.default_rng(seeds[idx - 1])
            )
            elapsed = time.perf_counter() - t0
            rows.append(summarise(f"{name}_{variant}", d))
            print(f"  {name} {variant}: {n_draws} draws, "
                  f"{nf} fail, {elapsed:.1f}s")

    df = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    print("\n=== 12-month rolling sums of D: real vs drawn baselines ===")
    print(df.round(4).to_string(index=False))

    # ratio of drawn sd to real sd (key diagnostic)
    for name in ("catchment", "cell"):
        real_sd = df.loc[
            df["source"] == f"{name}_real", "sd"
        ].iloc[0]
        for variant in ne.VARIANTS:
            drawn_sd = df.loc[
                df["source"] == f"{name}_{variant}", "sd"
            ].iloc[0]
            ratio = drawn_sd / real_sd
            print(f"  sd ratio {name} {variant}/real: "
                  f"{ratio:.4f}")


if __name__ == "__main__":
    main()