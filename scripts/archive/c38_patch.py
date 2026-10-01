"""C38: register the Brazil GCM-nesting result and update the work plan status."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEC = ROOT / "docs" / "DECISIONS.md"
PLAN = ROOT / "docs" / "CRAEI_work_plan_v2.md"

DEC_BLOCK = """
## C38 - GCM nesting in Brazil, GW-weighted (2026-10-01)

- Test: scripts/w3_inspect7.py (archived). Brazil thermal fleet via plant_units and
  heat_fuel, GW-weighted, fleets operating and planned_all, 3 scenarios, thresholds
  20, 30, 40 d (18 combinations). Countries in the data: BRA only.
- Result, as pasted: GW exposed in at least one GCM but outside the UKESM set is
  0.000 GW (0 plants) in 18 of 18 combinations, and UKESM is the maximum GCM in 18
  of 18. The union equals the UKESM set, so pct_gw_k1 = pct_max in Table 1 is
  nesting, not coincidence.
- The other GCMs are not a chain: GW exposed in the lowest GCM but not in all five
  ranges from 0.000 to 2.903 GW (maximum: operating, SSP5-8.5, 30 d, 23 plants).
  It is 0.000 only for planned_all SSP3-7.0 at 30 and 40 d.
- w3_inspect6 (3 countries, no capacity weight) found non-nested sets (1 to 75
  plants outside the UKESM set). It does not describe Brazil; inference: those
  plants lie outside Brazil (665 + 85 - 5 mixed plants = 745, all covered here).
- Reading rule: the upper bound of the GCM range is a single model (UKESM). The
  column k >= 1 of 5 is redundant with the maximum GCM. Report k >= 3 and k = 5 and
  the leave-one-GCM-out range (loo_min, loo_max of w3_heat_summary; values not read
  in this step). Why UKESM is the warmest in Brazilian cells is not tested here.

## Status updates appended 2026-10-01 (C38)

- Nesting result registered. W3f-4 (sensitivities of Axis 1) delivered in the same
  step; see STATUS_LOG for the floor.
"""

PLAN_BLOCK = """
## G addendum - status after W3f-3 (2026-10-01, written by C38)

- Done since the section G table: W3f-1 (Table 1, 4f83c3c), W3f-3 (scenario
  contrast, df72c93), W3f-4 (Axis 1 sensitivities, this step; hash in git log).
- Next: W3f-2 (Fig. 3 plotting table from w3_heat_summary and Table 1 bounds),
  then Axis 2 (W4a to W4f).
- O17, O25 and O26 are closed; D80, D81 and D87 are accepted. Pending author
  decisions: final n_boot, O20 (O16 only if a source is given).
"""

txt = DEC.read_text(encoding="utf-8")
if "## C38 - GCM nesting" in txt:
    print("ABORT: C38 block already present")
    raise SystemExit(1)
for path, block in ((DEC, DEC_BLOCK), (PLAN, PLAN_BLOCK)):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(block)
print("appended: C38 nesting result, work plan addendum")