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

## E. Prototype definitions verified in C27 prep (2026-09-30)

- c23d tx35_gw_pct (c23d_checks.py lines 412-430): exposed = delta TX35 >= 30 days/yr per plant and model; GW share = exposed capacity / group capacity (fuel x fleet), plants without a hazard row count as not exposed and stay in the denominator; reported value = median over the 5 GCMs. Matches D07.
- c23d fuel_group: per-plant mode over units on plants.parquet, gas and oil merged; fleet and capacity inherited from plants.parquet (D78/D79 errors). Provisional only.
- Concentration: with few large plants per group (e.g. 84 gas/oil operating plants) GW shares are discrete and dominated by a handful of plants (gas_oil operating identical in SSP126 and SSP370; coal operating 0.24% of GW vs 10% of plants in SSP126). C31 and Table 1 must report plant-count share and top-plant concentration beside GW share.
- C30 must include the null-sensitivity decision (O23) before Axis 2 numbers are quoted.


## F. Status update after C28/C29 (2026-10-01)

- Done: C27 (unit-level fuel x technology x fleet), C28 (plant_units.parquet, 16 checks), C29 (Brazil fleet table, capacity side of Fig. 1; both O22 versions).
- Test floor verified at this step: 153 passed, 1 skipped. Gate result: see the last STATUS_LOG entry.
- plants.parquet is unchanged; article capacity-by-fleet numbers come from plant_units.parquet (D78-D81).
- Waiting on the author: O24, O22, O23, and review of D80 and D81 (status proposed).
- Next: C25 slices S1-S4 (report first), then W3-W5 (promotion of the c23d prototypes on plant_units).

- Test floor after C25-S3: 143 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3a: 151 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3b: 154 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3c: 157 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3d: 161 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3e: 164 passed, 1 skipped (measured 2026-10-01).

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
| C25-S1 | 007cf6b | - |
| C25-S2 | 8e0bb96 | - |
| C25-S3 | c85044b, d239982 | - |
| C28 | not found | - |
| C29 | 1aed746 | - |
| C30 | 561df2e | - |
| W3a | 8b4cbb8, 05419e7, b01dade | 151 passed, 1 skipped |
| W3b | feab42b | 154 passed, 1 skipped |
| W3c | 9224829 | 157 passed, 1 skipped |
| W3d | 9755e5b, 26f2c53 | 161 passed, 1 skipped |
| W3e | ee27e3d | 164 passed, 1 skipped |
| C32 | f0c8ba6 | - |
| C33 | aa3b4fa | - |
| C34 | 26f2c53 | - |

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
| Ops | External copy, D:\found.000, PRT licence (author deferred) | author | open |
| Text | Methods, results, discussion, as tables close | W3f, W4, W5 | not started |

Author decisions pending: O17, O20, O26, D80, D81, D87 (proposed), final
n_boot for reported bootstrap tables.

- Test floor after W3f-1: 167 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3f-3: 170 passed, 1 skipped (measured 2026-10-01).

## G addendum - status after W3f-3 (2026-10-01, written by C38)

- Done since the section G table: W3f-1 (Table 1, 4f83c3c), W3f-3 (scenario
  contrast, df72c93), W3f-4 (Axis 1 sensitivities, this step; hash in git log).
- Next: W3f-2 (Fig. 3 plotting table from w3_heat_summary and Table 1 bounds),
  then Axis 2 (W4a to W4f).
- O17, O25 and O26 are closed; D80, D81 and D87 are accepted. Pending author
  decisions: final n_boot, O20 (O16 only if a source is given).

- Test floor after W3f-4: 173 passed, 1 skipped (measured 2026-10-01).

## G addendum 2 - status after W3f-4 (2026-10-01, written by C39)

- Done: W3f-4 (009b913), W3f-2 (this step). Axis 1 tables are complete except the
  TX40 grid (O27) and the final n_boot (author decision).
- Next: Axis 2, starting with W4a (null with blocks 12/24/36/60, AR(1) and white
  noise as limits).

- Test floor after W3f-2: 176 passed, 1 skipped (measured 2026-10-01).

- Test floor after W4a: 184 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3f-6: 188 passed, 1 skipped (measured 2026-10-01).

## G addendum 3 - plan after C44 (D88)
| Step | Content | Depends on | Status |
|---|---|---|---|
| W3g | Heat level classes (thermal and hydro; operating, planned), baseline and future classes, class shift, change classes (exclusive delta bins), per GCM, range, k of 5 | O28 | ready |
| W4g | Drought level classes against the null (20,000 simulations, stream [23, 99]); R_D classes with null rates | O29 | ready after pool check |
| W4h | Co-located exposure: 4 x 4 cross-tab, extreme in both, sensitivity high-or-extreme; thermal water-dependent and hydro | W3g, W4g, O32 | sketch |
| W3h | State and macro-region summary (Natural Earth admin1, nearest polygon for points outside) | W3g, W4g | sketch |
| W3f-7 | Planned minus operating under TX40 and plant-count weight | W3 tables | ready |
| W4b-W4f | As before; Itaipu b headline | W4a | ready |
| W3d/W3f-3 at 5,000 | Re-run, replace bootstrap limits | n_boot decision | pending |
| W5 | Sensitivity register, with the new families | W3, W4 | sketch |
| W6 | Figures: Fig 2 and Fig 4 become class maps; new co-exposure figure | W3g, W4g, W4h | after tables |

- Test floor after C44: 188 passed, 1 skipped (measured 2026-10-01).

- Test floor after C45: 188 passed, 1 skipped (measured 2026-10-01).

- Test floor after W3g: 195 passed, 1 skipped (measured 2026-10-01).

- Test floor after C47: 203 passed, 1 skipped (measured 2026-10-01).
