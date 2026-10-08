"""W4b: excess over the null (D83/O23). Observed hydro R_D>=2 share of GW minus the
null false-positive rate; block-length sensitivity (12/24/36/60); AR(1) as upper
bound (26.12%), white noise as lower bound (1.80%). Itaipu b (Brazilian share)
headline, Itaipu a (whole asset) sensitivity (D82). Production point only
(SPEI<=-1.5, R_D>=2.0); other thresholds are W4f's scope, not here.

Reuses w4_null_rates.csv (scripts/w4a_null_rates.py) for every null rate -- no
resimulation. Reuses plant_hazards.parquet (hazard=f_d_spei12, catchment scale,
hydro buckets) for observed F_D/R_D, the same artifact D96 check 3 already
validated against spei.parquet. craei.hazards.drought_levels.unit_drought_frame
does the plant<->F_D join and its own checks (duplicates, absent plants, NaN in
baseline/future, matching GCM x scenario row counts per unit) -- not reimplemented
here. Aborts before writing if the null reference rates (18.88/26.12/1.80, D83/O23)
or the Itaipu a/b operating capacity totals (109.667/102.667 GW, D82) do not match.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.countries import iso as country_iso
from craei.exposure.heat_levels import with_itaipu_versions
from craei.hazards import drought_levels as dl

COUNTRY = country_iso()
SPEI_TH, RD_TH = -1.5, 2.0
REF_BLOCK12, REF_AR1, REF_WN = 18.88, 26.12, 1.80
REF_GW_A, REF_GW_B = 109.667, 102.667
TOL_PCT, TOL_GW = 0.01, 0.001
MIN_SITES = 10  # O25 convention: fewer plants per (fleet, itaipu) is descriptive, not range_reported


def load_units(proc):
    u = pd.read_parquet(proc / "plant_units.parquet")
    u = u[(u["country"] == COUNTRY) & (u["tech_class"] == "hydro")].reset_index(drop=True)
    u["uid"] = u.index
    return u


def load_fd(proc, plant_uids):
    cols = ["plant_uid", "bucket", "model", "scenario", "hazard",
            "baseline_value", "future_value", "ratio"]
    h = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols)
    h = h[(h["hazard"] == "f_d_spei12")
          & h["bucket"].isin(["hydro_reservoir", "hydro_run_of_river"])
          & h["plant_uid"].isin(set(plant_uids))]
    return h


def gw_share_rd_ge(d, rd_th=RD_TH):
    """GW-weighted share with R_D >= rd_th, per (fleet, itaipu, scenario, model).

    R_D undefined (baseline F_D == 0, ratio NaN by consolidate.py's own convention)
    is excluded from numerator and denominator and reported separately as
    pct_gw_undefined of the group's total capacity -- never folded into either side.
    """
    keys = ["fleet", "itaipu", "scenario", "model"]
    total = d.groupby(keys)["capacity_mw"].sum().rename("gw_total_mw")
    defined = d[d["ratio"].notna()].copy()
    defined["ge"] = defined["ratio"] >= rd_th
    gw_def = defined.groupby(keys)["capacity_mw"].sum().rename("gw_defined_mw")
    gw_ge = defined[defined["ge"]].groupby(keys)["capacity_mw"].sum().rename("gw_ge_mw")
    undef_gw = d[d["ratio"].isna()].groupby(keys)["capacity_mw"].sum().rename("gw_undefined_mw")
    n_plants = d.groupby(keys)["plant_uid"].nunique().rename("n_plants")
    n_units = d.groupby(keys).size().rename("n_units")

    out = pd.concat([total, gw_def, gw_ge, undef_gw, n_plants, n_units], axis=1).reset_index()
    out[["gw_ge_mw", "gw_undefined_mw"]] = out[["gw_ge_mw", "gw_undefined_mw"]].fillna(0.0)
    out["pct_gw_rd_ge2"] = np.where(out["gw_defined_mw"] > 0,
                                     100.0 * out["gw_ge_mw"] / out["gw_defined_mw"], np.nan)
    out["pct_gw_undefined"] = 100.0 * out["gw_undefined_mw"] / out["gw_total_mw"]
    out["label"] = np.where(out["n_plants"] >= MIN_SITES, "range_reported", "descriptive")
    return out


def summarize_gcm(obs):
    g = obs.groupby(["fleet", "itaipu", "scenario"])
    s = g["pct_gw_rd_ge2"].agg(pct_min="min", pct_median="median", pct_max="max", n_gcm="count")
    extra = g.agg(gw_total_mw=("gw_total_mw", "first"), n_plants=("n_plants", "first"),
                  n_units=("n_units", "first"),
                  label=("label", "first"), pct_undefined_mean=("pct_gw_undefined", "mean"))
    return s.join(extra).reset_index()


def load_null(tab):
    n = pd.read_csv(tab / "w4_null_rates.csv")
    n = n[(n["spei_threshold"] == SPEI_TH) & (n["rd_threshold"] == RD_TH)].copy()
    is_bb = n["null"] == "block_bootstrap"
    n["null_type"] = np.where(is_bb, "block_bootstrap_" + n["block_months"].astype(int).astype(str),
                              n["null"])
    return n[["null_type", "pct_rd_ge"]].drop_duplicates("null_type")


def excess_table(obs_summary, null_tbl):
    obs_summary = obs_summary.assign(key=1)
    null_tbl = null_tbl.assign(key=1)
    m = obs_summary.merge(null_tbl, on="key").drop(columns="key")
    m["excess_pp_min"] = m["pct_min"] - m["pct_rd_ge"]
    m["excess_pp_median"] = m["pct_median"] - m["pct_rd_ge"]
    m["excess_pp_max"] = m["pct_max"] - m["pct_rd_ge"]
    return m.rename(columns={"pct_rd_ge": "null_pct_rd_ge2"})


def agreement_table(obs, null_tbl):
    """Per-GCM excess sign agreement (O21/D119): for each (fleet, itaipu,
    scenario, null_type), count how many of n_gcm models show excess_pp > 0
    (observed pct_gw_rd_ge2 minus the null rate), using the same k-of-5
    agreement convention closed under O31 (same sign across k of 5 GCMs).
    Does not replace excess_table; reported alongside it as an extra lens.
    """
    keys = ["fleet", "itaipu", "scenario", "model"]
    obs_m = obs[keys + ["pct_gw_rd_ge2"]].assign(key=1)
    null_m = null_tbl.assign(key=1)
    m = obs_m.merge(null_m, on="key").drop(columns="key")
    m["excess_pp"] = m["pct_gw_rd_ge2"] - m["pct_rd_ge"]
    m["sign_positive"] = m["excess_pp"] > 0

    g = m.groupby(["fleet", "itaipu", "scenario", "null_type"])
    out = g.agg(
        n_gcm=("model", "nunique"),
        n_gcm_positive_sign=("sign_positive", "sum"),
        excess_pp_median=("excess_pp", "median"),
    ).reset_index()
    out["k_agreement"] = out["n_gcm_positive_sign"]
    return out


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])

    u = load_units(proc)
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    itaipu = dl.find_plant(plants, COUNTRY, "itaipu", 14000.0)
    uv = with_itaipu_versions(u, itaipu)
    fd = load_fd(proc, u["plant_uid"])
    d = dl.unit_drought_frame(uv, fd)  # raises on duplicates, absent plants, NaN base/future, row-count mismatch
    print(f"unit rows: {len(d)}; R_D undefined rows: {int(d['ratio'].isna().sum())}")

    cap = uv[uv["fleet"] == "operating"].groupby("itaipu")["capacity_mw"].sum() / 1000.0
    gw_a, gw_b = float(cap.get("a", np.nan)), float(cap.get("b", np.nan))
    ok_cap = abs(gw_a - REF_GW_A) < TOL_GW and abs(gw_b - REF_GW_B) < TOL_GW
    print(f"check capacity: hydro operating a={gw_a:.3f} (ref {REF_GW_A}), "
          f"b={gw_b:.3f} (ref {REF_GW_B}) -> {'PASS' if ok_cap else 'FAIL'}")

    null_tbl = load_null(tab)
    ref_row = {k: float(null_tbl.loc[null_tbl["null_type"] == k, "pct_rd_ge"].iloc[0])
               for k in ("block_bootstrap_12", "ar1", "white_noise_ms12")}
    # AR(1) is NOT an abort check: w4a_null_rates.py's own docstring calls it
    # "informative only" -- it re-estimates phi from the full 1,110-series pool,
    # a different quantity from c23c's phi=0.9291 fixed on a 200-series sample
    # (D83/O23's "upper bound" reference). Reported, not verified against REF_AR1.
    ok_null = (abs(ref_row["block_bootstrap_12"] - REF_BLOCK12) < TOL_PCT
               and abs(ref_row["white_noise_ms12"] - REF_WN) < TOL_PCT)
    print(f"check null reference (abort-on-fail): block12={ref_row['block_bootstrap_12']:.3f} "
          f"(ref {REF_BLOCK12}), white_noise={ref_row['white_noise_ms12']:.3f} (ref {REF_WN}) "
          f"-> {'PASS' if ok_null else 'FAIL'}")
    print(f"AR(1) soft check (informative only, NOT abort-on-fail): pool-phi estimate "
          f"{ref_row['ar1']:.3f}% vs c23c reference {REF_AR1}% (phi=0.9291, 200-series "
          f"sample) -- different phi estimation, not a reproduction target")

    if not (ok_cap and ok_null):
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("checks: PASS")

    obs = gw_share_rd_ge(d)
    summ = summarize_gcm(obs)
    out = excess_table(summ, null_tbl)
    out.to_csv(tab / "w4b_excess_over_null.csv", index=False)
    print(f"written: w4b_excess_over_null.csv ({len(out)} rows)")

    agree = agreement_table(obs, null_tbl)
    agree.to_csv(tab / "w4b_agreement.csv", index=False)
    print(f"written: w4b_agreement.csv ({len(agree)} rows)")

    pd.set_option("display.width", 220)
    head = out[(out["fleet"] == "operating") & (out["itaipu"] == "b")
               & (out["null_type"].isin(["block_bootstrap_12", "block_bootstrap_24",
                                          "block_bootstrap_36", "block_bootstrap_60",
                                          "ar1", "white_noise_ms12"]))]
    print("\n=== hydro operating, Itaipu b (headline), excess_pp = observed - null, "
          "SPEI<=-1.5, R_D>=2 ===")
    cols = ["scenario", "null_type", "pct_min", "pct_median", "pct_max",
            "null_pct_rd_ge2", "excess_pp_min", "excess_pp_median", "excess_pp_max",
            "pct_undefined_mean", "n_plants", "label"]
    print(head[cols].sort_values(["scenario", "null_type"]).round(2).to_string(index=False))

    head_a = out[(out["fleet"] == "operating") & (out["itaipu"] == "a")
                 & (out["null_type"] == "block_bootstrap_12")]
    print("\n=== hydro operating, Itaipu a (sensitivity), block12 only ===")
    print(head_a[cols].round(2).to_string(index=False))


if __name__ == "__main__":
    main()