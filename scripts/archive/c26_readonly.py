"""C26 read-only: plants.py aggregation, c23d CSVs, binational hydro, mixed Type plants."""
import pathlib
import re

import pandas as pd
import yaml

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)
ROOT = pathlib.Path(".").resolve()
cfg = yaml.safe_load(open("config/paths.local.yaml", encoding="utf-8"))

print("== 1. plants.py lines 100-165 ==")
ls = (ROOT / "src/craei/inventory/plants.py").read_text(encoding="utf-8").splitlines()
for i in range(99, min(165, len(ls))):
    print(f"{i + 1}: {ls[i]}")

d = ROOT.parent / "data/outputs/audit/c23/c23d"
print("\n== 2. c23d files ==")
for p in sorted(d.glob("*")):
    print(p.name, p.stat().st_size)
for name in ("c23d_4_spi12_comparison.csv", "c23d_7_leave_one_out.csv"):
    p = d / name
    print(f"\n-- {name}")
    print(pd.read_csv(p).to_string(max_rows=45) if p.exists() else "missing")
rep = (d / "c23d_report.md").read_text(encoding="utf-8")
m = re.search(r"## 1\..*?(?=\n## 2\.)", rep, re.S)
print("\n-- c23d_report section 1 (null rationale, to quote in D76)")
print(m.group(0) if m else "section 1 not found")

gem = pathlib.Path(cfg["gem_file"])
if not gem.exists():
    gem = next(gem.parent.glob("gem_global*.xlsx"))
df = pd.read_excel(gem, sheet_name="Power facilities")
pl = pd.read_parquet(pathlib.Path(cfg["processed_dir"]) / "plants.parquet")

print("\n== 3. binational hydro touching Brazil (GEM) ==")
c1, c2 = "Country/area 1 (hydropower only)", "Country/area 2 (hydropower only)"
k1, k2 = ("Country/area 1 Capacity (MW) (hydropower only)",
          "Country/area 2 Capacity (MW) (hydropower only)")
h = df[(df["Type"] == "hydropower") & df[c2].notna()
       & (df[c1].astype(str).str.contains("Brazil") | df[c2].astype(str).str.contains("Brazil"))]
cols = ["Plant / Project name", "Country/area", "Status", "Capacity (MW)", c1, c2, k1, k2]
print(h[cols].to_string())
bh = pl[(pl["country"] == "BRA") & (pl["tech_class"] == "hydro")]
print("\nplants.parquet BRA hydro, top 8 by capacity_mw:")
print(bh.sort_values("capacity_mw", ascending=False)
        [["plant_name", "fleet", "hydro_type", "capacity_mw"]].head(8).to_string())

print("\n== 4. Brazil thermal plants whose units mix GEM Types (aggregation of tech_class) ==")
b = df[df["Country/area"].astype(str).str.contains("Brazil")].copy()
b = b[b["Type"].isin(["bioenergy", "coal", "nuclear", "oil/gas"])
      & b["Status"].isin(["operating", "construction", "pre-construction", "announced"])]
b["cap"] = pd.to_numeric(b["Capacity (MW)"], errors="coerce")
b["lat"] = pd.to_numeric(b["Latitude"], errors="coerce").round(4)
b["lon"] = pd.to_numeric(b["Longitude"], errors="coerce").round(4)
key = ["Plant / Project name", "lat", "lon"]
mix = b.groupby(key).filter(lambda x: x["Type"].nunique() > 1)
print("plants:", mix.groupby(key).ngroups, "| units:", len(mix), "| GW:", round(mix["cap"].sum() / 1000, 2))
if len(mix):
    print(mix.groupby(key + ["Type"])["cap"].sum().div(1000).round(3).to_string())