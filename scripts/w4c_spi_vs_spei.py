"""W4c Step 4: SPI-12 vs SPEI-12 excess over null, hydro + thermal (O18/D108 item 4).

Structural clone of scripts/w4b_excess_over_null.py, generalized along two new
dimensions: group (hydro, thermal_water_dependent) and hazard (spei: f_d_spei12
with scripts/w4_null.py's w4_null_rates.csv; spi: f_d_spi12 with Step 3's
w4c_null_rates_spi.csv). drought_levels.unit_drought_frame is called once per
(group, hazard) pair -- it raises on duplicate (plant_uid, model, scenario)
keys, so SPEI and SPI rows for the same units cannot be joined in one call.

Checks fixed before running (author-approved, chat):
  A (regression): the SPEI slice, hydro/operating/itaipu=b/block_bootstrap_12,
     must reproduce D102's headline excess_pp_median exactly (SSP126/370/585:
     40.75/43.20/53.94 pp), tolerance 0.01 pp -- guards against the hydro+
     thermal generalization silently changing the already-closed hydro result.
  B (hydro capacity): operating a=109.667 / b=102.667 GW (D82), tol 0.001 GW.
  C (thermal capacity, new): thermal_water_dependent operating = 39.7699 GW
     (confirmed this session via inventory.fleet.scope_units), tol 0.001 GW.

Output: w4c_spi_vs_spei.csv (long format, columns group/hazard added to the
w4b schema). Integration into w5_sensitivity.csv is a separate, later step.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.exposure.heat_levels import with_itaipu_versions
from craei.hazards import drought_levels as dl

COUNTRY = "BRA"
SPEI_TH, RD_TH = -1.5, 2.0
REF_GW_A, REF_GW_B, REF_GW_THERMAL = 109.667, 102.667, 39.1015
# REF_GW_THERMAL excludes 5 plants (0.6684 GW operating) whose plant-level
# bucket in plant_hazards.parquet is thermal_air_only despite having at
# least one thermal_water_dependent unit in plant_units.parquet -- a
# pre-existing plant-vs-unit granularity mismatch in consolidate.py's
# _assign_bucket (plant-level, dominant tech_class), not introduced here.
# Confirmed this session (chat); excluded units never had f_d_spei12/
# f_d_spi12 computed, so they cannot enter unit_drought_frame regardless.
TOL_GW = 0.001
MIN_SITES = 10

GROUPS = {
    "hydro": {"tech_class": "hydro", "buckets": ["hydro_reservoir", "hydro_run_of_river"]},
    "thermal_water_dependent": {"tech_class": "thermal_water_dependent",
                                 "buckets": ["thermal_water_dependent"]},
}
HAZARDS = {"spei": "f_d_spei12", "spi": "f_d_spi12"}
REF_EXCESS_D102 = {"ssp126": 40.75, "ssp370": 43.20, "ssp585": 53.94}
TOL_EXCESS_PP = 0.01


def load_fd(proc, plant_uids, hazard_name, buckets):
    cols = ["plant_uid", "bucket", "model", "scenario", "hazard",
            "baseline_value", "future_value", "ratio"]
    h = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols)
    h = h[(h["hazard"] == hazard_name) & h["bucket"].isin(buckets)
          & h["plant_uid"].isin(set(plant_uids))]
    return h


def gw_share_rd_ge(d, rd_th=RD_TH):
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
    out["pct_gw_rd_ge2"] = np.where(out["gw_defined_mw"] > 0,
                                     100.0 * out["gw_ge_mw"] / out["gw_defined_mw"], np.nan)
    out["pct_gw_undefined"] = 100.0 * out["gw_undefined_mw"] / out["gw_total_mw"]
    out["label"] = np.where(out["n_plants"] >= MIN_SITES, "range_reported", "descriptive")
    return out


def summarize_gcm(obs, extra_keys):
    keys = extra_keys + ["fleet", "itaipu", "scenario"]
    g = obs.groupby(keys)
    s = g["pct_gw_rd_ge2"].agg(pct_min="min", pct_median="median", pct_max="max", n_gcm="count")
    extra = g.agg(gw_total_mw=("gw_total_mw", "first"), n_plants=("n_plants", "first"),
                  label=("label", "first"), pct_undefined_mean=("pct_gw_undefined", "mean"))
    return s.join(extra).reset_index()


def load_null_spei(tab):
    n = pd.read_csv(tab / "w4_null_rates.csv")
    n = n[(n["spei_threshold"] == SPEI_TH) & (n["rd_threshold"] == RD_TH)].copy()
    is_bb = n["null"] == "block_bootstrap"
    n["null_type"] = np.where(is_bb, "block_bootstrap_" + n["block_months"].astype(int).astype(str), n["null"])
    return n[["null_type", "pct_rd_ge"]].drop_duplicates("null_type").assign(hazard="spei")


def load_null_spi(tab):
    n = pd.read_csv(tab / "w4c_null_rates_spi.csv")
    n = n[(n["spei_threshold"] == SPEI_TH) & (n["rd_threshold"] == RD_TH)].copy()
    is_bb = n["null"] == "block_bootstrap"
    n["null_type"] = np.where(is_bb, "block_bootstrap_" + n["block_months"].astype(int).astype(str), n["null"])
    return n[["null_type", "pct_rd_ge"]].drop_duplicates("null_type").assign(hazard="spi")


def excess_table(summ, null_tbl):
    m = summ.merge(null_tbl, on="hazard", how="left")
    m["excess_pp_min"] = m["pct_min"] - m["pct_rd_ge"]
    m["excess_pp_median"] = m["pct_median"] - m["pct_rd_ge"]
    m["excess_pp_max"] = m["pct_max"] - m["pct_rd_ge"]
    return m.rename(columns={"pct_rd_ge": "null_pct_rd_ge2"})


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])

    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[(units["country"] == COUNTRY)
                  & units["tech_class"].isin(["hydro", "thermal_water_dependent"])].reset_index(drop=True)
    units["uid"] = units.index

    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    itaipu = dl.find_plant(plants, COUNTRY, "itaipu", 14000.0)
    uv = with_itaipu_versions(units, itaipu)

    cap_hydro = uv[(uv["tech_class"] == "hydro") & (uv["fleet"] == "operating")]
    cap_hydro = cap_hydro.groupby("itaipu")["capacity_mw"].sum() / 1000.0
    gw_a, gw_b = float(cap_hydro.get("a", np.nan)), float(cap_hydro.get("b", np.nan))
    valid_bucket_uids_chk = set(
        pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
        .loc[lambda x: x["bucket"] == "thermal_water_dependent", "plant_uid"]
    )
    tw_filtered = uv[(uv["tech_class"] == "thermal_water_dependent")
                     & uv["plant_uid"].isin(valid_bucket_uids_chk)]
    cap_thermal = tw_filtered[tw_filtered["fleet"] == "operating"]["capacity_mw"].sum() / 1000.0
    ok_b = abs(gw_a - REF_GW_A) < TOL_GW and abs(gw_b - REF_GW_B) < TOL_GW
    ok_c = abs(cap_thermal - REF_GW_THERMAL) < TOL_GW
    print(f"check B hydro capacity: a={gw_a:.4f} (ref {REF_GW_A}), b={gw_b:.4f} (ref {REF_GW_B}) "
          f"-> {'PASS' if ok_b else 'FAIL'}")
    print(f"check C thermal capacity: {cap_thermal:.4f} (ref {REF_GW_THERMAL}) "
          f"-> {'PASS' if ok_c else 'FAIL'}")

    obs_parts = []
    valid_bucket_uids = set(
        pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
        .loc[lambda x: x["bucket"] == "thermal_water_dependent", "plant_uid"]
    )
    for group, spec in GROUPS.items():
        subset = uv[uv["tech_class"] == spec["tech_class"]]
        if group == "thermal_water_dependent":
            before = subset["plant_uid"].nunique()
            subset = subset[subset["plant_uid"].isin(valid_bucket_uids)]
            after = subset["plant_uid"].nunique()
            print(f"thermal_water_dependent plant filter: {before} -> {after} plants "
                  f"(excluded {before - after} with mismatched plant_hazards bucket)")
        for hz_label, hazard_name in HAZARDS.items():
            fd = load_fd(proc, subset["plant_uid"], hazard_name, spec["buckets"])
            d = dl.unit_drought_frame(subset, fd)
            obs = gw_share_rd_ge(d).assign(group=group, hazard=hz_label)
            obs_parts.append(obs)
            print(f"{group}/{hz_label}: unit rows {len(d)}, R_D undefined {int(d['ratio'].isna().sum())}")
    obs_all = pd.concat(obs_parts, ignore_index=True)

    summ = summarize_gcm(obs_all, ["group", "hazard"])
    null_tbl = pd.concat([load_null_spei(tab), load_null_spi(tab)], ignore_index=True)
    out = excess_table(summ, null_tbl)

    chk = out[(out["group"] == "hydro") & (out["hazard"] == "spei")
              & (out["fleet"] == "operating") & (out["itaipu"] == "b")
              & (out["null_type"] == "block_bootstrap_12")]
    chk = chk.set_index("scenario")["excess_pp_median"]
    ok_a = True
    for sc, ref_val in REF_EXCESS_D102.items():
        got = float(chk.get(sc, np.nan))
        diff = abs(got - ref_val)
        print(f"check A regression {sc}: excess_pp_median={got:.2f} (ref {ref_val}) "
              f"diff={diff:.4f} -> {'PASS' if diff < TOL_EXCESS_PP else 'FAIL'}")
        ok_a = ok_a and diff < TOL_EXCESS_PP

    if not (ok_a and ok_b and ok_c):
        print("\nCHECK FAILED: w4c_spi_vs_spei.csv not written")
        sys.exit(1)
    print("\nchecks A-C: PASS")

    out.to_csv(tab / "w4c_spi_vs_spei.csv", index=False)
    print(f"\nwritten: w4c_spi_vs_spei.csv ({len(out)} rows)")

    pd.set_option("display.width", 220)
    head = out[(out["fleet"] == "operating") & (out["itaipu"].isin(["b", "na"]))
               & (out["null_type"] == "block_bootstrap_12")]
    cols = ["group", "hazard", "scenario", "pct_min", "pct_median", "pct_max",
            "null_pct_rd_ge2", "excess_pp_median", "pct_undefined_mean", "n_plants", "label"]
    print("\n=== operating, block12, SPEI vs SPI side by side ===")
    print(head[cols].sort_values(["group", "hazard", "scenario"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
