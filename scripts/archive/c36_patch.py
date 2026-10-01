"""C36: accept D87, close O17, register O26 resolution and the ruff config note."""
from pathlib import Path

DEC = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"

BLOCK = """
## D87 - accepted (2026-10-01, C36)

- Accepted by the author together with the O17 proposal below. Unit of analysis,
  thresholds, fleets and reporting as in D87.

## O17 - closed (2026-10-01, C36)

- Threshold grid: 10, 20, 30, 40, 50, 60, 80, 100 d. The 30 d class is the
  headline point; 20 and 40 d are its neighbours.
- Planned fleet: planned_all is the main line, always shown with planned_adv and
  planned_early beside it. The text states that the planned-minus-operating
  reading depends on the planned-fleet definition and that at the all-thermal
  level no definition separates planned from operating (all bootstrap intervals
  include 0, D86 addendum).
- TX40 (present in plant_hazards) enters as a sensitivity in W3f-4.
- Observation from the w3_inspect5 output: planned_all equals planned_adv plus
  planned_early in GW (all thermal 48.35 = 17.31 + 31.04; gas 44.12 = 13.80 +
  30.32). The mapping of GEM statuses was not re-read in this step.
- Plateaus in the curves are concentration, not physics (operating gas stays at
  22.4% from 30 to 80 d in SSP3-7.0, as pasted); Table 1 and Fig. 3 carry the
  number of cells and the largest-cell share.

## O26 - resolution (2026-10-01, C36)

- Author authorised Natural Earth (public domain) as base geography. Written by
  scripts/geo_base.py to ..\\data\\external\\geo\\natural_earth_brazil.gpkg
  (layers brazil_admin0, southamerica_admin0, brazil_admin1) with SOURCE.txt.
  Feature counts: see the STATUS_LOG entry of W3f-1.
- matplotlib, geopandas and cartopy import but are not declared in pyproject.toml
  (only pyyaml; environment.yml holds the real list). Declaring them: W6a.

## Config note (C36)

- pyproject.toml ruff line-length changed from 150 to 250 by the author. Code
  delivered by the assistant stays at 100 columns or fewer.
- Ruff outside the archive, measured: 12 errors (expected 13 before the run).

## Status updates appended 2026-10-01 (C36)

- D87 accepted, O17 closed, O26 resolved. D80 and D81 remain proposed.
"""

txt = DEC.read_text(encoding="utf-8")
if "## O17 - closed" in txt:
    print("ABORT: C36 block already present")
    raise SystemExit(1)
with open(DEC, "a", encoding="utf-8") as fh:
    fh.write(BLOCK)
print("appended: D87 accepted, O17 closed, O26, config note")