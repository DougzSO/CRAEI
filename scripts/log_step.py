"""scripts/log_step.py - append one line to docs/STATUS_LOG.md (append-only).
Usage: python scripts\\log_step.py C27 done "note"
"""
import datetime as dt
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(__file__).resolve().parents[1] / "docs" / "STATUS_LOG.md"
if len(sys.argv) < 4:
    sys.exit("usage: log_step.py <id> <status> <note>")
step, status, note = sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])
new = not p.exists()
with open(p, "a", encoding="utf-8", newline="\n") as f:
    if new:
        f.write("# STATUS LOG (append-only; plan lives in CRAEI_work_plan_v2.md)\n\n"
                "| date | step | status | note |\n|---|---|---|---|\n")
    f.write(f"| {dt.date.today()} | {step} | {status} | {note} |\n")
print("logged:", step, status)