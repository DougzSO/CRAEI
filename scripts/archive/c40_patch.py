"""C40: register the TX40 distribution and the O27 grid proposal."""
from pathlib import Path

DEC = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"

BLOCK = """
## O27 - TX40 distribution and grid proposal (2026-10-01, C40)

- Source: w3_inspect8 (archived), Brazil thermal units, plants x GCM, delta in days
  per year (median, p90, max), SSP1-2.6 / SSP3-7.0 / SSP5-8.5, as pasted:
  - dTX35: 18.9, 70.9, 206.2 / 36.7, 122.0, 283.9 / 54.1, 158.3, 297.5.
  - dTX40: 0.1, 5.2, 58.1 / 0.3, 13.5, 97.8 / 1.3, 32.2, 137.9.
- Operating fleet, share of GW with dTX40 >= threshold, median [min-max] over GCMs:
  5 d: 7 [2-26] / 10 [7-38] / 21 [16-43]; 10 d: 2 [0-12] / 6 [3-31] / 15 [9-39];
  20 d: 0 [0-4] / 2 [1-24] / 6 [3-34]; 30 d: 0 [0-2] / 0 [0-13] / 4 [2-29].
- Proposal (assistant, not decided): grid 1, 2, 5, 10, 20, 30 d. TX40 is read as
  the shape of the curve, not as a replacement of the TX35 headline. Decision on
  the grid, or on not reporting TX40: TO BE DEFINED by the author.

## Lint note (C40)

- heat_curves.py was committed in 5ff7947 with an unused pandas import (ruff F401),
  because the closing lock did not require a clean lint. Fixed in this step.
  Rule from now on: the lock includes ruff on the files of the step.

## Status updates appended 2026-10-01 (C40)

- O27 distribution registered; grid pending. Axis 1 tables complete except the
  TX40 grid and the final n_boot.
"""

txt = DEC.read_text(encoding="utf-8")
if "## O27 - TX40 distribution" in txt:
    print("ABORT: C40 block already present")
    raise SystemExit(1)
with open(DEC, "a", encoding="utf-8") as fh:
    fh.write(BLOCK)
print("appended: O27 distribution, lint note")