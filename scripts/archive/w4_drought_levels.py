"""W4g: drought level classes against the no-change null (D88, O29).

Null percentiles from 20,000 simulations in default_rng([23, 99]) (block 12; AR(1) in
[23, 99, 1]); catchment pool (hydro) and cell pool (water-dependent thermal).
Aborts before writing if: pool sizes differ from 1,110 / 1,710; the W4a stream (2,000
simulations, seed 23) does not reproduce 18.88% and the percentiles pasted in C44; the
production F_D function does not reproduce plant_hazards; classes do not add up or the
reference totals fail. Cooling bound: upper (all water-dependent thermal), see O32.
"""

import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned
from craei.hazards import drought_levels as dl
from craei.hazards import null_model as nm
from craei.hazards.consolidate import _f_d_r_d

COUNTRY, TH, TOL = "BRA", -1.5, 1e-9
N_MONTHS, SEED, N_CHECK, N_PROD, MIN_SITES = 360, 23, 2000, 20000, 10
REF_POOLS = {"catchment": 1110, "cell": 1710}
REF_RATE, REF_N_DEF = 18.88, 1991
REF_PCT = {50: 6.11, 75: 8.61, 90: 11.11, 95: 12.78, 99: 15.0}
REF_GW = (109.67, 102.67, 39.77)
GROUPS = {"hydro": "catchment", "thermal_water_dependent": "cell"}
OTHER = {"catchment": "cell", "cell": "catchment"}
NULLS = ("block12", "ar1")
CATS_FD = {"level_fut": dl.FD_LABELS, "level_base": dl.FD_LABELS}
CATS_RD = {"rd_class": dl.RD_LABELS}
KEYS = [k for k in hl.GROUP_KEYS if k != "model"]
FD_COLS = ["plant_uid", "model", "scenario", "baseline_value", "future_value", "ratio"]


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet")
    keep = ["hydro", "thermal_water_dependent"]
    u = u[(u["country"] == COUNTRY) & u["tech_class"].isin(keep)].reset_index(drop=True)
    u["uid"] = u.index
    u["group"] = np.where(u["tech_class"] == "hydro", "hydro", "thermal_water_dependent")
    return u


def load_cell_spei(proc, ids):
    cols = ["id", "model", "scenario", "period", "scale", "month", "SPEI_12"]
    flt = [("scale", "==", "cell"), ("id", "in", sorted(ids))]
    return pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)


def load_catch_baseline(proc):
    cols = ["id", "model", "period", "scale", "month", "SPEI_12"]
    flt = [("scale", "==", "catchment"), ("period", "==", "baseline")]
    return pd.read_parquet(proc / "spei.parquet", columns=cols, filters=flt)


def summarise_null(b, f):
    return {"pct": dl.null_fd_percentiles(b, f, TH), "fd_future": dl.fd_pct(f, TH),
            "bins": dl.rd_null_shares(b, f, TH)}


def check_repro(pool):
    rng = np.random.default_rng(SEED)
    b, f = nm.simulate_block_bootstrap(pool, N_CHECK, N_MONTHS, 12, rng)
    t = nm.null_rate_table(b, f, [TH], [2.0]).iloc[0]
    p = dl.null_fd_percentiles(b, f, TH)
    got = {int(k): round(float(v), 2) for k, v in zip(p["percentile"], p["fd_future_pct"])}
    print(f"check 2 W4a stream: R_D>=2 {t.pct_rd_ge:.4f}% (n defined {int(t.n_rd_defined)}) "
          f"vs {REF_RATE} / {REF_N_DEF}; F_D future percentiles {got} vs {REF_PCT}")
    ok = abs(t.pct_rd_ge - REF_RATE) < 0.005 and int(t.n_rd_defined) == REF_N_DEF
    return ok and all(abs(got[k] - v) < 1e-9 for k, v in REF_PCT.items())


def run_nulls(pools):
    out = {}
    for name, pool in pools.items():
        rng = np.random.default_rng([SEED, 99])
        b, f = nm.simulate_block_bootstrap(pool, N_PROD, N_MONTHS, 12, rng)
        out[(name, "block12")] = summarise_null(b, f)
        del b, f
        gc.collect()
        phi = nm.estimate_phi(pool)
        b, f = nm.simulate_ar1(N_PROD, N_MONTHS, phi, np.random.default_rng([SEED, 99, 1]))
        out[(name, "ar1")] = summarise_null(b, f)
        out[(name, "ar1")]["phi"] = phi
        del b, f
        gc.collect()
    return out


def one_level_table(g, cuts, gaps):
    s370 = g["scenario"] == "ssp370"
    fut = g.assign(level_fut=dl.classify_fd(g["future_value"], cuts))
    base = g[s370].assign(level_base=dl.classify_fd(g.loc[s370, "baseline_value"], cuts))
    parts = []
    for col, frame, period in (("level_fut", fut, "future"), ("level_base", base, "baseline")):
        t = hl.gw_by_gcm(frame, [col], CATS_FD)
        gaps.append(hl.class_sum_gap(t))
        s = hl.summarise_gw(t, [col]).rename(columns={col: "class"})
        k = hl.agreement_k(frame, col, labels=dl.FD_LABELS).rename(columns={"cls": "class"})
        s = s.merge(k.drop(columns="mw_total"), on=KEYS + ["class"], how="left")
        s["period"] = period
        if period == "baseline":
            s["scenario"] = "baseline"
        parts.append(s)
    return pd.concat(parts, ignore_index=True)


def level_tables(d, nulls, gaps):
    parts = []
    for grp, own in GROUPS.items():
        g = d[d["group"] == grp]
        for pool in (own, OTHER[own]):
            for kind in NULLS:
                n = nulls[(pool, kind)]
                for cs_name, cs in dl.CUTSETS.items():
                    cuts = dl.fd_cuts(n["pct"], cs)
                    share = dl.null_class_shares(n["fd_future"], cuts)
                    t = one_level_table(g, cuts, gaps)
                    t["null_pct_expected"] = t["class"].map(share)
                    canon = pool == own and kind == "block12" and cs_name == "p50_p90_p99"
                    parts.append(t.assign(pool=pool, null=kind, cutset=cs_name, cut1=cuts[0],
                                          cut2=cuts[1], cut3=cuts[2], canonical=canon))
    return pd.concat(parts, ignore_index=True)


def change_tables(d, nulls, gaps):
    parts = []
    for grp, own in GROUPS.items():
        g = d[d["group"] == grp]
        fr = g.assign(rd_class=dl.classify_rd(g["ratio"]))
        t = hl.gw_by_gcm(fr, ["rd_class"], CATS_RD)
        gaps.append(hl.class_sum_gap(t))
        s = hl.summarise_gw(t, ["rd_class"]).rename(columns={"rd_class": "class"})
        k = hl.agreement_k(fr, "rd_class", labels=dl.RD_LABELS).rename(columns={"cls": "class"})
        s = s.merge(k.drop(columns="mw_total"), on=KEYS + ["class"], how="left")
        for kind in NULLS:
            b = nulls[(own, kind)]["bins"].set_index("rd_class")["null_pct"]
            s["null_pct_" + kind] = s["class"].map(b)
        parts.append(s)
    return pd.concat(parts, ignore_index=True)


def show_nulls(nulls):
    rows, rd = [], []
    for (pool, kind), n in nulls.items():
        r = n["pct"].set_index("percentile")["fd_future_pct"].round(2)
        rows.append({"pool": pool, "null": kind, "p50": r[50], "p75": r[75], "p90": r[90],
                     "p95": r[95], "p99": r[99]})
        b = n["bins"].set_index("rd_class")
        rd.append({"pool": pool, "null": kind,
                   "ge1.5": b.loc["rd_1_5_2", "null_pct_ge_lower"],
                   "ge2": b.loc["rd_2_3", "null_pct_ge_lower"],
                   "ge3": b.loc["rd_ge3", "null_pct_ge_lower"],
                   "undef_pct_all": b.loc["rd_undefined", "null_pct"]})
    print(f"\nnull F_D future percentiles (%), {N_PROD} simulations")
    print(pd.DataFrame(rows).to_string(index=False))
    print("\nnull R_D shares (%): at or above 1.5 / 2 / 3 among defined; undefined of all")
    print(pd.DataFrame(rd).round(2).to_string(index=False))
    phis = {k[0]: round(v["phi"], 4) for k, v in nulls.items() if "phi" in v}
    print("AR(1) phi per pool:", phis)


def show_levels(tab, grp, fleet, itaipu, pool, kind, cs):
    m = ((tab["group"] == grp) & (tab["fleet"] == fleet) & (tab["itaipu"] == itaipu)
         & (tab["pool"] == pool) & (tab["null"] == kind) & (tab["cutset"] == cs))
    s = tab[m]
    print(f"\n{grp} {fleet} (itaipu {itaipu}), pool {pool}, null {kind}, cuts {cs}: "
          "% of GW, median [min-max] over GCMs")
    for sc in ("baseline", "ssp126", "ssp370", "ssp585"):
        r = s[s["scenario"] == sc]
        cells = []
        for c in dl.FD_LABELS:
            x = r[r["class"] == c].iloc[0]
            cells.append(f"{c} {x.pct_median:.1f}[{x.pct_min:.1f}-{x.pct_max:.1f}]")
        print(f"  {sc:8s} " + " | ".join(cells))
    e = s[s["scenario"] == "ssp370"].set_index("class")["null_pct_expected"]
    print("  expected by chance (null %): " + " | ".join(f"{c} {e[c]:.1f}" for c in dl.FD_LABELS))


def show_extreme(tab):
    s = tab[(tab["class"] == "extreme") & (tab["fleet"] == "operating")
            & tab["itaipu"].isin(["na", "b"]) & (tab["period"] == "future")]
    p = s.pivot_table(index=["group", "pool", "null", "cutset"], columns="scenario",
                      values="pct_median")
    print("\nextreme class, operating, % of GW (median over GCMs), by configuration")
    print(p.round(1).to_string())


def show_change(tab, grp, itaipu):
    s = tab[(tab["group"] == grp) & (tab["fleet"] == "operating") & (tab["itaipu"] == itaipu)]
    print(f"\nR_D classes, {grp} operating (itaipu {itaipu}): % of GW median [min-max]; "
          "null % (block12 / ar1)")
    for sc in ("ssp126", "ssp370", "ssp585"):
        r = s[s["scenario"] == sc].set_index("class")
        cells = [f"{c} {r.loc[c, 'pct_median']:.1f}[{r.loc[c, 'pct_min']:.1f}-"
                 f"{r.loc[c, 'pct_max']:.1f}]" for c in dl.RD_LABELS]
        print(f"  {sc}: " + " | ".join(cells))
    r = s[s["scenario"] == "ssp370"].set_index("class")
    print("  null block12: " + " | ".join(f"{c} {r.loc[c, 'null_pct_block12']:.1f}"
                                          for c in dl.RD_LABELS))
    print("  null ar1:     " + " | ".join(f"{c} {r.loc[c, 'null_pct_ar1']:.1f}"
                                          for c in dl.RD_LABELS))


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    u = load_units(proc)
    cols = ["plant_uid", "plant_name", "country", "capacity_mw"]
    plants = pd.read_parquet(proc / "plants.parquet", columns=cols)
    uv = hl.with_itaipu_versions(u, dl.find_plant(plants, COUNTRY, "itaipu", 14000.0))
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                         columns=["plant_uid", "cell_lat", "cell_lon"])
    pc = pc.drop_duplicates("plant_uid")
    cellmap = dict(zip(pc["plant_uid"], pc["cell_lat"].astype(str) + "_"
                       + pc["cell_lon"].astype(str)))
    tw = u[u["group"] != "hydro"].drop_duplicates("plant_uid")
    tw_cell = tw["plant_uid"].map(cellmap)
    if tw_cell.isna().any():
        raise SystemExit("water-dependent thermal plants without a cell")
    hyd_ids = set(u.loc[u["group"] == "hydro", "plant_uid"])
    tw_ids = set(tw_cell)

    spei_cell = load_cell_spei(proc, tw_ids)
    vm = spei_cell[spei_cell["SPEI_12"].notna()]
    vm = vm.groupby(["id", "model", "scenario", "period"]).size()
    print("valid SPEI-12 months per series (median), cell scale:",
          vm.groupby(level="period").median().to_dict(), f"| null uses {N_MONTHS}")
    base = spei_cell[spei_cell["period"] == "baseline"]
    pool_cell, _ = nm.build_series_pool(base, tw_ids, N_MONTHS)
    pool_catch, _ = nm.build_series_pool(load_catch_baseline(proc), hyd_ids, N_MONTHS)
    pools = {"catchment": pool_catch, "cell": pool_cell}
    del spei_cell, base, vm
    got = {k: len(v) for k, v in pools.items()}
    ok1 = got == REF_POOLS
    print(f"check 1 pools: {got} vs {REF_POOLS}")
    ok2 = check_repro(pool_catch)

    spei_cell = load_cell_spei(proc, tw_ids)
    key = pd.DataFrame({"plant_uid": tw["plant_uid"].to_numpy(),
                        "bucket": "thermal_water_dependent", "id": tw_cell.to_numpy()})
    mine, _ = _f_d_r_d(spei_cell, key, "SPEI_12", "f_d_spei12", TH)
    del spei_cell
    h = pd.read_parquet(proc / "plant_hazards.parquet",
                        columns=["hazard"] + FD_COLS)
    h = h[h["hazard"] == "f_d_spei12"]
    dup = int(h.duplicated(dl.KEY).sum())
    h = h.drop_duplicates(dl.KEY)
    ref = h[h["plant_uid"].isin(set(tw["plant_uid"]))]
    n_both, worst, nan_mm = dl.compare_fd(mine, ref)
    no_fd = set(tw["plant_uid"]) - set(ref["plant_uid"])
    new = mine[mine["plant_uid"].isin(no_fd)]
    print(f"check 3 F_D vs plant_hazards: ref rows {len(ref)}, matched {n_both}, "
          f"max|diff| {worst:.2e}, NaN mismatches {nan_mm}; duplicate hazard rows {dup}")
    print(f"  plants without F_D in plant_hazards: {len(no_fd)}; computed here: "
          f"{new['plant_uid'].nunique()} plants, {len(new)} rows, ratio NaN "
          f"{int(new['ratio'].isna().sum())}")
    ok3 = n_both == len(ref) and worst < TOL and nan_mm == 0

    fd = pd.concat([h[h["plant_uid"].isin(hyd_ids)][FD_COLS], mine[FD_COLS]],
                   ignore_index=True)
    d = dl.unit_drought_frame(uv, fd)
    d["site"] = np.where(d["group"] == "hydro", d["plant_uid"], d["plant_uid"].map(cellmap))
    d = add_pooled_planned(d)
    print(f"unit rows {len(d)}; ratio NaN {int(d['ratio'].isna().sum())}")
    meta = d.groupby(["group", "fleet", "itaipu"]).agg(
        n_units=("uid", "nunique"), n_sites=("site", "nunique")).reset_index()
    meta["label"] = np.where(meta["n_sites"] >= MIN_SITES, "range_reported", "descriptive")

    nulls = run_nulls(pools)
    gaps = []
    lv = level_tables(d, nulls, gaps)
    ch = change_tables(d, nulls, gaps)
    op = uv[uv["fleet"] == "operating"].groupby(["group", "itaipu"])["capacity_mw"].sum()
    tot = (op[("hydro", "a")] / 1000, op[("hydro", "b")] / 1000,
           op[("thermal_water_dependent", "na")] / 1000)
    print(f"check 4 totals GW hydro a/b, thermal water operating: "
          f"{[round(float(x), 3) for x in tot]} vs {REF_GW}; max class-sum gap (MW) "
          f"{max(gaps):.2e}")
    ok4 = all(abs(a - b) < 0.01 for a, b in zip(tot, REF_GW)) and max(gaps) < 1e-6
    if not (ok1 and ok2 and ok3 and ok4):
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("checks 1-4: PASS")

    pct = []
    for (pool, kind), n in nulls.items():
        seed = f"{SEED},99" if kind == "block12" else f"{SEED},99,1"
        pct.append(n["pct"].assign(pool=pool, null=kind, n_sim=N_PROD, seed=seed,
                                   phi=n.get("phi", np.nan)))
    bins = [n["bins"].assign(pool=p, null=k) for (p, k), n in nulls.items()]
    lv = lv.merge(meta, on=["group", "fleet", "itaipu"], how="left")
    ch = ch.merge(meta, on=["group", "fleet", "itaipu"], how="left")
    outs = {"w4g_null_percentiles": pd.concat(pct, ignore_index=True),
            "w4g_null_rd_bins": pd.concat(bins, ignore_index=True),
            "w4g_drought_level_classes": lv, "w4g_drought_change_classes": ch,
            "w4g_fd_unit_values": fd}
    for name, t in outs.items():
        t.to_csv(tab / f"{name}.csv", index=False)
        print(f"written: {name}.csv ({len(t)} rows)")

    show_nulls(nulls)
    show_levels(lv, "hydro", "operating", "b", "catchment", "block12", "p50_p90_p99")
    show_levels(lv, "hydro", "operating", "a", "catchment", "block12", "p50_p90_p99")
    show_levels(lv, "hydro", "planned_all", "b", "catchment", "block12", "p50_p90_p99")
    show_levels(lv, "thermal_water_dependent", "operating", "na", "cell", "block12",
                "p50_p90_p99")
    show_levels(lv, "thermal_water_dependent", "planned_all", "na", "cell", "block12",
                "p50_p90_p99")
    show_extreme(lv)
    show_change(ch, "hydro", "b")
    show_change(ch, "thermal_water_dependent", "na")
    ds = meta[meta["label"] == "descriptive"]
    print(f"\ndescriptive fleets (< {MIN_SITES} sites): {len(ds)} of {len(meta)}")
    print(ds.to_string(index=False))


if __name__ == "__main__":
    main()