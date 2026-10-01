"""W3f-4: Axis 1 sensitivities (TX40, plant-count weight) against the W3a reference."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.exposure import heat_fuel as hf
from craei.exposure import heat_sensitivity as hs

GROUPS = ("fuel_class", "tech_class", None)
SCEN = ("ssp126", "ssp370", "ssp585")


def summary_for(df, weighted=False):
    parts = []
    for g in GROUPS:
        d = hs.plant_weighted(df, g) if weighted else df
        parts.append(hf.exposure_curves(d, g))
    return hf.summarise_gcms(pd.concat(parts, ignore_index=True))


def check_ref(ref, tables):
    old = pd.read_csv(tables / "w3_heat_summary.csv")
    m = ref.merge(old, on=hf.KEY, suffixes=("", "_old"), validate="one_to_one")
    d = max(float((m[c] - m[c + "_old"]).abs().max())
            for c in ("pct_min", "pct_median", "pct_max"))
    print(f"check reference vs w3_heat_summary: {len(m)}/{len(ref)} rows "
          f"(file {len(old)}), max |diff| {d:.2e}")
    return len(m) == len(ref) == len(old) and d <= 1e-6


def cell(summ, group, fleet, th):
    sub = summ[(summ["group"] == group) & (summ["fleet"] == fleet)
               & (summ["threshold"] == th)].set_index("scenario")
    out = {}
    for s in SCEN:
        r = sub.loc[s]
        out[s] = f"{r['pct_median']:.1f} [{r['pct_min']:.1f}-{r['pct_max']:.1f}]"
    return out


def headline(ref, a40, ap):
    spec = [
        ("reference: dTX35, GW weight, 30 d", ref, "all_thermal", "operating", 30),
        ("metric: dTX40", a40, "all_thermal", "operating", 30),
        ("weight: plant count", ap, "all_thermal", "operating", 30),
        ("threshold 20 d", ref, "all_thermal", "operating", 20),
        ("threshold 40 d", ref, "all_thermal", "operating", 40),
        ("fleet: planned_all", ref, "all_thermal", "planned_all", 30),
        ("fleet: planned_adv", ref, "all_thermal", "planned_adv", 30),
        ("fleet: planned_early", ref, "all_thermal", "planned_early", 30),
        ("tech: water-dependent", ref, "thermal_water_dependent", "operating", 30),
        ("tech: air-only", ref, "thermal_air_only", "operating", 30),
    ]
    rows = [{"choice": lab, **cell(s, g, f, t)} for lab, s, g, f, t in spec]
    return pd.DataFrame(rows)


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
    ref = summary_for(df35)
    if not check_ref(ref, tables):
        print("ABORT: reference does not reproduce w3_heat_summary; nothing written")
        sys.exit(1)
    a40, ap = summary_for(df40), summary_for(df35, weighted=True)
    tab = pd.concat([hs.compare(ref, a40, "metric_TX40"),
                     hs.compare(ref, ap, "weight_plant_count")], ignore_index=True)
    print(f"rows: reference {len(ref)}, long table {len(tab)} (expected {2 * len(ref)})")
    if len(tab) != 2 * len(ref):
        print("ABORT: row count mismatch; nothing written")
        sys.exit(1)
    tab.to_csv(tables / "w3_heat_sensitivity.csv", index=False)
    head = headline(ref, a40, ap)
    head.to_csv(tables / "w3_heat_sensitivity_headline.csv", index=False)
    print("written: w3_heat_sensitivity.csv, w3_heat_sensitivity_headline.csv")
    print("\nHeadline, all thermal: median [min-max] over GCMs, % (SSP126 / 370 / 585)")
    print(head.to_string(index=False))
    sel = tab[(tab["group"] == "all_thermal") & (tab["fleet"] == "operating")
              & (tab["threshold"] == 30)]
    show = ["choice", "scenario", "diff_median_pp", "ranges_overlap"]
    print("\nAlternative minus reference, all thermal, operating, 30 d:")
    print(sel[show].round(2).to_string(index=False))
    print("\nRows where GCM ranges do not overlap, by choice:")
    print(tab[~tab["ranges_overlap"]].groupby("choice").size().to_string())


if __name__ == "__main__":
    main()