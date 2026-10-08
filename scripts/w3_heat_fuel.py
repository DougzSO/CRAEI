"""W3a (axis 1): heat exposure of the Brazilian thermal fleet by fuel, per unit."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.countries import iso as country_iso
from craei.exposure import heat_fuel as hf

sys.stdout.reconfigure(encoding="utf-8")

FLEETS = ("operating", "planned_adv", "planned_early")
REF_GW = {
    "all": (47.67, 17.31, 31.04),
    "gas": (19.32, 13.80, 30.32),
    "bioenergy": (17.43, 2.11, 0.0),
    "coal": (3.00, 0.0, 0.0),
    "oil": (4.60, 0.0, 0.0),
    "nuclear": (1.99, 1.40, 0.0),
    "multi_fuel": (1.33, 0.0, 0.72),
}
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def check_capacity(units: pd.DataFrame) -> bool:
    th = units[(units["country"] == country_iso()) & units["fuel_class"].isin(hf.THERMAL_FUELS)]
    ok = True
    for grp, ref in REF_GW.items():
        sub = th if grp == "all" else th[th["fuel_class"] == grp]
        for fleet, want in zip(FLEETS, ref, strict=True):
            got = sub.loc[sub["fleet"] == fleet, "capacity_mw"].sum() / 1000.0
            good = abs(got - want) <= 0.006
            ok = ok and good
            tag = "PASS" if good else "FAIL"
            log(f"{tag} {grp:11s} {fleet:13s} got {got:8.3f} ref {want:6.2f}")
    return ok


def main() -> None:
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    log(f"processed_dir: {proc}")
    units = pd.read_parquet(proc / "plant_units.parquet")
    if not check_capacity(units):
        sys.exit("ABORT: capacity references failed; nothing written")
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    base = hf.build_unit_hazard(units, haz)
    log(f"unit x GCM x scenario rows: {len(base)}; plants: {base['plant_uid'].nunique()}")
    df = hf.add_pooled_planned(base)

    groups = ("fuel_class", "tech_class", None)
    curves = pd.concat([hf.exposure_curves(df, g) for g in groups], ignore_index=True)
    summary = hf.summarise_gcms(curves)
    summary = summary.merge(hf.leave_one_gcm_out(curves), on=hf.KEY, validate="one_to_one")
    wide = hf.wide_by_gcm(curves)
    pvo = pd.concat(
        [hf.planned_vs_operating(curves, p) for p in hf.PLANNED_FLEETS],
        ignore_index=True,
    )

    tables = Path(paths["outputs_tables_dir"])
    curves.to_csv(tables / "w3_heat_curves_by_gcm.csv", index=False)
    summary.to_csv(tables / "w3_heat_summary.csv", index=False)
    wide.to_csv(tables / "w3_heat_by_gcm_wide.csv", index=False)
    pvo.to_csv(tables / "w3_heat_planned_vs_operating.csv", index=False)

    log("")
    log("Headline at threshold 30 d (share of group GW; min / median / max over GCMs):")
    head = summary[summary["threshold"] == 30]
    show = ["group", "fleet", "scenario", "n_plants", "gw_total", "pct_min",
            "pct_median", "pct_max", "loo_min", "loo_max", "gw_median"]
    log(head[show].round(1).to_string(index=False))
    log("")
    log("Operating fleet at threshold 30 d, share of GW per GCM:")
    w = wide[(wide["threshold"] == 30) & (wide["fleet"] == "operating")]
    log(w.drop(columns=["threshold", "fleet"]).round(1).to_string(index=False))
    log("")
    log("Planned minus operating at threshold 30 (pp), GCMs with planned >= operating:")
    log(pvo[pvo["threshold"] == 30].round(1).to_string(index=False))

    out = Path(paths["outputs_audit_dir"]) / "w3"
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("tables:", tables)
    print("report:", out / "report.md")


if __name__ == "__main__":
    main()