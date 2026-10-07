"""Phase 6, item 3: non-monotonic cases (SSP3-7.0 below SSP1-2.6), decomposed by GCM and by plant.

Cases (operating fleet unless noted, Itaipu b for hydro):
  T2_reservoir    Table 2 reservoir bucket: raw share with SPEI-12 R_D >= 2 (capacity weighted)
  HYDRO_SPI       hydro excess over null, SPI-12 (D125): raw share R_D >= 2
  HYDRO_COEXT     hydro extreme heat x extreme drought (Table 3 cell, Fig 5a national)
  F5A_<state>     Fig 5a states whose median share falls from SSP1-2.6 to SSP3-7.0
  PLANNED_SPEI    planned_adv / planned_early hydro excess (D102 planned rows)
For each case: share per GCM and scenario (so the median over GCMs is traceable) and the plants that
carry the GCM-level change. Same units, fleets, cuts and classes as scripts/w3h_state_coexposure.py
(block12 cuts) and scripts/w4b_excess_over_null.py. Writes w6_nonmono_gcm.csv, w6_nonmono_plants.csv.
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import w3h_state_coexposure as w3h  # noqa: E402
import w4c_spi_vs_spei as w4c  # noqa: E402

from craei.config import load_paths  # noqa: E402
from craei.exposure import heat_levels as hl  # noqa: E402
from craei.exposure.heat_fuel import add_pooled_planned  # noqa: E402
from craei.geo.state_assignment import add_macro_region, assign_state  # noqa: E402
from craei.hazards import drought_levels as dl  # noqa: E402

S1, S3 = "ssp126", "ssp370"
GCM_ROWS, PLANT_ROWS = [], []


def share_by_gcm(u, flag, key):
    """Capacity share (%) of `flag` per GCM and scenario within `u` (one case)."""
    g = u.groupby(["model", "scenario"])
    tot = g["capacity_mw"].sum()
    fl = u[flag].astype(bool)
    mw = u.assign(_f=u["capacity_mw"] * fl).groupby(["model", "scenario"])["_f"].sum()
    n = u.assign(_n=fl).groupby(["model", "scenario"])["_n"].sum()
    out = pd.DataFrame({"gw_total": tot / 1000.0, "gw_flagged": mw / 1000.0, "n_units_flagged": n,
                        "n_units": g.size(), "share_pct": 100 * mw / tot}).reset_index()
    out.insert(0, "case", key)
    return out


def plant_changes(u, flag, key, models):
    for m in models:
        a = u[(u["model"] == m) & (u["scenario"] == S1)].groupby("plant_uid").agg(
            cap=("capacity_mw", "sum"), f1=(flag, "max"))
        b = u[(u["model"] == m) & (u["scenario"] == S3)].groupby("plant_uid").agg(f3=(flag, "max"))
        # plant-level flag when all units flagged (units of one plant share the plant value)
        j = a.join(b)
        j["delta_mw"] = j["cap"] * (j["f3"].astype(int) - j["f1"].astype(int))
        names = u.drop_duplicates("plant_uid").set_index("plant_uid")["plant_name"]
        j["plant_name"] = names.reindex(j.index).to_numpy()
        j = j[j["delta_mw"] != 0].sort_values("delta_mw")
        net = j["delta_mw"].sum()
        for uid, r in pd.concat([j.head(4), j.tail(4)]).drop_duplicates().iterrows():
            PLANT_ROWS.append({"case": key, "model": m, "plant_uid": uid, "plant_name": r["plant_name"],
                               "capacity_mw": r["cap"], "flag_ssp126": bool(r["f1"]),
                               "flag_ssp370": bool(r["f3"]), "delta_mw": r["delta_mw"],
                               "net_delta_mw_all_plants": net,
                               "n_plants_changed": len(j)})


def add_case(u, flag, key):
    s = share_by_gcm(u, flag, key)
    GCM_ROWS.append(s)
    piv = s.pivot(index="model", columns="scenario", values="share_pct")
    med = piv.median()
    print(f"\n[{key}] median over GCMs: " + ", ".join(f"{c}={med[c]:.2f}" for c in piv.columns)
          + f" | gw_total {s['gw_total'].iloc[0]:.3f}, plants {u['plant_uid'].nunique()}")
    print(piv.round(2).to_string())
    plant_changes(u, flag, key, list(piv.index))
    return piv


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    units = w3h.load_units(proc)
    fd = pd.read_csv(tab / "w4g_fd_unit_values.csv")
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw", "lat", "lon"])
    bra = plants[plants["country"] == "BRA"]
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, "BRA", "itaipu", 14000.0))
    d = dl.unit_drought_frame(uv, fd)
    heat = pd.concat([w3h.thermal_tx35(proc, units), w3h.hydro_tx35(proc, units)], ignore_index=True)
    d = d.merge(heat, on=["plant_uid", "model", "scenario"], how="left")
    assert not d[["base_tx35", "fut_tx35"]].isna().any().any()
    d["heat_class"] = hl.classify(d["fut_tx35"], hl.LEVEL_CUTS, hl.LEVEL_LABELS)
    d = add_pooled_planned(d)
    d = d.merge(bra[["plant_uid", "plant_name"]], on="plant_uid", how="left")
    w4g_pct = pd.read_csv(tab / "w4g_null_percentiles.csv")
    cuts = w3h.cuts_block12(w4g_pct, "catchment")
    h = d[d["group"] == "hydro"].copy()
    h["drought_class"] = dl.classify_fd(h["future_value"], cuts)
    h["co_extreme"] = (h["heat_class"] == "extreme") & (h["drought_class"] == "extreme")
    h["rd_ge2"] = h["ratio"].notna() & (h["ratio"] >= 2.0)
    bucket = (pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
              .drop_duplicates("plant_uid").set_index("plant_uid")["bucket"])
    h["bucket"] = h["plant_uid"].map(bucket)

    op = h[(h["fleet"] == "operating") & (h["itaipu"] == "b")]
    add_case(op[op["bucket"] == "hydro_reservoir"], "rd_ge2", "T2_reservoir")
    add_case(op, "co_extreme", "HYDRO_COEXT")

    uh = uv[uv["tech_class"] == "hydro"]
    spi = w4c.load_fd(proc, uh["plant_uid"].unique(), "f_d_spi12", ["hydro_reservoir", "hydro_run_of_river"])
    dsp = dl.unit_drought_frame(uh, spi)
    dsp = dsp[(dsp["fleet"] == "operating") & (dsp["itaipu"] == "b")].merge(
        bra[["plant_uid", "plant_name"]], on="plant_uid", how="left")
    dsp["rd_ge2"] = dsp["ratio"].notna() & (dsp["ratio"] >= 2.0)
    add_case(dsp, "rd_ge2", "HYDRO_SPI")

    for fl in ("planned_adv", "planned_early"):
        pl = h[(h["fleet"] == fl) & (h["itaipu"] == "b")]
        add_case(pl, "rd_ge2", f"PLANNED_SPEI_{fl}")

    admin1 = gpd.read_file(r"..\data\external\geo\natural_earth_brazil.gpkg", layer="brazil_admin1")
    a = assign_state(bra[bra["plant_uid"].isin(set(op["plant_uid"]))], admin1,
                     lat_col="lat", lon_col="lon", uid_col="plant_uid")
    a = add_macro_region(a, w3h.load_macro_map(), postal_col="state_postal")
    ops = op.merge(a[["plant_uid", "state_postal"]], on="plant_uid", how="left")
    for st in ("AL", "BA", "GO", "MS", "PI", "TO"):
        add_case(ops[ops["state_postal"] == st], "co_extreme", f"F5A_{st}")

    pd.concat(GCM_ROWS, ignore_index=True).to_csv(tab / "w6_nonmono_gcm.csv", index=False, lineterminator="\n")
    pl = pd.DataFrame(PLANT_ROWS)
    pl.to_csv(tab / "w6_nonmono_plants.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    for key in ("T2_reservoir", "HYDRO_SPI", "HYDRO_COEXT"):
        x = pl[pl["case"] == key]
        print(f"\n--- plants, {key} ---")
        print(x[["model", "plant_name", "capacity_mw", "flag_ssp126", "flag_ssp370", "delta_mw",
                 "net_delta_mw_all_plants", "n_plants_changed"]].round(0).to_string(index=False))


if __name__ == "__main__":
    main()
