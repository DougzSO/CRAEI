"""W4f: SPEI/R_D threshold-grid sensitivity for drought exposure (D108 plan).

Generalizes W4b's fixed production point (SPEI<=-1.5, R_D>=2) to the full
3x3 grid of SPEI severity thresholds ({-1.0,-1.5,-2.0}) x R_D cuts
({1.5,2.0,3.0}) already used on the null side in w4_null_rates.csv
(scripts/w4_null.py). Observed side is recomputed here by calling
craei.hazards.consolidate.compute_drought_hazards() directly with each
SPEI threshold (threshold is a plain function argument there, not read
from params.yaml internally -- only consolidate.plant_hazards()'s wrapper
fixes it to params.yaml's drought_spei_threshold.value=-1.5), so
plant_hazards.parquet itself is never touched or regenerated.

Scope: HYDRO ONLY (hydro_reservoir + hydro_run_of_river buckets, SPEI_12).
w4_null_rates.csv's null distribution was built from the 1,110-series
hydro BRA pool only (Sec.7/METHODS_SPEC Sec.6) -- there is no null
reference for thermal_water_dependent at any threshold, so this script
does not attempt an excess-over-null number for thermal. Documented scope
limit, not an oversight; extending the null to thermal is future work.

Checks (fixed before running, abort-on-fail before any CSV is written):
  Check 0 (identity): recomputing drought hazards at threshold=-1.5 must
    exactly reproduce the already-promoted plant_hazards.parquet's
    f_d_spei12 rows (baseline_value/future_value/ratio), max abs diff
    <= 1e-9, confirming the recompute path before trusting other thresholds.
  Check A (regression): at (spei_threshold=-1.5, rd_threshold=2.0,
    fleet=operating, itaipu=b, null_type=block_bootstrap_12), excess_pp
    median must reproduce D102's headline (+40.75/+43.20/+53.94 pp for
    ssp126/370/585), tol 0.01 pp.
  Check B (capacity): hydro operating capacity, itaipu=a/b, must be
    109.667/102.667 GW (D82), tol 0.001 GW.

Output: w4f_threshold_grid.csv (one row per spei_threshold x rd_threshold
x fleet x itaipu x scenario x null_type).
"""

import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.exposure.heat_levels import with_itaipu_versions
from craei.hazards import consolidate
from craei.hazards import drought_levels as dl

COUNTRY = "BRA"
SPEI_THRESHOLDS = [-1.0, -1.5, -2.0]
RD_THRESHOLDS = [1.5, 2.0, 3.0]
REF_GW_A, REF_GW_B = 109.667, 102.667
TOL_GW = 0.001
TOL_IDENTITY = 1e-9
TOL_PP = 0.01
MIN_SITES = 10  # O25 convention, same as w4b_excess_over_null.py
HYDRO_BUCKETS = ["hydro_reservoir", "hydro_run_of_river"]
FD_COLS = ["plant_uid", "bucket", "model", "scenario", "hazard",
           "baseline_value", "future_value", "ratio"]

# D102 headline reference (SPEI<=-1.5, R_D>=2, operating, itaipu=b, block_bootstrap_12)
REF_EXCESS_MEDIAN = {"ssp126": 40.75, "ssp370": 43.20, "ssp585": 53.94}


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet")
    u = u[(u["country"] == COUNTRY) & (u["tech_class"] == "hydro")].reset_index(drop=True)
    u["uid"] = u.index
    return u


def gw_share_rd_ge(d, rd_th):
    """GW-weighted share with R_D >= rd_th, per (fleet, itaipu, scenario, model).
    Adapted from scripts/w4b_excess_over_null.py::gw_share_rd_ge (D102/O25);
    rd_th is a required argument here instead of a module constant.
    """
    keys = ["fleet", "itaipu", "scenario", "model"]
    total = d.groupby(keys)["capacity_mw"].sum().rename("gw_total_mw")
    defined = d[d["ratio"].notna()].copy()
    defined["ge"] = defined["ratio"] >= rd_th
    gw_def = defined.groupby(keys)["capacity_mw"].sum().rename("gw_defined_mw")
    gw_ge = defined[defined["ge"]].groupby(keys)["capacity_mw"].sum().rename("gw_ge_mw")
    undef_gw = d[d["ratio"].isna()].groupby(keys)["capacity_mw"].sum().rename("gw_undefined_mw")
    n_plants = d.groupby(keys)["plant_uid"].nunique().rename("n_plants")

    out = pd.concat([total, gw_def, gw_ge, undef_gw, n_plants], axis=1).reset_index()
    out[["gw_ge_mw", "gw_undefined_mw"]] = out[["gw_ge_mw", "gw_undefined_mw"]].fillna(0.0)
    out["pct_gw_rd_ge"] = np.where(out["gw_defined_mw"] > 0,
                                    100.0 * out["gw_ge_mw"] / out["gw_defined_mw"], np.nan)
    out["pct_gw_undefined"] = 100.0 * out["gw_undefined_mw"] / out["gw_total_mw"]
    out["label"] = np.where(out["n_plants"] >= MIN_SITES, "range_reported", "descriptive")
    return out


def summarize_gcm(obs):
    g = obs.groupby(["fleet", "itaipu", "scenario"])
    s = g["pct_gw_rd_ge"].agg(pct_min="min", pct_median="median", pct_max="max", n_gcm="count")
    extra = g.agg(gw_total_mw=("gw_total_mw", "first"), n_plants=("n_plants", "first"),
                  label=("label", "first"), pct_undefined_mean=("pct_gw_undefined", "mean"))
    return s.join(extra).reset_index()


def load_null_grid(tab):
    n = pd.read_csv(tab / "w4_null_rates.csv")
    is_bb = n["null"] == "block_bootstrap"
    n["null_type"] = np.where(is_bb, "block_bootstrap_" + n["block_months"].astype(int).astype(str),
                               n["null"])
    return n[["spei_threshold", "rd_threshold", "null_type", "pct_rd_ge"]].drop_duplicates(
        ["spei_threshold", "rd_threshold", "null_type"]
    )


def excess_table(obs_summary, null_tbl, spei_threshold, rd_threshold):
    nt = null_tbl[(null_tbl["spei_threshold"] == spei_threshold)
                  & (null_tbl["rd_threshold"] == rd_threshold)][["null_type", "pct_rd_ge"]]
    obs_summary = obs_summary.assign(key=1)
    nt = nt.assign(key=1)
    m = obs_summary.merge(nt, on="key").drop(columns="key")
    m["excess_pp_min"] = m["pct_min"] - m["pct_rd_ge"]
    m["excess_pp_median"] = m["pct_median"] - m["pct_rd_ge"]
    m["excess_pp_max"] = m["pct_max"] - m["pct_rd_ge"]
    m["spei_threshold"] = spei_threshold
    m["rd_threshold"] = rd_threshold
    return m.rename(columns={"pct_rd_ge": "null_pct_rd_ge"})


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])

    plants_full = pd.read_parquet(proc / "plants.parquet").copy()
    plants_full["bucket"] = consolidate._assign_bucket(plants_full)

    spei = pd.read_parquet(proc / "spei.parquet")
    plant_cell = pd.read_parquet(proc / "plant_cell.parquet")

    u = load_units(proc)
    itaipu = dl.find_plant(
        plants_full[["plant_uid", "plant_name", "country", "capacity_mw"]],
        COUNTRY, "itaipu", 14000.0,
    )
    uv = with_itaipu_versions(u, itaipu)

    cap = uv[uv["fleet"] == "operating"].groupby("itaipu")["capacity_mw"].sum() / 1000.0
    gw_a, gw_b = float(cap.get("a", np.nan)), float(cap.get("b", np.nan))
    ok_cap = abs(gw_a - REF_GW_A) < TOL_GW and abs(gw_b - REF_GW_B) < TOL_GW
    print(f"Check B (capacity): hydro operating a={gw_a:.3f} (ref {REF_GW_A}), "
          f"b={gw_b:.3f} (ref {REF_GW_B}) -> {'PASS' if ok_cap else 'FAIL'}")
    if not ok_cap:
        print("CHECK B FAILED: nothing written")
        sys.exit(1)

    null_tbl = load_null_grid(tab)

    all_rows = []
    identity_checked = False

    for spei_threshold in SPEI_THRESHOLDS:
        drought, _ = consolidate.compute_drought_hazards(plants_full, spei, plant_cell, spei_threshold)
        fd = drought[(drought["hazard"] == "f_d_spei12")
                     & (drought["bucket"].isin(HYDRO_BUCKETS))][FD_COLS].copy()

        if spei_threshold == -1.5:
            ref = pd.read_parquet(proc / "plant_hazards.parquet", columns=FD_COLS)
            ref = ref[(ref["hazard"] == "f_d_spei12") & (ref["bucket"].isin(HYDRO_BUCKETS))]
            keys = ["plant_uid", "bucket", "model", "scenario"]
            m = fd.merge(ref, on=keys, suffixes=("", "_ref"), how="inner")
            if len(m) != len(fd) or len(m) != len(ref):
                print(f"CHECK 0 FAILED: row count mismatch (recomputed {len(fd)}, "
                      f"reference {len(ref)}, matched {len(m)})")
                sys.exit(1)
            worst = 0.0
            for c in ("baseline_value", "future_value", "ratio"):
                a, b = m[c], m[c + "_ref"]
                if (a.isna() != b.isna()).any():
                    print(f"CHECK 0 FAILED: NaN mismatch in {c}")
                    sys.exit(1)
                both = a.notna() & b.notna()
                if both.any():
                    worst = max(worst, float((a[both] - b[both]).abs().max()))
            ok_identity = worst <= TOL_IDENTITY
            print(f"Check 0 (identity vs plant_hazards.parquet at threshold=-1.5): "
                  f"max|diff|={worst:.2e} -> {'PASS' if ok_identity else 'FAIL'}")
            if not ok_identity:
                print("CHECK 0 FAILED: nothing written")
                sys.exit(1)
            identity_checked = True

        d = dl.unit_drought_frame(uv, fd)

        for rd_threshold in RD_THRESHOLDS:
            obs = gw_share_rd_ge(d, rd_threshold)
            summ = summarize_gcm(obs)
            out = excess_table(summ, null_tbl, spei_threshold, rd_threshold)
            all_rows.append(out)

        del drought, fd, d
        gc.collect()

    if not identity_checked:
        print("CHECK 0 FAILED: never ran (threshold -1.5 missing from grid)")
        sys.exit(1)

    result = pd.concat(all_rows, ignore_index=True)

    check_a = result[
        (result["spei_threshold"] == -1.5) & (result["rd_threshold"] == 2.0)
        & (result["fleet"] == "operating") & (result["itaipu"] == "b")
        & (result["null_type"] == "block_bootstrap_12")
    ]
    ok_a = True
    for scenario, ref_val in REF_EXCESS_MEDIAN.items():
        row = check_a[check_a["scenario"] == scenario]
        if len(row) != 1:
            print(f"CHECK A FAILED: expected exactly one row for {scenario}, found {len(row)}")
            ok_a = False
            continue
        got = float(row["excess_pp_median"].iloc[0])
        passed = abs(got - ref_val) < TOL_PP
        ok_a = ok_a and passed
        print(f"Check A ({scenario}): excess_pp_median={got:.3f} (ref {ref_val}) "
              f"-> {'PASS' if passed else 'FAIL'}")
    if not ok_a:
        print("CHECK A FAILED: nothing written")
        sys.exit(1)

    print("All checks: PASS")
    result.to_csv(tab / "w4f_threshold_grid.csv", index=False)
    print(f"written: w4f_threshold_grid.csv ({len(result)} rows)")

    pd.set_option("display.width", 220)
    head = result[(result["fleet"] == "operating") & (result["itaipu"] == "b")
                  & (result["null_type"] == "block_bootstrap_12")]
    cols = ["spei_threshold", "rd_threshold", "scenario", "pct_min", "pct_median", "pct_max",
            "null_pct_rd_ge", "excess_pp_min", "excess_pp_median", "excess_pp_max",
            "pct_undefined_mean", "n_plants", "label"]
    print("\n=== hydro operating, Itaipu b, block_bootstrap_12, full SPEI x R_D grid ===")
    print(head[cols].sort_values(["spei_threshold", "rd_threshold", "scenario"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
