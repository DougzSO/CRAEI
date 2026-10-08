"""W4h: co-located exposure, heat level x drought level, under the three nulls (D88 M8).

Population: hydro and thermal_water_dependent only (D89 upper bound), own pool only per
group (hydro -> catchment, thermal_water_dependent -> cell; no cross-pool sensitivity
here, that question is already answered in W4g). Both hazards use the FUTURE level class
(same GCM, same scenario): heat = TX35 future (cuts 10/30/60, fixed); drought = F_D
future against the null (block12 cuts from w4g_null_percentiles.csv, reused as-is;
year/anystart cuts from w4r_null_percentiles.csv, checked against the stored draws
before use, same check as w4g_rev / D96). No null is canonical (D90); "canonical" is
True only for null==block12, cutset==p50_p90_p99 (pre-D90 default display).

Heat values: thermal from plant_hazards (hazard==TX35), population selected by
tech_class of plant_units (not by bucket, which mislabels 2 of 1285 plants, D77/M2).
Hydro has no TX35 in plant_hazards; computed the same way as W3g (indices_daily -> cell
values -> merged by plant cell), restricted to hydro cells only.
Drought values: reused as-is from w4g_fd_unit_values.csv, no recomputation.

Checks before writing (abort otherwise): (1) no missing/NaN heat values after merge;
(2) percentiles recomputed from the stored draws match w4r_null_percentiles.csv
(year/anystart only, tol 1e-6); (3) heat-only marginal (summarise_gw of the raw per-GCM
table collapsed on heat_class alone) matches w3g_heat_level_classes.csv, future period,
tol 1e-6 on gw_median and pct_median; (4) drought-only marginal (same idea, collapsed on
drought_class alone, per null/cutset) matches w4g_drought_level_classes.csv (block12) or
w4grev_drought_level_classes.csv (year/anystart), future period, same tolerance;
(5) class-sum gap of the joint 4x4 table (16 cells) and of both 1-D marginals < 1e-6 MW.
These marginal checks are done BEFORE taking the median across GCMs (median is not
additive across classes, D80); comparing already-summarised gw_median values directly
would be invalid.

anystart caveat (D94/O37, closed): its own-series variance is inflated ~15-16% and its
baseline is not a valid reference under real-series parameters (D93). Shown here like
the other nulls, never singled out as equivalent to block12 or year in the text.

Writes (only if all checks pass): w4h_coexposure.csv (group, fleet, itaipu, scenario,
pool, null, cutset, heat_class, drought_class, n_gcm, gw_total, gw_min/median/max,
pct_min/median/max, canonical).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned
from craei.hazards import drought_levels as dl

COUNTRY, PCT_TOL, GAP_TOL, MARGIN_TOL = "BRA", 1e-6, 1e-6, 1e-6
GROUPS = {"hydro": "catchment", "thermal_water_dependent": "cell"}
NULLS = ("block12", "year", "anystart")
HEAT_CATS = {"heat_class": list(hl.LEVEL_LABELS)}
DROUGHT_CATS = {"drought_class": list(dl.FD_LABELS)}
JOINT_CATS = {"heat_class": list(hl.LEVEL_LABELS), "drought_class": list(dl.FD_LABELS)}
KEYS = [k for k in hl.GROUP_KEYS if k != "model"]


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet")
    keep = ["hydro", "thermal_water_dependent"]
    u = u[(u["country"] == COUNTRY) & u["tech_class"].isin(keep)].reset_index(drop=True)
    u["uid"] = u.index
    u["group"] = np.where(u["tech_class"] == "hydro", "hydro", "thermal_water_dependent")
    return u


def thermal_tx35(proc, units):
    tw_uids = set(units.loc[units["group"] == "thermal_water_dependent", "plant_uid"])
    cols = ["plant_uid", "hazard", "model", "scenario", "baseline_value", "future_value"]
    h = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols)
    h = h[(h["hazard"] == "TX35") & h["plant_uid"].isin(tw_uids)]
    missing = tw_uids - set(h["plant_uid"])
    if missing:
        raise SystemExit(f"ABORT: {len(missing)} thermal plants without TX35 in plant_hazards")
    return h[["plant_uid", "model", "scenario", "baseline_value", "future_value"]].rename(
        columns={"baseline_value": "base_tx35", "future_value": "fut_tx35"})


def hydro_tx35(proc, units):
    hyd_uids = set(units.loc[units["group"] == "hydro", "plant_uid"])
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                          columns=["plant_uid", "cell_lat", "cell_lon"]).drop_duplicates("plant_uid")
    pc_h = pc[pc["plant_uid"].isin(hyd_uids)]
    if pc_h["plant_uid"].nunique() != len(hyd_uids):
        raise SystemExit("ABORT: hydro plants without a cell")
    cells = pc_h[["cell_lat", "cell_lon"]].drop_duplicates()
    cols = ["index", "cell_lat", "cell_lon", "model", "scenario", "period", "value"]
    ix = pd.read_parquet(proc / "indices_daily.parquet", columns=cols,
                          filters=[("index", "==", "tx35")])
    ix = ix.merge(cells, on=["cell_lat", "cell_lon"], how="inner")
    cv = hl.cell_values(ix)
    del ix
    out = pc_h.merge(cv, on=["cell_lat", "cell_lon"], how="left")
    if out[["base", "fut"]].isna().any().any():
        raise SystemExit("ABORT: hydro plant-cell without TX35 cell values")
    return out[["plant_uid", "model", "scenario", "base", "fut"]].rename(
        columns={"base": "base_tx35", "fut": "fut_tx35"})


def check_percentiles(fd_fut, row):
    for p in (50, 75, 90, 95, 99):
        got = float(np.percentile(fd_fut, p))
        want = float(row[f"p{p}"])
        if abs(got - want) > PCT_TOL:
            raise SystemExit(
                f"ABORT: recomputed p{p}={got} != w4r_null_percentiles {want} "
                f"for {row['pool']} {row['null']}"
            )


def cuts_block12(w4g_pct, pool, cutset_pcts):
    t = w4g_pct[(w4g_pct["pool"] == pool) & (w4g_pct["null"] == "block12")]
    t = t.set_index("percentile")["fd_future_pct"]
    return tuple(float(t.loc[p]) for p in cutset_pcts)


def cuts_emulated(w4r_pct, draws, pool, null_kind, cutset_pcts):
    m = (w4r_pct["pool"] == pool) & (w4r_pct["null"] == null_kind)
    row = w4r_pct[m].iloc[0]
    fd_fut = draws[(pool, null_kind)]
    check_percentiles(fd_fut, row)
    return tuple(float(row[f"p{p}"]) for p in cutset_pcts)


def check_heat_marginal(d_full, tab, gaps):
    t = hl.gw_by_gcm(d_full, ["heat_class"], HEAT_CATS)
    gaps.append(hl.class_sum_gap(t))
    mine = hl.summarise_gw(t, ["heat_class"]).rename(columns={"heat_class": "class"})
    ref = pd.read_csv(tab / "w3g_heat_level_classes.csv")
    ref = ref[(ref["period"] == "future") & ref["group"].isin(GROUPS.keys())]
    m = mine.merge(ref, on=KEYS + ["class"], how="inner", suffixes=("", "_ref"))
    worst_gw = float((m["gw_median"] - m["gw_median_ref"]).abs().max())
    worst_pct = float((m["pct_median"] - m["pct_median_ref"]).abs().max())
    print(f"check heat marginal vs w3g_heat_level_classes: rows {len(m)} of {len(mine)}, "
          f"max|d gw_median| {worst_gw:.2e}, max|d pct_median| {worst_pct:.2e}")
    return len(m) == len(mine) and worst_gw < MARGIN_TOL and worst_pct < MARGIN_TOL


def check_drought_marginal(sub, tab, pool, null_kind, cs_name, gaps):
    t = hl.gw_by_gcm(sub, ["drought_class"], DROUGHT_CATS)
    gaps.append(hl.class_sum_gap(t))
    mine = hl.summarise_gw(t, ["drought_class"]).rename(columns={"drought_class": "class"})
    fname = "w4g_drought_level_classes.csv" if null_kind == "block12" else "w4grev_drought_level_classes.csv"
    ref = pd.read_csv(tab / fname)
    m = (ref["period"] == "future") & (ref["pool"] == pool) & (ref["null"] == null_kind) & (ref["cutset"] == cs_name)
    ref = ref[m]
    m = mine.merge(ref, on=KEYS + ["class"], how="inner", suffixes=("", "_ref"))
    worst_gw = float((m["gw_median"] - m["gw_median_ref"]).abs().max())
    worst_pct = float((m["pct_median"] - m["pct_median_ref"]).abs().max())
    ok = len(m) == len(mine) and worst_gw < MARGIN_TOL and worst_pct < MARGIN_TOL
    return ok, len(m), len(mine), worst_gw, worst_pct


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    audit = tab.parent / "audit" / "w4r"

    units = load_units(proc)
    fd = pd.read_csv(tab / "w4g_fd_unit_values.csv")
    plants = pd.read_parquet(proc / "plants.parquet",
                              columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, COUNTRY, "itaipu", 14000.0))
    d = dl.unit_drought_frame(uv, fd)
    print(f"unit rows {len(d)}, plants {d['plant_uid'].nunique()}")

    heat = pd.concat([thermal_tx35(proc, units), hydro_tx35(proc, units)], ignore_index=True)
    d_full = d.merge(heat, on=["plant_uid", "model", "scenario"], how="left")
    if d_full[["base_tx35", "fut_tx35"]].isna().any().any():
        raise SystemExit("ABORT: units without a heat value after merge")
    d_full["heat_class"] = hl.classify(d_full["fut_tx35"], hl.LEVEL_CUTS, hl.LEVEL_LABELS)
    d_full = add_pooled_planned(d_full)

    gaps = []
    ok_heat = check_heat_marginal(d_full, tab, gaps)

    w4g_pct = pd.read_csv(tab / "w4g_null_percentiles.csv")
    w4r_pct = pd.read_csv(tab / "w4r_null_percentiles.csv")
    draws = {}
    for _, r in w4r_pct.iterrows():
        z = np.load(audit / f"draws_{r['pool']}_{r['null']}.npz")
        draws[(r["pool"], r["null"])] = z["fd_fut"]

    parts, drought_checks = [], []
    for grp, pool in GROUPS.items():
        g = d_full[d_full["group"] == grp]
        for null_kind in NULLS:
            for cs_name, cs_pcts in dl.CUTSETS.items():
                cuts = (cuts_block12(w4g_pct, pool, cs_pcts) if null_kind == "block12"
                        else cuts_emulated(w4r_pct, draws, pool, null_kind, cs_pcts))
                sub = g.assign(drought_class=dl.classify_fd(g["future_value"], cuts))
                ok, n_ok, n_tot, dgw, dpct = check_drought_marginal(
                    sub, tab, pool, null_kind, cs_name, gaps)
                drought_checks.append(ok)
                print(f"check drought marginal {grp:24s} pool={pool:9s} null={null_kind:9s} "
                      f"cutset={cs_name}: rows {n_ok}/{n_tot}, max|d gw| {dgw:.2e}, "
                      f"max|d pct| {dpct:.2e} -> {'PASS' if ok else 'FAIL'}")
                t = hl.gw_by_gcm(sub, ["heat_class", "drought_class"], JOINT_CATS)
                gaps.append(hl.class_sum_gap(t))
                s = hl.summarise_gw(t, ["heat_class", "drought_class"])
                canon = null_kind == "block12" and cs_name == "p50_p90_p99"
                parts.append(s.assign(pool=pool, null=null_kind, cutset=cs_name,
                                       cut1=cuts[0], cut2=cuts[1], cut3=cuts[2],
                                       canonical=canon))

    joint = pd.concat(parts, ignore_index=True)
    max_gap = max(gaps)
    print(f"\nmax class-sum gap over all 1-D and 2-D tables (MW): {max_gap:.2e}")
    if not (ok_heat and all(drought_checks) and max_gap < GAP_TOL):
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("all checks: PASS")

    joint.to_csv(tab / "w4h_coexposure.csv", index=False)
    print(f"\nwritten: w4h_coexposure.csv ({len(joint)} rows)")

    pd.set_option("display.width", 250)
    sel = (joint["heat_class"] == "extreme") & (joint["drought_class"] == "extreme") \
        & (joint["fleet"] == "operating") & (joint["cutset"] == "p50_p90_p99") \
        & (joint["itaipu"].isin(["na", "b"]))
    print("\n=== CO2 headline: extreme heat x extreme drought, operating, p50_p90_p99 "
          "(% of GW, median over GCMs) ===")
    print(joint[sel].pivot_table(index=["group", "null"], columns="scenario",
                                  values="pct_median").round(1).to_string())

    hi = ["high", "extreme"]
    sel2 = joint["heat_class"].isin(hi) & joint["drought_class"].isin(hi) \
        & (joint["fleet"] == "operating") & (joint["cutset"] == "p50_p90_p99") \
        & (joint["itaipu"].isin(["na", "b"]))
    sens = joint[sel2].groupby(["group", "null", "scenario"], as_index=False)["gw_median"].sum()
    print("\n=== CO3 sensitivity: high-or-extreme both ways, operating, p50_p90_p99 "
          "(sum of gw_median across the 4 matching cells; not re-summarised, see docstring) ===")
    print(sens.pivot_table(index=["group", "null"], columns="scenario",
                            values="gw_median").round(2).to_string())
    print("\nNOTE: anystart rows above carry the D94/O37 caveat (own-series variance "
          "inflated ~15-16%, baseline not a valid reference under real parameters, D93); "
          "not equivalent to block12 or year.")


if __name__ == "__main__":
    main()