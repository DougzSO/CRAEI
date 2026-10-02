# PIPELINE MAP (C53)

Purpose: one row per stage, as the skeleton of a future runner (`python -m craei run`, not built). Built from an inventory of docstrings, public names, imports and file-name literals in the code; script bodies and `config/params.yaml` were NOT read. Reads/Writes are therefore "as they appear in code literals" and may be incomplete. "TBD" = TO BE DEFINED. Update one row at each phase closure. Stage state: done / legacy / planned.

Rules for a future runner (design, not implemented): a stage is skipped when its outputs exist and the hash of inputs, parameters and code version is unchanged; each stage ends with its checks as post-conditions (failure stops the run); decision constants (cuts, seeds, n_boot, country) move to a per-country config, each linked to its D-id.

## Executed stages

| Stage | Script (scripts/) | Modules (src/craei) | Reads | Writes | Tests (tests/) | Decisions | State |
|---|---|---|---|---|---|---|---|
| S0 config | - | config | config/params.yaml, datasets.yaml, paths.local.yaml | - | test_config | TBD | done |
| S1 acquisition | 02_acquire, 04_full_acquire | acquire.isimip, w5e5, auxiliary, dgeg, ren; manifest | ISIMIP3b, W5E5, auxiliary sources | manifest.json, raw climate cache (location TBD; ..\data\raw\climate shows 54 files, 2.99 GB), dgeg_hydro_generation.parquet, ren_iph.parquet | test_acquire_isimip, _w5e5, _auxiliary, _dgeg, _ren, test_manifest | D44 (memory fixes), D60 (date mapping) | done |
| S2 inventory | 05_plants, 05b_plant_units | inventory.plants, units | GEM workbook (location TBD; ..\data\raw\gem shows 0 files); catchment_validation.csv (optional, written by S3; attaches basin_id); plants.parquet (05b) | plants.parquet, plants_discarded.csv, plant_units.parquet | test_inventory_plants, _units, _units_io | D77-D80 | done |
| S2b fleet table | c29_fleet_table | inventory.fleet | plant_units, plants | fleet_brazil.csv | test_inventory_fleet | D81, D82 | done |
| S3 spatial | 06_spatial | spatial.grid, catchments | plants.parquet, HydroBASINS, ISIMIP crop gfdl-esm4_historical_tasmax_{iso}.nc (grid) | plant_cell.parquet, catchment_weights.parquet, catchment_validation.csv | test_spatial_grid, _catchments | TBD | done |
| S4 daily indices | 04_daily_indices | hazards.heat, precip, loading | ISIMIP tasmax/tasmin/pr crops, plant_cell | indices_daily.parquet (n35, tx35, tx40, rx5day, p95_exceedance_frequency [precipitation, H4]) | test_hazards_heat, _precip | TBD | done |
| S5 water balance | 07_water_balance; audit_tx_tn_and_pet_truncation (diagnostic) | hazards.pet | ISIMIP crops, catchment_weights, plant_cell | water_balance_catchment.parquet, water_balance_cell.parquet, truncated_pet_cells.parquet | test_hazards_pet | TBD | done |
| S6 SPEI/SPI | 08_spei | hazards.spei; rolling (top-level craei.rolling) | water_balance_catchment.parquet, water_balance_cell.parquet, plants.parquet, catchment_weights.parquet, truncated_pet_cells.parquet (path built in 08_spei.py:222; read vs write NOT confirmed) | spei.parquet (SPEI_12, SPEI_3, SPI_12) | test_hazards_spei | D44, D45, D54, D55 | done |
| S7 consolidation | 09_consolidate | hazards.consolidate, aqueduct | indices_daily, spei, plant_cell, plants, Aqueduct | plant_hazards.parquet, plant_aqueduct.parquet, plant_hazards_r_d_baseline_zero.csv | test_hazards_consolidate, _aqueduct | D80 (bucket error) | done (Aqueduct/H3 out of v2 scope) |
| S8 legacy exposure | 10_exposure | exposure.aggregate | plant_hazards, plant_aqueduct, plants | exposure_summary.csv, exposure_aqueduct.csv, exposure_si.csv | test_exposure_aggregate | D80 | legacy (bucket logic; guarded by c23b_regression_gate; role in v2 TBD) |
| S9 Axis 1 heat by fuel (W3a-W3f-6) | w3_heat_fuel, w3_agreement, w3_influence, w3_bootstrap, w3_season, w3_table1, w3_scenario, w3_sensitivity, w3_curves, w3_tx40, w3_gcm_exclusion | exposure.heat_fuel, heat_agreement, heat_influence, heat_bootstrap, heat_season, heat_table1, heat_scenario, heat_sensitivity, heat_curves; hazards.gcm_exclusion | plant_hazards, plant_units, plant_cell, indices_daily | w3_* tables (see outputs\tables) | test_exposure_heat_*, test_gcm_exclusion | D85-D87, O17, O25, O27 | done |
| S10 heat level classes (W3g) | archive/w3_heat_levels | exposure.heat_levels | indices_daily, plant_hazards, plant_units, plant_cell | w3g_* tables | test_heat_levels | D88, O28 | done (script archived) |
| S11a null W4a | w4_null | hazards.null_model | spei, plant_hazards | w4_null_rates.csv | test_null_model | D83 | done |
| S11b drought classes W4g | archive/w4_drought_levels | hazards.drought_levels | spei, plant_cell, plant_units, plant_hazards | w4g_* tables | test_drought_levels | D89, O29 | done (script archived; reading under three nulls pending, W4g-rev) |
| S11c emulated nulls W4r | w4r_emulator_check; archive/w4r_null_production | hazards.null_emulator | spei, water balance tables, plant_units, plant_cell | w4r_* tables; audit\w4r\draws_*.npz | test_null_emulator | D90, D92, O35 | done |
| S11d O36 | archive/o36_param_uncertainty | hazards.null_emulator | w4r draws, water balance, spei | o36_forms.csv, o36_decomposition.csv; audit\w4r\o36_*.npy | - | D93, O37 | done |
| S12 validation | 22_validate_ren_iph, 24_w5e5_spei_validation, 25_validation_stats, 26_emdat_descriptive | validation.ren_iph | ren_iph.parquet, dgeg_hydro_generation.parquet, emdat_events.parquet (producer: see Observation 9), spei.parquet, plants.parquet, catchment_weights.parquet, manifest.json, ren_iph_reference_annual.csv, ren_iph_reference_apa.csv (CRAEI\data\validation), ENA_Diario_por_Subsistema-*.csv (location TBD), W5E5 climate (location TBD) | validation.csv, spei_w5e5.parquet, water_balance_catchment_w5e5.parquet, emdat_descriptive.csv | test_validation_ren_iph | D60 | done |
| S13 geography | geo_base | - | Natural Earth (cartopy) | ..\data\external\geo\natural_earth_brazil.gpkg | - | O26 | done |

## Planned stages (no code yet)

W4g-rev (drought classes under the three nulls), trend-removed sensitivity (own id), W4h (co-located exposure 4x4), TH1 (D91; needs daily tasmax, path not seen), W3h (state/macro-region), W3f-7, W4c, W4b, W4d, W4e, W4f, rerun of W3d and W3f-3 at 5,000 draws, W5 (sensitivity register), W6a-c (figures; `src/craei/figures` and `src/craei/sensitivity` contain only `__init__`), W7 (reproducibility run, D43), W8 (extended validation; data not verified).

## Support scripts

c27b_cleanup (housekeeping), c23b_regression_gate (8 hash checks), log_step (STATUS_LOG), c23c_checks, c23d_checks, c23e_inventory (audits, outputs in audit\c23), c21_2_fix_emdat, c23b_delete_c_origins, c23b_repoint_manifest, c23b_verify_copy (last four: one-shot, still in scripts/).

## Observations from the inventory (facts; no action taken)

1. `compound.csv` is in outputs\tables but no generator exists in scripts/ (11_compound.py and exposure/compound.py were removed in C25-S3); compound is out of scope.
2. Work plan C-id table (C25-C50) and STATUS_LOG use the same numbers with different meanings (for example C48); STATUS_LOG governs; C49 and C50 remain reserved in the work plan.
3. STATUS_LOG repeats the C25-S3 line 3 times (log_step is not idempotent; append-only).
4. No test imports `craei.rolling` or `craei.hazards.loading`.
5. One-shot C23-B scripts remain in scripts/: c23b_delete_c_origins, c23b_repoint_manifest, c23b_verify_copy; also c21_2_fix_emdat.
6. Brazil-only filters: `COUNTRY = "BRA"` is a constant in the W4r script; whether decision constants (cuts, seeds, n_boot) are in params.yaml was not checked.
7. Raw location of GEM, Aqueduct, EM-DAT and GADM files after C23-B: not seen (..\data\raw subfolders show 0 files).

8. Order of S2 and S3 is S2, S3, S2: `05_plants.py:34-40` attaches basin_id from `catchment_validation.csv` if it exists; `06_spatial.py:52` writes it and reads `plants.parquet`. A runner has to split S2 in two.
9. `emdat_events.parquet` has three writers (`scripts/c21_2_fix_emdat.py:56`, `archive/c21_2_fix_blockers.py:169`, `archive/c21_2_fix_final.py:86`); which one produced the file on disk was NOT determined; the raw EM-DAT location was not seen.
10. `truncated_pet_cells.parquet`: written by `audit_tx_tn_and_pet_truncation.py:144` (diagnostic); `08_spei.py:222` builds the path, read vs write NOT confirmed. If it is read, S6 depends on a diagnostic script.

## Corrections (C54)

Checked against file-name literals and path lines in the code (static; bodies not read):
- S6 module is the top-level `craei.rolling`, not `hazards.rolling`.
- `catchment_validation.csv` is written by S3 (moved from S2); S2 reads it optionally.
- `ren_iph.parquet` and `dgeg_hydro_generation.parquet` are written by S1 (`acquire/ren.py:191`, `acquire/dgeg.py:93`); S12 only reads them.
- Reads completed only for S2, S3, S6 and S12. Reads of S4, S5 and S7-S11 are still incomplete (they omit `plants.parquet`, `plant_cell.parquet`, `catchment_weights.parquet` and others that appear as literals in their code); TBD.
- Outputs outside the stage rows: `n360_pwm_vs_pearson3_gap.csv` (archive `audit_n360_pwm_vs_pearson3_gap.py:116`, audit output); `compound.csv` (no generator).

## Constants outside params.yaml (static scan of scripts/ root and src/; scripts/archive NOT scanned)

- `config/params.yaml` has 16 keys. Used by the v2 article: heat_tx35_threshold_c 35, heat_tx40_threshold_c 40, heat_class_dtx35_days_per_yr 30, drought_spei_threshold -1.5, drought_class_rd_ratio 2, spei_clip_bound 3, model_agreement_fraction 0.8. The other keys concern Aqueduct, compound, solar, wet-day percentile and coastal buffer (out of scope).
- `model_agreement_fraction` 0.8 (4 of 5) is not what the tables use (k = 1, 3, 5): see O31.
- `craei.exposure.heat_fuel`, `heat_levels`, `craei.hazards.drought_levels` and `null_emulator` do not import `craei.config` (from their imports). `null_emulator.THRESHOLD = -1.5` equals `drought_spei_threshold` with no link between them.
- Bootstrap and seeds in scripts: `w3_bootstrap.py` and `w3_scenario.py` N_BOOT 2000, SEED 86 (the accepted 5,000 is pending); `w4_null.py` SEED 23, N_SIM 2000, N_MONTHS 360, CANON_BLOCK 12; `25_validation_stats.py` N_BOOT 10_000 (RNG_SEED value not seen). W4r: SEED [23, 99, 20], 20,000 draws (archived script).
- Heat cuts 10/30/60, the 10..100 d grid and the null percentiles p50/p90/p99 are not in params.yaml; where they sit in the code was not read.
- Fixed "BRA" (script constant or function default): `05b_plant_units`, `24_w5e5_spei_validation` (["BRA", "PRT"]), `25_validation_stats`, `c29_fleet_table`, `geo_base`, `w3_heat_fuel`, `w3_season`, `w4_null`, `w4r_emulator_check`, `heat_fuel` (default), `fleet.scope_units` (default). Country lists in `02_acquire`, `acquire/isimip.py`, `acquire/auxiliary.py`, `inventory/plants.py` are expected there.
