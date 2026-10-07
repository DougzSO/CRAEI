"""E3: W5E5 SPEI-12 / SPI-12 against ONS ENA by submarket approximation (D144).

ENA bruta (MWmed, daily, ONS subsystems N, NE, S, SE) -> monthly mean -> anomaly standardized by
calendar month (mean and sd of the same calendar month over 2000-2019). Regions: macro_region as an
approximation of the submarket (Sudeste + Centro-Oeste against ONS SE, i.e. SE/CO). Index: SPEI-12 and
SPI-12 of W5E5, capacity-weighted over the operating hydro plants of the region (E1 population, Itaipu b).
Lag L: index at t-L against ENA anomaly at t, L = 0..6, all reported. Spearman, moving-block bootstrap
(block 12, 2,000 resamples, seed [23, 4, k]).

Writes ena_monthly.parquet (processed_dir) and e3_spearman.csv, e3_regional_series.csv,
e3_episodes.csv (outputs_tables_dir). No hit-rate statistic is computed here (D144).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1_colocation as col  # noqa: E402
import e1_populations as pops  # noqa: E402

from craei.config import load_paths  # noqa: E402
from craei.exposure import hedge  # noqa: E402

MONTHS = pd.date_range("2000-01-01", "2019-12-01", freq="MS")
REGION_TO_ONS = {"Sudeste": "SE", "Centro-Oeste": "SE", "Sul": "S", "Nordeste": "NE", "Norte": "N"}
GROUPS = ["SE/CO", "S", "NE", "N"]
LAGS = range(7)
BLOCK, N_SIM = 12, 2000


def ena_monthly(raw_dir):
    fs = sorted((raw_dir / "validation" / "ons_ena").glob("ENA_Diario_por_Subsistema-*.csv"))
    d = pd.concat([pd.read_csv(f, sep=";", parse_dates=["ena_data"]) for f in fs], ignore_index=True)
    d["id_subsistema"] = d["id_subsistema"].str.strip()
    assert set(d["id_subsistema"]) == {"N", "NE", "S", "SE"}
    d["month"] = d["ena_data"].dt.to_period("M").dt.to_timestamp()
    m = d.groupby(["id_subsistema", "month"], as_index=False).agg(
        ena_mwmed=("ena_bruta_regiao_mwmed", "mean"), n_days=("ena_data", "nunique"))
    m = m[m["month"] <= "2019-12-01"]
    ref = m[m["month"] >= "2000-01-01"].copy()
    ref["cal"] = ref["month"].dt.month
    st = ref.groupby(["id_subsistema", "cal"])["ena_mwmed"].agg(["mean", "std"]).reset_index()
    ref = ref.merge(st, on=["id_subsistema", "cal"])
    ref["ena_anom"] = (ref["ena_mwmed"] - ref["mean"]) / ref["std"]
    return ref[["id_subsistema", "month", "ena_mwmed", "n_days", "ena_anom"]]


def hydro_regional(proc, thr_dummy=None):
    p = pops.load_populations(proc)
    hy = col.region_of_plants(proc, p["hydro"])
    assert len(hy) == len(p["hydro"]) and hy["macro_region"].notna().all()
    hy["grp"] = hy["macro_region"].map(REGION_TO_ONS).replace({"SE": "SE/CO"})
    w = pd.read_parquet(proc / "spei_w5e5.parquet", columns=["id", "month", "SPEI_12"])
    s = pd.read_parquet(proc / "w5e5_hydro_spi12.parquet")
    idx = pd.date_range("1984-01-01", "2019-12-01", freq="MS")
    out = {}
    for name, df, col_ in (("SPEI_12", w, "SPEI_12"), ("SPI_12", s, "SPI_12")):
        df = df[df["id"].isin(set(hy["plant_uid"]))]
        mat = df.pivot(index="id", columns="month", values=col_).reindex(index=list(hy["plant_uid"]))
        mat = mat.reindex(columns=MONTHS)
        for g in GROUPS:
            sel = (hy["grp"] == g).to_numpy()
            x = mat.to_numpy()[sel]
            wt = hy.loc[sel, "capacity_mw"].to_numpy()
            assert not np.isnan(x).any(), (name, g)
            out[(name, g)] = (wt[:, None] * x).sum(0) / wt.sum()
    caps = hy.groupby("grp").agg(n_plants=("plant_uid", "size"), gw=("capacity_mw", lambda c: c.sum() / 1000))
    del idx
    return out, caps


def spearman(x, y):
    rx, ry = rankdata(x), rankdata(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def boot_rho(x, y, rng):
    ix = hedge.mbb_indices(len(x), BLOCK, N_SIM, rng)
    r = np.array([spearman(x[i], y[i]) for i in ix])
    return hedge.percentile_ci(r)


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    ena = ena_monthly(Path(paths["raw_dir"]))
    ena.to_parquet(proc / "ena_monthly.parquet", index=False)
    assert ena.groupby("id_subsistema")["month"].count().eq(240).all()
    series, caps = hydro_regional(proc)
    print(caps.round(2).to_string())
    ena_g = {"SE/CO": "SE", "S": "S", "NE": "NE", "N": "N"}
    rows, ser_rows = [], []
    k = 0
    for g in GROUPS:
        e = ena[ena["id_subsistema"] == ena_g[g]].set_index("month").loc[MONTHS, "ena_anom"].to_numpy()
        for name in ("SPEI_12", "SPI_12"):
            x = series[(name, g)]
            ser_rows += [{"group": g, "index": name, "month": m, "index_value": v, "ena_anom": a}
                         for m, v, a in zip(MONTHS, x, e)]
            for L in LAGS:
                xs, ys = x[: len(x) - L], e[L:]
                ok = np.isfinite(xs) & np.isfinite(ys)
                xs, ys = xs[ok], ys[ok]
                lo, hi = boot_rho(xs, ys, np.random.default_rng([23, 4, k]))
                k += 1
                rows.append({"group": g, "index": name, "lag": L, "n": int(len(xs)),
                             "rho": spearman(xs, ys), "ci_lo": lo, "ci_hi": hi,
                             "ci_excludes_0": bool(lo > 0 or hi < 0),
                             "gw": float(caps.loc[g, "gw"]), "n_plants": int(caps.loc[g, "n_plants"])})
    res, ser = pd.DataFrame(rows), pd.DataFrame(ser_rows)
    res.to_csv(tab / "e3_spearman.csv", index=False, lineterminator="\n")
    ser.to_csv(tab / "e3_regional_series.csv", index=False, lineterminator="\n")
    ep = ser[ser["month"].dt.year.isin([2001, 2014, 2015])].copy()
    ep["year"] = ep["month"].dt.year
    ep = ep.groupby(["group", "index", "year"], as_index=False).agg(
        index_mean=("index_value", "mean"), index_min=("index_value", "min"),
        ena_anom_mean=("ena_anom", "mean"), ena_anom_min=("ena_anom", "min"))
    ep.to_csv(tab / "e3_episodes.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 220)
    print(res.round(3).to_string(index=False))
    print(ep.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
