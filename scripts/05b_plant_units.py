"""05b_plant_units.py - build processed/plant_units.parquet (unit level; D78/D79/D80).

Reads GEM and plants.parquet (read-only, for the conservation check). Writes
plant_units.parquet only if all checks pass (or with --force), and a report to
<outputs_dir>/audit/c28/report.md.
Usage: python scripts/05b_plant_units.py [--force]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 200)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from craei.config import load_paths  # noqa: E402
from craei.inventory import plants as P  # noqa: E402
from craei.inventory import units as U  # noqa: E402

TOL = 0.015
REF_FLEET = {"operating": 47.67, "planned_adv": 17.31, "planned_early": 31.04}
REF_OPERATING = {
    "gas": 19.32, "bioenergy": 17.43, "oil": 4.60,
    "coal": 3.00, "nuclear": 1.99, "multi_fuel": 1.33,
}
REF_MIXED = {"fleet": (5, 10.01), "fuel_class": (7, 8.04), "tech_class": (6, 6.16)}
LINES: list[str] = []


def out(s=""):
    print(s)
    LINES.append(str(s))


def brazil_thermal(units: pd.DataFrame) -> pd.DataFrame:
    return units[(units.country == "BRA") & units.tech_class.str.startswith("thermal")]


def fleet_fuel_gw(th: pd.DataFrame) -> pd.DataFrame:
    return th.pivot_table(index="fuel_class", columns="fleet", values="capacity_mw",
                          aggfunc="sum", fill_value=0) / 1000


def _cell(tab: pd.DataFrame, fuel: str, fleet: str) -> float:
    if fuel in tab.index and fleet in tab.columns:
        return float(tab.loc[fuel, fleet])
    return float("nan")


def run_checks(units: pd.DataFrame, plants: pd.DataFrame):
    checks: list[tuple[str, bool, str]] = []

    def chk(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # 1. conservation against plants.parquet (all countries, all technologies)
    uu, pu = set(units.plant_uid), set(plants.plant_uid)
    chk("uid sets equal", uu == pu,
        f"units {len(uu)} | plants {len(pu)} | only units {len(uu - pu)} "
        f"| only plants {len(pu - uu)}")
    s = units.groupby("plant_uid")["capacity_mw"].sum()
    m = plants.set_index("plant_uid")["capacity_mw"]
    j = pd.concat([s.rename("u"), m.rename("p")], axis=1).dropna()
    maxdiff = float((j.u - j.p).abs().max()) if len(j) else float("nan")
    chk("capacity per plant_uid == plants.parquet", maxdiff < 1e-6,
        f"max abs diff {maxdiff:.2e} MW over {len(j)} plants")
    c = pd.concat([units.groupby("plant_uid")["country"].first().rename("u"),
                   plants.set_index("plant_uid")["country"].rename("p")], axis=1).dropna()
    bad = int((c.u != c.p).sum())
    chk("country per plant_uid", bad == 0, f"{bad} mismatches")

    # 2. D77 / C27 references (Brazil thermal, by unit)
    th = brazil_thermal(units)
    tab = fleet_fuel_gw(th)
    tot = tab.sum()
    for fl, v in REF_FLEET.items():
        got = float(tot.get(fl, float("nan")))
        chk(f"D77 {fl} TOTAL", abs(got - v) <= TOL, f"expected {v:.2f} got {got:.2f}")
    for fc, v in REF_OPERATING.items():
        got = _cell(tab, fc, "operating")
        chk(f"D77 operating {fc}", abs(got - v) <= TOL, f"expected {v:.2f} got {got:.2f}")
    agri = th[(th.bio_subtype == "agricultural_waste") & (th.fleet == "operating")]
    aw = agri.capacity_mw.sum() / 1000
    chk("D77 agricultural_waste operating", abs(aw - 12.08) <= TOL,
        f"expected 12.08 got {aw:.2f}")

    # 3. mixed plants (C27 section 7)
    for col, (n_exp, gw_exp) in REF_MIXED.items():
        n_vals = th.groupby("plant_uid")[col].nunique()
        ids = n_vals[n_vals > 1].index
        gw = th[th.plant_uid.isin(ids)].capacity_mw.sum() / 1000
        chk(f"mixed {col}", len(ids) == n_exp and abs(gw - gw_exp) <= TOL,
            f"expected {n_exp} / {gw_exp:.2f} GW got {len(ids)} / {gw:.2f} GW")
    return checks, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    paths = load_paths()
    proc = Path(paths["processed_dir"])
    rep_dir = Path(paths["outputs_dir"]) / "audit" / "c28"
    gem_path = Path(paths["gem_file"])
    if not gem_path.exists():
        gem_path = next(gem_path.parent.glob("gem_global*.xlsx"))

    gem = P.load_gem(gem_path)
    units = U.build_units(gem)
    plants = pd.read_parquet(proc / "plants.parquet")
    out(f"GEM: {gem_path.name} | units kept: {len(units)} | plants.parquet rows: {len(plants)}")
    out(f"gem_unit_id column present: {'gem_unit_id' in units.columns}")

    checks, tab = run_checks(units, plants)
    out("\n== checks ==")
    for name, ok, det in checks:
        out(f"  {'PASS' if ok else 'FAIL'}  {name}  [{det}]")
    all_ok = all(ok for _, ok, _ in checks)
    out(f"  {sum(ok for _, ok, _ in checks)}/{len(checks)} PASS")

    out("\n== Brazil thermal GW by fuel_class x fleet (unit level) ==")
    out(tab.round(2).to_string())
    out("\n== units and GW by country x tech_class ==")
    g = units.groupby(["country", "tech_class"]).agg(
        units=("capacity_mw", "size"),
        gw=("capacity_mw", lambda x: round(x.sum() / 1000, 2)),
    )
    out(g.to_string())

    if all_ok or a.force:
        proc.mkdir(parents=True, exist_ok=True)
        dest = proc / "plant_units.parquet"
        units.to_parquet(dest, index=False)
        note = "" if all_ok else "  [--force: checks FAILED]"
        out(f"\nwritten: {dest} ({len(units)} rows){note}")
    else:
        out("\nNOT written: checks failed (use --force to override)")

    rep_dir.mkdir(parents=True, exist_ok=True)
    (rep_dir / "report.md").write_text("\n".join(LINES), encoding="utf-8")
    print(f"report: {rep_dir / 'report.md'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()