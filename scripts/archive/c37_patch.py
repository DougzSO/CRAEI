"""C37: accept D80 and D81, register geography details and Table 1 agreement checks."""
from pathlib import Path

DEC = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"

BLOCK = """
## D80 and D81 - accepted (2026-10-01, C37)

- Accepted by the author on the assistant's recommendation, after re-reading the
  texts. They describe the unit-level reconciliation and plant_units.parquet as
  implemented, with the 16 build checks and the tests listed in D81.

## O26 - geography details (2026-10-01, C37)

- natural_earth_brazil.gpkg layers (pyogrio): brazil_admin0, southamerica_admin0,
  brazil_admin1, all MultiPolygon, EPSG:4326. Features: 1, 15 and 27. Brazil
  bounds (lon min, lat min, lon max, lat max): -74.02, -33.74, -28.88, 5.27.
- This replaces the pointer in the C36 block, which sent the counts to the
  STATUS_LOG; the log note did not carry them.
- The data/external/geo folder (sibling of CRAEI) is outside git: include it in
  the external copy.

## W3f-1 checks on Table 1 (2026-10-01, C37)

- w3_table1.csv: 243 rows, 153 range_reported and 90 descriptive (O25 rule).
- pct_gw_k1 equals pct_max in 243 of 243 rows (max abs difference 0.0).
  pct_gw_k5 exceeds pct_min in 0 rows, equals it in 168 and is below it in 75.
  Whether the exposed sets are nested across GCMs is tested in W3f-3 (w3_inspect6).
- Two lines that looked missing in pasted code and text were found on disk
  (geo_base.py, DECISIONS plateau note): paste artifact, no change.

## Status updates appended 2026-10-01 (C37)

- D80 and D81 accepted. All D-items of the v2 scope are now accepted except
  D84 (option A, licence not confirmed).
"""

txt = DEC.read_text(encoding="utf-8")
if "## D80 and D81 - accepted" in txt:
    print("ABORT: C37 block already present")
    raise SystemExit(1)
with open(DEC, "a", encoding="utf-8") as fh:
    fh.write(BLOCK)
print("appended: D80 and D81 accepted, geography details, Table 1 checks")