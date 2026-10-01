"""C39: register W3f-4 results, open O27 (TX40 grid), work plan status."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEC = ROOT / "docs" / "DECISIONS.md"
PLAN = ROOT / "docs" / "CRAEI_work_plan_v2.md"

DEC_BLOCK = """
## W3f-4 - Axis 1 sensitivities, results (2026-10-01, C39)

- Tables w3_heat_sensitivity.csv (long, 1,296 rows) and
  w3_heat_sensitivity_headline.csv (text, for reading only). The reference
  recomputed in the script reproduces w3_heat_summary: 648/648 rows, max |diff|
  1.42e-14.
- Headline, all thermal, operating, 30 d, median [min-max] over GCMs, %,
  SSP1-2.6 / SSP3-7.0 / SSP5-8.5, as pasted:
  - reference (dTX35, GW weight): 28.4 [19.1-49.3] / 36.3 [31.4-77.0] /
    49.1 [42.3-92.2].
  - plant-count weight: 32.5 [25.1-54.1] / 46.5 [40.3-81.7] / 55.9 [50.7-91.7];
    difference of medians +4.11 / +10.20 / +6.80 pp, ranges overlap, 12 rows
    without overlap in the long table. Why smaller plants are more exposed was
    not tested.
  - threshold 20 d: 41.2 / 62.3 / 69.2; threshold 40 d: 20.2 / 31.9 / 35.3.
  - planned_all 15.9 / 39.0 / 61.6; planned_adv 37.1 / 55.0 / 55.4;
    planned_early 6.6 / 30.1 / 65.2 (the sign of planned minus operating depends
    on the definition, as in O17).
  - water-dependent 27.9 / 37.4 / 51.3; air-only 30.6 / 30.6 / 44.2 with ranges
    15.5-38.4, 26.4-88.8 and 31.3-100.0. Cell counts of air-only were not read
    here; the O25 rule applies.
- TX40 on the TX35 day grid: dTX40 >= 30 d gives 0.0 [0.0-2.1] / 0.0 [0.0-13.2] /
  4.0 [2.3-29.3] %, and 400 long-table rows have non-overlapping ranges. This is
  not a sensitivity result: it compares a rarer event on the same grid. Do not
  quote it as fragility of the headline.

## O27 - TX40 sensitivity grid (open)

- TX40 needs its own threshold grid (candidate 1, 2, 5, 10, 20, 30 d). The
  distribution of dTX40 was printed by w3_inspect8 (archived); the grid is TO BE
  DEFINED by the author after reading it. Until then TX40 is not a reported
  sensitivity.

## Status updates appended 2026-10-01 (C39)

- W3f-4 results registered, O27 opened. W3f-2 (plotting table of the threshold
  curves, w3_curves_plot.csv) delivered in the same step.
"""

PLAN_BLOCK = """
## G addendum 2 - status after W3f-4 (2026-10-01, written by C39)

- Done: W3f-4 (009b913), W3f-2 (this step). Axis 1 tables are complete except the
  TX40 grid (O27) and the final n_boot (author decision).
- Next: Axis 2, starting with W4a (null with blocks 12/24/36/60, AR(1) and white
  noise as limits).
"""

txt = DEC.read_text(encoding="utf-8")
if "## W3f-4 - Axis 1 sensitivities" in txt:
    print("ABORT: C39 block already present")
    raise SystemExit(1)
for path, block in ((DEC, DEC_BLOCK), (PLAN, PLAN_BLOCK)):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(block)
print("appended: W3f-4 results, O27, work plan addendum 2")