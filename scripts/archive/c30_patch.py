"""C30 one-shot patch (append-only): D83-D85 + status in DECISIONS.md, ruff exclude."""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "DECISIONS.md"
PYPROJECT = ROOT / "pyproject.toml"


def build_block(h: str, today: str) -> str:
    lines = [
        "",
        f"{h} D83 - Null for the drought excess: bootstrap reference, block range (O23)",
        "",
        f"- Status: accepted by the author ({today}). Resolves O23.",
        "- Decision:",
        "  1. The reference null stays the block bootstrap of c23d (12-month blocks,",
        "     2,000 simulations, seed 23, pool of 1,110 series): R_D >= 2 by chance",
        "     in 18.88% of cases.",
        "  2. Sensitivity to block length: 12, 24, 36 and 60 months, same pool,",
        "     simulations and seed. The excess over the null is reported as a range.",
        "  3. Bounds: AR(1) of c23c (phi = 0.9291, 200 series, 26.12%) as the upper",
        "     reference; white noise (1.80%) as the lower reference.",
        "- Caveats:",
        "  - The rationale for replacing AR(1) by the bootstrap is not in the repo (D76).",
        "  - Hypothesis, not a finding: 12-month blocks break persistence beyond 12",
        "    months, which would understate the null and overstate the excess.",
        "    The block-size sensitivity is the test of this hypothesis.",
        "  - With n = 360 months, 60-month blocks give only 6 blocks per series.",
        "    Check in W4 that the resampling is still meaningful.",
        "- Results of the sensitivity: TO BE DEFINED (W4/W5).",
        "",
        f"{h} D84 - Validation reference files for PRT under version control (O24)",
        "",
        f"- Status: accepted in part, conditional ({today}).",
        "- Decision: force-add only the two PRT reference files read by",
        "  scripts/22_validate_ren_iph.py:",
        "  - data/validation/ren_iph_reference_apa.csv",
        "  - data/validation/ren_iph_reference_annual.csv",
        "- Condition: first confirm that the source (ERSE/APA) allows redistribution.",
        "  Confirmation: TO BE DEFINED. Until then both files stay untracked.",
        "- `.gitignore` is not changed (data/ stays ignored); this is an explicit",
        "  exception through `git add -f`. No other file under data/ is touched.",
        "- Both files must be included in the CRAEI_backup copy.",
        "",
        f"{h} D85 - Principle: always report ranges and test sensitivity",
        "",
        f"- Status: accepted by the author ({today}). Applies to every result.",
        "- Rules:",
        "  1. Report a range, not a single value, and state where the range comes from.",
        "  2. Across GCMs: minimum, median and maximum over the 5 GCMs, plus sign",
        "     agreement where it applies.",
        "  3. Null model: block-size sensitivity (D83) with AR(1) and white noise bounds.",
        "  4. Itaipu: version b (Brazilian share) as headline, version a (whole asset)",
        "     as sensitivity (D82).",
        "  5. Leave-one-out and SPI x SPEI are reported next to the headline.",
        "  6. Open analytical choices (e.g. O16, O17) get a sensitivity run, not a",
        "     silent default.",
        "- A headline value is one flagged choice, with its range beside it.",
        "- Code follows the same rule: a choice without a sensitivity check is listed",
        "  as an open item.",
        "",
        f"{h} Status updates appended {today}",
        "",
        "- O22: closed by D82 (the index at the top may still list it as open; D82",
        "  prevails).",
        "- O23: accepted, registered as D83.",
        "- O24: accepted in part, registered as D84 (pending the licence check).",
        "- Principle of ranges and sensitivity: registered as D85.",
        "- D80 and D81 remain `proposed`.",
        "",
    ]
    return "\n".join(lines)


def append_text(path: Path, block: str) -> None:
    raw = path.read_bytes()
    crlf = b"\r\n" in raw
    if not raw.decode("utf-8").endswith("\n"):
        block = "\n" + block
    if crlf:
        block = block.replace("\n", "\r\n")
    path.write_bytes(raw + block.encode("utf-8"))


def patch_decisions() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    if re.search(r"^\W*D8[345]\b", text, re.M):
        sys.exit("ABORT: D83/D84/D85 already present in DECISIONS.md")
    m = re.search(r"^(#+)\s.*\bD82\b", text, re.M)
    h = m.group(1) if m else "##"
    print("heading level:", h, "(from D82)" if m else "(default, D82 heading not found)")
    append_text(DECISIONS, build_block(h, dt.date.today().isoformat()))
    print("appended to", DECISIONS)


def patch_pyproject() -> None:
    text = PYPROJECT.read_bytes().decode("utf-8")
    if "extend-exclude" in text:
        print("pyproject: extend-exclude already present, skipped")
        return
    nl = "\r\n" if "\r\n" in text else "\n"
    target = "line-length = 150" + nl
    if text.count(target) != 1:
        sys.exit("ABORT: expected exactly one 'line-length = 150' line in pyproject.toml")
    new = target + 'extend-exclude = ["scripts/archive"]' + nl
    PYPROJECT.write_bytes(text.replace(target, new).encode("utf-8"))
    print("pyproject: extend-exclude inserted")


if __name__ == "__main__":
    patch_decisions()
    patch_pyproject()