"""W4r: production run of the emulated drought nulls (D90).

Pools: hydro catchment and water-dependent thermal cell, baseline D of 1985-2014.
Aborts before writing if the pool sizes differ from 1,110 / 1,710, refitting the real D
does not reproduce the stored SPEI-12, or more than 0.1% of draws fail to fit.
The validity rule (|d sd| <= 0.20, |d corr| <= 0.10 against the real baseline) is
reported in the validation table, never used to drop a null silently.
Usage: python scripts/w4r_null_production.py [n_sim]; tables only when n_sim == 20000.
"""

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.hazards import null_emulator as ne

COUNTRY = "BRA"
N_FULL = 20000
REF_POOLS = {"catchment": 1110, "cell": 1710}
REF_CELLS = 342
TOL_Z, TOL_FD, MAX_FAIL = 1e-3, 0.01, 0.001
SEED = [23, 99, 20]
N_ROWS = 372


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet",
                        columns=["plant_uid", "country", "tech_class"])
    keep = ["hydro", "thermal_water_dependent"]
    return u[(u["country"] == COUNTRY) & u["tech_class"].isin(keep)]


def cell_table(proc, uids):
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                         columns=["plant_uid", "cell_lat", "cell_lon"])
    pc = pc.drop_duplicates("plant_uid")
    pc = pc[pc["plant_uid"].isin(set(uids))].copy()
    pc["id"] = pc["cell_lat"].astype(str) + "_" + pc["cell_lon"].astype(str)
    return pc.drop_duplicates("id")[["cell_lat", "cell_lon", "id"]]


def load_stored(proc, scale, ids):
    cols = ["id", "model", "period", "scale", "month", "SPEI_12", "distribution"]
    flt = [("scale", "==", scale), ("period", "==", "baseline")]
    sp = pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)
    sp = sp[sp["id"].isin(set(ids))].sort_values(["id", "model", "month"])
    out = {}
    for k, g in sp.groupby(["id", "model"], sort=False):
        out[k] = (g["SPEI_12"].to_numpy(dtype=float), g["distribution"].iloc[0])
    return out


def load_d(proc, name, cells, ids):
    flt = [("period", "==", "baseline")]
    if name == "catchment":
        cols = ["id", "model", "period", "month", "D"]
        wb = pd.read_parquet(proc / "water_balance_catchment.parquet",
                             columns=cols, filters=flt)
        return wb[wb["id"].isin(set(ids))]
    cols = ["cell_lat", "cell_lon", "model", "period", "month", "D"]
    wb = pd.read_parquet(proc / "water_balance_cell.parquet", columns=cols, filters=flt)
    wb = wb.merge(cells, on=["cell_lat", "cell_lon"], how="inner")
    return wb[["id", "model", "period", "month", "D"]]


def assemble(wb, stored):
    wb = wb.sort_values(["id", "model", "month"])
    keys, dd, ss, labels = [], [], [], []
    for k, g in wb.groupby(["id", "model"], sort=False):
        s = stored.get(k)
        if s is None or len(g) != N_ROWS or len(s[0]) != N_ROWS:
            continue
        keys.append(k)
        dd.append(g["D"].to_numpy(dtype=float))
        ss.append(s[0])
        labels.append(s[1])
    models = np.array([k[1] for k in keys])
    return keys, models, np.vstack(dd), np.vstack(ss), labels


def get_draws(name, variant, pool, n_sim, seq, audit, full):
    f = audit / f"draws_{name}_{variant}.npz"
    if full and f.exists():
        z = np.load(f)
        if int(z["n_sim"]) == n_sim:
            sim = {k: z[k] for k in z.files if k not in ("n_sim", "n_fail")}
            sim["n_fail"] = int(z["n_fail"])
            print(f"  {name} {variant}: loaded {f.name}")
            return sim
    t0 = time.perf_counter()
    sim = ne.simulate_emulated(pool, variant, n_sim, np.random.default_rng(seq))
    print(f"  {name} {variant}: {n_sim} draws in {time.perf_counter() - t0:.0f} s, "
          f"fit failures {sim['n_fail']}")
    if full:
        audit.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(f, n_sim=n_sim, **sim)
    return sim


def validation_rows(name, variant, sim, models, rf, h1, h2):
    gm = models[sim["series"]]
    rows = []
    for g in ["all"] + sorted(set(models)):
        sel = np.ones(len(gm), bool) if g == "all" else gm == g
        rs = np.ones(len(models), bool) if g == "all" else models == g
        sub = {k: sim[k][sel] for k in ("fd_base", "fd_h1", "fd_h2")}
        sd, co = ne.validation_metrics(sub)
        rsd = float(rf[rs].std(ddof=1))
        rco = float(np.corrcoef(h1[rs], h2[rs])[0, 1])
        rows.append({
            "pool": name, "null": variant, "gcm": g, "n_draws": int(sel.sum()),
            "n_real_series": int(rs.sum()), "sd": sd, "corr_halves": co,
            "real_sd": rsd, "real_corr_halves": rco,
            "mean_h2_minus_h1": float((sub["fd_h2"] - sub["fd_h1"]).mean()),
            "real_mean_h2_minus_h1": float((h2[rs] - h1[rs]).mean()),
            "validity": "PASS" if ne.passes_validation(sd, co, rsd, rco) else "FAIL"})
    return rows


def pct_row(name, variant, sim, n_sim):
    fut, base = sim["fd_fut"], sim["fd_base"]
    half = len(fut) // 2
    row = {"pool": name, "null": variant, "n_sim": n_sim, "n_fail": sim["n_fail"],
           "n_used": len(fut), "seed": "-".join(str(s) for s in SEED),
           "fut_mean": float(fut.mean()), "fut_sd": float(fut.std(ddof=1))}
    row.update(ne.percentile_row(fut))
    row.update({f"base_{k}": v for k, v in ne.percentile_row(base).items()})
    for tag, part in (("h1", fut[:half]), ("h2", fut[half:])):
        r = ne.percentile_row(part, (90, 99))
        row.update({f"{k}_{tag}": v for k, v in r.items()})
    return row


def main():
    n_sim = int(sys.argv[1]) if len(sys.argv) > 1 else N_FULL
    full = n_sim == N_FULL
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    audit = tab.parent / "audit" / "w4r"
    u = load_units(proc)
    tw_uids = u.loc[u["tech_class"] == "thermal_water_dependent", "plant_uid"].unique()
    hyd_ids = u.loc[u["tech_class"] == "hydro", "plant_uid"].unique()
    cells = cell_table(proc, tw_uids)
    print(f"water-dependent thermal cells: {len(cells)} (expected {REF_CELLS})")
    pools = {}
    for name, ids in (("catchment", hyd_ids), ("cell", list(cells["id"]))):
        stored = load_stored(proc, name, ids)
        wb = load_d(proc, name, cells, ids)
        pools[name] = assemble(wb, stored)
        del stored, wb
        gc.collect()
    ok = len(cells) == REF_CELLS
    for name, (keys, _, da, st, labels) in pools.items():
        nf, nl, mz, mf = ne.fidelity_stats(da, st, labels)
        good = (len(keys) == REF_POOLS[name] and nf == 0 and nl == 0
                and mz <= TOL_Z and mf <= TOL_FD)
        print(f"check {name}: series {len(keys)} (expected {REF_POOLS[name]}) | "
              f"fit failures {nf} | label mismatches {nl} | max |z-stored| {mz:.2e} | "
              f"max |dF_D| {mf:.4f} pp | {'PASS' if good else 'FAIL'}")
        ok = ok and good
    if not ok:
        raise SystemExit("ABORT: pool or fidelity check failed; nothing written")

    seeds = np.random.SeedSequence(SEED).spawn(4)
    val, pct, rdt = [], [], []
    i = 0
    for name, (keys, models, da, st, labels) in pools.items():
        rf, h1, h2 = ne.real_baseline_stats(st)
        print(f"real baseline F_D, {name}: mean {rf.mean():.2f} sd {rf.std(ddof=1):.2f} "
              f"corr halves {np.corrcoef(h1, h2)[0, 1]:.3f} "
              f"mean(h2-h1) {(h2 - h1).mean():.2f}")
        for variant in ne.VARIANTS:
            sim = get_draws(name, variant, da[:, 12:], n_sim, seeds[i], audit, full)
            i += 1
            if sim["n_fail"] / n_sim > MAX_FAIL:
                raise SystemExit(f"ABORT: {name} {variant} fit failures {sim['n_fail']}")
            val += validation_rows(name, variant, sim, models, rf, h1, h2)
            pct.append(pct_row(name, variant, sim, n_sim))
            rd = {"pool": name, "null": variant}
            rd.update(ne.rd_bins(sim["fd_base"], sim["fd_fut"]))
            rdt.append(rd)
    vt, pt, rt = pd.DataFrame(val), pd.DataFrame(pct), pd.DataFrame(rdt)
    pd.set_option("display.width", 250)
    print("\n=== validity at n =", n_sim)
    print(vt.round(3).to_string(index=False))
    print("\n=== F_D future percentiles (%), emulated baseline p50/p99, halves p99")
    show = ["pool", "null", "n_used", "fut_mean", "fut_sd", "p50", "p75", "p90", "p95",
            "p99", "base_p50", "base_p99", "p99_h1", "p99_h2"]
    print(pt[show].round(2).to_string(index=False))
    print("\n=== null R_D (% of defined draws; undefined % of all)")
    print(rt.to_string(index=False))
    if not full:
        print("\nn_sim != 20000: nothing written")
        return
    tab.mkdir(parents=True, exist_ok=True)
    vt.to_csv(tab / "w4r_emulator_validation.csv", index=False)
    pt.to_csv(tab / "w4r_null_percentiles.csv", index=False)
    rt.to_csv(tab / "w4r_null_rd.csv", index=False)
    print("\nwritten: w4r_emulator_validation.csv, w4r_null_percentiles.csv, w4r_null_rd.csv")


if __name__ == "__main__":
    main()