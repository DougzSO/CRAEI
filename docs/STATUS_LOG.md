# STATUS LOG (append-only; plan lives in CRAEI_work_plan_v2.md)

| date | step | status | note |
|---|---|---|---|
| 2026-10-01 | C27 | done | unit-level fuel x tech x fleet table (c27_fuel_units.py); D77 reference checks 10/10 PASS; O23 and work plan section E added |
| 2026-10-01 | C27b | done | cleanup: caches removed, 4 root stdout files moved to audit/stdout_root, 20 root logs zipped to CRAEI_backup/logs and verified; pytest 141 passed 1 skipped and gate 8/8 PASS afterwards |
| 2026-10-01 | C27c | done | addendum to D79 appended to DECISIONS.md (status proposed, pending author review) |
| 2026-10-01 | C27d | done | one-shot scripts (c24, c26, c27 patches and readonly) moved to scripts/archive via git mv |
| 2026-10-01 | C28 | done | plant_units.parquet built by unit (inventory/units.py, scripts/05b_plant_units.py); 16/16 checks PASS; capacity per plant_uid == plants.parquet (12459 plants); text columns cast for parquet; ruff line-length 100->120; pytest 149 passed 1 skipped; gate 8/8 |
| 2026-10-01 | C29 | done | Brazil fleet table by tech x fuel x fleet from plant_units (inventory/fleet.py, scripts/c29_fleet_table.py), both O22 versions side by side; D81 and O24 registered; pytest 153 passed, 1 skipped; gate lines checked |
| 2026-10-01 | C29b | done | O22 resolved as D82: headline Brazilian share 7 GW, sensitivity whole asset; c23d capacity-weighted numbers to be recomputed in W5 |
| 2026-10-01 | C25-S2 | done | 3 FutureWarnings fixed in exposure/aggregate.py (eq(True) x2, concat skips empty blocks); pytest 153 passed, 1 skipped; gate checked; no numeric change |
| 2026-10-01 | C30 | done | D83-D85 appended to DECISIONS.md; ruff extend-exclude scripts/archive; pytest 153 passed, 1 skipped, 4 warnings in 7.65s |
| 2026-10-01 | C25-S1 | done | ruff extend-exclude scripts/archive; import order fixed in c27b_cleanup.py and log_step.py; pytest 153 passed, 1 skipped, 4 warnings in 7.31s |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | W3a | done | heat exposure of BRA thermal fleet by fuel per unit (exposure/heat_fuel.py, w3_heat_fuel.py, 8 tests); 21 capacity checks PASS; tables w3_heat_*.csv; pytest 151 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | W3b | done | GW exposed in >= k of 5 GCMs per plant (exposure/heat_agreement.py, w3_agreement.py, 3 tests); BRA thermal operating total 47.67 GW matches fleet table; pytest 154 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C32 | done | ruff: unused variable and empty f-string in 09_consolidate.py, unused imports in c23c/c23d_checks.py, import order in 07_water_balance.py; no logic change (py_compile OK); pytest 157 passed, 1 skipped (measured with W3c tests present); gate 8 PASS |
| 2026-10-01 | W3c | done | leave-one-cell-out influence on heat shares (exposure/heat_influence.py, w3_influence.py, 3 tests); thresholds 20/30/40; one-cell groups give NaN; pytest 157 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C33 | done | D86 (LOCO + cell bootstrap as composition sensitivity), D87 (axis 1 metrics, proposed), O16 note appended to DECISIONS.md; numbers copied from W3a/W3b/W3c outputs |
| 2026-10-01 | W3d | done | cell-cluster bootstrap (2000 draws, seed 86) of GCM-median heat shares and of the paired planned-minus-operating difference, with paired LOCO (exposure/heat_bootstrap.py, w3_bootstrap.py, 4 tests); observed statistics reproduce W3a tables; pytest 161 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | C34 | done | D86 addendum (W3d bootstrap results) and O25 (reporting rule, open) appended to DECISIONS.md; numbers copied from the w3_bootstrap output |
