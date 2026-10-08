"""W5 Table 3 additive version: mean over GCMs per heat x drought cell (A4, D137).

The per-cell median over GCMs (table3_coexposure.csv, C85) is not additive: the 16 medians do
not sum to the fleet total (gap_gw, D80/D96/D97/D99/D106). Here each cell is the MEAN over the 5
GCMs of the GW in that cell, with min and max; the 16 means sum exactly to the fleet total.
The mean differs from the headlines, which use the median (D102, D125). The median per cell
stays in the output as a reference column.

Same per-GCM tables as scripts/archive/w4h_coexposure.py (Itaipu version b for hydro / na for
thermal, block12 null, p50_p90_p99 cuts, canonical pools), except that the water-dependent thermal
population is classified by plant-level class (D151, craei.exposure.plant_class): 618 plants,
39.1015 GW operating. Operating and planned_all fleets, 3 scenarios. Checks before writing: the
hydro median reproduces the previous table3_coexposure.csv (hydro is unchanged by D151); the 16
means sum to gw_total.

Writes outputs_tables_dir/table3_coexposure_gcm_mean.csv (192 rows) and the per-cell median table
table3_coexposure.csv (same 192 rows, columns of C85 plus gap_gw; producer of record since D151,
replacing scripts/archive/w5_table3_coexposure.py).
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "archive"))
import w4h_coexposure as w4h  # noqa: E402

from craei.config import load_paths  # noqa: E402
from craei.countries import iso as country_iso  # noqa: E402
from craei.exposure import heat_levels as hl  # noqa: E402
from craei.exposure.heat_fuel import add_pooled_planned  # noqa: E402
from craei.exposure.plant_class import plant_class_filter  # noqa: E402
from craei.hazards import drought_levels as dl  # noqa: E402

COUNTRY = country_iso()
CUTSET = "p50_p90_p99"
FLEETS = ["operating", "planned_all"]
ITAIPU = {"hydro": "b", "thermal_water_dependent": "na"}
SUM_TOL_GW, V1_TOL_GW = 1e-9, 1e-6
OUT_NAME = "table3_coexposure_gcm_mean.csv"
KEYS = ["group", "fleet", "itaipu", "scenario"]
CELL = KEYS + ["heat_class", "drought_class"]
MEDIAN_COLS = ["group", "fleet", "itaipu", "scenario", "heat_class", "drought_class", "n_gcm", "gw_total",
               "gw_min", "gw_median", "gw_max", "pct_min", "pct_median", "pct_max", "pool", "null", "cutset",
               "cut1", "cut2", "cut3", "canonical", "gap_gw"]


def per_gcm_tables(paths):
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    units = w4h.load_units(proc)
    bucket = (pd.read_parquet(proc / "plant_hazards.parquet", columns=["plant_uid", "bucket"])
              .drop_duplicates("plant_uid").set_index("plant_uid")["bucket"])
    units, dropped = plant_class_filter(units, bucket)
    print(f"plant-level class: {dropped['plant_uid'].nunique()} plants / {len(dropped)} units / "
          f"{dropped['capacity_mw'].sum():.1f} MW leave the water-dependent population")
    fd = pd.read_csv(tab / "w4g_fd_unit_values.csv")
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    uv = hl.with_itaipu_versions(units, dl.find_plant(plants, COUNTRY, "itaipu", 14000.0))
    d = dl.unit_drought_frame(uv, fd)
    heat = pd.concat([w4h.thermal_tx35(proc, units), w4h.hydro_tx35(proc, units)],
                     ignore_index=True)
    d = d.merge(heat, on=["plant_uid", "model", "scenario"], how="left")
    assert not d[["base_tx35", "fut_tx35"]].isna().any().any()
    d["heat_class"] = hl.classify(d["fut_tx35"], hl.LEVEL_CUTS, hl.LEVEL_LABELS)
    d = add_pooled_planned(d)
    w4g_pct = pd.read_csv(tab / "w4g_null_percentiles.csv")
    parts = []
    for grp, pool in w4h.GROUPS.items():
        g = d[(d["group"] == grp) & d["fleet"].isin(FLEETS) & (d["itaipu"] == ITAIPU[grp])]
        cuts = w4h.cuts_block12(w4g_pct, pool, dl.CUTSETS[CUTSET])
        sub = g.assign(drought_class=dl.classify_fd(g["future_value"], cuts))
        t = hl.gw_by_gcm(sub, ["heat_class", "drought_class"], w4h.JOINT_CATS)
        parts.append(t.assign(pool=pool, cut1=cuts[0], cut2=cuts[1], cut3=cuts[2]))
    t = pd.concat(parts, ignore_index=True)
    t["gw"] = t["mw"] / 1000.0
    t["gw_total"] = t["mw_total"] / 1000.0
    # denominator population of the percentages: unit rows and plants of the group / fleet / Itaipu version
    sel = d[d["group"].isin(w4h.GROUPS) & d["fleet"].isin(FLEETS)]
    sel = sel[sel["itaipu"] == sel["group"].map(ITAIPU)]
    cnt = (sel[sel["model"] == sel["model"].iloc[0]].groupby(KEYS)
           .agg(n_units=("plant_uid", "size"), n_plants=("plant_uid", "nunique")).reset_index())
    return t.merge(cnt, on=KEYS, how="left")


def summarise(t):
    t = t.assign(pct=100.0 * t["gw"] / t["gw_total"])
    g = t.groupby(CELL + ["pool", "cut1", "cut2", "cut3"])
    out = g.agg(n_gcm=("model", "nunique"), gw_total=("gw_total", "first"),
                n_units=("n_units", "first"), n_plants=("n_plants", "first"),
                gw_mean=("gw", "mean"), gw_min=("gw", "min"), gw_max=("gw", "max"),
                gw_median=("gw", "median"), pct_mean=("pct", "mean"), pct_median=("pct", "median"),
                pct_min=("pct", "min"), pct_max=("pct", "max")).reset_index()
    return out


def main():
    paths = load_paths()
    out = summarise(per_gcm_tables(paths))
    assert len(out) == 192 and out["n_gcm"].eq(5).all(), (len(out), out["n_gcm"].unique())
    s = out.groupby(KEYS).agg(total=("gw_total", "first"), mean_sum=("gw_mean", "sum"),
                              median_sum=("gw_median", "sum"))
    assert len(s) == 12
    assert (s["mean_sum"] - s["total"]).abs().max() < SUM_TOL_GW, "means do not sum to total"
    out = out.merge(s["total"].rename("t").reset_index().merge(
        s["median_sum"].reset_index())[KEYS + ["t", "median_sum"]], on=KEYS)
    out["gap_gw_median"] = out["t"] - out["median_sum"]
    out = out.drop(columns=["t", "median_sum"])
    ref = pd.read_csv(Path(paths["outputs_tables_dir"]) / "table3_coexposure.csv")
    ref = ref[ref["canonical"] & (ref["pool"] == ref["group"].map(w4h.GROUPS)) & (ref["group"] == "hydro")]
    m = out.merge(ref[CELL + ["gw_median", "gap_gw"]], on=CELL, suffixes=("", "_ref"))
    assert len(m) == 96  # hydro rows only: the thermal population changed (D151)
    assert (m["gw_median"] - m["gw_median_ref"]).abs().max() < V1_TOL_GW, "median != Table 3"
    assert (m["gap_gw_median"] - m["gap_gw"]).abs().max() < V1_TOL_GW, "gap != Table 3"
    out["null"], out["cutset"], out["canonical"] = "block12", CUTSET, True
    path = Path(paths["outputs_tables_dir"]) / OUT_NAME
    out.to_csv(path, index=False, lineterminator="\n")
    med = out.assign(gap_gw=out["gap_gw_median"])[MEDIAN_COLS]
    med.to_csv(path.with_name("table3_coexposure.csv"), index=False, lineterminator="\n")
    print("hydro median reproduces the previous table3_coexposure.csv; means sum to fleet total. "
          "written:", path, "and table3_coexposure.csv")


if __name__ == "__main__":
    main()
