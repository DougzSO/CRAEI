"""O36: why the emulated future F_D mean exceeds the emulated baseline mean (D92).

Replays the W4r draws (same seeds, same call order) and scores each drawn baseline and
future twice: (A) parameters refitted on the drawn baseline (what the emulator does);
(B) parameters fitted on the real series (no parameter uncertainty).
Aborts if the replay does not reproduce the stored W4r draws or a fit fails.
Descriptive only: no null is chosen or excluded.
Usage: python scripts/o36_param_uncertainty.py [n_sim]; tables only when n_sim == 20000.
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
CLASSES = ("low", "medium", "high", "extreme")


def load_w4r():
    f = Path(__file__).resolve().parent / "archive" / "w4r_null_production.py"
    spec = importlib.util.spec_from_file_location("w4r_prod", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ref_fits(da, labels, name):
    out = []
    for d, lab in zip(da, labels):
        params, dist, _ = ne.fit_quiet(ne.accumulate(d)[1:])
        if params is None or dist != lab:
            raise SystemExit(f"ABORT: {name} reference fit differs from stored label")
        out.append((params, dist))
    return out


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


def matches_saved(audit, name, variant, arr):
    z = np.load(audit / f"draws_{name}_{variant}.npz")
    n = len(arr)
    return bool(np.array_equal(z["series"][:n], arr[:, 0].astype(int))
                and np.allclose(z["fd_base"][:n], arr[:, 1], atol=1e-9)
                and np.allclose(z["fd_fut"][:n], arr[:, 2], atol=1e-9))


def reading(share):
    if not np.isfinite(share):
        return "n/a"
    if share >= SHARE_MOSTLY:
        return "mostly"
    return "partly" if share >= SHARE_PARTLY else "not"


def class_shares(x, cuts):
    parts = [x <= cuts[0], (x > cuts[0]) & (x <= cuts[1]),
             (x > cuts[1]) & (x <= cuts[2]), x > cuts[2]]
    return [float(p.mean() * 100) for p in parts]


def summarise(name, variant, arr):
    cols = {"A_base": arr[:, 1], "A_fut": arr[:, 2], "B_base": arr[:, 3], "B_fut": arr[:, 4]}
    forms = []
    for form, x in cols.items():
        row = {"pool": name, "null": variant, "form": form, "n": len(x),
               "mean": float(x.mean()), "sd": float(x.std(ddof=1))}
        row.update(ne.percentile_row(x))
        forms.append(row)
    paired = cols["A_fut"] - cols["B_fut"]
    m = {k: float(v.mean()) for k, v in cols.items()}
    excess = m["A_fut"] - m["A_base"]
    param = m["A_fut"] - m["B_fut"]
    sample = m["B_fut"] - m["B_base"]
    fit = m["B_base"] - m["A_base"]
    if abs(excess - (param + sample + fit)) > 1e-9:
        raise SystemExit("ABORT: decomposition identity failed")
    share = param / excess if excess > 0 else float("nan")
    dec = {"pool": name, "null": variant, "n": len(paired), "excess_fut_minus_base_A": excess,
           "param_A_fut_minus_B_fut": param,
           "param_se": float(paired.std(ddof=1) / np.sqrt(len(paired))),
           "sample_B_fut_minus_B_base": sample, "fit_B_base_minus_A_base": fit,
           "param_share": share, "reading": reading(share)}
    cuts = np.percentile(cols["A_fut"], [50, 90, 99])
    for form in ("A_fut", "B_fut"):
        for c, s in zip(CLASSES, class_shares(cols[form], cuts)):
            dec[f"{form}_{c}_pct"] = s
    return forms, dec


def main():
    n_sim = int(sys.argv[1]) if len(sys.argv) > 1 else N_FULL
    full = n_sim == N_FULL
    w4r = load_w4r()
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    audit = tab.parent / "audit" / "w4r"
    u = w4r.load_units(proc)
    tw = u.loc[u["tech_class"] == "thermal_water_dependent", "plant_uid"].unique()
    hyd = u.loc[u["tech_class"] == "hydro", "plant_uid"].unique()
    cells = w4r.cell_table(proc, tw)
    if len(cells) != w4r.REF_CELLS:
        raise SystemExit("ABORT: cell count differs from 342")
    pools = {}
    for name, ids in (("catchment", hyd), ("cell", list(cells["id"]))):
        stored = w4r.load_stored(proc, name, ids)
        wb = w4r.load_d(proc, name, cells, ids)
        keys, _, da, _, labels = w4r.assemble(wb, stored)
        if len(keys) != w4r.REF_POOLS[name]:
            raise SystemExit(f"ABORT: pool {name} has {len(keys)} series")
        pools[name] = (da, ref_fits(da, labels, name))
        del stored, wb
        gc.collect()
    seeds = np.random.SeedSequence(w4r.SEED).spawn(4)
    forms, decs = [], []
    i = 0
    for name, (da, refs) in pools.items():
        for variant in ne.VARIANTS:
            i += 1
            f = audit / f"o36_{name}_{variant}.npy"
            if full and f.exists() and len(np.load(f)) == n_sim:
                arr = np.load(f)
                print(f"  {name} {variant}: loaded {f.name}")
            else:
                t0 = time.perf_counter()
                arr = replay(da, refs, variant, n_sim, np.random.default_rng(seeds[i - 1]))
                print(f"  {name} {variant}: {n_sim} draws in "
                      f"{time.perf_counter() - t0:.0f} s")
            if len(arr) != n_sim:
                raise SystemExit(f"ABORT: {name} {variant} lost draws to fit failures")
            if not matches_saved(audit, name, variant, arr):
                raise SystemExit(f"ABORT: replay differs from stored W4r draws "
                                 f"({name} {variant})")
            print(f"  {name} {variant}: replay reproduces stored W4r draws (first {n_sim})")
            if full:
                np.save(f, arr)
            fr, dr = summarise(name, variant, arr)
            forms += fr
            decs.append(dr)
    ft, dt = pd.DataFrame(forms), pd.DataFrame(decs)
    pd.set_option("display.width", 250)
    print("\n=== F_D (%) by form: A = refit on drawn baseline; B = real-series parameters")
    print(ft.round(3).to_string(index=False))
    print("\n=== decomposition of mean(fut_A) - mean(base_A) and class shares in A cuts")
    print(dt.round(3).to_string(index=False))
    if not full:
        print("\nn_sim != 20000: nothing written")
        return
    ft.to_csv(tab / "o36_forms.csv", index=False)
    dt.to_csv(tab / "o36_decomposition.csv", index=False)
    print("\nwritten: o36_forms.csv, o36_decomposition.csv")


if __name__ == "__main__":
    main()