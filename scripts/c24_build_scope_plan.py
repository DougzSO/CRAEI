"""C24 build B: SCOPE.md and CRAEI_work_plan_v2.md + cross-checks."""
import pathlib
import re

DOCS = pathlib.Path("docs")

SCOPE = """# SCOPE (v2)

## Research question
How does climate change alter heat and drought exposure of the Brazilian power fleet at plant level, and does current planning site new capacity in conditions that will get worse? Exposure only: never impact, loss or vulnerability (L03, L23).

## Two axes
- **Axis 1 (main).** Heat (TX35) exposure of the thermal fleet by fuel, operating vs planned, 5 GCMs, 3 SSPs. Novelty: the breakdown by fuel and the operating-vs-planned comparison.
- **Axis 2 (secondary).** Hydro drought exposure (SPEI-12 at catchment scale), reported honestly: excess over an internal-variability null, GCM spread and agreement, SPI vs SPEI, leave-one-out of the largest plants.

## In and out of scope
| Item | Status | Reason |
|---|---|---|
| Brazil | in | single-country article (D71) |
| India, Portugal | out (pipeline kept) | second article or data descriptor |
| Compound drought-heat metric | out (D72) | not part of the two axes |
| H3 Aqueduct, H4 precipitation | out (D74) | Aqueduct inconsistent with ISIMIP3b (L06, L13); neither serves the axes |
| Solar, wind | out | no metric / low confidence (D04, L18) |
| Flooding | out | no data |
| Composite score | out | D05 |
| ONS validation | supplementary (D73) | weak national result (rho 0.361, CI 0.027-0.811); strengthens honesty of Axis 2 at zero cost |

## Article structure
Introduction; Data and methods (ISIMIP3b, 5 GCMs, 3 SSPs, continuous hazards, internal-variability null); Results: Fig 1 fleet and capacity by technology and fuel; Fig 2 TX35 exposure maps per thermal plant by fuel; Fig 3 heat-threshold curves (GW fraction vs dTX35), operating vs planned; Fig 4 drought maps (SPEI and SPI side by side) per hydro plant; Fig 5 excess over null by bucket and scenario with GCM range; Table 1 GW fraction exposed by technology, fuel and scenario (operating and planned); Table 2 leave-one-out of the 5 largest hydro plants; Discussion (planning implications for gas and bioenergy; limits: Hargreaves, validation, effective n; drought as a mixed signal); Conclusion.

## Target journals
Climate Risk Management, Renewable Energy, Applied Energy; Earth's Future if the planning component is strong (D75).

## Hypotheses (all untested)
| Id | Statement | Falsified if | Data | Status |
|---|---|---|---|---|
| HA1 | Bioenergy thermal plants have higher GW-weighted dTX35 than gas plants | median difference is not positive, or is smaller than the GCM range | plant_hazards + plant_units (C31) | untested |
| HA2 | Planned thermal capacity (mostly gas) sits in cells with higher dTX35 than the operating fleet | planned GW share above the class is not above the operating share, beyond the GCM range | C31, C34 (O17) | untested |
| HA3 | Heat exposure of the thermal fleet grows consistently across GCMs | fewer than 4 of 5 GCMs agree over most thermal GW | C31 | untested |
| HA4 | Hydro drought exposure exceeds the internal-variability null in every SSP | excess is not positive in the median, or the GCM range crosses zero over most capacity | C30, C36 | partially seen (see below) |
| HA5 | GCM agreement on the sign of drought change is weak | at least 4 of 5 agree over most hydro GW | C36 | untested |
| HA6 | SPI and SPEI give materially different hydro exposure | difference within the GCM range | C35 (O18) | untested |
| HA7 | The hydro headline is sensitive to the largest plants | removal of any of the 5 changes the share by less than the GCM range | C37 (O19) | untested |

Preliminary reading of c23d_report.md (not a result): median excess over the block-bootstrap null is 31-60 points for hydro, but the GCM minimum is below the null for hydro_reservoir SSP1-2.6 (15.7% vs 18.88%) and for thermal_water_dependent SSP3-7.0 (2.3%). HA4 is therefore not yet supported at the level of every GCM.

## Claim-language rules
Use exposure, never impact, vulnerability or generation loss. Fuel differences are reported as siting-driven exposure (L23). Bagasse is a declared proxy (L24). Excess over null is descriptive (L26).

## Reviewer-risk notes
1. **Exposure vs vulnerability by fuel.** Differences between fuels come from where plants are, not from the technology.
2. **Bagasse seasonality.** Operation is concentrated in the harvest season; annual TX35 may not represent it. Monthly n35 exists in indices_daily.parquet, so a seasonal variant needs no climate reprocessing (O16).
3. **Operating vs planned.** The central claim needs this comparison in Table 1 and Fig 3 (O17).

## Pending verification
- Mixed-status plants: 5 thermal plants carry the wrong fleet in plants.parquet (net +3.55/-3.55 GW); fixed via plant_units (D78, C28).
- Binational hydro (Itaipu): full capacity counted as Brazilian? (L30, C26).
- Fuel facts: gas incl. LNG (19.32 GW) exceeds bioenergy (17.43 GW) in operating GW; bioenergy is the largest renewable-labelled thermal group. The scope text must not say bioenergy is the largest thermal fuel.
- c23d SPI and leave-one-out result CSVs not yet read (C26).
- SPI fit scheme differs from SPEI (O18).

## What stays in the pipeline for article 2
IND and PRT results, compound metric, H3 Aqueduct, H4 precipitation, solar rows, REN/DGEG validation, EM-DAT descriptive.
"""

PLAN = """# CRAEI work plan v2

Replaces PROGRESS.json (frozen at docs/archive/PROGRESS_v1.json). Old command numbers are frozen; new commands start at C26 (C25 keeps its old definition). Rules: no calculation in figure modules; after any change touching plants or hazards run pytest (baseline 141 passed, 1 skipped) and scripts/c23b_regression_gate.py (8/8 PASS); never commit without author authorization; Brazil filter at table level; documents in English.

## A. Inherited, closed
| Block | Commit | Summary (detail in DECISIONS) |
|---|---|---|
| P0 C01-C06 | 39afbb9 | bootstrap, CI |
| P1 C07-C09 | 3933799 | blocking verifications |
| P2 C10-C12 | 5b5d785, 47b95ea | ISIMIP acquisition 60/60 jobs, 180 crops |
| P3 C13-C14 | 99dd494 | plant inventory, spatial mapping |
| P4 C15-C18 | 1e7e70a | heat and drought indices, SPEI D54/D55, plant_hazards |
| P5 C19-C20 | 241a256 | exposure aggregation |
| C21, C22 | see git log | validation, compound closure (compound now out of scope) |
| C23-B | 18ca66e, tag pre-cleanup | raw-data reorganization, archives, gate 8/8 |
| C24 | pending commit, tag pre-docs-v2 | docs v2 |

## B. New phases
Status: done, ready, sketch, blocked-by-O-xx.

### W1 Read-only verifications
| Id | Objective | Inputs | Outputs | Acceptance | Deps | Status |
|---|---|---|---|---|---|---|
| C26 | Confirm mixed-status mechanism and tech_class/hydro_type aggregation in plants.py; check binational plants (Itaipu) against GEM per-country capacity; read c23d_3/4/7 CSVs | GEM xlsx, plants.py, c23d CSVs | report in data/outputs/audit/c26/ | reproduces +3.55/-3.55 GW; Itaipu Brazilian share stated; SPI and LOO numbers listed | none | ready |
| C27 | Brazil fuel x tech x fleet table (GW and plant counts) with the D77 rule | GEM xlsx | CSV + report | totals 47.67 / 17.31 / 31.04 GW; D77 reference values reproduced | C26 | ready |

### W2 Pipeline additions
| Id | Objective | Inputs | Outputs | Acceptance | Deps | Status |
|---|---|---|---|---|---|---|
| C28 | Build plant_units.parquet (D77, D78); plants.parquet untouched | GEM xlsx, plants.parquet | scripts/05b_plant_units.py, plant_units.parquet, tests | unit sums per plant equal plants.capacity_mw except documented cases; fleet GW equal GEM; gate 8/8; pytest at least 141 + new | C27 | ready |
| C25 | src/ cleanup in slices S1-S4 (lint, FutureWarnings in aggregate.py, remove compound/audit modules and readers, dead code), report first | src/, scripts/ | docs/c25_src_report.md, slices | pytest and gate after every slice; no numerical change | C28 | sketch |

### W3 Null and excess
| Id | Objective | Inputs | Outputs | Acceptance | Deps | Status |
|---|---|---|---|---|---|---|
| C30 | Promote c23d null and excess to production, with tests; quote c23d section 1 rationale | c23d_checks.py, spei.parquet, plant_hazards | scripts/28_null_excess.py, null table | reproduces 18.88% and 1.80% (seed 23, N_SIM 2000) and the c23d excess table | C28 | ready |

### W4 Heat by fuel
| Id | Objective | Inputs | Outputs | Acceptance | Deps | Status |
|---|---|---|---|---|---|---|
| C29 | Fleet and capacity by technology and fuel (Fig 1 data) | plant_units | CSV | operating total 47.67 GW thermal, 109.67 GW hydro (or Brazilian share, L30) | C28 | ready |
| C31 | Exposure by fuel, fleet, scenario, model (class dTX35 >= 30); median, range, agreement | plant_hazards h1, plant_units | table | no plant dropped; GW totals reconcile with C29 | C28 | ready |
| C32 | Threshold curves GW fraction vs dTX35 | same | table | curve at 30 equals C31 | C31, O17 | blocked-by-O17 |
| C33 | Harvest-season heat variant | indices_daily n35 | table | windows as chosen in O16 | C31 | blocked-by-O16 |
| C34 | Operating vs planned comparison with uncertainty | C31 | table | metric as chosen in O17 | C31 | blocked-by-O17 |

### W5 Drought axis
| Id | Objective | Inputs | Outputs | Acceptance | Deps | Status |
|---|---|---|---|---|---|---|
| C35 | SPI vs SPEI per hydro plant | spei.parquet | table | resolves fit-scheme confound and null per O18 | C30 | blocked-by-O18 |
| C36 | Excess over null with GCM range and agreement | C30 table, plant_hazards | table | metric as chosen in O20, O21 | C30 | blocked-by-O21 |
| C37 | Leave-one-out of the 5 largest hydro plants, promoted from c23d item 7 | plant_hazards, plants | table | matches c23d_7 CSV; binational treatment per L30 | C26, C30 | blocked-by-O19 |

### W6 Tables and figures (no calculation in figure modules)
| Id | Objective | Deps | Status |
|---|---|---|---|
| C38 | Table 1 | C31, C34 | sketch |
| C39 | Table 2 | C37 | sketch |
| C40 | Figure I/O and style module | none | sketch |
| C41 | Fig 1 | C29, C40 | sketch |
| C42 | Fig 2 | C31, C40 | sketch |
| C43 | Fig 3 | C32, C34, C40 | sketch |
| C44 | Fig 4 | C35, C40 | sketch |
| C45 | Fig 5 | C36, C40 | sketch |
| C46 | Supplementary ONS validation table/figure (validation.csv exists) | C40 | sketch |

### W7 Reproducibility
| Id | Objective | Acceptance | Deps | Status |
|---|---|---|---|---|
| C47 | Full run, time per step on declared hardware, hashes, tag (D43) | times reported, no ceiling; hashes identical | W6 | sketch |

### W8 Operations and backlog
| Id | Objective | Status |
|---|---|---|
| C48 | External copy of CRAEI_raw_data and CRAEI_backup (single disk D:) | ready |
| C49 | Diagnose D:\\found.000 (Get-PhysicalDisk, Repair-Volume -Scan) | ready |
| C50 | Backlog for article 2 / data descriptor: IND, PRT, compound, H3, H4; gfdl tasmin 1981_1990 cache gap (re-download about 2 GB only for a global thermal extension) | sketch |

## C. Open items tracked here
O16 (harvest-season metric), O17 (operating vs planned metric, curve grid), O18 (SPI vs SPEI), O19 (leave-one-out), O20 (thermal bucket in Fig 5), O21 (excess uncertainty).
"""

for name, txt in (("SCOPE.md", SCOPE), ("CRAEI_work_plan_v2.md", PLAN)):
    (DOCS / name).write_bytes(txt.encode("utf-8"))
    print("written", DOCS / name)

# ---- cross-checks
plan = PLAN
dec = (DOCS / "DECISIONS.md").read_text(encoding="utf-8-sig")
spec = (DOCS / "METHODS_SPEC.md").read_text(encoding="utf-8-sig")
for o in ("O16", "O17", "O18", "O19", "O20", "O21"):
    assert o in plan, f"{o} missing in work plan"
    assert f"| {o} |" in dec, f"{o} missing in DECISIONS"
for l in spec.splitlines():
    if "TO BE DEFINED" in l:
        assert re.search(r"O\d+", l), f"TBD without O-id: {l[:80]}"
for f in ("SCOPE.md", "CRAEI_work_plan_v2.md", "DECISIONS.md", "LIMITATIONS.md", "METHODS_SPEC.md"):
    assert "\u00c2\u00a7" not in (DOCS / f).read_text(encoding="utf-8-sig"), f"mojibake in {f}"
print("cross-checks OK")

# ---- PROGRESS.json readers
hits = []
roots = [pathlib.Path("scripts"), pathlib.Path("src"), pathlib.Path("tests")]
for r in roots:
    for p in r.rglob("*.py"):
        if "archive" in p.parts or p.name.startswith("c24_"):
            continue
        if "PROGRESS.json" in p.read_text(encoding="utf-8", errors="ignore"):
            hits.append(str(p))
print("code files reading PROGRESS.json:", hits or "none")
cl = pathlib.Path("CLAUDE.md")
if not hits and cl.exists():
    t = cl.read_bytes().decode("utf-8")
    n = t.count("PROGRESS.json")
    cl.write_bytes(t.replace("PROGRESS.json", "docs/CRAEI_work_plan_v2.md").encode("utf-8"))
    print(f"CLAUDE.md: {n} pointer(s) updated")