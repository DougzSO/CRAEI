"""c29_docs_patch.py - append-only: D81 and O24 (DECISIONS.md), section F (work plan),
test-floor note (CLAUDE.md). The pytest string must come from a verified run.
Usage: python scripts/c29_docs_patch.py --pytest "153 passed, 1 skipped"
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
TODAY = dt.date.today()


def append(path: Path, text: str) -> None:
    raw = path.read_bytes()
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        if raw and not raw.endswith(b"\n"):
            f.write("\n")
        f.write(text)
    print("appended to", path.name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pytest", required=True)
    pytest_line = ap.parse_args().pytest

    dec = ROOT / "docs" / "DECISIONS.md"
    txt = dec.read_text(encoding="utf-8")
    if "Addendum to D78 (C28" in txt:
        sys.exit("already applied (marker found); nothing written")
    last = [ln for ln in txt.splitlines() if ln.strip()][-1]
    if not last.startswith("|"):
        sys.exit("last non-empty line of DECISIONS.md is not a table row; aborting")
    d_ids = [int(m) for m in re.findall(r"^\| D(\d+) \|", txt, flags=re.M)]
    o_ids = [int(m) for m in re.findall(r"^\| O(\d+) \|", txt, flags=re.M)]
    if not d_ids or not o_ids:
        sys.exit("could not find existing D or O ids; aborting")
    d_new, o_new = f"D{max(d_ids) + 1}", f"O{max(o_ids) + 1}"

    d_row = (
        f"| {d_new} | Addendum to D78 (C28; source: scripts/05b_plant_units.py, GEM snapshot "
        "2026-08-09). plant_units.parquet is written to data/processed by inventory/units.py: "
        "14,280 rows (one per kept GEM unit; BRA, IND and PRT; all technologies), 12,459 "
        "distinct plant_uid, the same set as plants.parquet; capacity summed per plant_uid "
        "reproduces plants.parquet (max abs diff 0.00 MW). Columns: plant_uid, gem_row, "
        "unit_name, country, fleet, fuel_class, bio_subtype, tech_class, water_dependent, "
        "hydro_type, capacity_mw, gem_unit_id. fleet, fuel_class, bio_subtype and tech_class "
        "are assigned per unit (D79, D80). fuel_class values assigned by the code: coal, "
        "nuclear, bioenergy, gas, oil, multi_fuel, oil_gas_unclassified, hydro, solar, other. "
        "unit_name and gem_unit_id are stored as text because GEM mixes strings and numbers "
        "(the value '--' is kept as is; its meaning was not verified; uniqueness of "
        "gem_unit_id was not verified). gem_row is the row index of the 'Power facilities' "
        "sheet as read by pandas and identifies a unit only within this snapshot. The build "
        "is guarded by 16 checks (3 conservation, 3 fleet totals, 6 operating fuel totals, "
        "agricultural_waste, 3 mixed-plant counts) and writes the parquet only if all pass. "
        "plants.parquet is neither read for values nor written by the build beyond the "
        f"conservation check. | proposed | assistant, C29; pending author review | {TODAY} |\n"
    )
    o_row = (
        f"| {o_new} | data/validation is not versioned. The folder CRAEI/data/validation "
        "holds ren_iph_reference_apa.csv and ren_iph_reference_annual.csv (5,310 bytes "
        "together), read by scripts/22_validate_ren_iph.py (REPO_ROOT/data/validation). "
        ".gitignore ignores data/, so they are not in git. They are not duplicates of "
        "data/raw/validation (hash grouping found only one repeated hash, between "
        "data/raw/validation/ren_iph/2014.json and 2026.json; their content was not "
        "inspected). Options: (a) git add -f the two CSVs; (b) move them to docs/refs or "
        "config and update the script path; (c) back up only in D:. Portugal is "
        "OUT-OF-SCOPE-v2, so urgency is low, but the retained code depends on them. Not "
        f"chosen. | open | author | {TODAY} |\n"
    )
    append(dec, d_row + o_row)

    plan = (
        f"\n## F. Status update after C28/C29 ({TODAY})\n\n"
        "- Done: C27 (unit-level fuel x technology x fleet), C28 (plant_units.parquet, 16 "
        "checks), C29 (Brazil fleet table, capacity side of Fig. 1; both O22 versions).\n"
        f"- Test floor verified at this step: {pytest_line}. Gate result: see the last "
        "STATUS_LOG entry.\n"
        "- plants.parquet is unchanged; article capacity-by-fleet numbers come from "
        "plant_units.parquet (D78-D81).\n"
        f"- Waiting on the author: {o_new}, O22, O23, and review of D80 and {d_new} "
        "(status proposed).\n"
        "- Next: C25 slices S1-S4 (report first), then W3-W5 (promotion of the c23d "
        "prototypes on plant_units).\n"
    )
    append(ROOT / "docs" / "CRAEI_work_plan_v2.md", plan)

    note = (
        f"\n## Test floor and status (updated {TODAY}, C29)\n\n"
        f"- Current pytest floor: {pytest_line} (supersedes any earlier floor in this file).\n"
        "- Status log: docs/STATUS_LOG.md (append-only). Plan: docs/CRAEI_work_plan_v2.md.\n"
    )
    append(ROOT / "CLAUDE.md", note)
    print("new ids:", d_new, o_new)


if __name__ == "__main__":
    main()