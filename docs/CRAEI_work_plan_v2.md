# CRAEI work plan v2

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
| C24 | bd7184d | docs v2 (SCOPE, work plan, status indexes, METHODS_SPEC v2) |

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
| C49 | Diagnose D:\found.000 (Get-PhysicalDisk, Repair-Volume -Scan) | ready |
| C50 | Backlog for article 2 / data descriptor: IND, PRT, compound, H3, H4; gfdl tasmin 1981_1990 cache gap (re-download about 2 GB only for a global thermal extension) | sketch |

## C. Open items tracked here
O16 (harvest-season metric), O17 (operating vs planned metric, curve grid), O18 (SPI vs SPEI), O19 (leave-one-out), O20 (thermal bucket in Fig 5), O21 (excess uncertainty).

## D. Revision after C26 (2026-09-30): W3-W5 are promotions of existing prototypes

Prototype outputs live in data/outputs/audit/c23/c23d/ (script scripts/c23d_checks.py). They are provisional: fuel_group there is the per-plant mode over plants.parquet (gas and oil merged), so it inherits D78/D79 errors (e.g. bioenergy operating 20.57 GW vs 17.43 GW per unit; coal 5.14 vs 3.00).

| Prototype (c23d item) | Provisional finding | Promoted by | Change vs prototype |
|---|---|---|---|
| 2-3 null and excess over null | null R_D>=2: 18.88% (block bootstrap), 1.80% (white noise) | C30 | rationale for null to be restated (D76) |
| 4 SPI-12 vs SPEI-12 | hydro_reservoir SPEI 53.0/49.8/76.5%, SPI 41.4/22.1/50.8% (SSP126/370/585) | C35 | resolve fit-scheme confound (O18) |
| 5 sign agreement | hydro 1-3 of 5 GCMs; thermal water-dependent 4-5 of 5 | C36 | add O21 uncertainty |
| 6 fuel x fleet TX35 | planned >= operating (bioenergy 41 to 62% SSP126) | C31 | use plant_units, split gas/oil (D77), verify definition of tx35_gw_pct |
| 7 leave-one-out | removing Itaipu: 53.0 to 62.1 / 49.8 to 61.6 / 76.5 to 71.0% | C37 | prototype removed the largest per bucket (3 reservoir + 2 run-of-river), not the 5 largest overall (O19); Itaipu treatment per O22 |

Open items now tracked: O16-O22. Commands C27 (fuel x tech x fleet per unit) and C28 (plant_units) come first; C29-C37 start only after C28 passes pytest and the regression gate.

