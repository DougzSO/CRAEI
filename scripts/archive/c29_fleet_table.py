"""c29_fleet_table.py - Brazil fleet by technology x fuel x fleet from plant_units (C29).

Capacity side of Fig. 1 and Table 1 (no hazards). Reads plant_units.parquet and, only for
plant names, plants.parquet. Both O22 versions (Itaipu) are written side by side:
a_asset_whole (14,000 MW) and b_brazil_share (7,000 MW). Writes
<outputs_dir>/tables/fleet_brazil.csv and a report to <outputs_dir>/audit/c29/report.md.
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 200)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from craei.config import load_paths  # noqa: E402
from craei.inventory import fleet as F  # noqa: E402

TOL = 0.015
ITAIPU_TOTAL_MW = 14000.0  # plants.parquet value (O22)
PARAGUAY_MW = 7000.0  # GEM Paraguayan share (O22)
REF_FLEET = {"operating": 47.67, "planned_adv": 17.31, "planned_early": 31.04}
# Reference values quoted in the O22 text of DECISIONS.md (not recomputed elsewhere).
REF_HYDRO_OPERATING = {"a_asset_whole": 109.67, "b_brazil_share": 102.67}
LINES: list[str] = []


def out(s=""):
    print(s)
    LINES.append(str(s))


def pivot(tab: pd.DataFrame, index: str) -> pd.DataFrame:
    p = tab.pivot_table(index=index, columns="fleet", values="capacity_gw",
                        aggfunc="sum", fill_value=0)
    p = p.reindex(columns=F.FLEETS, fill_value=0)
    p.loc["TOTAL"] = p.sum()
    return p.round(2)


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    units_path = proc / "plant_units.parquet"
    if not units_path.exists():
        sys.exit("plant_units.parquet not found; run scripts/05b_plant_units.py first")
    units = pd.read_parquet(units_path)
    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country", "capacity_mw"])
    base = F.scope_units(units, "BRA")
    out(f"plant_units rows: {len(units)} | Brazil hydro+thermal units: {len(base)} "
        f"| {base.capacity_mw.sum() / 1000:.2f} GW")

    named = plants.plant_name.str.contains("itaipu", case=False, na=False)
    cand = plants[(plants.country == "BRA") & named]
    out("\n== Itaipu candidates in plants.parquet (BRA, name contains 'itaipu') ==")
    out(cand.to_string(index=False) if len(cand) else "none")
    big = cand[(cand.capacity_mw - ITAIPU_TOTAL_MW).abs() < 1e-6]

    tabs = {"a_asset_whole": F.fleet_table(base)}
    expected = {"a_asset_whole": float(base.capacity_mw.sum())}
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Itaipu: exactly one BRA plant with 14000 MW", len(big) == 1,
                   f"found {len(big)}"))
    if len(big) == 1:
        uids = set(big.plant_uid)
        itu = base[base.plant_uid.isin(uids)]
        out("\n== Itaipu units in plant_units (by fleet): count and MW ==")
        out(itu.groupby("fleet")["capacity_mw"].agg(["size", "sum"]).to_string())
        shared = F.apply_foreign_share(base, uids, ITAIPU_TOTAL_MW, PARAGUAY_MW)
        tabs["b_brazil_share"] = F.fleet_table(shared)
        expected["b_brazil_share"] = expected["a_asset_whole"] - PARAGUAY_MW
    else:
        out("\nversion b_brazil_share SKIPPED (Itaipu not uniquely identified)")

    th = tabs["a_asset_whole"]
    th = th[th.tech_class.str.startswith("thermal")]
    tot = th.groupby("fleet")["capacity_gw"].sum()
    for fl, v in REF_FLEET.items():
        got = float(tot.get(fl, float("nan")))
        checks.append((f"thermal {fl} total", abs(got - v) <= TOL,
                       f"expected {v:.2f} got {got:.2f}"))
    for ver, tab in tabs.items():
        diff = abs(float(tab.capacity_mw.sum()) - expected[ver])
        checks.append((f"{ver} conserves capacity", diff < 1e-6, f"abs diff {diff:.2e} MW"))
        hyd = tab[(tab.tech_class == "hydro") & (tab.fleet == "operating")]
        got = float(hyd.capacity_gw.sum())
        v = REF_HYDRO_OPERATING[ver]
        checks.append((f"{ver} hydro operating (O22 ref)", abs(got - v) <= TOL,
                       f"expected {v:.2f} got {got:.2f}"))

    out("\n== checks ==")
    for name, ok, det in checks:
        out(f"  {'PASS' if ok else 'FAIL'}  {name}  [{det}]")
    n_ok = sum(ok for _, ok, _ in checks)
    out(f"  {n_ok}/{len(checks)} PASS")

    a = tabs["a_asset_whole"]
    out("\n== thermal GW by fuel_class x fleet ==")
    out(pivot(a[a.tech_class.str.startswith("thermal")], "fuel_class").to_string())
    out("\n== thermal GW by tech_class (water vs air) x fleet ==")
    out(pivot(a[a.tech_class.str.startswith("thermal")], "tech_class").to_string())
    out("\n== bioenergy GW by subtype x fleet ==")
    out(pivot(a[a.fuel_class == "bioenergy"], "bio_subtype").to_string())
    for ver, tab in tabs.items():
        out(f"\n== hydro GW by hydro_type x fleet, version {ver} ==")
        out(pivot(tab[tab.tech_class == "hydro"], "hydro_type").to_string())

    long = pd.concat([t.assign(version=v) for v, t in tabs.items()], ignore_index=True)
    long = long[["version"] + [c for c in long.columns if c != "version"]]
    tdir = Path(paths["outputs_dir"]) / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    long.to_csv(tdir / "fleet_brazil.csv", index=False)
    out(f"\nwritten: {tdir / 'fleet_brazil.csv'} ({len(long)} rows)")

    rep = Path(paths["outputs_dir"]) / "audit" / "c29"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / "report.md").write_text("\n".join(LINES), encoding="utf-8")
    print(f"report: {rep / 'report.md'}")
    sys.exit(0 if n_ok == len(checks) else 1)


if __name__ == "__main__":
    main()