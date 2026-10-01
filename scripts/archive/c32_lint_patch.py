"""C32 one-shot patch: dead code flagged by ruff in scripts/09_consolidate.py."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TARGET = Path(__file__).resolve().parents[1] / "scripts" / "09_consolidate.py"
EDITS = [
    (
        re.compile(r"^ {4}expected = n_water_dep \* 4 \* 2[^\r\n]*$", re.M),
        "    # baseline is folded into ws/bws columns, not extra rows here",
    ),
    (re.compile(r'print\(f"\(baseline bws'), 'print("(baseline bws'),
]


def main() -> None:
    text = TARGET.read_bytes().decode("utf-8")
    for pat, repl in EDITS:
        n = len(pat.findall(text))
        if n != 1:
            sys.exit(f"ABORT: {n} matches for {pat.pattern!r}; nothing written")
        text = pat.sub(lambda _m, r=repl: r, text)
    TARGET.write_bytes(text.encode("utf-8"))
    print("patched", TARGET)


if __name__ == "__main__":
    main()