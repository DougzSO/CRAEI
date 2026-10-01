"""C34 one-shot patch (append-only): W3d results (D86 addendum) and O25."""
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
        f"{h} D86 addendum - W3d cell bootstrap results (O21)",
        "",
        f"- Status: done ({today}). Script w3_bootstrap.py; tables",
        "  w3_heat_bootstrap_shares.csv and w3_heat_bootstrap_paired.csv.",
        "- Setup: cells resampled with replacement, 2,000 draws, seed 86",
        "  (default_rng([seed, group index])), thresholds 20/30/40 d, percentile range",
        "  2.5-97.5. It is a sensitivity to fleet composition, not a confidence interval.",
        "- Unit: per group, the union of the cells of all its fleets, shared by the",
        "  operating and planned fleets in each draw. n_cells therefore differs from the",
        "  W3c count (354 vs 326 for all thermal, operating).",
        "- Check: observed statistics reproduce the W3a tables (243/243 share rows, max",
        "  |diff| 2.84e-14; 162/162 paired rows, max |diff| 4.26e-14; n_planned_ge equal).",
        "- Operating thermal share at 30 d, observed [bootstrap 2.5-97.5]:",
        "  SSP1-2.6 28.38 [18.65, 40.97]; SSP3-7.0 36.27 [25.68, 49.80];",
        "  SSP5-8.5 49.14 [38.00, 64.04].",
        "- Paired planned_all minus operating, all thermal at 30 d, median over GCMs (pp)",
        "  [bootstrap 2.5-97.5]; share of draws > 0; LOCO range:",
        "  - SSP1-2.6: -7.16 [-20.43, 8.28]; 0.17; [-12.04, -3.91].",
        "  - SSP3-7.0: -0.12 [-16.57, 17.13]; 0.51; [-1.87, 2.98].",
        "  - SSP5-8.5: +1.35 [-10.19, 19.73]; 0.70; [-1.10, 6.53].",
        "  All three bootstrap intervals include 0. planned_adv and planned_early also",
        "  include 0 in all scenarios (planned_early SSP1-2.6: -15.30 [-27.06, 1.07]).",
        "- Bioenergy, planned_all minus operating: +13.67 / +15.72 / +11.09 pp, 5 of 5",
        "  GCMs, LOCO ranges 8.45-18.83 / 9.82-20.69 / 5.74-16.21, bootstrap intervals",
        "  [-7.69, 35.12] / [-7.49, 31.50] / [-6.93, 26.61] (planned: 2.1 GW in 42 cells).",
        "  Sign consistent across GCMs and LOCO; the composition range includes 0.",
        "- Reading rules: the share of draws > 0 is not a p-value. Rows whose planned",
        "  fleet has few cells (planned multi-fuel: 1 cell, nan_frac 0.34; planned",
        "  air-only: 3 cells, nan_frac 0.04) give percentiles conditional on drawing a",
        "  planned cell and must not be reported. Nuclear (1 cell) gives NaN.",
        "  The bootstrap median differs from the observed one in concentrated groups",
        "  (gas, SSP5-8.5: 40.40 observed, 43.75 bootstrap median): report the observed",
        "  value and use the bootstrap only for the range.",
        "- Not done: paired scenario contrast (same draws); seed and n_boot stability.",
        "",
        f"{h} O25 - Reporting rule for bootstrap rows (open)",
        "",
        f"- ({today}) Minimum number of cells in the fleet and maximum nan_frac for a",
        "  bootstrap row to be reported. Cut-offs: TO BE DEFINED by the author.",
        "  Suggestion under review: at least 10 cells and nan_frac = 0; below that,",
        "  report only the observed value and the GCM count, labelled descriptive.",
        "- Also open: stability of the percentiles to seed and n_boot, and a paired",
        "  scenario contrast.",
        "",
        f"{h} Status updates appended {today} (C34)",
        "",
        "- D86 addendum: W3d done. O25 opened. D87 stays proposed. O17 stays open, but in",
        "  these runs no definition of the planned fleet separates planned from",
        "  operating at the all-thermal level.",
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
    if "D86 addendum - W3d" in text or re.search(r"^\W*O25\b", text, re.M):
        sys.exit("ABORT: W3d addendum or O25 already present")
    m = re.search(r"^(#+)\s.*\bD82\b", text, re.M)
    h = m.group(1) if m else "##"
    append_text(DECISIONS, build_block(h, dt.date.today().isoformat()))


if __name__ == "__main__":
    main()