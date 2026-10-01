"""scripts/c27c_docs_addendum.py - append-only addendum to D79 in docs/DECISIONS.md."""
import datetime as dt, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"
raw = p.read_bytes()
txt = raw.decode("utf-8")
if "Addendum to D79" in txt:
    sys.exit("already applied (marker found); nothing written")
last = [l for l in txt.splitlines() if l.strip()][-1]
if not last.startswith("|"):
    sys.exit(f"last non-empty line is not a table row; aborting: {last[:80]!r}")
ids = [int(m) for m in re.findall(r"^\| D(\d+) \|", txt, flags=re.M)]
new_id = "D" + str(max(ids) + 1)
row = (
    f"| {new_id} | Addendum to D79 (C27 unit-level reconciliation; source: scripts/c27_fuel_units.py "
    "section 7, GEM snapshot 2026-08-09). D79 counted 6 plants / 22 units / 7.63 GW with mixed GEM types. "
    "The unit-level table with fuel_class gives 7 plants / 24 units / 8.04 GW; the difference is exactly "
    "Termo Norte (2 units, 0.413 GW: multi_fuel 0.349 + oil 0.064), 8.0417 - 0.4130 = 7.6287. Why D79's "
    "count omitted Termo Norte was not verified. Definitions for the article, all by unit: mixed fleet "
    "status = 5 plants, 22 units, 10.01 GW (units with operating status 3.56 GW, planned_early 6.46 GW, "
    "summed from the by_fleet column; mode-based assignment moves +3.55 GW to operating and -3.55 GW from "
    "planned_early); mixed fuel_class = 7 plants, 8.04 GW; mixed tech_class (water-dependent vs air-only) "
    "= 6 plants, 6.16 GW (same count as D79's six by coincidence of definition, not necessarily the same "
    "set). plant_units.parquet must also carry tech_class per unit (adds to D78's column list; relevant to "
    "O20, because the water/air thermal bucket of plants.parquet is wrong for 6 plants). "
    f"| proposed | assistant, C27; pending author review | {dt.date.today()} |\n"
)
with open(p, "a", encoding="utf-8", newline="\n") as f:
    if not raw.endswith(b"\n"):
        f.write("\n")
    f.write(row)
print("appended", new_id)