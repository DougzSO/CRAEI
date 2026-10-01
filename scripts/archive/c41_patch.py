"""C41: close O27 (TX40 grid) and register Axis 2 facts seen before W4a."""
from pathlib import Path

DEC = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"

BLOCK = """
## O27 - closed (2026-10-01, C41)

- Grid accepted by the author: 1, 2, 5, 10, 20, 30 d for dTX40. Table
  w3_tx40_curves.csv (script w3_tx40.py): GW share per group, fleet, scenario with
  min, median, max over GCMs; no bootstrap (label not_computed). At 10, 20 and
  30 d it reproduces the metric_TX40 rows of w3_heat_sensitivity.csv.
- TX40 is read as the shape of the curve, not as a replacement of the TX35
  headline.

## Axis 2 facts seen before W4a (2026-10-01, C41; from pasted output)

- spei.parquet: 28,001,820 rows; columns id, model, scenario, period, month,
  SPEI_12, distribution, SPI_12, SPEI_3, scale. scale takes catchment and cell;
  distribution takes loglogistic and pearson3. The id is a hash; its link to
  plant_uid was not seen in this step.
- plant_units, Brazil hydro, operating: reservoir 73.42 GW, run-of-river 36.24
  GW. The largest plant is 14,000 MW (version a of D82); the second and third
  are 11,233 and 8,535 MW. Version b needs a 7,000 MW override for Itaipu, taken
  from fleet_brazil.csv.
- plant_hazards, drought: f_d_spei12 for 394 reservoir, 261 run-of-river and
  1,280 water-dependent thermal plants (three countries); f_d_spei3 for the 261
  run-of-river only. baseline_value and future_value are in percent; ratio is
  unitless (c23d report).
- c23d null: block bootstrap 18.88% over 1,991 defined draws of 2,000 (0.45% of
  draws had zero baseline F_D, so R_D is undefined); white noise 1.80% over 2,000.
  White noise ignores the 12-month overlap of SPEI-12, which is consistent with
  its role as lower limit (D83) and must be stated in the text.

## Status updates appended 2026-10-01 (C41)

- O27 closed. Axis 1 tables complete except the final n_boot (author decision).
  W4a is next, after reading the null code of c23d.
"""

txt = DEC.read_text(encoding="utf-8")
if "## O27 - closed" in txt:
    print("ABORT: C41 block already present")
    raise SystemExit(1)
with open(DEC, "a", encoding="utf-8") as fh:
    fh.write(BLOCK)
print("appended: O27 closed, Axis 2 facts")