"""E1 driver: hydrothermal hedge failure, Brazil national (D140, docs/article/E1_spec.md).

Reads (selectively): plants / plant_units / plant_hazards / plant_cell, spei.parquet (catchment scale for
hydro, cell scale for thermal), indices_daily.parquet (n35, thermal cells), spei_w5e5.parquet,
w5e5_hydro_spi12.parquet and w5e5_thermal_cells_monthly.parquet (scripts/e1_w5e5_inputs.py).
Writes to outputs_tables_dir: e1_hedge_series.csv, e1_hedge_metrics.csv, e1_hedge_delta.csv,
e1_hedge_summary.csv, e1_hedge_criterion.csv, e1_hedge_observed.csv.

Seeds: np.random.default_rng([23, 3, k]) with k the running index of the bootstrap / test calls, in the
fixed loop order pair -> fleet -> model -> period -> variant -> block (see `Rng`).
"""

import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1_populations as pops  # noqa: E402

from craei.config import load_params, load_paths  # noqa: E402
from craei.exposure import hedge  # noqa: E402

SCEN = ["ssp126", "ssp370", "ssp585"]
BASE_MONTHS = pd.date_range("1985-01-01", "2014-12-01", freq="MS")
# Future SPEI-12 has no accumulation history: the first 11 months of 2041 are undefined, so every future
# series uses the 29 full years 2042-2070 (348 months), the same window for all channels.
FUT_MONTHS = pd.date_range("2042-01-01", "2070-12-01", freq="MS")
# Observed W5E5 SPEI-12 starts in 1985, so its first 11 months are undefined: observed window 1986-2014.
OBS_MONTHS = pd.date_range("1986-01-01", "2014-12-01", freq="MS")
N_SIM = 2000
BLOCKS = (12, 24, 36)
MAIN_BLOCK = 12
SEED_ROOT = (23, 3)
H_CH = ("spei", "spi")
T_CH = ("heat", "heat_cal", "spei", "spi", "any_spei", "any_spi")
PAIRS = [("spi", "spi"), ("spei", "spei"), ("spei", "heat"), ("spi", "heat"), ("spei", "any_spei"),
         ("spi", "any_spi"), ("spei", "heat_cal"), ("spi", "heat_cal")]
CONTROL = ("spi", "spi")
FLEETS = ["operating", "operating_plus_planned"]


class Rng:
    """Deterministic stream: the k-th call returns default_rng([23, 3, k])."""

    def __init__(self):
        self.k = 0

    def next(self):
        r = np.random.default_rng([*SEED_ROOT, self.k])
        self.k += 1
        return r


def pivot(df, ids, months, col):
    """(len(ids), len(months)) matrix of `col` by id x month; raises on gaps or NaN."""
    m = (df.pivot(index="id", columns="month", values=col)
         .reindex(index=list(ids), columns=list(months)))
    if m.isna().any().any():
        raise ValueError(f"NaN or missing entries in {col} matrix")
    return m.to_numpy(dtype=float)


def read_spei(proc, scale, ids, models, thr_cols):
    cols = ["id", "model", "scenario", "period", "month", *thr_cols]
    df = pd.read_parquet(proc / "spei.parquet", columns=cols,
                         filters=[("scale", "==", scale), ("id", "in", list(ids))])
    return df[df["model"].isin(models)]


def read_n35(proc, cells, model):
    d = pd.read_parquet(proc / "indices_daily.parquet",
                        columns=["cell_lat", "cell_lon", "scenario", "period", "month", "value"],
                        filters=[("index", "==", "n35"), ("model", "==", model)])
    d["id"] = d["cell_lat"].astype(str) + "_" + d["cell_lon"].astype(str)
    return d[d["id"].isin(set(cells))]


def thermal_flags(n35_base, n35, spei_m, spi_m, cell_row, thr):
    """Plant-month boolean flags per channel; the heat thresholds come from `n35_base` (cells x 360)."""
    q = np.quantile(n35_base, hedge.Q_EVENT, axis=1)  # local P90 over all baseline months
    qc = np.quantile(n35_base.reshape(len(n35_base), -1, 12), hedge.Q_EVENT, axis=1)  # per calendar month
    heat = (n35 > q[:, None])[cell_row]
    heat_cal = (n35.reshape(len(n35), -1, 12) > qc[:, None, :]).reshape(len(n35), -1)[cell_row]
    spei_f = (spei_m <= thr)[cell_row]
    spi_f = (spi_m <= thr)[cell_row]
    return {"heat": heat, "heat_cal": heat_cal, "spei": spei_f, "spi": spi_f,
            "any_spei": heat | spei_f, "any_spi": heat | spi_f}


def build_series(proc, p, thr):
    """{(model, period): {'H': {ch: series}, 'T': {fleet: {ch: series}}}} for the GCMs."""
    hy, t_all = p["hydro"], p["operating_plus_planned"]
    cells = list(t_all["cell_id"].drop_duplicates())
    cell_ix = {c: i for i, c in enumerate(cells)}
    out = {}
    models = sorted(pd.read_parquet(proc / "spei.parquet", columns=["model"],
                                    filters=[("scale", "==", "catchment")])["model"].unique())
    hs = read_spei(proc, "catchment", hy["plant_uid"], models, ["SPEI_12", "SPI_12"])
    ts = read_spei(proc, "cell", cells, models, ["SPEI_12", "SPI_12"])
    for m in models:
        n35 = read_n35(proc, cells, m)
        periods = {"baseline": ("historical", BASE_MONTHS), **{s: (s, FUT_MONTHS) for s in SCEN}}
        mats, base_n35 = {}, None
        for label, (scen, months) in periods.items():
            hh = hs[(hs["model"] == m) & (hs["scenario"] == scen)]
            tt = ts[(ts["model"] == m) & (ts["scenario"] == scen)]
            nn = n35[n35["scenario"] == scen]
            mats[label] = {
                "h_spei": pivot(hh, hy["plant_uid"], months, "SPEI_12"),
                "h_spi": pivot(hh, hy["plant_uid"], months, "SPI_12"),
                "c_spei": pivot(tt, cells, months, "SPEI_12"),
                "c_spi": pivot(tt, cells, months, "SPI_12"),
                "n35": pivot(nn, cells, months, "value")}
        base_n35 = mats["baseline"]["n35"]
        for label, mm in mats.items():
            ser = {"H": {"spei": hedge.weighted_share(mm["h_spei"] <= thr, hy["capacity_mw"]),
                         "spi": hedge.weighted_share(mm["h_spi"] <= thr, hy["capacity_mw"])},
                   "T": {}}
            for fleet in FLEETS:
                pf = p[fleet]
                row = np.array([cell_ix[c] for c in pf["cell_id"]])
                fl = thermal_flags(base_n35, mm["n35"], mm["c_spei"], mm["c_spi"], row, thr)
                ser["T"][fleet] = {c: hedge.weighted_share(fl[c], pf["capacity_mw"]) for c in T_CH}
            out[(m, label)] = ser
        del n35, mats
        gc.collect()
    return out, models


def build_observed(proc, p, thr):
    hy, t_all = p["hydro"], p["operating_plus_planned"]
    cells = list(t_all["cell_id"].drop_duplicates())
    cell_ix = {c: i for i, c in enumerate(cells)}
    w = pd.read_parquet(proc / "spei_w5e5.parquet", columns=["id", "month", "SPEI_12"])
    w = w[w["id"].isin(set(hy["plant_uid"])) & w["month"].isin(OBS_MONTHS)]
    hsp = pd.read_parquet(proc / "w5e5_hydro_spi12.parquet")
    hsp = hsp[hsp["month"].isin(OBS_MONTHS)]
    t = pd.read_parquet(proc / "w5e5_thermal_cells_monthly.parquet")
    t = t[t["month"].isin(OBS_MONTHS)]
    h_spei = pivot(w, hy["plant_uid"], OBS_MONTHS, "SPEI_12")
    h_spi = pivot(hsp, hy["plant_uid"], OBS_MONTHS, "SPI_12")
    mats = {k: pivot(t, cells, OBS_MONTHS, k) for k in ("SPEI_12", "SPI_12", "N35")}
    ser = {"H": {"spei": hedge.weighted_share(h_spei <= thr, hy["capacity_mw"]),
                 "spi": hedge.weighted_share(h_spi <= thr, hy["capacity_mw"])}, "T": {}}
    for fleet in FLEETS:
        pf = p[fleet]
        row = np.array([cell_ix[c] for c in pf["cell_id"]])
        fl = thermal_flags(mats["N35"], mats["N35"], mats["SPEI_12"], mats["SPI_12"], row, thr)
        ser["T"][fleet] = {c: hedge.weighted_share(fl[c], pf["capacity_mw"]) for c in T_CH}
    return ser


def estimate_rows(hp, tp, qh, qt, variant, base_info):
    """Metrics of one period for a variant; thresholds: A -> (qh, qt) from the baseline, B -> own P90."""
    if variant == "B":
        qh, qt = hedge.p90_threshold(hp), hedge.p90_threshold(tp)
    h, u = hedge.events(hp, qh), hedge.events(tp, qt)
    return hedge.joint_metrics(h, u), h, u, qh, qt


def run_pairs(series, models, rng):
    metrics, boots = [], {}
    periods = ["baseline", *SCEN]
    for hc, tc in PAIRS:
        for fleet in FLEETS:
            for m in models:
                hb = series[(m, "baseline")]["H"][hc]
                tb = series[(m, "baseline")]["T"][fleet][tc]
                qh0, qt0 = hedge.p90_threshold(hb), hedge.p90_threshold(tb)
                for per in periods:
                    hp = series[(m, per)]["H"][hc]
                    tp = series[(m, per)]["T"][fleet][tc]
                    for variant in ("A", "B"):
                        est, h, u, qh, qt = estimate_rows(hp, tp, qh0, qt0, variant, None)
                        p_circ = hedge.circular_shift_pvalue(h, u, N_SIM, rng.next())
                        for block in BLOCKS:
                            bt = hedge.bootstrap_period(hp, tp, variant, qh, qt, block, N_SIM, rng.next())
                            boots[(hc, tc, fleet, m, per, variant, block)] = bt
                            row = {"h_channel": hc, "t_channel": tc, "fleet": fleet, "variant": variant,
                                   "model": m, "period": per, "block": block, "q_H": qh, "q_T": qt,
                                   **{k: float(est[k]) for k in hedge.METRICS},
                                   "p_circ_D_gt_1": p_circ}
                            for k in ("P_HT", "P_T_given_H", "D"):
                                row[k + "_lo"], row[k + "_hi"] = hedge.percentile_ci(bt[k])
                            metrics.append(row)
    return pd.DataFrame(metrics), boots


def delta_rows(met, boots, models):
    rows = []
    key = ["h_channel", "t_channel", "fleet", "model", "period", "variant", "block"]
    mi = met.set_index(key)
    for hc, tc in PAIRS:
        for fleet in FLEETS:
            for m in models:
                for s in SCEN:
                    for block in BLOCKS:
                        a_b = mi.loc[(hc, tc, fleet, m, "baseline", "A", block)]
                        a_f = mi.loc[(hc, tc, fleet, m, s, "A", block)]
                        b_b = mi.loc[(hc, tc, fleet, m, "baseline", "B", block)]
                        b_f = mi.loc[(hc, tc, fleet, m, s, "B", block)]
                        dec = hedge.decompose_delta(a_b, a_f)
                        bp = boots[(hc, tc, fleet, m, "baseline", "A", block)]["P_HT"]
                        fp = boots[(hc, tc, fleet, m, s, "A", block)]["P_HT"]
                        bd = boots[(hc, tc, fleet, m, "baseline", "B", block)]["D"]
                        fd = boots[(hc, tc, fleet, m, s, "B", block)]["D"]
                        d_lo, d_hi = hedge.percentile_ci(fp - bp)
                        dd_lo, dd_hi = hedge.percentile_ci(fd - bd)
                        rows.append({
                            "h_channel": hc, "t_channel": tc, "fleet": fleet, "model": m, "scenario": s,
                            "block": block, "P_HT_A_base": a_b["P_HT"], "P_HT_A_fut": a_f["P_HT"],
                            "dP_HT_A": dec["dP_HT"], "dP_HT_marginal": dec["marginal"],
                            "dP_HT_dependence": dec["dependence"], "dP_HT_A_lo": d_lo, "dP_HT_A_hi": d_hi,
                            "P_T_given_H_A_base": a_b["P_T_given_H"], "P_T_given_H_A_fut": a_f["P_T_given_H"],
                            "D_B_base": b_b["D"], "D_B_fut": b_f["D"], "dD_B": b_f["D"] - b_b["D"],
                            "dD_B_lo": dd_lo, "dD_B_hi": dd_hi})
    return pd.DataFrame(rows)


def k_agree(x):
    """Number of GCMs with the same sign as the median over GCMs (O31 definition); 0 if median is 0."""
    x = pd.Series(x).dropna()
    med = x.median()
    return int((np.sign(x) == np.sign(med)).sum()) if med != 0 else 0


def summarise(delta):
    d = delta[delta["block"] == MAIN_BLOCK]
    rows = []
    for (hc, tc, fleet, s), g in d.groupby(["h_channel", "t_channel", "fleet", "scenario"]):
        rows.append({"h_channel": hc, "t_channel": tc, "fleet": fleet, "scenario": s,
                     "n_gcm": int(g["model"].nunique()),
                     "median_P_HT_base": g["P_HT_A_base"].median(), "median_P_HT_fut": g["P_HT_A_fut"].median(),
                     "median_dP_HT_A": g["dP_HT_A"].median(), "k_dP_up": int((g["dP_HT_A"] > 0).sum()),
                     "k_dP_agree": k_agree(g["dP_HT_A"]),
                     "median_dP_marginal": g["dP_HT_marginal"].median(),
                     "median_dP_dependence": g["dP_HT_dependence"].median(),
                     "median_P_T_given_H_base": g["P_T_given_H_A_base"].median(),
                     "median_P_T_given_H_fut": g["P_T_given_H_A_fut"].median(),
                     "median_D_B_base": g["D_B_base"].median(), "median_D_B_fut": g["D_B_fut"].median(),
                     "median_dD_B": g["dD_B"].median(), "k_dD_up": int((g["dD_B"] > 0).sum()),
                     "k_dD_agree": k_agree(g["dD_B"])})
    return pd.DataFrame(rows)


def observed_rows(obs, met, models):
    rng = Rng()
    rng.k = 10_000  # observed stream, separate from the GCM stream
    rows = []
    for hc, tc in PAIRS:
        for fleet in FLEETS:
            hp, tp = obs["H"][hc], obs["T"][fleet][tc]
            est, h, u, qh, qt = estimate_rows(hp, tp, None, None, "B", None)
            row = {"h_channel": hc, "t_channel": tc, "fleet": fleet, "source": "w5e5_1986_2014",
                   **{k: float(est[k]) for k in hedge.METRICS},
                   "p_circ_D_gt_1": hedge.circular_shift_pvalue(h, u, N_SIM, rng.next())}
            for block in BLOCKS:
                bt = hedge.bootstrap_period(hp, tp, "B", qh, qt, block, N_SIM, rng.next())
                for k in ("P_HT", "P_T_given_H", "D"):
                    lo, hi = hedge.percentile_ci(bt[k])
                    row[f"{k}_lo_b{block}"], row[f"{k}_hi_b{block}"] = lo, hi
            g = met[(met["h_channel"] == hc) & (met["t_channel"] == tc) & (met["fleet"] == fleet)
                    & (met["period"] == "baseline") & (met["variant"] == "B") & (met["block"] == MAIN_BLOCK)]
            row["D_gcm_baseline_median"], row["D_gcm_baseline_min"], row["D_gcm_baseline_max"] = (
                g["D"].median(), g["D"].min(), g["D"].max())
            rows.append(row)
    return pd.DataFrame(rows)


def criterion(summary, observed):
    """Pre-specified criterion (E1_spec.md section 0b), control pair, operating fleet."""
    c = summary[(summary["h_channel"] == CONTROL[0]) & (summary["t_channel"] == CONTROL[1])
                & (summary["fleet"] == "operating")].set_index("scenario")
    rows = []
    for s in ("ssp370", "ssp585"):
        rows.append({"item": f"primary: P(H and T) A increases in >=4/5 GCMs, {s}", "scenario": s,
                     "value": int(c.loc[s, "k_dP_up"]), "met": bool(c.loc[s, "k_dP_up"] >= 4)})
    rows.append({"item": "primary overall (both SSP3-7.0 and SSP5-8.5)", "scenario": "both",
                 "value": int(min(c.loc["ssp370", "k_dP_up"], c.loc["ssp585", "k_dP_up"])),
                 "met": bool(all(r["met"] for r in rows))})
    for s in SCEN:
        rows.append({"item": f"reinforcing: dD B > 0 with k>=4/5, {s}", "scenario": s,
                     "value": int(c.loc[s, "k_dD_up"]), "met": bool(c.loc[s, "k_dD_up"] >= 4)})
    o = observed[(observed["h_channel"] == CONTROL[0]) & (observed["t_channel"] == CONTROL[1])
                 & (observed["fleet"] == "operating")].iloc[0]
    rows.append({"item": "reinforcing: observed W5E5 D > 1 with block-12 CI excluding 1",
                 "scenario": "observed", "value": float(o["D"]),
                 "met": bool(o["D"] > 1 and o["D_lo_b12"] > 1)})
    return pd.DataFrame(rows)


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    thr = float(load_params()["drought_spei_threshold"]["value"])
    p = pops.load_populations(proc)
    series, models = build_series(proc, p, thr)
    print("models:", models)
    obs_series = build_observed(proc, p, thr)

    rows = []
    for (m, per), ser in series.items():
        months = BASE_MONTHS if per == "baseline" else FUT_MONTHS
        for hc, v in ser["H"].items():
            rows += [("H", "-", hc, m, per, i, months[i], x) for i, x in enumerate(v)]
        for fleet, chans in ser["T"].items():
            for tc, v in chans.items():
                rows += [("T", fleet, tc, m, per, i, months[i], x) for i, x in enumerate(v)]
    for hc, v in obs_series["H"].items():
        rows += [("H", "-", hc, "w5e5", "observed", i, OBS_MONTHS[i], x) for i, x in enumerate(v)]
    for fleet, chans in obs_series["T"].items():
        for tc, v in chans.items():
            rows += [("T", fleet, tc, "w5e5", "observed", i, OBS_MONTHS[i], x) for i, x in enumerate(v)]
    ser_df = pd.DataFrame(rows, columns=["series", "fleet", "channel", "model", "period", "t",
                                         "month", "value"])
    ser_df.to_csv(tab / "e1_hedge_series.csv", index=False, lineterminator="\n")

    met, boots = run_pairs(series, models, Rng())
    delta = delta_rows(met, boots, models)
    summary = summarise(delta)
    observed = observed_rows(obs_series, met, models)
    crit = criterion(summary, observed)
    for name, df in [("metrics", met), ("delta", delta), ("summary", summary),
                     ("criterion", crit), ("observed", observed)]:
        df.to_csv(tab / f"e1_hedge_{name}.csv", index=False, lineterminator="\n")
        print(f"written e1_hedge_{name}.csv ({len(df)} rows)")
    pd.set_option("display.width", 250)
    print(crit.to_string(index=False))


if __name__ == "__main__":
    main()
