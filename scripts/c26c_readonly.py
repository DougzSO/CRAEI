"""C26c read-only: null rationale search + definition of tx35_gw_pct."""
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(".").resolve()


def show(path, a, b, prose_only=True):
    ls = path.read_text(encoding="utf-8").splitlines()
    print(f"\n-- {path.name} lines {a}-{b}")
    for i in range(a - 1, min(b, len(ls))):
        l = ls[i]
        if not prose_only or re.match(r"\s*(#|p\(|h\(|f?\"|\"\"\")", l):
            print(f"{i + 1}: {l.rstrip()[:200]}")


c23c = ROOT / "scripts/c23c_checks.py"
c23d = ROOT / "scripts/c23d_checks.py"

print("== 1. docstrings ==")
for p in (c23c, c23d):
    ls = p.read_text(encoding="utf-8").splitlines()
    print(f"\n-- {p.name} (1-45)")
    print("\n".join(ls[:45]))

print("\n== 2. null prose ==")
show(c23c, 360, 455)
show(c23d, 140, 240)

print("\n== 3. docs: AR(1) / bootstrap / autocorrel ==")
pat = re.compile(r"AR\(1\)|bootstrap em blocos|block bootstrap|autocorrel|autocorrela", re.I)
for p in [ROOT / "docs/archive/DECISIONS_v1_pre_rework.md",
          ROOT / "docs/archive/LIMITATIONS_v1_pre_rework.md",
          ROOT.parent / "data/outputs/audit/c23/c23c/c23c_report.md",
          ROOT.parent / "data/outputs/audit/c23/c23d/c23d_report.md"]:
    if p.exists():
        for i, l in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(l):
                print(f"{p.name}:{i}: {l.strip()[:300]}")

print("\n== 4. c23d fuel exposure computation (definition of tx35_gw_pct) ==")
show(c23d, 351, 437, prose_only=False)