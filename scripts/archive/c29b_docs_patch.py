"""c29b_docs_patch.py - append-only: D82 (resolution of O22) to docs/DECISIONS.md.
One-shot. Usage: python scripts/c29b_docs_patch.py
"""
import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"
raw = p.read_bytes()
txt = raw.decode("utf-8")
if "Resolution of O22" in txt:
    sys.exit("already applied (marker found); nothing written")
last = [ln for ln in txt.splitlines() if ln.strip()][-1]
if not last.startswith("|"):
    sys.exit("last non-empty line is not a table row; aborting")
ids = [int(m) for m in re.findall(r"^\| D(\d+) \|", txt, flags=re.M)]
new_id = "D" + str(max(ids) + 1)
row = (
    f"| {new_id} | Resolution of O22 (Itaipu, binational hydro). Headline: Brazilian share "
    "(version b_brazil_share of scripts/c29_fleet_table.py): Itaipu counted as 7,000 MW "
    "instead of 14,000 MW, hydro operating 102.67 GW. Sensitivity: version a_asset_whole "
    "(109.67 GW). Itaipu also appears in the leave-one-out table under both versions. "
    "Basis: GEM allocates 7,000 MW to Brazil and 7,000 MW to Paraguay, and the thermal "
    "fleet already follows the GEM per-unit allocation, so (b) applies the same criterion. "
    "Location is identical in both versions: hazards are unchanged, only the capacity "
    "weight of Itaipu changes. Verified in outputs/audit/c29/report.md: Itaipu is one "
    "operating unit of 14,000 MW in plant_units, the only Brazilian plant with that "
    "capacity, classed reservoir (73.42 GW reservoir in a, 66.42 GW in b; whether the "
    "class comes from the GEM Technology field or the D11 default was not verified). "
    "Consequences: (1) capacity-weighted results computed from plants.parquet capacities "
    "(c23d: hydro_reservoir 53.0/49.8/76.5%, Itaipu leave-one-out deltas) correspond to "
    "version a and must be recomputed in W5 with plant_units capacities scaled by "
    "inventory.fleet.apply_foreign_share; that the c23d shares are capacity-weighted was "
    "not verified. (2) Panambi (576 MW, 288 MW Brazilian share) is filed under Argentina "
    "and is not added (0.288 GW, 0.28% of 102.67 GW); it stays a limitation (L30). "
    "(3) plants.parquet is unchanged. The status index at the top of this file still "
    f"lists O22 as open; this row prevails. | closed | author delegated to assistant, C29b "
    f"| {dt.date.today()} |\n"
)
with open(p, "a", encoding="utf-8", newline="\n") as f:
    if not raw.endswith(b"\n"):
        f.write("\n")
    f.write(row)
print("appended", new_id)