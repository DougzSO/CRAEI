"""c25_s2_patch.py - fix the 3 FutureWarnings in exposure/aggregate.py (C25-S2).

One-shot: each target line must occur exactly once, else nothing is written.
File line endings are preserved. Usage: python scripts/c25_s2_patch.py
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
PATH = Path(__file__).resolve().parents[1] / "src" / "craei" / "exposure" / "aggregate.py"

OLD1 = '    merged["exposed"] = merged["exposed"].fillna(False).astype(bool)'
NEW1 = '    merged["exposed"] = merged["exposed"].eq(True)'
OLD2 = '    agree_with_cap["agrees"] = agree_with_cap["agrees"].fillna(False).astype(bool)'
NEW2 = '    agree_with_cap["agrees"] = agree_with_cap["agrees"].eq(True)'
OLD3 = "    out = pd.concat([heat, drought], ignore_index=True)"
NEW3 = [
    "    parts = [d for d in (heat, drought) if len(d)]",
    "    out = pd.concat(parts, ignore_index=True) if parts else heat.copy()",
]


def main():
    with open(PATH, encoding="utf-8", newline="") as f:
        txt = f.read()
    nl = "\r\n" if "\r\n" in txt else "\n"
    counts = {name: txt.count(old) for name, old in
              (("line174", OLD1), ("line204", OLD2), ("line272", OLD3))}
    print("occurrences:", counts)
    if any(c != 1 for c in counts.values()):
        sys.exit("aborted: each target must occur exactly once; nothing written")
    txt = txt.replace(OLD1, NEW1).replace(OLD2, NEW2).replace(OLD3, nl.join(NEW3))
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    print("patched:", PATH)


if __name__ == "__main__":
    main()