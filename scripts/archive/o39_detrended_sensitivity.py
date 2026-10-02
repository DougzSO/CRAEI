"""O39 sensitivity: emulated drought nulls on a detrended D (own id; never headline).

Repeats the O36/D93 design (replay year/anystart block draws; score each drawn
baseline/future with A = parameters refit on the draw and B = parameters fit on
the real-series pool; decompose fut_A - base_A into parameter/sample/fit terms;
same mostly/partly/not reading, >=0.75 / 0.25-0.75 / <0.25) on a copy of the
monthly D series with each series' own ordinary-least-squares linear trend (over
month index, full 372-month series) subtracted, keeping its own mean. Design
fixed before running (chat), per-series detrending (not per-GCM), same
decomposition and reading convention as D93 -- no new category.

Uses the SAME SeedSequence spawn(4) as scripts/archive/w4r_null_production.py
and scripts/archive/o36_param_uncertainty.py, so the random draw stream (which
series is picked, which blocks) is identical to the undetrended run; any
difference in the results comes from detrending alone, not from different
draws.

A refit that lands on a different distribution family than the series' stored
(undetrended) label is NOT an error here (detrending can plausibly change the
fit); it is only counted and reported. A refit that fails outright still
aborts, matching this project's abort-before-write convention.

Read-only with respect to production tables and null_emulator; writes its own
o39_* tables only when n_sim == N_FULL. Sensitivity only: never a headline
result, never changes W4r's tolerance, cuts, or FAIL handling.

Usage: python scripts/o39_detrended_sensitivity.py [n_sim]
"""

import gc
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.hazards import null_emulator as ne

N_FULL = 20000
SHARE_MOSTLY, SHARE_PARTLY = 0.75, 0.25


def load_w4r():
    f = Path(__file__).resolve().parent / "archive" / "w4r_null_production.py"
    spec = importlib.util.spec_from_file_location("w4r_prod", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def detrend(da):
    """Remove each row's own OLS linear trend against month index; keep its mean.

    Returns (detrended array, slopes, r_squared), one slope/r2 per series.
    """
    _, m = da.shape
    t_c = np.arange(m, dtype=float) - (m - 1) / 2.0
    denom = float((t_c**2).sum())
    slopes = (da * t_c).sum(axis=1) / denom
    fitted = np.outer(slopes, t_c)
    out = da - fitted
    centered = da - da.mean(axis=1, keepdims=True)
    resid_var = (centered - fitted) ** 2
    total_var = centered**2
    with np.errstate(divide="ignore", invalid="ignore"):
        r2 = 1.0 - resid_var.sum(axis=1) / total_var.sum(axis=1)
    return out, slopes, r2


def ref_fits(da, labels, name):
    out, n_mismatch = [], 0
    for d, lab in zip(da, labels):
        params, dist, _ = ne.fit_quiet(ne.accumulate(d)[1:])
        if params is None:
            raise SystemExit(f"ABORT: {name} reference fit failed on detrended series")
        if dist != lab:
            n_mismatch += 1
        out.append((params, dist))
    return out, n_mismatch


def draw_row(d_base, d_fut, ref):
    acc_b, acc_f = ne.accumulate(d_base), ne.accumulate(d_fut)
    params, dist, _ = ne.fit_quiet(acc_b[1:])
    if params is None:
        return None
    za = ne.standardize_acc(acc_b, dist, params)[1:]
    zf = ne.standardize_acc(acc_f, dist, params)
    zb_ref = ne.standardize_acc(acc_b, ref[1], ref[0])[1:]
    zf_ref = ne.standardize_acc(acc_f, ref[1], ref[0])
    return ne.fd_pct(za), ne.fd_pct(zf), ne.fd_pct(zb_ref), ne.fd_pct(zf_ref)


def replay(da, refs, variant, n_sim, rng):
    pool = da[:, 12:]
    rows = []
    for _ in range(n_sim):
        i = int(rng.integers(0, pool.shape[0]))
        d_base = ne.resample_months(pool[i], ne.N_BASE_BLOCKS, variant, rng)
        d_fut = ne.resample_months(pool[i], ne.N_FUT_BLOCKS, variant, rng)
        res = draw_row(d_base, d_fut, refs[i])
        if res is not None:
            rows.append((i,) + res)
    return np.array(rows, dtype=float).reshape(-1, 5)


def reading(share):
    if not np.isfinite(share):
        return "n/a"
    if share >= SHARE_MOSTLY:
        return "mostly"
    return "partly" if share >= SHARE_PARTLY else "not"


def summarise(name, variant, arr):
    cols = {"A_base": arr[:, 1], "A_fut": arr[:, 2], "B_base": arr[:, 3], "B_fut": arr[:, 4]}
    forms = []
    for form, x in cols.items():
        row = {"pool": name, "null": variant, "form": form, "n": len(x),
               "mean": float(x.mean()), "sd": float(x.std(ddof=1))}
        row.update(ne.percentile_row(x))
        forms.append(row)
    m = {k: float(v.mean()) for k, v in cols.items()}
    excess = m["A_fut"] - m["A_base"]
    param = m["A_fut"] - m["B_fut"]
    sample = m["B_fut"] - m["B_base"]
    fit = m["B_base"] - m["A_base"]
    if abs(excess - (param + sample + fit)) > 1e-9:
        raise SystemExit("ABORT: decomposition identity failed")
    share = param / excess if excess > 0 else float("nan")
    paired = cols["A_fut"] - cols["B_fut"]
    dec = {"pool": name, "null": variant, "n": len(paired), "excess_fut_minus_base_A": excess,
           "param_A_fut_minus_B_fut": param,
           "param_se": float(paired.std(ddof=1) / np.sqrt(len(paired))),
           "sample_B_fut_minus_B_base": sample, "fit_B_base_minus_A_base": fit,
           "param_share": share, "reading": reading(share)}
    p = np.percentile(cols["A_fut"], [50, 90, 99])
    dec["A_fut_p50"], dec["A_fut_p90"], dec["A_fut_p99"] = p[0], p[1], p[2]
    return forms, dec


def main():
    n_sim = int(sys.argv[1]) if len(sys.argv) > 1 else N_FULL
    full = n_sim == N_FULL
    w4r = load_w4r()
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    u = w4r.load_units(proc)
    tw = u.loc[u["tech_class"] == "thermal_water_dependent", "plant_uid"].unique()
    hyd = u.loc[u["tech_class"] == "hydro", "plant_uid"].unique()
    cells = w4r.cell_table(proc, tw)
    if len(cells) != w4r.REF_CELLS:
        raise SystemExit("ABORT: cell count differs from 342")
    pools, trend_rows = {}, []
    for name, ids in (("catchment", hyd), ("cell", list(cells["id"]))):
        stored = w4r.load_stored(proc, name, ids)
        wb = w4r.load_d(proc, name, cells, ids)
        keys, _, da, _, labels = w4r.assemble(wb, stored)
        if len(keys) != w4r.REF_POOLS[name]:
            raise SystemExit(f"ABORT: pool {name} has {len(keys)} series")
        da_dt, slopes, r2 = detrend(da)
        refs, n_mismatch = ref_fits(da_dt, labels, name)
        pools[name] = (da_dt, refs)
        trend_rows.append({"pool": name, "n_series": len(slopes),
                            "slope_mean": float(np.mean(slopes)),
                            "slope_sd": float(np.std(slopes, ddof=1)),
                            "slope_min": float(np.min(slopes)),
                            "slope_max": float(np.max(slopes)),
                            "r2_median": float(np.median(r2)),
                            "n_label_mismatch": n_mismatch})
        del stored, wb
        gc.collect()
    trend_t = pd.DataFrame(trend_rows)
    print("=== per-series linear trend removed from D (slope: D units / month) ===")
    print(trend_t.round(4).to_string(index=False))

    seeds = np.random.SeedSequence(w4r.SEED).spawn(4)
    forms, decs = [], []
    i = 0
    for name, (da_dt, refs) in pools.items():
        for variant in ne.VARIANTS:
            i += 1
            t0 = time.perf_counter()
            arr = replay(da_dt, refs, variant, n_sim, np.random.default_rng(seeds[i - 1]))
            print(f"  {name} {variant}: {n_sim} draws in {time.perf_counter() - t0:.0f} s, "
                  f"{n_sim - len(arr)} lost to fit failures")
            if len(arr) != n_sim:
                raise SystemExit(f"ABORT: {name} {variant} lost draws to fit failures")
            fr, dr = summarise(name, variant, arr)
            forms += fr
            decs.append(dr)
    ft, dt = pd.DataFrame(forms), pd.DataFrame(decs)
    pd.set_option("display.width", 250)
    print("\n=== F_D (%) by form, detrended D: A = refit on drawn baseline; B = real-series params")
    print(ft.round(3).to_string(index=False))
    print("\n=== decomposition of mean(fut_A) - mean(base_A), detrended D ===")
    print(dt.round(3).to_string(index=False))
    if not full:
        print("\nn_sim != 20000: nothing written")
        return
    trend_t.to_csv(tab / "o39_trend_summary.csv", index=False)
    ft.to_csv(tab / "o39_forms.csv", index=False)
    dt.to_csv(tab / "o39_decomposition.csv", index=False)
    print("\nwritten: o39_trend_summary.csv, o39_forms.csv, o39_decomposition.csv")


if __name__ == "__main__":
    main()