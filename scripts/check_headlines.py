"""Regression gate: verify the headline numbers of the C87 state.

Reads production tables via `craei.config.load_paths`; prints PASS/FAIL per
item and exits non-zero if any item fails. Sources and definitions:
 - D102/W4b hydro: w4b_excess_over_null.csv, operating, Itaipu b, block12.
 - D125/W4c thermal: w4c_spi_vs_spei.csv, thermal_water_dependent, operating, block12.
 - Table 1: article/tables/table1_fleet_capacity.csv.
 - Fig 1: plants.parquet x plant_cell.parquet x w3g_heat_cell_class.csv (ssp585).
 - Fig 3: w4g_fd_unit_values.csv, per-plant median ratio over GCMs >= 2.0.

The Fig 1 and Fig 3 definitions were reconstructed after the original figure
scripts were lost (_tmp_* removed after use). They are not necessarily identical
to the original generation logic: they are a continuity regression from C88,
not proof that they replicate the pipeline that produced the C87 PNGs.
"""

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.countries import iso as country_iso

TOL = 1e-3
SCEN = ["ssp126", "ssp370", "ssp585"]
RD_EXPOSED = 2.0
THERMAL = ["thermal_water_dependent", "thermal_air_only"]
# Fleet capacity (GW) the state tables must add up to. Thermal: plant-level cooling class, 618 plants (D151).
STATE_FLEET_GW = {"hydro": 102.667, "thermal": 39.1015}

RESULTS = []


def check(name, got, want, tol=TOL):
    ok = len(got) == len(want) and all(abs(g - w) <= tol for g, w in zip(got, want))
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got {list(got)} want {list(want)}")


def excess(df, **filt):
    sel = df
    for k, v in filt.items():
        sel = sel[sel[k] == v]
    sel = sel.set_index("scenario").loc[SCEN]
    return [round(float(v), 2) for v in sel["excess_pp_median"]]


def main():
    paths = load_paths()
    tdir = Path(paths["outputs_tables_dir"])
    proc = Path(paths["processed_dir"])
    art_tables = Path(paths["outputs_dir"]) / "article" / "tables"

    w4b = pd.read_csv(tdir / "w4b_excess_over_null.csv")
    check("D102 W4b hydro operating, Itaipu b, block12 (pp)",
          excess(w4b, fleet="operating", itaipu="b", null_type="block_bootstrap_12"),
          [40.75, 43.20, 53.94])

    w4c = pd.read_csv(tdir / "w4c_spi_vs_spei.csv")
    base = dict(group="thermal_water_dependent", fleet="operating",
                null_type="block_bootstrap_12")
    check("D125 W4c thermal SPEI (pp)", excess(w4c, hazard="spei", **base),
          [20.63, 28.50, 48.06])
    check("D125 W4c thermal SPI (pp)", excess(w4c, hazard="spi", **base),
          [-1.08, 5.44, 27.50])

    t1 = pd.read_csv(art_tables / "table1_fleet_capacity.csv")
    hydro = t1[(t1["Fleet"] == "Operating") & (t1["Technology"] == "Hydro")]
    check("Table 1 hydro operating (GW)", [hydro["Capacity (GW)"].sum()], [102.667])
    gas = t1[(t1["Fleet"] == "Planned (all stages)")
             & (t1["Technology"] == "Thermal (water-dependent)")
             & (t1["Fuel"] == "Natural gas")]
    check("Table 1 water-dependent gas planned (GW)", [gas["Capacity (GW)"].sum()],
          [39.354])

    check("table3_coexposure.csv rows", [len(pd.read_csv(tdir / "table3_coexposure.csv"))],
          [192], tol=0)
    fd = pd.read_csv(tdir / "w4g_fd_unit_values.csv")
    check("w4g_fd_unit_values.csv rows", [len(fd)], [13815], tol=0)

    med = fd.groupby(["scenario", "plant_uid"])["ratio"].median().reset_index()
    exposed = (med["ratio"] >= RD_EXPOSED).groupby(med["scenario"]).sum()
    check("Fig 3 exposed plants (ssp126/370/585)", [int(exposed[s]) for s in SCEN],
          [339, 433, 770], tol=0)

    plants = pd.read_parquet(proc / "plants.parquet")
    thermal = plants[(plants["country"] == country_iso()) & plants["tech_class"].isin(THERMAL)]
    pc = pd.read_parquet(proc / "plant_cell.parquet").drop_duplicates("plant_uid")
    cc = pd.read_csv(tdir / "w3g_heat_cell_class.csv")
    cc = cc[cc["scenario"] == "ssp585"]
    j = thermal.merge(pc, on="plant_uid").merge(cc, on=["cell_lat", "cell_lon"])
    check("Fig 1 thermal plants joined", [len(thermal), len(j)], [745, 745], tol=0)
    check("Fig 1 thermal in extreme cell, ssp585",
          [int((j["class_median"] == "extreme").sum())], [340], tol=0)

    # O49: the states of w3h_state_coexposure.csv must add up to the fleet (gw_total was 5x before D149).
    st = pd.read_csv(tdir / "w3h_state_coexposure.csv")
    st = st[(st["fleet"] == "operating") & (st["null"] == "block12") & (st["co_class"] == "co_extreme")]
    for grp, itaipu, want in (("hydro", "b", STATE_FLEET_GW["hydro"]),
                              ("thermal_water_dependent", "na", STATE_FLEET_GW["thermal"])):
        s = st[(st["group"] == grp) & (st["itaipu"] == itaipu)].groupby("scenario")["gw_total"].sum()
        check(f"w3h states sum gw_total, {grp} operating (GW, ssp126/370/585)",
              [round(float(s[x]), 4) for x in SCEN], [want] * 3)

    t3 = pd.read_csv(tdir / "table3_coexposure.csv")
    t3 = t3[(t3["group"] == "thermal_water_dependent") & (t3["fleet"] == "operating")]
    check("Table 3 thermal operating fleet (GW, 16 cells x 3 scenarios)",
          [round(float(t3["gw_total"].min()), 4), round(float(t3["gw_total"].max()), 4)],
          [STATE_FLEET_GW["thermal"]] * 2)

    n_fail = RESULTS.count(False)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} PASS")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
