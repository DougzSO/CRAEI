"""W3e (axis 1, O16): monthly delta N35 profile of the operating thermal groups."""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import pandas as pd

from craei.config import load_paths
from craei.countries import iso as country_iso
from craei.exposure import heat_fuel as hf
from craei.exposure import heat_season as hs

sys.stdout.reconfigure(encoding="utf-8")

TOL = 1e-6
CELL = ["cell_lat", "cell_lon"]
SHOW = ("bioenergy_all", "bioenergy_agricultural_waste", "gas")
LOG: list[str] = []


def log(msg: object = "") -> None:
    LOG.append(str(msg))
    print(msg)


def group_masks(op: pd.DataFrame) -> dict[str, pd.Series]:
    bio = op["fuel_class"] == "bioenergy"
    agri = op["bio_subtype"] == "agricultural_waste"
    return {
        "bioenergy_all": bio,
        "bioenergy_agricultural_waste": bio & agri,
        "bioenergy_other": bio & ~agri,
        "gas": op["fuel_class"] == "gas",
        "all_thermal": pd.Series(True, index=op.index),
    }


def check_annual(name: str, sub: pd.DataFrame, prof: pd.DataFrame, haz: pd.DataFrame) -> bool:
    """Sum of the 12 monthly deltas must equal the weighted annual delta of plant_hazards."""
    cap = sub.groupby("plant_uid", as_index=False)["capacity_mw"].sum()
    m = cap.merge(haz, on="plant_uid", validate="one_to_many")
    m = m.assign(wd=m["capacity_mw"] * m["delta"])
    ref = m.groupby(["model", "scenario"]).agg(wd=("wd", "sum"), mw=("capacity_mw", "sum"))
    ref["ref"] = ref["wd"] / ref["mw"]
    got = prof.groupby(["model", "scenario"])["delta_n35"].sum().rename("got")
    j = ref.join(got, how="outer")
    diff = (j["ref"] - j["got"]).abs()
    months = prof.groupby(["model", "scenario"])["month"].nunique()
    ok = bool(len(j) == 15 and not diff.isna().any() and diff.max() <= TOL)
    ok = ok and bool((months == 12).all())
    log(f"check {name}: {len(j)} GCM x scenario, max |sum(monthly) - annual| "
        f"{diff.max():.2e}, months per series {sorted(months.unique())}, ok={ok}")
    return ok


def main() -> None:
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    tables = Path(paths["outputs_tables_dir"])
    units = pd.read_parquet(proc / "plant_units.parquet")
    keep = (units["country"] == country_iso()) & units["fuel_class"].isin(hf.THERMAL_FUELS)
    op = units[keep & (units["fleet"] == "operating")]
    bio = op["fuel_class"] == "bioenergy"
    log("bio_subtype, operating bioenergy units: "
        + str(op.loc[bio, "bio_subtype"].value_counts(dropna=False).to_dict()))
    cells = pd.read_parquet(proc / "plant_cell.parquet", columns=["plant_uid", *CELL])
    op = op.merge(cells, on="plant_uid", how="left", validate="many_to_one")
    if op[CELL].isna().any().any():
        sys.exit("ABORT: some operating units have no cell")

    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    haz = pd.read_parquet(
        proc / "plant_hazards.parquet", columns=cols, filters=[("hazard", "==", "TX35")]
    )
    haz = haz[["plant_uid", "model", "scenario", "delta"]]
    raw = pd.read_parquet(
        proc / "indices_daily.parquet",
        columns=[*CELL, "model", "scenario", "period", "year", "month", "index", "value"],
        filters=[("index", "==", "n35")],
    )
    n35 = raw.merge(op[CELL].drop_duplicates(), on=CELL, how="inner")
    del raw
    gc.collect()
    log(f"n35 rows on operating thermal cells: {len(n35)}; periods "
        f"{sorted(n35['period'].unique())}; scenarios {sorted(n35['scenario'].unique())}")

    profiles = []
    all_ok = True
    for name, mask in group_masks(op).items():
        sub = op[mask]
        if sub.empty:
            sys.exit(f"ABORT: group {name} is empty")
        w = sub.groupby(CELL, as_index=False)["capacity_mw"].sum()
        prof = hs.monthly_profile(n35, w.rename(columns={"capacity_mw": "mw"}))
        prof.insert(0, "group", name)
        all_ok = check_annual(name, sub, prof, haz) and all_ok
        profiles.append(prof)
    if not all_ok:
        sys.exit("ABORT: monthly profile does not reproduce the annual delta; nothing written")

    prof = pd.concat(profiles, ignore_index=True)
    summ = pd.concat(
        [hs.summarise_gcms(p).assign(group=p["group"].iloc[0]) for p in profiles],
        ignore_index=True,
    )
    prof.to_csv(tables / "w3_heat_season_by_gcm.csv", index=False)
    summ.to_csv(tables / "w3_heat_season_summary.csv", index=False)

    log("")
    log("Monthly delta N35 (days per month, future - baseline), median [min-max] over GCMs.")
    for name in SHOW:
        s = summ[summ["group"] == name].copy()
        s["txt"] = [
            f"{a:.1f} [{b:.1f}-{c:.1f}]"
            for a, b, c in zip(s["delta_median"], s["delta_min"], s["delta_max"], strict=True)
        ]
        log("")
        log(f"{name} (operating):")
        log(s.pivot(index="month", columns="scenario", values="txt").to_string())
    log("")
    log("Month with the largest median delta, and its share of the annual delta:")
    idx = summ.groupby(["group", "scenario"])["delta_median"].idxmax()
    peak = summ.loc[idx, ["group", "scenario", "month", "delta_median", "share_median"]]
    log(peak.round(2).to_string(index=False))

    audit = Path(paths["outputs_audit_dir"]) / "w3e"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "report.md").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("tables:", tables)
    print("report:", audit / "report.md")


if __name__ == "__main__":
    main()