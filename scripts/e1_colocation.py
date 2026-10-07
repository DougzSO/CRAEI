"""E1 co-location check (D143): control pair (H_spi x T_spi), thermal restricted to one macro_region.

National hydro share H_t against the share of water-dependent operating thermal capacity in drought
(SPI-12 <= threshold) computed only over the plants of one macro_region. Variant B (own P90 per series),
block-12 moving-block bootstrap for the observed W5E5 series. Same populations, windows and series
builders as scripts/e1_hedge.py; regions via scripts/w3h_state_coexposure.py (assign_state +
add_macro_region). Writes e1_colocation.csv to outputs_tables_dir.
"""

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1_hedge as eh  # noqa: E402
import e1_populations as pops  # noqa: E402
from w3h_state_coexposure import load_macro_map  # noqa: E402

from craei.config import load_params, load_paths  # noqa: E402
from craei.exposure import hedge  # noqa: E402
from craei.geo.state_assignment import add_macro_region, assign_state  # noqa: E402


def region_of_plants(proc, thermal):
    plants = pd.read_parquet(proc / "plants.parquet", columns=["plant_uid", "lat", "lon"])
    sub = plants[plants["plant_uid"].isin(set(thermal["plant_uid"]))]
    admin1 = gpd.read_file(r"..\data\external\geo\natural_earth_brazil.gpkg", layer="brazil_admin1")
    a = assign_state(sub, admin1, lat_col="lat", lon_col="lon", uid_col="plant_uid")
    a = add_macro_region(a, load_macro_map(), postal_col="state_postal")
    return thermal.merge(a[["plant_uid", "macro_region"]], on="plant_uid", how="left")


def spi_series(proc, p, thr, models):
    """H national and per-plant thermal SPI flags for GCM baseline/observed; regional shares built later."""
    hy, th = p["hydro"], p["operating"]
    cells = list(th["cell_id"].drop_duplicates())
    cell_ix = {c: i for i, c in enumerate(cells)}
    row = np.array([cell_ix[c] for c in th["cell_id"]])
    hs = eh.read_spei(proc, "catchment", hy["plant_uid"], models, ["SPI_12"])
    ts = eh.read_spei(proc, "cell", cells, models, ["SPI_12"])
    out = {}
    for m in models:
        h = hs[(hs["model"] == m) & (hs["scenario"] == "historical")]
        t = ts[(ts["model"] == m) & (ts["scenario"] == "historical")]
        hf = eh.pivot(h, hy["plant_uid"], eh.BASE_MONTHS, "SPI_12") <= thr
        tf = (eh.pivot(t, cells, eh.BASE_MONTHS, "SPI_12") <= thr)[row]
        out[m] = (hedge.weighted_share(hf, hy["capacity_mw"]), tf)
    w = pd.read_parquet(proc / "w5e5_hydro_spi12.parquet")
    w = w[w["month"].isin(eh.OBS_MONTHS)]
    tw = pd.read_parquet(proc / "w5e5_thermal_cells_monthly.parquet", columns=["id", "month", "SPI_12"])
    tw = tw[tw["month"].isin(eh.OBS_MONTHS)]
    hf = eh.pivot(w, hy["plant_uid"], eh.OBS_MONTHS, "SPI_12") <= thr
    tf = (eh.pivot(tw, cells, eh.OBS_MONTHS, "SPI_12") <= thr)[row]
    out["w5e5"] = (hedge.weighted_share(hf, hy["capacity_mw"]), tf)
    return out


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    thr = float(load_params()["drought_spei_threshold"]["value"])
    p = pops.load_populations(proc)
    th = region_of_plants(proc, p["operating"])
    assert len(th) == len(p["operating"]) and th["macro_region"].notna().all()
    models = sorted(m for m in pd.read_parquet(proc / "spei.parquet", columns=["model"],
                                              filters=[("scale", "==", "catchment")])["model"].unique())
    ser = spi_series(proc, p, thr, models)
    regions = [*sorted(th["macro_region"].unique()), "ALL"]
    rng = eh.Rng()
    rng.k = 20_000
    rows = []
    for reg in regions:
        sel = (th["macro_region"] == reg).to_numpy() if reg != "ALL" else np.ones(len(th), bool)
        cap = th.loc[sel, "capacity_mw"].to_numpy()
        base = {"region": reg, "n_plants": int(sel.sum()), "gw": cap.sum() / 1000}
        d_gcm = {}
        for m in [*models, "w5e5"]:
            h, tf = ser[m]
            t = hedge.weighted_share(tf[sel], cap)
            est = hedge.joint_metrics(hedge.events(h, hedge.p90_threshold(h)),
                                      hedge.events(t, hedge.p90_threshold(t)))
            d_gcm[m] = est
            if m == "w5e5":
                bt = hedge.bootstrap_period(h, t, "B", None, None, eh.MAIN_BLOCK, eh.N_SIM, rng.next())
                lo, hi = hedge.percentile_ci(bt["D"])
                obs = {"obs_D": est["D"], "obs_D_lo": lo, "obs_D_hi": hi,
                       "obs_P_T_given_H": est["P_T_given_H"], "obs_P_T": est["P_T"]}
        gd = np.array([d_gcm[m]["D"] for m in models])
        rows.append({**base, **obs, "gcm_D_median": np.nanmedian(gd), "gcm_D_min": np.nanmin(gd),
                     "gcm_D_max": np.nanmax(gd),
                     "gcm_P_T_given_H_median": np.nanmedian([d_gcm[m]["P_T_given_H"] for m in models]),
                     "gcm_P_T_median": np.nanmedian([d_gcm[m]["P_T"] for m in models])})
    out = pd.DataFrame(rows)
    out.to_csv(tab / "e1_colocation.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
