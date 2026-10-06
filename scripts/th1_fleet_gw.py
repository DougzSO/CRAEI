"""TH1 fleet/GW aggregation (O39): relative heat threshold days/yr by level class.

Extends TH1 (D91, cell/GCM scope, th1_relative_threshold.csv) to fleet/GW scope,
reusing the TX35 W3g level-class machinery as-is: same LEVEL_CUTS (config-linked,
O38), same Itaipu a/b treatment, same capacity universe. Read-only against
th1_relative_threshold.csv and plant_units/plant_cell/plants; writes
th1_fleet_gw.csv only if both checks pass.

Design approved by the author (chat, before running), per D91s open item:
level classes only (no shift/level-x-delta/cell-map tables -- those were W3g-
specific extras, out of the approved O39 scope).

Checks (fixed before running; same capacity universe as W3g, only the hazard
metric differs, so the reference totals are identical to w3g_heat_levels.py):
  (1) class-sum gap: GW summed over level classes must equal the group/fleet/
      itaipu/scenario total, tolerance 1e-6 MW.
  (2) reference totals (future, operating, ssp370): all_thermal 47.67 GW,
      hydro itaipu-a 109.67 GW, hydro itaipu-b 102.67 GW (D82), tolerance
      0.01 GW.
"""

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned
from craei.hazards import drought_levels as dl

COUNTRY = "BRA"
KEEP = ("hydro", "thermal_water_dependent", "thermal_air_only")
REF_TOTALS = {"all_thermal": 47.67, "hydro_a": 109.67, "hydro_b": 102.67}
TOTAL_TOL = 0.01
GAP_TOL = 1e-6


def check_gaps(g):
    gaps = [hl.class_sum_gap(hl.gw_by_gcm(g, ["level_fut"], {"level_fut": hl.LEVEL_LABELS}))]
    base_g = g[g["scenario"] == "ssp370"]
    gaps.append(hl.class_sum_gap(hl.gw_by_gcm(base_g, ["level_base"], {"level_base": hl.LEVEL_LABELS})))
    worst = max(gaps)
    print(f"check 1 class-sum gap (MW): {worst:.2e}, tol {GAP_TOL:.0e}")
    return worst < GAP_TOL


def check_totals(lv):
    s = lv[(lv["period"] == "future") & (lv["fleet"] == "operating")
           & (lv["scenario"] == "ssp370")].drop_duplicates(["group", "itaipu"])
    s = s.set_index(["group", "itaipu"])["gw_total"]
    got = {
        "all_thermal": float(s.loc[("all_thermal", "na")]),
        "hydro_a": float(s.loc[("hydro", "a")]),
        "hydro_b": float(s.loc[("hydro", "b")]),
    }
    print(f"check 2 reference totals (GW): got {got}")
    print(f"                         want {REF_TOTALS}, tol {TOTAL_TOL}")
    return all(abs(got[k] - REF_TOTALS[k]) < TOTAL_TOL for k in REF_TOTALS)


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])

    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[(units["country"] == COUNTRY) & units["tech_class"].isin(KEEP)]
    units = units.reset_index(drop=True)
    units["uid"] = units.index

    plants = pd.read_parquet(proc / "plants.parquet",
                              columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    itaipu_uids = dl.find_plant(plants, COUNTRY, "itaipu", 14000.0)
    uv = hl.with_itaipu_versions(units, itaipu_uids)

    pc = pd.read_parquet(proc / "plant_cell.parquet",
                          columns=["plant_uid", "cell_lat", "cell_lon"])

    th1_cols = ["cell_lat", "cell_lon", "model", "scenario", "period", "value"]
    th1 = pd.read_csv(tab / "th1_relative_threshold.csv", usecols=th1_cols)
    cv = hl.cell_values(th1)

    d = hl.add_classes(hl.unit_values(uv, pc, cv))
    print(f"units {len(units)}, unit rows {len(d)}, cells {d['cell_lat'].nunique()}")

    g = hl.expand_groups(add_pooled_planned(d))
    meta = hl.fleet_meta(g)
    lv = hl.level_classes_table(g)

    ok1 = check_gaps(g)
    ok2 = check_totals(lv)
    if not (ok1 and ok2):
        print("CHECK FAILED: th1_fleet_gw.csv not written")
        sys.exit(1)
    print("checks 1-2: PASS")

    out = lv.merge(meta, on=["group", "fleet", "itaipu"], how="left")
    out.to_csv(tab / "th1_fleet_gw.csv", index=False)
    print(f"written: th1_fleet_gw.csv ({len(out)} rows)")

    pd.set_option("display.width", 200)
    sel = out[(out["fleet"] == "operating") & (out["itaipu"].isin(["na", "b"]))
              & (out["period"] == "future") & (out["scenario"] == "ssp370")]
    print("\nTH1 level classes, operating, future, ssp370 (% of GW, median [min-max]):")
    for grp in ("all_thermal", "hydro"):
        s = sel[sel["group"] == grp]
        cells = []
        for c in hl.LEVEL_LABELS:
            x = s[s["class"] == c]
            if len(x):
                r = x.iloc[0]
                cells.append(f"{c} {r.pct_median:.1f}[{r.pct_min:.1f}-{r.pct_max:.1f}]")
        print(f"  {grp:12s} " + " | ".join(cells))


if __name__ == "__main__":
    main()
