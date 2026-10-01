"""C27 read-only: Brazil thermal GW by fleet x fuel class x tech_class, per GEM unit (D77)."""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from craei.config import load_paths  # noqa: E402
from craei.inventory import plants as P  # noqa: E402

paths = load_paths()
OUT = Path(paths["outputs_dir"]) / "audit" / "c27"
OUT.mkdir(parents=True, exist_ok=True)

gem = Path(paths["gem_file"])
if not gem.exists():
    gem = next(gem.parent.glob("gem_global*.xlsx"))
df = pd.read_excel(gem, sheet_name="Power facilities")
g = df[df["Country/area"].astype(str).str.strip() == "Brazil"].copy()

FLEET = {"operating": "operating", "construction": "planned_adv",
         "pre-construction": "planned_adv", "announced": "planned_early"}
THERM = {"coal", "nuclear", "bioenergy", "oil/gas"}
g["type_n"] = g["Type"].astype(str).str.strip().str.lower()
g["fleet"] = g["Status"].astype(str).str.strip().str.lower().map(FLEET)
g = g[g["type_n"].isin(THERM) & g["fleet"].notna()].copy()
g["cap_mw"] = pd.to_numeric(g["Capacity (MW)"], errors="coerce")
g["lat"] = pd.to_numeric(g["Latitude"], errors="coerce")
g["lon"] = pd.to_numeric(g["Longitude"], errors="coerce")


def oil_gas_class(v):
    v = str(v).strip().lower()
    if v in ("gas", "lng only"):
        return "gas"
    if v == "oil":
        return "oil"
    if v == "multi fuel":
        return "multi_fuel"
    return "oil_gas_unclassified"


def bio_token(t):
    t = t.strip().lower().replace("bioenergy:", "").strip()
    if t == "agricultural waste (solids)":
        return "agricultural_waste"
    if t == "paper mill wastes":
        return "paper_mill_waste"
    if t.startswith("wood & other biomass"):
        return "wood_biomass"
    return "other_bioenergy"


def bio_class(v):
    cls = {bio_token(x) for x in str(v).split(",") if x.strip()}
    return cls.pop() if len(cls) == 1 else "bio_mixed"


def fuel_class(r):
    t = r["type_n"]
    if t in ("coal", "nuclear"):
        return t
    if t == "bioenergy":
        return "bioenergy"
    return oil_gas_class(r["Fuel classification (oil/gas only)"])


def unit_tech(r):
    try:
        return P._classify(P._norm(r["Type"]), P._norm(r["Technology"]))[0]
    except Exception:
        return "n/a"


def uid(r):
    if pd.isna(r["lat"]) or pd.isna(r["lon"]):
        return None
    return P.plant_uid(str(r["Plant / Project name"]), r["Latitude"], r["Longitude"])


g["fuel_class"] = g.apply(fuel_class, axis=1)
g["bio_class"] = g.apply(lambda r: bio_class(r["Fuel (combustion only)"])
                         if r["type_n"] == "bioenergy" else None, axis=1)
g["tech_unit"] = g.apply(unit_tech, axis=1)
g["uid"] = g.apply(uid, axis=1)

print(f"units: {len(g)} | no capacity: {int(g.cap_mw.isna().sum())} | "
      f"no coordinates: {int(g.uid.isna().sum())} "
      f"({g.loc[g.uid.isna(), 'cap_mw'].sum() / 1000:.3f} GW) | tech n/a: {int((g.tech_unit == 'n/a').sum())}")

print("\n== 1. GW by fuel_class x fleet (unit level, D77) ==")
ff = (g.pivot_table(index="fuel_class", columns="fleet", values="cap_mw",
                    aggfunc="sum", fill_value=0) / 1000).round(2)
ff.loc["TOTAL"] = ff.sum()
print(ff.to_string())
ff.to_csv(OUT / "c27_fleet_fuel_gw.csv")

print("\n== 2. units count by fuel_class x fleet ==")
print(g.pivot_table(index="fuel_class", columns="fleet", values="cap_mw",
                    aggfunc="size", fill_value=0).to_string())

print("\n== 3. bioenergy subtype GW by fleet ==")
bb = (g[g.fuel_class == "bioenergy"].pivot_table(
    index="bio_class", columns="fleet", values="cap_mw", aggfunc="sum", fill_value=0) / 1000).round(3)
print(bb.to_string())
bb.to_csv(OUT / "c27_bio_subtype_gw.csv")

print("\n== 4. fuel_class x unit tech_class, GW ==")
ft = (g.pivot_table(index=["fleet", "fuel_class"], columns="tech_unit", values="cap_mw",
                    aggfunc="sum", fill_value=0) / 1000).round(2)
print(ft.to_string())

print("\n== 5. reference check (D77, operating; fleets totals) ==")
ref = {("operating", "TOTAL"): 47.67, ("operating", "gas"): 19.32, ("operating", "bioenergy"): 17.43,
       ("operating", "oil"): 4.60, ("operating", "coal"): 3.00, ("operating", "nuclear"): 1.99,
       ("operating", "multi_fuel"): 1.33, ("planned_adv", "TOTAL"): 17.31,
       ("planned_early", "TOTAL"): 31.04}
for (fl, fc), v in ref.items():
    got = float(ff.loc[fc, fl]) if fl in ff.columns and fc in ff.index else float("nan")
    print(f"{fl:14s} {fc:11s} expected {v:6.2f} got {got:6.2f} "
          f"{'PASS' if abs(got - v) <= 0.015 else 'FAIL'}")
bm = bb.loc[["agricultural_waste"], "operating"].iat[0] if "agricultural_waste" in bb.index else float("nan")
print(f"agricultural_waste operating expected 12.08 got {bm:.2f} "
      f"{'PASS' if abs(bm - 12.08) <= 0.015 else 'FAIL'}")

print("\n== 6. plants.parquet (BRA thermal) vs unit level, GW by fleet ==")
pl = pd.read_parquet(Path(paths["processed_dir"]) / "plants.parquet")
pb = pl[(pl["country"] == "BRA") & pl["tech_class"].str.startswith("thermal")]
cmp = pd.DataFrame({"plants_parquet": pb.groupby("fleet")["capacity_mw"].sum() / 1000,
                    "units_gem": g.groupby("fleet")["cap_mw"].sum() / 1000}).round(2)
cmp["diff"] = (cmp.plants_parquet - cmp.units_gem).round(2)
print(cmp.to_string())

print("\n== 7. mixed plants (fleet / fuel_class / tech_class differ among units) ==")
gu = g[g.uid.notna()]
agg = gu.groupby("uid").agg(
    name=("Plant / Project name", "first"), n_units=("cap_mw", "size"),
    gw=("cap_mw", lambda s: s.sum() / 1000), n_fleet=("fleet", "nunique"),
    n_fuel=("fuel_class", "nunique"), n_tech=("tech_unit", "nunique"))
for col, lab in (("n_fleet", "fleet"), ("n_fuel", "fuel_class"), ("n_tech", "tech_class")):
    m = agg[agg[col] > 1]
    print(f"mixed {lab}: {len(m)} plants, {m.gw.sum():.2f} GW")
mixed = agg[(agg.n_fleet > 1) | (agg.n_fuel > 1) | (agg.n_tech > 1)].copy()


def desc(u, col):
    s = gu[gu.uid == u].groupby(col)["cap_mw"].sum() / 1000
    return "; ".join(f"{k}:{v:.3f}" for k, v in s.items())


pbi = pb.set_index("plant_uid")
mixed["pp_fleet"] = [pbi.fleet.get(u, "-") for u in mixed.index]
mixed["pp_tech"] = [pbi.tech_class.get(u, "-") for u in mixed.index]
mixed["pp_cap_gw"] = [round(pbi.capacity_mw.get(u, float("nan")) / 1000, 3) for u in mixed.index]
mixed["by_fleet"] = [desc(u, "fleet") for u in mixed.index]
mixed["by_fuel"] = [desc(u, "fuel_class") for u in mixed.index]
mixed = mixed.sort_values("gw", ascending=False)
print(mixed[["name", "n_units", "gw", "pp_fleet", "pp_tech", "pp_cap_gw", "by_fleet", "by_fuel"]]
      .head(30).to_string())
mixed.to_csv(OUT / "c27_mixed_plants.csv")

print("\n== 8. plant_uid coverage ==")
gem_u, pp_u = set(agg.index), set(pb.plant_uid)
print(f"GEM thermal uids: {len(gem_u)} | plants.parquet BRA thermal: {len(pp_u)} | "
      f"only GEM: {len(gem_u - pp_u)} | only plants.parquet: {len(pp_u - gem_u)}")
if gem_u - pp_u:
    print(agg.loc[sorted(gem_u - pp_u), ["name", "n_units", "gw"]].head(15).to_string())

keep = ["uid", "Plant / Project name", "Unit / Phase name", "Status", "fleet", "type_n", "Technology",
        "Fuel (combustion only)", "Fuel classification (oil/gas only)", "fuel_class", "bio_class",
        "tech_unit", "cap_mw", "lat", "lon"]
g[keep].to_csv(OUT / "c27_units_brazil_thermal.csv", index=False)
print(f"\nwritten: {OUT}")