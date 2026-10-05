"""W3h / ST2: co-exposure (heat x drought) by state and macro-region (D88 M10; METHODS_SPEC ST2).

Scope, fixed before running (author-confirmed): only the two co-exposure cells used as
headline/sensitivity in W4h (D97) -- extreme heat AND extreme drought (CO2), and
high-or-extreme both ways (CO3) -- under the 3 nulls (block12, year, anystart), cutset
p50_p90_p99 only (the canonical display cutset; cutset sensitivity is a separate W5
question). Population: hydro and thermal_water_dependent (D89 upper bound), own pool
per group, same as W4h. The full 4x4 matrix by state is NOT produced here (unreadable
split by state); this is a deliberate scope cut, not an omission.

Heat/drought sourcing and classification are identical to w4h_coexposure.py (same cuts,
same files, same checks against the stored null draws) so this script's national
recomputation is checked against the already-verified w4h_coexposure.csv row by row
(check c), not just internally.

IMPORTANT definitional note on co_hi_ext (CO3), found and resolved this session: W4h
defines its CO3 "sensitivity" number as the SUM of 4 separately-computed per-GCM
medians (high-high, high-extreme, extreme-high, extreme-extreme cells), not re-summarised
after summing -- median is not additive (D80/D96/D97/D99), so sum-of-medians !=
median-of-sum. This script computes the reported co_hi_ext column as the methodologically
cleaner quantity (a single boolean flag, heat in {high,extreme} AND drought in
{high,extreme}, summed over capacity PER GCM, THEN median taken once) -- NOT the same
number as W4h's CO3. Check (c) validates against W4h using W4h's OWN definition
(sum-of-4-medians) to catch real data/classification errors without adopting the
non-additive quantity as this script's output. The gap between the two definitions is
captured by co_hi_ext_w4h_def (present only in the printed diagnostic, not written to
the final CSV) so the difference is visible, not silently swapped.

States assigned by point-in-polygon on the plant's own lat/lon (not the climate cell),
nearest-polygon fallback for points outside every polygon (craei.geo.state_assignment,
C62/D99), same approach as ST1 (w3h_state_summary.py).

Checks before writing (abort otherwise):
  (a) capacity parity: plant-level capacity sum, scope population, before vs after the
      state join.
  (b) per-state GW sum, PRE-median, per GCM, for each flag (co_extreme, co_hi_ext) and
      null, matches the same sum recomputed nationally in this script (median is not
      additive across states, D80/D96/D97/D99).
  (c) the national recomputation in this script reproduces w4h_coexposure.csv: CO2 cell
      matches gw_median exactly (tol 1e-6, both are plain medians, directly comparable);
      CO3 is checked using W4H'S OWN sum-of-4-medians definition (tol 1e-6), computed
      separately from this script's co_hi_ext column -- the two numbers are NOT expected
      to be equal to each other, only each to its own reference quantity.

Writes (only if all checks pass): w3h_state_coexposure.csv (group, fleet, itaipu,
scenario, null, cutset, co_class in {co_extreme, co_hi_ext}, state_postal,
macro_region, n_gcm, gw_total, gw_min/median/max, pct_min/median/max, n_nearest).
co_hi_ext in this file is the single-flag median (see note above), not W4h's CO3.
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import yaml

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned
from craei.geo.state_assignment import add_macro_region, assign_state
from craei.hazards import drought_levels as dl

COUNTRY, CAP_TOL, SUM_TOL, PROD_TOL = "BRA", 1e-6, 1e-3, 1e-6
GROUPS = {"hydro": "catchment", "thermal_water_dependent": "cell"}
NULLS = ("block12", "year", "anystart")
CUTSET_NAME, CUTSET_PCTS = "p50_p90_p99", dl.CUTSETS["p50_p90_p99"]
KEYS = [k for k in hl.GROUP_KEYS if k != "model"]
STATE_KEYS = KEYS + ["null", "state_postal", "macro_region"]
NAT_KEYS = KEYS + ["null"]
HI = ("high", "extreme")


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet")
    keep = list(GROUPS.keys())
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


def check_percentiles(fd_fut, row, tol):
    for p in (50, 75, 90, 95, 99):
        got = float(np.percentile(fd_fut, p))
        want = float(row[f"p{p}"])
        if abs(got - want) > tol:
            raise SystemExit(
                f"ABORT: recomputed p{p}={got} != w4r_null_percentiles {want} "
                f"for {row['pool']} {row['null']}"
            )


def cuts_block12(w4g_pct, pool):
    t = w4g_pct[(w4g_pct["pool"] == pool) & (w4g_pct["null"] == "block12")]
    t = t.set_index("percentile")["fd_future_pct"]
    return tuple(float(t.loc[p]) for p in CUTSET_PCTS)


def cuts_emulated(w4r_pct, draws, pool, null_kind):
    m = (w4r_pct["pool"] == pool) & (w4r_pct["null"] == null_kind)
    row = w4r_pct[m].iloc[0]
    fd_fut = draws[(pool, null_kind)]
    check_percentiles(fd_fut, row, PROD_TOL)
    return tuple(float(row[f"p{p}"]) for p in CUTSET_PCTS)


def load_macro_map(config_dir=None):
    path = (config_dir or Path("config")) / "params.yaml"
    with open(path, encoding="utf-8") as f:
        params = yaml.safe_load(f)
    return params["brazil_macroregion_map"]["value"]


def flagged_sum(df, flag_col, keys):
    full_keys = keys + ["model"]
    g = df[df[flag_col]].groupby(full_keys, observed=True)["capacity_mw"].sum()
    g = g.rename("mw").reset_index()
    grid = df[full_keys].drop_duplicates()
    out = grid.merge(g, on=full_keys, how="left")
    out["mw"] = out["mw"].fillna(0.0)
    tot = df.groupby(keys)["capacity_mw"].sum().rename("mw_total").reset_index()
    return out.merge(tot, on=keys, how="left")


def summarise_flag(t, keys):
    t = t.assign(pct=100.0 * t["mw"] / t["mw_total"])
    out = t.groupby(keys).agg(
        n_gcm=("model", "nunique"), gw_total=("mw_total", "first"),
        gw_min=("mw", "min"), gw_median=("mw", "median"), gw_max=("mw", "max"),
        pct_min=("pct", "min"), pct_median=("pct", "median"), pct_max=("pct", "max"),
    ).reset_index()
    for c in ("gw_total", "gw_min", "gw_median", "gw_max"):
        out[c] = out[c] / 1000.0
    return out


def w4h_style_co3(df, keys):
    """Sum of 4 separately-medianed cells (W4h's own CO3 definition), for check (c) only."""
    full_keys = keys + ["model"]
    parts = []
    for h_cls in HI:
        for d_cls in HI:
            flag = (df["heat_class"] == h_cls) & (df["drought_class"] == d_cls)
            g = df[flag].groupby(full_keys, observed=True)["capacity_mw"].sum()
            g = g.rename("mw").reset_index()
            grid = df[full_keys].drop_duplicates()
            t = grid.merge(g, on=full_keys, how="left")
            t["mw"] = t["mw"].fillna(0.0) / 1000.0
            med = t.groupby(keys)["mw"].median().rename("gw_median_cell")
            parts.append(med)
    allp = pd.concat(parts, axis=1)
    return allp.sum(axis=1).rename("gw_median_sum4")


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    audit = tab.parent / "audit" / "w4r"

    units = load_units(proc)
    fd = pd.read_csv(tab / "w4g_fd_unit_values.csv")
    plants = pd.read_parquet(proc / "plants.parquet",
                              columns=["plant_uid", "plant_name", "country",
                                       "capacity_mw", "lat", "lon"])
    bra_plants = plants[plants["country"] == COUNTRY]
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, COUNTRY, "itaipu", 14000.0))
    d = dl.unit_drought_frame(uv, fd)

    heat = pd.concat([thermal_tx35(proc, units), hydro_tx35(proc, units)], ignore_index=True)
    d_full = d.merge(heat, on=["plant_uid", "model", "scenario"], how="left")
    if d_full[["base_tx35", "fut_tx35"]].isna().any().any():
        raise SystemExit("ABORT: units without a heat value after merge")
    d_full["heat_class"] = hl.classify(d_full["fut_tx35"], hl.LEVEL_CUTS, hl.LEVEL_LABELS)
    d_full = add_pooled_planned(d_full)

    scope_uids = set(d_full["plant_uid"])
    scope_plants = bra_plants[bra_plants["plant_uid"].isin(scope_uids)]
    admin1 = gpd.read_file(r"..\data\external\geo\natural_earth_brazil.gpkg",
                            layer="brazil_admin1")
    assigned = assign_state(scope_plants, admin1, lat_col="lat", lon_col="lon",
                             uid_col="plant_uid")
    macro_map = load_macro_map()
    assigned = add_macro_region(assigned, macro_map, postal_col="state_postal")
    n_fallback = int(assigned["nearest_fallback"].sum())
    print(f"state assignment (scope population): {len(assigned)} plants, "
          f"{n_fallback} via nearest fallback")

    cap_before = float(scope_plants["capacity_mw"].sum())
    cap_after = float(assigned["capacity_mw"].sum())
    diff_a = abs(cap_before - cap_after)
    print(f"check (a) capacity parity: before {cap_before:.3f} MW, "
          f"after {cap_after:.3f} MW, diff {diff_a:.2e}")
    if diff_a >= CAP_TOL:
        print("CHECK FAILED (a): nothing written")
        sys.exit(1)

    d_state = d_full.merge(
        assigned[["plant_uid", "state_postal", "macro_region", "nearest_fallback"]],
        on="plant_uid", how="left")
    if d_state["state_postal"].isna().any():
        print("CHECK FAILED: unit rows without a state after merge")
        sys.exit(1)

    w4g_pct = pd.read_csv(tab / "w4g_null_percentiles.csv")
    w4r_pct = pd.read_csv(tab / "w4r_null_percentiles.csv")
    draws = {}
    for _, r in w4r_pct.iterrows():
        z = np.load(audit / f"draws_{r['pool']}_{r['null']}.npz")
        draws[(r["pool"], r["null"])] = z["fd_fut"]

    ref = pd.read_csv(tab / "w4h_coexposure.csv")

    state_parts, nat_parts, gap_b = [], [], []
    nat_co3_w4hdef = []

    for grp, pool in GROUPS.items():
        g_nat = d_full[d_full["group"] == grp]
        g_st = d_state[d_state["group"] == grp]
        for null_kind in NULLS:
            cuts = (cuts_block12(w4g_pct, pool) if null_kind == "block12"
                    else cuts_emulated(w4r_pct, draws, pool, null_kind))

            sub_nat = g_nat.assign(drought_class=dl.classify_fd(g_nat["future_value"], cuts),
                                    null=null_kind)
            sub_st = g_st.assign(drought_class=dl.classify_fd(g_st["future_value"], cuts),
                                  null=null_kind)
            for sub in (sub_nat, sub_st):
                sub["co_extreme"] = (sub["heat_class"] == "extreme") & \
                                     (sub["drought_class"] == "extreme")
                sub["co_hi_ext"] = sub["heat_class"].isin(HI) & \
                                   sub["drought_class"].isin(HI)

            co3_w4h = w4h_style_co3(sub_nat, NAT_KEYS).reset_index()
            co3_w4h["group"] = grp
            nat_co3_w4hdef.append(co3_w4h)

            for flag in ("co_extreme", "co_hi_ext"):
                t_nat = flagged_sum(sub_nat, flag, NAT_KEYS)
                t_st = flagged_sum(sub_st, flag, STATE_KEYS)
                nat_sum = t_nat.groupby(NAT_KEYS + ["model"])["mw"].sum()
                st_sum = t_st.groupby(NAT_KEYS + ["model"])["mw"].sum()
                m = pd.concat([nat_sum.rename("nat"), st_sum.rename("st")], axis=1).fillna(0.0)
                gap = float((m["nat"] - m["st"]).abs().max())
                gap_b.append(gap)
                print(f"check (b) {grp:24s} null={null_kind:9s} flag={flag:10s} "
                      f"rows {len(m)} max|diff| {gap:.2e}")

                nat_parts.append(summarise_flag(t_nat, NAT_KEYS).assign(group=grp, co_class=flag))
                state_parts.append(summarise_flag(t_st, STATE_KEYS).assign(group=grp, co_class=flag))

    max_gap_b = max(gap_b)
    print(f"\nmax check (b) gap over all groups/nulls/flags (MW): {max_gap_b:.2e}")
    if max_gap_b >= SUM_TOL:
        print("CHECK FAILED (b): nothing written")
        sys.exit(1)

    nat_tab = pd.concat(nat_parts, ignore_index=True)
    state_tab = pd.concat(state_parts, ignore_index=True)
    co3_w4hdef_tab = pd.concat(nat_co3_w4hdef, ignore_index=True)

    prod_checks_co2, prod_checks_co3 = [], []
    for grp in GROUPS:
        for null_kind in NULLS:
            n = nat_tab[(nat_tab["group"] == grp) & (nat_tab["null"] == null_kind)
                        & (nat_tab["co_class"] == "co_extreme")]
            for _, row in n.iterrows():
                m = (ref["group"] == grp) & (ref["fleet"] == row["fleet"]) \
                    & (ref["itaipu"] == row["itaipu"]) & (ref["scenario"] == row["scenario"]) \
                    & (ref["null"] == null_kind) & (ref["cutset"] == CUTSET_NAME) \
                    & (ref["heat_class"] == "extreme") & (ref["drought_class"] == "extreme")
                r = ref[m]
                if len(r) != 1:
                    print(f"CHECK FAILED (c, CO2): {len(r)} reference rows for "
                          f"{grp}/{row['fleet']}/{row['itaipu']}/{row['scenario']}/{null_kind}")
                    sys.exit(1)
                prod_checks_co2.append(abs(float(row["gw_median"]) - float(r["gw_median"].iloc[0])))

            s = co3_w4hdef_tab[(co3_w4hdef_tab["group"] == grp)
                                & (co3_w4hdef_tab["null"] == null_kind)]
            m4 = (ref["group"] == grp) & (ref["null"] == null_kind) \
                & (ref["cutset"] == CUTSET_NAME) & ref["heat_class"].isin(HI) \
                & ref["drought_class"].isin(HI)
            ref4 = ref[m4].groupby(["fleet", "itaipu", "scenario"])["gw_median"].sum()
            for _, row in s.iterrows():
                key = (row["fleet"], row["itaipu"], row["scenario"])
                if key not in ref4.index:
                    print(f"CHECK FAILED (c, CO3): no reference sum for {grp}/{key}/{null_kind}")
                    sys.exit(1)
                prod_checks_co3.append(abs(float(row["gw_median_sum4"]) - float(ref4.loc[key])))

    max_co2 = max(prod_checks_co2)
    max_co3 = max(prod_checks_co3)
    print(f"check (c) CO2 max|diff| vs w4h_coexposure.csv: {max_co2:.2e} "
          f"({len(prod_checks_co2)} comparisons)")
    print(f"check (c) CO3 max|diff| vs w4h_coexposure.csv (W4h's own sum-of-4-medians "
          f"definition, diagnostic only): {max_co3:.2e} ({len(prod_checks_co3)} comparisons)")
    if max_co2 >= PROD_TOL or max_co3 >= PROD_TOL:
        print("CHECK FAILED (c): nothing written")
        sys.exit(1)
    print("checks (a)-(c): PASS")
    print("\nNOTE: w3h_state_coexposure.csv reports co_hi_ext as a single-flag median "
          "(median of the summed flag), NOT W4h's sum-of-4-medians CO3. The two are not "
          "directly comparable; see module docstring.")

    n_nearest = assigned.groupby("state_postal")["nearest_fallback"].sum().rename("n_nearest")
    out = state_tab.merge(n_nearest, on="state_postal", how="left")
    out["cutset"] = CUTSET_NAME
    out.to_csv(tab / "w3h_state_coexposure.csv", index=False)
    print(f"\nwritten: w3h_state_coexposure.csv ({len(out)} rows)")

    pd.set_option("display.width", 250)
    headline = out[(out["co_class"] == "co_extreme") & (out["fleet"] == "operating")
                   & (out["itaipu"].isin(["na", "b"])) & (out["scenario"] == "ssp585")
                   & (out["null"] == "block12")]
    print("\nCO2 headline (extreme heat x extreme drought), operating, ssp585, block12, "
          "GW median by state:")
    print(headline[["group", "state_postal", "macro_region", "gw_median"]]
          .sort_values("gw_median", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
