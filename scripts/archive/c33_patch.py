"""C33 one-shot patch (append-only): D86, D87 and an O16 note in DECISIONS.md."""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DECISIONS = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"


def build_block(h: str, today: str) -> str:
    lines = [
        "",
        f"{h} D86 - Cell-level influence and composition uncertainty, axis 1 (O19, O21)",
        "",
        f"- Status: accepted by the author ({today}): leave-one-cell-out (LOCO) as the",
        "  main analysis, plus a cluster bootstrap as a sensitivity to fleet composition.",
        "- Why: the hazard is defined per 0.5-degree cell (5 gas plants in 2 cells repeat",
        "  identical delta TX35 values in w3_inspect4) and GEM is the whole inventory,",
        "  not a sample. A bootstrap interval is therefore a sensitivity to composition,",
        "  not a sampling error, and must be labelled so.",
        "- Main (done, W3c): per group x fleet x scenario at 20, 30 and 40 d, the range",
        "  of the GCM-median share when one occupied cell is dropped, the most influential",
        "  cell and its share of the group GW. Table: w3_heat_influence.csv. A group with",
        "  one cell gives NaN with n_cells = 1 (information, not an error).",
        "- Secondary (TO BE DEFINED, W3d): bootstrap over cells. Number of resamples and",
        "  seed to be fixed and reported. It must include the paired planned-minus-",
        "  operating difference per GCM.",
        "- Results at 30 d, operating fleet (W3c output, SSP1-2.6 / SSP3-7.0 / SSP5-8.5):",
        "  - All thermal, 326 cells: median 28.38 / 36.27 / 49.14%; LOCO range",
        "    25.39-30.32 / 33.61-38.75 / 45.66-51.70%; largest cell 4.0 / 4.0 / 6.4% of GW.",
        "  - Gas, 32 cells, SSP1-2.6: median 22.36%, LOCO 13.85-26.48%; top cell",
        "    (-4.75, -44.25) holds 9.87% of the gas GW (shift -8.50 pp).",
        "  - Coal, 5 cells, SSP5-8.5: median 48.21%, LOCO 18.83-67.52%; top cell",
        "    (-3.75, -38.75) holds 36.20% of the coal GW (shift -29.39 pp).",
        "  - Nuclear (operating and planned) and planned multi-fuel: 1 cell, NaN.",
        "- Caveat: LOCO ranges are per fleet. Subtracting fleet medians is not the paired",
        "  planned-minus-operating difference. For all thermal in SSP5-8.5, planned_all",
        "  median 61.64% minus operating 49.14% is 12.5 pp, while the median of the",
        "  paired per-GCM differences is +1.4 pp (W3a). Report the paired difference.",
        "",
        f"{h} D87 - Axis 1 metrics: unit level, threshold grid, GCM agreement (O17)",
        "",
        f"- Status: proposed ({today}). O17 stays open (choice of the planned fleet).",
        "- Unit of analysis: generating unit from plant_units, linked to the plant-level",
        "  TX35 row by plant_uid. Share = exposed capacity / group capacity, per GCM.",
        "- Thresholds: 10, 20, 30, 40, 50, 60, 80, 100 d. The 30 d class is one point of",
        "  the curve. The grid is the assistant's choice, not yet the author's.",
        "- Fleets: operating, planned_adv, planned_early and planned_all (the two pooled).",
        "- Reported per group, fleet and scenario: min / median / max over the 5 GCMs",
        "  (w3_heat_summary.csv), the share per GCM, GW exposed in >= k of 5 GCMs with",
        "  each plant counted once (w3_heat_agreement.csv) and LOCO (D86).",
        "- Denominator: verified, no Brazilian unit lacks a hazard row (0 of 7,808);",
        "  745 thermal plants have 15 TX35 rows each, no NaN, no duplicated key.",
        "- Results at 30 d, operating, all thermal (47.67 GW; 665 plants in the",
        "  agreement table), SSP1-2.6 / SSP3-7.0 / SSP5-8.5:",
        "  - per GCM: min 19.1 / 31.4 / 42.3, median 28.4 / 36.3 / 49.1,",
        "    max 49.3 / 77.0 / 92.2 %.",
        "  - exposed in >= 1 / >= 3 / 5 of 5 GCMs: 49.3 / 29.0 / 14.4 (SSP1-2.6),",
        "    77.0 / 36.7 / 31.2 (SSP3-7.0), 92.2 / 54.8 / 36.3 (SSP5-8.5).",
        "  - The union at SSP1-2.6 (49.3) exceeds the intersection at SSP5-8.5 (36.3).",
        "- Planned minus operating, all thermal at 30 d: planned_all median difference",
        "  -7.2 / -0.1 / +1.4 pp, planned >= operating in 1 / 2 / 5 of 5 GCMs;",
        "  planned_adv 4 / 4 / 3 of 5; planned_early 1 / 2 / 3 of 5. The reading depends",
        "  on the planned-fleet definition, which is why O17 is not closed.",
        "- Monthly n35 summed over the 12 months reproduces annual tx35 (1,122,600 keys,",
        "  max difference 0.000000), so a seasonal window (O16) needs no new acquisition.",
        "- The ranges are structural (5 GCMs are not a probabilistic sample); do not call",
        "  them confidence intervals.",
        "",
        f"{h} O16 update - harvest window source unknown",
        "",
        f"- ({today}) The author does not know a source for the harvest window.",
        "  Window: TO BE DEFINED. It applies only to agricultural_waste (12.08 of the",
        "  17.43 GW operating bioenergy), not to pulp and paper.",
        "- Planned step (W3e), independent of any source: monthly delta N35 profile of the",
        "  bioenergy cells. Window sensitivity (whole year vs harvest window) only once a",
        "  cited source is found.",
        "",
        f"{h} Status updates appended {today} (C33)",
        "",
        "- D86 accepted; D87 proposed. O21: LOCO done, cluster bootstrap pending (W3d).",
        "- O16: source unknown. O17: open. D80 and D81 remain `proposed`.",
        "",
    ]
    return "\n".join(lines)


def append_text(path: Path, block: str) -> None:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    if not text.endswith("\n"):
        block = "\n" + block
    if "\r\n" in text:
        block = block.replace("\n", "\r\n")
    path.write_bytes(raw + block.encode("utf-8"))
    print("appended to", path)


def main() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    if re.search(r"^\W*D8[67]\b", text, re.M):
        sys.exit("ABORT: D86/D87 already present in DECISIONS.md")
    m = re.search(r"^(#+)\s.*\bD82\b", text, re.M)
    h = m.group(1) if m else "##"
    append_text(DECISIONS, build_block(h, dt.date.today().isoformat()))


if __name__ == "__main__":
    main()