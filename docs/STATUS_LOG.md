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
