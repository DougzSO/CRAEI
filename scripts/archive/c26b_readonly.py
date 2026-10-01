"""C26b read-only: D56, PROGRESS.json refs, c23d fuel/sign/null prototypes."""
import pathlib
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 70)
ROOT = pathlib.Path(".").resolve()
d = ROOT.parent / "data/outputs/audit/c23/c23d"

print("== 1. D56 (original row) ==")
v1 = (ROOT / "docs/archive/DECISIONS_v1_pre_rework.md").read_text(encoding="utf-8-sig")
hit = [l for l in v1.splitlines() if l.startswith("| D56 |")]
print(hit[0][:1800] if hit else "D56 row not found in v1")

print("\n== 2. PROGRESS.json references (context) ==")
for n in ("c23b_finish.py", "c23_code_audit.py", "c23_scope_audit.py"):
    for i, l in enumerate((ROOT / "scripts" / n).read_text(encoding="utf-8").splitlines(), 1):
        if "PROGRESS.json" in l:
            print(f"{n}:{i}: {l.strip()[:150]}")

print("\n== 3. c23d CSVs ==")
for n in ("c23d_2_null_rates.csv", "c23d_5_sign_agreement.csv",
          "c23d_6_fuel_summary.csv", "c23d_6_fuel_tx35_exposure.csv"):
    print(f"\n-- {n}")
    print(pd.read_csv(d / n).to_string(max_rows=60))

print("\n== 4. c23d report sections 5-6 and 7 text ==")
rep = (d / "c23d_report.md").read_text(encoding="utf-8")
m = re.search(r"## 5\..*?(?=\n## 7\.)", rep, re.S)
print(m.group(0)[:6000] if m else "sections 5-6 not found")
m = re.search(r"## 7\..*", rep, re.S)
txt = m.group(0) if m else ""
print("\n".join(l for l in txt.splitlines() if not l.startswith("|"))[:2500])

print("\n== 5. c23d_checks.py: null construction and fuel assignment ==")
src = (ROOT / "scripts/c23d_checks.py").read_text(encoding="utf-8").splitlines()
for i in range(142, 165):
    print(f"{i + 1}: {src[i]}")
pat = re.compile(r"fuel|bagasse|bioenergy|agricultural|plant_fuel|merge\(|AR\(1\)|ar1|why|because", re.I)
print("-- keyword lines --")
for i, l in enumerate(src, 1):
    if pat.search(l):
        print(f"{i}: {l.strip()[:140]}")