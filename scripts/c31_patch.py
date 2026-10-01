"""C31 one-shot patch (append-only): D84 option B; test floor line."""
from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "docs" / "DECISIONS.md"
CLAUDE = ROOT / "CLAUDE.md"
PLAN = ROOT / "docs" / "CRAEI_work_plan_v2.md"
FLOOR_RE = re.compile(r"^\d+ passed, \d+ skipped$")


def append_text(path: Path, block: str) -> None:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    if not text.endswith("\n"):
        block = "\n" + block
    if "\r\n" in text:
        block = block.replace("\n", "\r\n")
    path.write_bytes(raw + block.encode("utf-8"))
    print("appended to", path)


def d84() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    if "D84 addendum" in text:
        sys.exit("ABORT: D84 addendum already present")
    m = re.search(r"^(#+)\s.*\bD84\b", text, re.M)
    if not m:
        sys.exit("ABORT: D84 heading not found")
    today = dt.date.today().isoformat()
    lines = [
        "",
        f"{m.group(1)} D84 addendum - option B chosen (O24)",
        "",
        f"- Status: the author chose option B on {today}: version the two PRT",
        "  reference files after the licence check.",
        "- Condition unchanged: written confirmation that the source allows",
        "  redistribution. Record the URL, access date and terms in this entry.",
        "  Confirmation: TO BE DEFINED. `git add -f` has NOT been run.",
        "- Sources named in the CSV headers: APA, Monitorizacao Agrometeorologica e",
        "  Hidrologica, 30 June 2018, Table 7 (monthly series, from REN statistics);",
        "  ERSE/REN (annual series).",
        "- Fallback if redistribution is not allowed or not confirmed: keep both",
        "  files untracked and document the source and table for reconstruction.",
        "- Observed, not edited: the annual CSV source_note has the typo",
        "  'porprodutibilidade' (missing space).",
        "",
    ]
    append_text(DECISIONS, "\n".join(lines))


def floor(summary: str, step: str) -> None:
    if not FLOOR_RE.match(summary):
        sys.exit('ABORT: floor must look like "143 passed, 1 skipped"')
    tag = f"floor after {step}"
    for path in (CLAUDE, PLAN):
        if tag in path.read_text(encoding="utf-8"):
            sys.exit(f"ABORT: {path.name} already has '{tag}'")
    today = dt.date.today().isoformat()
    append_text(
        CLAUDE,
        f"\n- Pytest {tag}: {summary} (measured {today}; supersedes the floor above).\n",
    )
    append_text(PLAN, f"\n- Test {tag}: {summary} (measured {today}).\n")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "d84":
        d84()
    elif mode == "floor" and len(sys.argv) == 4:
        floor(sys.argv[2], sys.argv[3])
    else:
        sys.exit('usage: c31_patch.py d84 | floor "<N passed, M skipped>" <step>')