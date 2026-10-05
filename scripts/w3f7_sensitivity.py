"""W3f-7: planned-operating contrast under TX40 and under plant-count weighting.

Reuses heat_fuel.planned_vs_operating() exactly as already used for the TX35/GW-weight
reference in scripts/w3_heat_fuel.py (producing w3_heat_planned_vs_operating.csv). This
script applies the same function to two alternatives already validated elsewhere in the
sensitivity register (w3_heat_sensitivity.csv, choices metric_TX40 and weight_plant_count,
scripts/w3_sensitivity.py): (a) TX40 hazard instead of TX35, same GW weight; (b) TX35
hazard, plant-count weight instead of GW (heat_sensitivity.plant_weighted). No new hazard
metric or weighting scheme is introduced here; this only extends an existing comparison
(share of exposed GW) to the planned-vs-operating contrast, which neither w3_heat_fuel.py
nor w3_sensitivity.py reports for these two alternatives.

Checks before writing (abort otherwise, tol 1e-6 unless noted):
  (1) reference reconstruction (TX35, GW weight) reproduces w3_heat_planned_vs_operating.csv
      row for row (diff_min/median/max, gw_planned; n_gcm and n_planned_ge exact match).
  (2) TX40 curves (hf.exposure_curves on the TX40 hazard, full THRESHOLDS grid) reproduce
      the summarised shares already checked into w3_heat_sensitivity.csv under
      choice == "metric_TX40" (pct_min/median/max), at every shared key.
  (3) plant-count-weighted curves (TX35 hazard, heat_sensitivity.plant_weighted) reproduce
      w3_heat_sensitivity.csv under choice == "weight_plant_count", same way.
  (4) row counts of the two new planned-vs-operating tables match the reference table's
      row count (same shape, different inputs).

Writes (only if all checks pass): w3f7_planned_vs_operating.csv, long format, column
`choice` in {reference, metric_TX40, weight_plant_count}, same columns as
heat_fuel.planned_vs_operating() output.
"""

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf
from craei.exposure import heat_sensitivity as hs

TOL = 1e-6
GROUPS = ("fuel_class", "tech_class", None)


def curves_for(df, groups=GROUPS):
    return pd.concat([hf.exposure_curves(df, g) for g in groups], ignore_index=True)


def pvo_for(curves):
    return pd.concat(
        [hf.planned_vs_operating(curves, p) for p in hf.PLANNED_FLEETS],
        ignore_index=True,
    )


def check_reference_pvo(pvo_ref, tables):
    old = pd.read_csv(tables / "w3_heat_planned_vs_operating.csv")
    key = ["planned_fleet", "group", "scenario", "threshold"]
    m = pvo_ref.merge(old, on=key, how="inner", suffixes=("", "_old"), validate="one_to_one")
    d = max(float((m[c] - m[c + "_old"]).abs().max())
            for c in ("gw_planned", "diff_min", "diff_median", "diff_max"))
    int_ok = bool((m["n_gcm"] == m["n_gcm_old"]).all()
                  and (m["n_planned_ge"] == m["n_planned_ge_old"]).all())
    ok = len(m) == len(pvo_ref) == len(old) and d <= TOL and int_ok
    print(f"check (1) reference pvo vs w3_heat_planned_vs_operating.csv: "
          f"{len(m)}/{len(pvo_ref)} rows (file {len(old)}), max|diff| {d:.2e}, "
          f"int cols match: {int_ok}")
    return ok


def check_curve_choice(curves, tables, choice):
    mine = hf.summarise_gcms(curves)
    ref = pd.read_csv(tables / "w3_heat_sensitivity.csv")
    ref = ref[ref["choice"] == choice]
    m = mine.merge(ref, on=hf.KEY, how="inner", suffixes=("", "_sens"), validate="one_to_one")
    d = max(float((m[c] - m[f"{c}_alt"]).abs().max())
            for c in ("pct_min", "pct_median", "pct_max"))
    ok = len(m) == len(mine) == len(ref) and d <= TOL
    print(f"check curves vs w3_heat_sensitivity.csv choice={choice}: "
          f"{len(m)}/{len(mine)} rows (file {len(ref)}), max|diff| {d:.2e}")
    return ok


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    tables = Path(paths["outputs_tables_dir"])

    units = pd.read_parquet(proc / "plant_units.parquet")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(proc / "plant_hazards.parquet", columns=cols,
                          filters=[("hazard", "in", ["TX35", "TX40"])])

    df35 = hf.add_pooled_planned(hf.build_unit_hazard(units, haz, "TX35"))
    df40 = hf.add_pooled_planned(hf.build_unit_hazard(units, haz, "TX40"))

    curves_ref = curves_for(df35)
    pvo_ref = pvo_for(curves_ref)
    ok1 = check_reference_pvo(pvo_ref, tables)

    curves_tx40 = curves_for(df40)
    ok2 = check_curve_choice(curves_tx40, tables, "metric_TX40")

    curves_pw = pd.concat(
        [hf.exposure_curves(hs.plant_weighted(df35, g), g) for g in GROUPS],
        ignore_index=True,
    )
    ok3 = check_curve_choice(curves_pw, tables, "weight_plant_count")

    if not (ok1 and ok2 and ok3):
        print("CHECK FAILED: nothing written")
        sys.exit(1)

    pvo_tx40 = pvo_for(curves_tx40)
    pvo_pw = pvo_for(curves_pw)

    ok4 = len(pvo_tx40) == len(pvo_ref) and len(pvo_pw) == len(pvo_ref)
    print(f"check (4) row counts: reference {len(pvo_ref)}, TX40 {len(pvo_tx40)}, "
          f"plant-weight {len(pvo_pw)}")
    if not ok4:
        print("CHECK FAILED (4): nothing written")
        sys.exit(1)
    print("checks (1)-(4): PASS")

    out = pd.concat([
        pvo_ref.assign(choice="reference"),
        pvo_tx40.assign(choice="metric_TX40"),
        pvo_pw.assign(choice="weight_plant_count"),
    ], ignore_index=True)
    out.to_csv(tables / "w3f7_planned_vs_operating.csv", index=False)
    print(f"\nwritten: w3f7_planned_vs_operating.csv ({len(out)} rows)")

    pd.set_option("display.width", 250)
    sel = out[(out["group"] == "all_thermal") & (out["planned_fleet"] == "planned_all")
              & (out["threshold"] == 30)]
    show = ["choice", "scenario", "gw_planned", "diff_min", "diff_median", "diff_max",
            "n_gcm", "n_planned_ge"]
    print("\nHeadline, all thermal, planned_all - operating, threshold 30, by choice:")
    print(sel[show].round(2).to_string(index=False))


if __name__ == "__main__":
    main()
