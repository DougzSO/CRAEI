"""Phase 6, items 1-2: 3-GCM subset (drop UKESM1-0-LL and IPSL-CM6A-LR) and k/5 agreement.

Subset definition: the pair of scripts/w3_gcm_exclusion.py (craei.hazards.gcm_exclusion.exclusion_sets).
Recomputes, for the kept GCMs: D102 (hydro SPEI excess), D125 (hydro SPI, thermal SPEI and SPI excess),
the extreme x extreme cell of Table 3 and the E1 metrics (from e1_hedge_delta / metrics, no new draw).
Null rate for the excess: (a) 5-GCM pool as in the headlines, (b) re-simulated on the 3-GCM pool with the
source scripts' own streams (w4_null.py, w4c_null_spi.py, w4c_null_thermal.py), block 12, 2,000 draws.
Item 2: k-of-5 agreement (D114: GCMs sharing the sign of the median) for the sign-bearing headlines.
Writes w6_subset_excess.csv, w6_subset_coextreme.csv, w6_subset_e1.csv, w6_agreement_k.csv.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1_hedge as eh  # noqa: E402
import w4_null  # noqa: E402
import w4c_null_spi  # noqa: E402
import w4c_null_thermal as w4t  # noqa: E402
import w4c_spi_vs_spei as w4c  # noqa: E402
import w5_table3_gcm_mean as w5m  # noqa: E402

from craei.config import load_paths  # noqa: E402
from craei.exposure.heat_levels import with_itaipu_versions  # noqa: E402
from craei.hazards import drought_levels as dl  # noqa: E402
from craei.hazards import gcm_exclusion as gx  # noqa: E402
from craei.hazards import null_model as nm  # noqa: E402

SEED, N_SIM, N_MONTHS, BLOCK = 23, 2000, 360, 12
DROP = ("ukesm1-0-ll", "ipsl-cm6a-lr")


def k_same_sign(x):
    """Number of GCMs sharing the sign of the median (D114); 0 if the median is 0."""
    x = pd.Series(x).dropna()
    med = x.median()
    return int((np.sign(x) == np.sign(med)).sum()) if med != 0 else 0


def bb12_rate(pool, rng):
    base, fut = nm.simulate_block_bootstrap(pool, N_SIM, N_MONTHS, BLOCK, rng)
    t = nm.null_rate_table(base, fut, [-1.5], [2.0])
    return float(t["pct_rd_ge"].iloc[0])


def null_rates(proc, keep):
    """{(group, hazard): (rate_5gcm_resimulated, rate_3gcm)} with the sources' streams."""
    out = {}
    pool, keys, _ = w4_null.load_pool(proc)
    sel = [i for i, k in enumerate(keys) if k[1] in keep]
    out[("hydro", "spei")] = (bb12_rate(pool, np.random.default_rng(SEED)),
                              bb12_rate([pool[i] for i in sel], np.random.default_rng(SEED)))
    pool, keys, _ = w4c_null_spi.load_pool(proc)
    sel = [i for i, k in enumerate(keys) if k[1] in keep]
    out[("hydro", "spi")] = (bb12_rate(pool, np.random.default_rng(SEED)),
                             bb12_rate([pool[i] for i in sel], np.random.default_rng(SEED)))
    ids, _ = w4t.thermal_cell_ids(proc)
    for hz, vc in w4t.VALUE_COLS.items():
        pool, keys = w4t.load_pool(proc, ids, vc)
        sel = [i for i, k in enumerate(keys) if k[1] in keep]
        out[("thermal_water_dependent", hz)] = (
            bb12_rate(pool, np.random.default_rng([SEED, 100])),
            bb12_rate([pool[i] for i in sel], np.random.default_rng([SEED, 100])))
    return out


def observed_per_gcm(proc):
    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[(units["country"] == w4c.COUNTRY)
                  & units["tech_class"].isin(["hydro", "thermal_water_dependent"])].reset_index(drop=True)
    units["uid"] = units.index
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    uv = with_itaipu_versions(units, dl.find_plant(plants, w4c.COUNTRY, "itaipu", 14000.0))
    valid = set(pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
                .loc[lambda x: x["bucket"] == "thermal_water_dependent", "plant_uid"])
    parts = []
    for group, spec in w4c.GROUPS.items():
        sub = uv[uv["tech_class"] == spec["tech_class"]]
        if group == "thermal_water_dependent":
            sub = sub[sub["plant_uid"].isin(valid)]
        for hz, name in w4c.HAZARDS.items():
            fd = w4c.load_fd(proc, sub["plant_uid"], name, spec["buckets"])
            d = dl.unit_drought_frame(sub, fd)
            parts.append(w4c.gw_share_rd_ge(d).assign(group=group, hazard=hz))
    obs = pd.concat(parts, ignore_index=True)
    return obs[(obs["fleet"] == "operating") & obs["itaipu"].isin(["b", "na"])]


def excess_tables(obs, nulls, keep, all_models):
    rows, agree = [], []
    for (group, hz, sc), g in obs.groupby(["group", "hazard", "scenario"]):
        r5, r3 = nulls[(group, hz)]
        for name, models, null in (("all5", all_models, r5), ("keep3_null5", keep, r5),
                                   ("keep3_null3", keep, r3)):
            x = g[g["model"].isin(models)]["pct_gw_rd_ge2"]
            rows.append({"group": group, "hazard": hz, "scenario": sc, "set": name, "n_gcm": len(x),
                         "pct_min": x.min(), "pct_median": x.median(), "pct_max": x.max(),
                         "null_pct": null, "excess_pp_median": x.median() - null,
                         "excess_pp_min": x.min() - null, "excess_pp_max": x.max() - null,
                         "k_same_sign": k_same_sign(x - null),
                         "gw_total": float(g["gw_total_mw"].iloc[0]) / 1000.0,
                         "n_units_plants": int(g["n_plants"].iloc[0])})
        agree.append({"number": f"{group} {hz} excess over null (block12), operating",
                      "scenario": sc, "median": float((g["pct_gw_rd_ge2"] - r5).median()),
                      "k_of_5": k_same_sign(g["pct_gw_rd_ge2"] - r5), "n_gcm": int(g["model"].nunique())})
    return pd.DataFrame(rows), pd.DataFrame(agree)


def coextreme(paths, keep):
    t = w5m.per_gcm_tables(paths)
    ext = t[(t["heat_class"] == "extreme") & (t["drought_class"] == "extreme")]
    dro = t[t["drought_class"] == "extreme"].groupby(
        ["group", "fleet", "itaipu", "scenario", "model"], as_index=False)["gw"].sum().rename(
        columns={"gw": "gw_drought_extreme"})
    ext = ext.merge(dro, on=["group", "fleet", "itaipu", "scenario", "model"])
    ext["ratio_co_over_drought"] = ext["gw"] / ext["gw_drought_extreme"]
    rows = []
    for (grp, fleet, itaipu, sc), g in ext.groupby(["group", "fleet", "itaipu", "scenario"]):
        for name, models in (("all5", sorted(g["model"].unique())), ("keep3", keep)):
            x = g[g["model"].isin(models)]
            rows.append({"group": grp, "fleet": fleet, "itaipu": itaipu, "scenario": sc, "set": name,
                         "n_gcm": len(x), "gw_total": float(x["gw_total"].iloc[0]),
                         "gw_co_mean": x["gw"].mean(), "gw_co_median": x["gw"].median(),
                         "gw_co_min": x["gw"].min(), "gw_co_max": x["gw"].max(),
                         "pct_co_mean": 100 * (x["gw"] / x["gw_total"]).mean(),
                         "ratio_co_over_drought_mean": x["ratio_co_over_drought"].mean(),
                         "ratio_co_over_drought_min": x["ratio_co_over_drought"].min(),
                         "ratio_co_over_drought_max": x["ratio_co_over_drought"].max()})
    return pd.DataFrame(rows)


def e1_subset(tab, keep):
    d = pd.read_csv(tab / "e1_hedge_delta.csv")
    d = d[d["block"] == eh.MAIN_BLOCK]
    rows = []
    for (hc, tc, fleet, sc), g in d.groupby(["h_channel", "t_channel", "fleet", "scenario"]):
        for name, models in (("all5", sorted(g["model"].unique())), ("keep3", keep)):
            x = g[g["model"].isin(models)]
            n = len(x)
            rows.append({"h_channel": hc, "t_channel": tc, "fleet": fleet, "scenario": sc, "set": name,
                         "n_gcm": n, "median_P_HT_base": x["P_HT_A_base"].median(),
                         "median_P_HT_fut": x["P_HT_A_fut"].median(),
                         "median_dP_HT_A": x["dP_HT_A"].median(), "k_dP_up": int((x["dP_HT_A"] > 0).sum()),
                         "k_dP_same_sign": k_same_sign(x["dP_HT_A"]),
                         "median_dP_marginal": x["dP_HT_marginal"].median(),
                         "median_dP_dependence": x["dP_HT_dependence"].median(),
                         "median_D_B_base": x["D_B_base"].median(), "median_D_B_fut": x["D_B_fut"].median(),
                         "median_dD_B": x["dD_B"].median(), "k_dD_up": int((x["dD_B"] > 0).sum()),
                         "k_dD_same_sign": k_same_sign(x["dD_B"])})
    out = pd.DataFrame(rows)
    m = pd.read_csv(tab / "e1_hedge_metrics.csv")
    m = m[(m["period"] == "baseline") & (m["variant"] == "B") & (m["block"] == eh.MAIN_BLOCK)]
    b = (m[m["model"].isin(keep)].groupby(["h_channel", "t_channel", "fleet"])["D"]
         .agg(D_baseline_keep3_median="median", D_baseline_keep3_min="min", D_baseline_keep3_max="max")
         .reset_index())
    return out.merge(b, on=["h_channel", "t_channel", "fleet"], how="left")


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    models = sorted(pd.read_parquet(proc / "spei.parquet", columns=["model"],
                                    filters=[("scale", "==", "catchment")])["model"].unique())
    keep = gx.exclusion_sets(models, pair=DROP)["drop_" + "+".join(DROP)]
    print("kept GCMs:", keep)
    nulls = null_rates(proc, keep)
    ref = {"hydro": {"spei": 18.88}}
    print("null rates (5-GCM re-simulated, 3-GCM):", {k: tuple(round(x, 3) for x in v) for k, v in nulls.items()})
    assert abs(nulls[("hydro", "spei")][0] - ref["hydro"]["spei"]) < 0.005, "hydro SPEI null not reproduced"
    obs = observed_per_gcm(proc)
    ex, agree = excess_tables(obs, nulls, keep, models)
    chk = ex[(ex["group"] == "hydro") & (ex["hazard"] == "spei") & (ex["set"] == "all5")
             & (ex["scenario"] == "ssp126")]["excess_pp_median"].iloc[0]
    assert abs(chk - 40.75) < 0.01, f"D102 SSP1-2.6 not reproduced: {chk}"
    ex.to_csv(tab / "w6_subset_excess.csv", index=False, lineterminator="\n")
    co = coextreme(paths, keep)
    co.to_csv(tab / "w6_subset_coextreme.csv", index=False, lineterminator="\n")
    e1 = e1_subset(tab, keep)
    e1.to_csv(tab / "w6_subset_e1.csv", index=False, lineterminator="\n")
    ks = e1[(e1["set"] == "all5") & (e1["fleet"] == "operating")]
    e1_agree = pd.concat([
        ks.assign(number=lambda x: "E1 dP(HT) " + x["h_channel"] + "x" + x["t_channel"],
                  median=lambda x: x["median_dP_HT_A"], k_of_5=lambda x: x["k_dP_same_sign"]
                  )[["number", "scenario", "median", "k_of_5", "n_gcm"]],
        ks.assign(number=lambda x: "E1 dD (B) " + x["h_channel"] + "x" + x["t_channel"],
                  median=lambda x: x["median_dD_B"], k_of_5=lambda x: x["k_dD_same_sign"]
                  )[["number", "scenario", "median", "k_of_5", "n_gcm"]]])
    pd.concat([agree, e1_agree], ignore_index=True).to_csv(
        tab / "w6_agreement_k.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    print(ex[ex["scenario"].isin(["ssp126", "ssp370", "ssp585"])].round(2).to_string(index=False))
    print(co.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
