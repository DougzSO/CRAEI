"""C35: append section G to the work plan; close O25, restore D84 A, open O26."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "CRAEI_work_plan_v2.md"
DEC = ROOT / "docs" / "DECISIONS.md"
STEPS = ["C25-S1", "C25-S2", "C25-S3", "C28", "C29", "C30", "W3a", "W3b", "W3c",
         "W3d", "W3e", "C32", "C33", "C34"]
FLOOR_RE = re.compile(r"\((\d+ passed, \d+ skipped)\)")

G_HEAD = """
## G. Status update after W3e (2026-10-01, written by C35)

- Sections A-F are history. Their Status columns and the header baseline
  (141 passed) are superseded by this section. Current floor: 164 passed,
  1 skipped (W3e, measured; also measured at HEAD with the uncommitted test
  change stashed, same count).
- Step IDs in practice differ from the old plan: C32 was lint of production
  scripts, C33 a docs patch, C34 the D86 addendum. The old C31-C34 (exposure by
  fuel, curves, harvest, operating vs planned) were delivered as W3a-W3e (curve
  data in W3a); Fig. 3 and Table 1 close in W3f.
- Step to commit map (from git log; floor only where the subject carries it,
  the full floor series is in section F):

| Step | Commit(s) | Floor in subject |
|---|---|---|
"""

G_TAIL = """
Remaining steps (order of work: close all tables, consolidate sensitivities,
then figures, then reproducibility; figure modules only read tables):

| Id | Deliverable | Depends on | Status |
|---|---|---|---|
| W3f-1 | Table 1: GW and % by technology, fuel, fleet, scenario; min, median, max, agreement k, n cells, top-plant share | O17 | ready after O17 proposal |
| W3f-2 | Threshold curves with GCM range (grid per O17) | O17 | ready after O17 proposal |
| W3f-3 | Paired scenario contrast SSP585 - SSP126 per GCM, cell bootstrap, O25 rule | W3d | approved by author |
| W3f-4 | Axis 1 sensitivity table (long): threshold, TX40, planned fleet, GW vs plant count, water vs air | W3a-W3d | ready |
| W4a | Null with blocks 12/24/36/60, AR(1) and white noise as limits | none | ready |
| W4b | Excess over null on plant_units; Itaipu b headline, a sensitivity | W4a | ready |
| W4c | SPI vs SPEI with the same fit scheme (O18) | none | blocked-by-O18 |
| W4d | Leave-one-out of the 5 largest hydro overall, Itaipu a/b (O19) | W4b | ready |
| W4e | GCM range, agreement, hydro cell bootstrap (O20, O21) | W4b | blocked-by-O20 |
| W4f | Axis 2 sensitivities: SPEI threshold, R_D threshold, SPEI-3 vs SPEI-12 | W4b | ready |
| W5 | Sensitivity register (choice, alternatives, effect on headline, range; D85) | W3f, W4 | sketch |
| W6a | Figure I/O and style module; base geography; declare dependencies | O26 | blocked-by-O26 |
| W6b | Fig. 1, Table 1, Table 2, Fig. 3 | W3f, W4d | sketch |
| W6c | Fig. 2, Fig. 4, Fig. 5, ONS supplementary table | W6a | sketch |
| C25-S4 | Dead code by transitive reachability; remaining ruff errors | none | sketch |
| W7 | Reproducibility run, time per step, hashes, tag (D43) | W6 | sketch |
| Ops | External copy, D:\\found.000, PRT licence (author deferred) | author | open |
| Text | Methods, results, discussion, as tables close | W3f, W4, W5 | not started |

Author decisions pending: O17, O20, O26, D80, D81, D87 (proposed), final
n_boot for reported bootstrap tables.
"""

DEC_BLOCK = """
## O25 - closed (2026-10-01, C35)

- Rule accepted by the author: report bootstrap percentiles only if the fleet
  has at least 10 cells and nan_frac = 0; otherwise report the observed value
  and the GCM count, labelled descriptive. The 10-cell cut-off is a convention;
  the stability run did not test it.
- Stability run (w3_bootstrap_stability, 51 rows compared with the reference
  n_boot=2000, seed=86), as pasted: p2.5 and p97.5 differ by up to 2.07 and
  2.87 pp (seed 1, 2000 draws); 1.85 pp (seed 2, 2000, p2.5 only in the paste);
  1.12 and 1.23 pp (seed 86, 5000); 2.34 and 2.36 pp (seed 7, 5000). Median
  absolute difference 0.22 to 0.60 pp.
- Consequence: bounds are reported in whole pp and are indicative; seed-level
  differences of 2 to 3 pp remain in the extremes. Final n_boot for reported
  tables: TO BE DEFINED by the author (5000 is a candidate).
- The paired scenario contrast (same draws) was approved for W3f-3.

## D84 addendum 2 - option A restored (2026-10-01, C35)

- Option B (version the two PRT CSVs) is reverted to A. The licence was not
  confirmed. The files stay git-ignored (data/ in .gitignore; git check-ignore
  confirmed for both). No git add -f.
- Checked: tests/test_validation_ren_iph.py has no csv, read_, tmp_path or
  Path( reference; tests call the functions on in-memory frames, so the suite
  does not need the files. The article is Brazil only.
- Source per file headers: APA (bulletin of 30/06/2018, Table 7) and ERSE/REN.
  How to obtain the files: TO BE DEFINED by the author.

## O26 - Base geography for maps (open)

- matplotlib 3.10.8 and geopandas 1.1.2 import, but neither is declared in
  pyproject.toml (requirements files not checked). No .shp, .geojson or .gpkg
  was found under ..\\data. Source of Brazil and state boundaries: TO BE DEFINED
  by the author. Blocks W6a and the maps (Fig. 2, Fig. 4).

## Status updates appended 2026-10-01 (C35)

- Work plan section G added (commit map, floor 164, remaining steps).
- O25 closed, D84 option A restored, O26 opened. D80, D81 and D87 remain
  proposed; D80 and D81 text was not re-read in this step.
"""


def commit_rows():
    res = subprocess.run(["git", "log", "--format=%h|%s"], cwd=ROOT, check=True,
                         capture_output=True, text=True, encoding="utf-8")
    log = [ln.split("|", 1) for ln in res.stdout.splitlines() if "|" in ln]
    rows = []
    for key in STEPS:
        pat = re.compile(r"(?<![\w-])" + re.escape(key) + r"(?![\w-])")
        hits = [(h, s) for h, s in log if pat.search(s)]
        hashes = ", ".join(h for h, _ in reversed(hits)) or "not found"
        floors = [m.group(1) for _, s in hits for m in [FLOOR_RE.search(s)] if m]
        floor = floors[0] if floors else "-"
        rows.append("| " + key + " | " + hashes + " | " + floor + " |")
    return rows


def append(path, text):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def main():
    plan = PLAN.read_text(encoding="utf-8")
    dec = DEC.read_text(encoding="utf-8")
    if "## G. Status update after W3e" in plan or "## O25 - closed" in dec:
        print("ABORT: C35 blocks already present")
        return 1
    if "## O26 " in dec:
        print("ABORT: O26 already exists")
        return 1
    rows = commit_rows()
    append(PLAN, G_HEAD + "\n".join(rows) + "\n" + G_TAIL)
    append(DEC, DEC_BLOCK)
    print("\n".join(rows))
    print("appended: work plan section G; DECISIONS O25 closed, D84 A, O26")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())