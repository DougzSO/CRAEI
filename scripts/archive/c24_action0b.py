"""C24 Action 0b: fleet reconciliation (GEM units vs plants.parquet) + null report."""
import pathlib
import re

import pandas as pd
import yaml

ROOT = pathlib.Path(".").resolve()
cfg = yaml.safe_load(open("config/paths.local.yaml", encoding="utf-8"))

# ---- 1. reconciliation -------------------------------------------------
gem = pathlib.Path(cfg["gem_file"])
if not gem.exists():
    gem = next(gem.parent.glob("gem_global*.xlsx"))
df = pd.read_excel(gem, sheet_name="Power facilities")
b = df[df["Country/area"].astype(str).str.contains("Brazil", case=False)].copy()
b["cap"] = pd.to_numeric(b["Capacity (MW)"], errors="coerce")
THERM = ["bioenergy", "coal", "nuclear", "oil/gas"]
FLEET = {"operating": "operating", "construction": "planned_adv",
         "pre-construction": "planned_adv", "announced": "planned_early"}
t = b[b["Type"].isin(THERM) & b["Status"].isin(FLEET)].copy()
t["fleet_unit"] = t["Status"].map(FLEET)

print("== 1a. GEM thermal GW by fleet (unit-level status) ==")
print((t.groupby("fleet_unit")["cap"].sum() / 1000).round(2).to_string())

pl = pd.read_parquet(pathlib.Path(cfg["processed_dir"]) / "plants.parquet")
pb = pl[(pl["country"] == "BRA") & pl["tech_class"].str.startswith("thermal")]
print("\n== 1b. plants.parquet thermal GW by fleet ==")
print((pb.groupby("fleet")["capacity_mw"].sum() / 1000).round(2).to_string())

# plants whose units carry more than one planning/operating status
t["lat"] = pd.to_numeric(t["Latitude"], errors="coerce").round(4)
t["lon"] = pd.to_numeric(t["Longitude"], errors="coerce").round(4)
key = ["Plant / Project name", "lat", "lon"]
g = t.groupby(key)
mixed = g.filter(lambda x: x["fleet_unit"].nunique() > 1)
print("\n== 1c. mixed-status plants (thermal, BRA) ==")
print("plants:", mixed.groupby(key).ngroups, "| units:", len(mixed))
pv = (mixed.pivot_table(index=key, columns="fleet_unit", values="cap",
                        aggfunc="sum", fill_value=0) / 1000).round(3)
print("GW by fleet inside mixed plants:\n", pv.sum().round(2).to_string())
print("\ntop 15 mixed plants by non-operating GW:")
other = [c for c in pv.columns if c != "operating"]
print(pv.assign(non_op=pv[other].sum(axis=1))
        .sort_values("non_op", ascending=False).head(15).to_string())

# ---- 2. where fleet is assigned ----------------------------------------
print("\n== 2. fleet/status logic in src/craei/inventory/plants.py ==")
src = ROOT / "src" / "craei" / "inventory" / "plants.py"
for i, ln in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
    if re.search(r"fleet|status|aggregate|groupby", ln, re.I):
        print(f"{i}: {ln.rstrip()[:150]}")

# ---- 3. null report -----------------------------------------------------
print("\n== 3. c23d_report.md sections 2-3 ==")
rep = ROOT.parent / "data" / "outputs" / "audit" / "c23" / "c23d" / "c23d_report.md"
txt = rep.read_text(encoding="utf-8")
m = re.search(r"## 2\..*?(?=\n## 4\.|\Z)", txt, re.S)
print(m.group(0) if m else "section not found")

# ---- 4. LOO / SPI search, no per-file cap -------------------------------
print("\n== 4. leave-one-out / SPI hits ==")
pat = re.compile(r"leave|\bLOO\b|\bSPI\b|spi12", re.I)
targets = list((ROOT / "scripts").glob("c2*.py")) + list(
    (ROOT.parent / "data" / "outputs" / "audit").rglob("*.md"))
for p in targets:
    for i, ln in enumerate(p.read_text(encoding="utf-8", errors="ignore")
                           .splitlines(), 1):
        if pat.search(ln):
            print(f"{p.name}:{i}: {ln.strip()[:130]}")