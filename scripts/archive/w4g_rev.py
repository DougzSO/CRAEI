"""W4g-rev: drought level and R_D change classes under all three nulls (D90 plan item 1).

Extends the free-null W4g production (scripts/archive/w4_drought_levels.py; block12 and
AR(1), already validated, written to w4g_drought_level_classes.csv and
w4g_drought_change_classes.csv) with the two emulated nulls from W4r (year, anystart;
D92/D93/D94/D95). Read-only against both productions; writes new w4grev_* tables only.
No null is canonical (D90): all three (free block12, year, anystart) are shown side by
side, plus AR(1) as an extra free-null sensitivity already present in the W4g table.
The "canonical" column inherited from the free-null rows flags pool==own, null==block12,
cutset==p50_p90_p99 as the historical default-display combination (predates D90's "no
canonical null" rule); it is never set True for the emulated rows added here and is not
read as a statement that block12 is the correct null.

Level classes (F_D vs null percentiles): cuts for year/anystart come from
w4r_null_percentiles.csv's p50/p75/p90/p95/p99 columns (both cutsets, matching the free
null's p50_p90_p99 and p50_p75_p95). Expected class shares by chance come from
drought_levels.null_class_shares() on the stored per-draw future F_D array in
audit/w4r/draws_{pool}_{variant}.npz (same draws D92/D93 are built on); percentiles
recomputed from that array are checked against w4r_null_percentiles.csv before anything
is written (abort on mismatch). Units and real F_D values come from already-validated
artifacts (plant_units, plants, plant_cell, w4g_fd_unit_values.csv) via
drought_levels.unit_drought_frame(), which itself raises on any missing plant or NaN.

R_D change classes: year/anystart null shares per class come directly from
w4r_null_rd.csv (already computed from the same draws), added as two more columns
(null_pct_year, null_pct_anystart) beside the existing null_pct_block12/null_pct_ar1 --
no reclassification needed, since the R_D class edges (1.5/2/3) do not depend on a null.

anystart caveat (D94, closed): anystart inflates the variance of the real series' own
12-month D sums by ~15-16% (year matches it within 2%), and its baseline is not a valid
reference under real-series parameters (D93). Shown here like the other nulls, but any
use of anystart in the text must carry this caveat, not treat it as equivalent to the
free null or to year.

Also prints: the share of future draws landing exactly on the p50 cut (discreteness;
the emulated distributions are built from a finite set of 349 valid monthly values).

Writes (only if all checks pass): w4grev_null_percentiles.csv,
w4grev_drought_level_classes.csv, w4grev_drought_change_classes.csv.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths

GAP_TOL = 1e-6
PCT_TOL = 1e-6
EMULATED_NULLS = ("year", "anystart")
HEADLINE_NULLS = ("block12", "year", "anystart")


def load_w4g():
    f = Path(__file__).resolve().parent / "archive" / "w4_drought_levels.py"
    spec = importlib.util.spec_from_file_location("w4g_prod", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_units(w4g, proc, tab):
    u = w4g.load_units(proc)
    cols = ["plant_uid", "plant_name", "country", "capacity_mw"]
    plants = pd.read_parquet(proc / "plants.parquet", columns=cols)
    itaipu = w4g.dl.find_plant(plants, w4g.COUNTRY, "itaipu", 14000.0)
    uv = w4g.hl.with_itaipu_versions(u, itaipu)
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                          columns=["plant_uid", "cell_lat", "cell_lon"])
    pc = pc.drop_duplicates("plant_uid")
    cellmap = dict(zip(pc["plant_uid"],
                        pc["cell_lat"].astype(str) + "_" + pc["cell_lon"].astype(str)))
    fd = pd.read_csv(tab / "w4g_fd_unit_values.csv")
    d = w4g.dl.unit_drought_frame(uv, fd)
    d["site"] = np.where(d["group"] == "hydro", d["plant_uid"], d["plant_uid"].map(cellmap))
    if d["site"].isna().any():
        raise SystemExit("ABORT: water-dependent thermal plant without a cell")
    d = w4g.add_pooled_planned(d)
    meta = d.groupby(["group", "fleet", "itaipu"]).agg(
        n_units=("uid", "nunique"), n_sites=("site", "nunique")).reset_index()
    meta["label"] = np.where(meta["n_sites"] >= w4g.MIN_SITES, "range_reported", "descriptive")
    return d, meta


def load_all_draws(audit, w4r_pct):
    cache = {}
    for _, r in w4r_pct.iterrows():
        z = np.load(audit / f"draws_{r['pool']}_{r['null']}.npz")
        cache[(r["pool"], r["null"])] = z["fd_fut"]
    return cache


def check_percentiles(fd_fut, row):
    for p in (50, 75, 90, 95, 99):
        got = float(np.percentile(fd_fut, p))
        want = float(row[f"p{p}"])
        if abs(got - want) > PCT_TOL:
            raise SystemExit(
                f"ABORT: recomputed p{p}={got} != w4r_null_percentiles {want} "
                f"for {row['pool']} {row['null']}"
            )


def level_rows(w4g, d, w4r_pct, draws, gaps):
    rows = []
    for grp, own in w4g.GROUPS.items():
        g = d[d["group"] == grp]
        for pool in (own, w4g.OTHER[own]):
            for null_kind in EMULATED_NULLS:
                m = (w4r_pct["pool"] == pool) & (w4r_pct["null"] == null_kind)
                row = w4r_pct[m].iloc[0]
                fd_fut = draws[(pool, null_kind)]
                check_percentiles(fd_fut, row)
                for cs_name, cs_pcts in w4g.dl.CUTSETS.items():
                    cuts = tuple(float(row[f"p{p}"]) for p in cs_pcts)
                    share = w4g.dl.null_class_shares(fd_fut, cuts)
                    t = w4g.one_level_table(g, cuts, gaps)
                    t["null_pct_expected"] = t["class"].map(share)
                    rows.append(t.assign(pool=pool, null=null_kind, cutset=cs_name,
                                          cut1=cuts[0], cut2=cuts[1], cut3=cuts[2],
                                          canonical=False))
    return pd.concat(rows, ignore_index=True)


def change_columns(w4g, w4r_rd):
    lookup = {}
    for grp, pool in w4g.GROUPS.items():
        for null_kind in EMULATED_NULLS:
            m = (w4r_rd["pool"] == pool) & (w4r_rd["null"] == null_kind)
            r = w4r_rd[m].iloc[0]
            lookup[(grp, null_kind)] = {
                "rd_lt1_5": r["rd_lt_1p5"], "rd_1_5_2": r["rd_1p5_2"],
                "rd_2_3": r["rd_2_3"], "rd_ge3": r["rd_ge_3"],
                "rd_undefined": r["undefined_pct"],
            }
    return lookup


def combined_percentiles(tab, w4r_pct):
    cols = ["percentile", "fd_future_pct", "fd_baseline_pct", "pool", "null"]
    free_pct = pd.read_csv(tab / "w4g_null_percentiles.csv")[cols]
    melt_rows = []
    for _, r in w4r_pct.iterrows():
        for p in (50, 75, 90, 95, 99):
            melt_rows.append({"percentile": p, "fd_future_pct": r[f"p{p}"],
                               "fd_baseline_pct": r[f"base_p{p}"],
                               "pool": r["pool"], "null": r["null"]})
    return pd.concat([free_pct, pd.DataFrame(melt_rows)], ignore_index=True)


def print_tie_shares(w4r_pct, draws):
    print("\n=== share of future draws exactly at the p50 cut (discreteness) ===")
    for _, r in w4r_pct.iterrows():
        fd_fut = draws[(r["pool"], r["null"])]
        tie = 100.0 * float(np.mean(fd_fut == r["p50"]))
        print(f"  {r['pool']:9s} {r['null']:9s}: {tie:.2f}% at p50={r['p50']:.3f}")


def print_headline(combined_lv, w4g):
    s = combined_lv[(combined_lv["class"] == "extreme")
                     & (combined_lv["fleet"] == "operating")
                     & (combined_lv["period"] == "future")
                     & (combined_lv["cutset"] == "p50_p90_p99")
                     & combined_lv["null"].isin(HEADLINE_NULLS)]
    own_pool = s["group"].map(w4g.GROUPS)
    s = s[s["pool"] == own_pool]
    piv = s.pivot_table(index=["group", "itaipu", "scenario"], columns="null",
                         values="pct_median")
    cols = [c for c in HEADLINE_NULLS if c in piv.columns]
    print("\n=== Extreme class, operating, future, p50_p90_p99, pool = own group's null ===")
    print("(median %% of GW over 5 GCMs; three nulls side by side, none canonical)")
    print(piv[cols].round(1).to_string())


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    audit = tab.parent / "audit" / "w4r"
    w4g = load_w4g()

    d, meta = build_units(w4g, proc, tab)
    print(f"unit rows {len(d)}, plants {d['plant_uid'].nunique()}")

    w4r_pct = pd.read_csv(tab / "w4r_null_percentiles.csv")
    w4r_rd = pd.read_csv(tab / "w4r_null_rd.csv")
    draws = load_all_draws(audit, w4r_pct)
    print_tie_shares(w4r_pct, draws)

    gaps = []
    new_lv = level_rows(w4g, d, w4r_pct, draws, gaps)
    new_lv = new_lv.merge(meta, on=["group", "fleet", "itaipu"], how="left")
    if gaps and max(gaps) >= GAP_TOL:
        raise SystemExit(f"ABORT: class-sum gap {max(gaps):.2e} MW exceeds {GAP_TOL:.0e}")

    free_lv = pd.read_csv(tab / "w4g_drought_level_classes.csv")
    if set(free_lv.columns) != set(new_lv.columns):
        diff = set(free_lv.columns) ^ set(new_lv.columns)
        raise SystemExit(f"ABORT: column mismatch between free and emulated: {diff}")
    if len(new_lv) != len(free_lv):
        raise SystemExit(
            f"ABORT: row count mismatch, free {len(free_lv)} vs emulated {len(new_lv)}"
        )
    combined_lv = pd.concat([free_lv, new_lv[free_lv.columns]], ignore_index=True)

    free_ch = pd.read_csv(tab / "w4g_drought_change_classes.csv")
    lookup = change_columns(w4g, w4r_rd)
    for null_kind in EMULATED_NULLS:
        free_ch[f"null_pct_{null_kind}"] = free_ch.apply(
            lambda r, nk=null_kind: lookup[(r["group"], nk)][r["class"]], axis=1
        )
    combined_ch = free_ch

    combined_pct = combined_percentiles(tab, w4r_pct)

    pd.set_option("display.width", 250)
    print_headline(combined_lv, w4g)

    combined_pct.to_csv(tab / "w4grev_null_percentiles.csv", index=False)
    combined_lv.to_csv(tab / "w4grev_drought_level_classes.csv", index=False)
    combined_ch.to_csv(tab / "w4grev_drought_change_classes.csv", index=False)
    print("\nwritten: w4grev_null_percentiles.csv, w4grev_drought_level_classes.csv, "
          "w4grev_drought_change_classes.csv")


if __name__ == "__main__":
    main()