"""W3g: TX35 level classes (10/30/60), shift, delta classes, level x delta, cell map.

Aborts before writing if (1) TX35 and delta of thermal units differ from plant_hazards,
(2) share with delta >= 30 or gw_total differ from w3_heat_curves_by_gcm, (3) classes do
not add up to the total or the reference totals (47.67, 109.67, 102.67 GW) fail.
"""

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned

COUNTRY, TOL = "BRA", 1e-9
KEEP = ("hydro", "thermal_water_dependent", "thermal_air_only")
THERMAL_GROUPS = ("all_thermal",) + hl.TECH_THERMAL + hl.FUELS
CATS = {"level_base": hl.LEVEL_LABELS, "level_fut": hl.LEVEL_LABELS,
        "delta_class": hl.DELTA_LABELS}
SPECS = {"w3g_heat_class_shift": ["level_base", "level_fut"],
         "w3g_heat_level_x_delta": ["level_fut", "delta_class"],
         "w3g_heat_change_classes": ["delta_class"]}
KEYS4 = ["group", "fleet", "scenario", "model"]


def find_itaipu(plants):
    named = plants[(plants["country"] == COUNTRY)
                   & plants["plant_name"].str.contains("itaipu", case=False, na=False)]
    big = named[(named["capacity_mw"] - 14000.0).abs() < 1e-6]
    if len(big) != 1:
        raise SystemExit("Itaipu not uniquely identified")
    return set(big["plant_uid"])


def check_hazards(d, proc):
    cols = ["plant_uid", "model", "scenario", "hazard", "baseline_value",
            "future_value", "delta"]
    h = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols)
    h = h[h["hazard"] == "TX35"].drop_duplicates(["plant_uid", "model", "scenario"])
    h = h.rename(columns={"delta": "delta_h"})
    t = d[d["tech_class"] != "hydro"].drop_duplicates(["plant_uid", "model", "scenario"])
    m = t.merge(h, on=["plant_uid", "model", "scenario"], how="left")
    miss = int(m["baseline_value"].isna().sum())
    dif = max(float((m["base"] - m["baseline_value"]).abs().max()),
              float((m["fut"] - m["future_value"]).abs().max()),
              float((m["delta"] - m["delta_h"]).abs().max()))
    print(f"check 1 thermal TX35 vs plant_hazards: rows {len(m)}, missing {miss}, "
          f"max|diff| {dif:.2e}")
    return miss == 0 and dif < TOL


def check_curves(g, tab):
    ref = pd.read_csv(tab / "w3_heat_curves_by_gcm.csv")
    ref = ref[ref["threshold"] == 30][KEYS4 + ["gw_total", "pct_gw"]]
    t = g[g["group"].isin(THERMAL_GROUPS)]
    t = t.assign(mwe=t["capacity_mw"].where(t["delta"] >= 30, 0.0))
    mine = t.groupby(KEYS4).agg(mw=("capacity_mw", "sum"), mwe=("mwe", "sum")).reset_index()
    mine["pct_mine"] = 100.0 * mine["mwe"] / mine["mw"]
    mine["gw_mine"] = mine["mw"] / 1000.0
    m = mine.merge(ref, on=KEYS4, how="outer", indicator=True)
    both = m[m["_merge"] == "both"].copy()
    both["d_pct"] = (both["pct_mine"] - both["pct_gw"]).abs()
    both["d_gw"] = (both["gw_mine"] - both["gw_total"]).abs()
    worst = both.groupby("group")[["d_pct", "d_gw"]].max()
    n_only = len(m) - len(both)
    print(f"check 2 delta>=30 vs w3_heat_curves_by_gcm: both {len(both)}, "
          f"only one side {n_only}")
    print(worst.to_string(float_format=lambda x: f"{x:.2e}"))
    return n_only == 0 and float(worst.max().max()) < TOL


def check_totals(lv, gaps):
    s = lv[(lv["period"] == "future") & (lv["fleet"] == "operating")
           & (lv["scenario"] == "ssp370")].drop_duplicates(["group", "itaipu"])
    s = s.set_index(["group", "itaipu"])["gw_total"]
    got = (s.loc[("all_thermal", "na")], s.loc[("hydro", "a")], s.loc[("hydro", "b")])
    ref = (47.67, 109.67, 102.67)
    print(f"check 3 totals GW thermal/hydro a/hydro b: {[round(x, 3) for x in got]} "
          f"vs {ref}; max class-sum gap (MW) {max(gaps):.2e}")
    return all(abs(a - b) < 0.01 for a, b in zip(got, ref)) and max(gaps) < 1e-6


def show_levels(lv, group, fleet, itaipu):
    s = lv[(lv["group"] == group) & (lv["fleet"] == fleet) & (lv["itaipu"] == itaipu)]
    print(f"\n{group} {fleet} (itaipu {itaipu}): % of GW, median [min-max] over GCMs")
    for sc in ("baseline", "ssp126", "ssp370", "ssp585"):
        r = s[s["scenario"] == sc]
        cells = []
        for c in hl.LEVEL_LABELS:
            x = r[r["class"] == c].iloc[0]
            cells.append(f"{c} {x.pct_median:.1f}[{x.pct_min:.1f}-{x.pct_max:.1f}]")
        print(f"  {sc:8s} " + " | ".join(cells))


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[(units["country"] == COUNTRY) & units["tech_class"].isin(KEEP)]
    units = units.reset_index(drop=True)
    units["uid"] = units.index
    cols = ["plant_uid", "plant_name", "country", "capacity_mw"]
    uv = hl.with_itaipu_versions(units, find_itaipu(pd.read_parquet(proc / "plants.parquet",
                                                                    columns=cols)))
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                         columns=["plant_uid", "cell_lat", "cell_lon"])
    c = ["index", "cell_lat", "cell_lon", "model", "scenario", "period", "value"]
    ix = pd.read_parquet(proc / "indices_daily.parquet", columns=c,
                         filters=[("index", "==", "tx35")])
    cv = hl.cell_values(ix)
    del ix
    d = hl.add_classes(hl.unit_values(uv, pc, cv))
    print(f"units {len(units)}, unit rows {len(d)}, cells {d['cell_lat'].nunique()}")
    ok1 = check_hazards(d, proc)
    g = hl.expand_groups(add_pooled_planned(d))
    ok2 = check_curves(g, tab)

    meta = hl.fleet_meta(g)
    out = {"w3g_heat_level_classes": hl.level_classes_table(g)}
    gaps = []
    for name, cl in SPECS.items():
        t = hl.gw_by_gcm(g, cl, CATS)
        gaps.append(hl.class_sum_gap(t))
        out[name] = hl.summarise_gw(t, cl)
    gaps.append(hl.class_sum_gap(hl.gw_by_gcm(g, ["level_fut"], CATS)))
    ok3 = check_totals(out["w3g_heat_level_classes"], gaps)
    if not (ok1 and ok2 and ok3):
        print("CHECK FAILED: nothing written")
        sys.exit(1)
    print("checks 1-3: PASS")

    for name, tb in out.items():
        tb = tb.merge(meta, on=["group", "fleet", "itaipu"], how="left")
        tb.to_csv(tab / f"{name}.csv", index=False)
        out[name] = tb
        print(f"written: {name}.csv ({len(tb)} rows)")
    ub = uv[uv["itaipu"] != "a"].merge(pc.drop_duplicates("plant_uid"), on="plant_uid")
    cells = ub[["cell_lat", "cell_lon"]].drop_duplicates()
    cm = hl.cell_class_table(cv.merge(cells, on=["cell_lat", "cell_lon"]))
    cm = cm.merge(hl.cell_gw(ub), on=["cell_lat", "cell_lon"], how="left")
    cm.to_csv(tab / "w3g_heat_cell_class.csv", index=False)
    print(f"written: w3g_heat_cell_class.csv ({len(cm)} rows)")

    lv = out["w3g_heat_level_classes"]
    show_levels(lv, "all_thermal", "operating", "na")
    show_levels(lv, "all_thermal", "planned_all", "na")
    show_levels(lv, "hydro", "operating", "b")
    show_levels(lv, "hydro", "operating", "a")
    show_levels(lv, "hydro", "planned_all", "b")
    sel = {"group": "all_thermal", "fleet": "operating", "itaipu": "na", "scenario": "ssp370"}
    for name, idx, col in (("w3g_heat_level_x_delta", "level_fut", "delta_class"),
                           ("w3g_heat_class_shift", "level_base", "level_fut")):
        x = out[name]
        for k, v in sel.items():
            x = x[x[k] == v]
        p = x.pivot(index=idx, columns=col, values="gw_median")
        p = p.reindex(index=hl.LEVEL_LABELS, columns=CATS[col]).round(2)
        print(f"\n{name}: thermal operating SSP370, GW (median over GCMs)\n{p.to_string()}")
    ds = meta[meta["label"] == "descriptive"]
    print(f"\ndescriptive fleets (< {hl.MIN_CELLS} cells): {len(ds)} of {len(meta)}")
    print(ds[ds["fleet"] == "operating"].to_string(index=False))
    print(f"\ncell map: {cm['cell_lat'].nunique()} lat x cells; rows {len(cm)}; "
          f"n_gcm_same < 5 in {int((cm['n_gcm_same'] < 5).sum())} rows")


if __name__ == "__main__":
    main()