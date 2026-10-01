# COMANDO 23-B: raw-data reorganization

Date: 2026-09-30. Tag `pre-cleanup` created before any change in this
command (in addition to the pre-existing `pre-scope-audit` tag and
`archive/full-3-countries` branch, both confirmed present).

## Folders created

- `D:/Douglas/OUTROS/CRAEI_raw_data/` (RAW_ROOT), sibling of
  `D:/Douglas/OUTROS/CRAEI_isimip_raw_cache/` (untouched by this command).
  - `RAW_ROOT/raw/` -- full mirror of the former `raw_dir` (367 files,
    20.5412 GB), copied (not moved) from `C:` via robocopy
    (`/E /COPY:DAT`, 103 directories, 367 files, 0 failures).
  - `RAW_ROOT/README.md` -- dataset index (source, license, sha256/manifest
    pointer, config key, size, consumer script per dataset); states the
    ISIMIP cache is global/190 files/pr,tasmax,tasmin-only/not manifest-
    covered, that the 180 country crops are manifest-covered, that three
    crops (`gfdl-esm4_historical_tasmax_{BRA,IND,PRT}.nc`) have no retained
    global source, that CRAEI no longer depends on GEAR_framework, that
    there is no `.env`, and that EM-DAT is not redistributable.
  - `RAW_ROOT/FUTURE_IDEAS.md` -- Article 2 backlog and the four other
    backlog items (global thermal extension, unresolved water-sector
    availability, unverified ONS EAR/ANA/ENTSO-E/REN Data Hub, staging-space
    operational note).

## Baseline (Bloc 0.3)

`data/outputs/audit/c23b_baseline.csv` -- content hash (parquet, via
`pandas.util.hash_pandas_object`) or byte hash (CSV) of `plant_hazards`,
`plant_aqueduct`, `plants`, `exposure_summary`, `exposure_aqueduct`,
`validation.csv`, taken before any change in this command.

## Test suite (Bloc 0.2, re-run after the switch in Bloc 1)

141 passed, 1 skipped, both before and after the `raw_dir` switch. No test
lost.

## Scripts added

- `scripts/c23b_verify_copy.py` -- sha256-verifies every file copied from
  the old `raw_dir` (C:) into `RAW_ROOT/raw` (D:) against both the source
  file directly and the manifest, where a manifest hash exists.
- `scripts/c23b_repoint_manifest.py` -- rewrites the `path` field (only) of
  every entry in the `RAW_ROOT/raw/manifest.json` copy from the old C:
  prefix to the new D: prefix. No `sha256` value was touched.

## Bloc 1.3: copy and verification

- Robocopy: 103 directories, 367 files, 20.5412 GB (19.130 GiB), 0 failures,
  0 mismatches, 0 extras. Source and destination file counts and total
  bytes reconcile exactly (367 files / 20.5412 GB each side).
- sha256 verification (`c23b_copy_verification.csv`): 366 non-manifest
  files checked (the 367th is `manifest.json` itself, excluded), 0
  divergences. 293/366 files carry a manifest sha256 (all matched); the
  remaining 73 (shapefile sidecars, Aqueduct `.gdb` internals, README/
  VERSION files, etc.) were verified by direct source=destination sha256
  comparison. All 180 ISIMIP country crops are among the 293
  manifest-covered files and all matched.

## Bloc 1.5: config diff

`config/paths.local.yaml` is gitignored; this is the full before/after
diff, kept here since git does not track it.

```diff
- raw_dir: "C:/Users/User/Desktop/DOUGLAS/DOUTORADO/PHD RELATED WORKS/CLIMATE RISK FRAMEWORK/data/raw"
+ raw_dir: "D:/Douglas/OUTROS/CRAEI_raw_data/raw"

- gem_file: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/assets/gem_global_integrated_power_tracker_{20260809}.xlsx"
+ gem_file: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/gem/gem_global_integrated_power_tracker_{20260809}.xlsx"

- aqueduct_dir: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/climate/aqueduct"
+ aqueduct_dir: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/aqueduct"

- emdat_dir: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/validation"
+ emdat_dir: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/emdat"

- gadm_dir: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/boundaries/gadm"
+ gadm_dir: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/gadm"

- natural_earth_coastline: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/boundaries/natural_earth_coastline/ne_10m_coastline.shp"
+ natural_earth_coastline: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/boundaries/ne_10m_coastline.shp"

- natural_earth_rivers: "D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/boundaries/natural_earth_rivers/ne_10m_rivers_lake_centerlines.shp"
+ natural_earth_rivers: "D:/Douglas/OUTROS/CRAEI_raw_data/raw/boundaries/ne_10m_rivers_lake_centerlines.shp"
```

Unchanged: `data_root`, `interim_dir`, `processed_dir`, `outputs_dir`
(all still on C:), `isimip_global_cache_dir`, `isimip_staging_dir`. There is
no `.env`; `config/paths.local.yaml` remains the only local-path source and
was not converted to one.

`RAW_ROOT/raw/manifest.json`: 293 `path` values rewritten from the old C:
prefix to the new D: prefix via `c23b_repoint_manifest.py`. No `sha256`
field was changed. The original manifest.json under the old C: `raw_dir`
was left untouched (that whole tree is kept as a backup pending Parada A
authorization -- see below).

## Smoke test + suite (Bloc 1.5, after the switch)

- `raw_dir` resolves to `D:/Douglas/OUTROS/CRAEI_raw_data/raw` and exists.
- Every production-script data input checked resolves under the new
  `raw_dir` (GEM xlsx, coastline shapefile, all 3 GADM gpkg, HydroBASINS
  dir, Aqueduct dir, EM-DAT CSV, the gfdl-esm4/historical/tasmax/BRA crop
  used as the grid template by `06_spatial.py`, W5E5 dir, REN/IPH dir,
  DGEG dir, ONS ENA dir).
- All six explicit config keys (`gem_file`, `aqueduct_dir`, `emdat_dir`,
  `gadm_dir`, `natural_earth_coastline`, `natural_earth_rivers`) resolve to
  existing files/dirs under `RAW_ROOT/raw`.
- `Manifest.is_intact()` re-hashed all 295 non-`datasets` entries against
  their unchanged sha256: 0 not intact.
- Steps 04-09 were NOT run, per instruction.
- Test suite: 141 passed, 1 skipped (unchanged from the Bloc 0.2 baseline).

## Free disk space

| | before (C23-E, pre-copy) | after copy + switch |
|---|---|---|
| C: free | 14.5 GB | 14.1 GB |
| D: free | 1250.4 GB | 1229.2 GB (-21.2 GB, consistent with the 20.5 GB copy) |

## Pending: Parada A, part 2 (deletion authorization)

Not deleted yet. Candidates for the next authorization, once given
(GEAR_framework is never a candidate -- it was only ever a copy source and
was not modified):

**C: `raw_dir` origin** (`C:/.../data/raw/`, now fully mirrored and
sha256-verified at `RAW_ROOT/raw/`):

| subfolder | files | size | verified copy at RAW_ROOT | deletion candidate |
|---|---|---|---|---|
| aqueduct | 59 | 1.0658 GB | yes | yes |
| boundaries | 19 | 0.0553 GB | yes | yes |
| climate (excl. the 3 crops below) | 225 | 18.83 GB minus ~0.284 GB | yes | yes |
| climate/isimip3b/gfdl-esm4/historical/tasmax/{BRA,IND,PRT}.nc | 3 | 0.284 GB | yes (byte-identical) | **NO -- kept on C: as the only backup; these 3 have no retained global source (route `direct_download_crop_delete`)** |
| emdat | 10 | 0.1058 GB | yes | yes |
| gadm | 3 | 0.4523 GB | yes | yes |
| gem | 1 | 0.0288 GB | yes | yes |
| validation (dgeg/ren_iph/ons_ena) | 45 | 0.0031 GB | yes | yes |
| manifest.json | 1 | 0.00028 GB | superseded by the repointed copy at RAW_ROOT | keep as historical record, or delete -- author's call |

Total deletable now (everything above except the 3 kept crops and
`manifest.json`): 20.5412 GB - 0.284 GB ~= **20.26 GB**, which would raise
C: free space from ~14.1 GB to ~34.4 GB.

Nothing with a failed sha256 check exists (0 divergences project-wide), so
there is no "copy did not verify" exclusion beyond the 3 crops above.

**Staging-dir leftovers** (`C:/Users/User/AppData/Local/CRAEI_staging`,
COMANDO 12 leftover, unrelated to this reorg but flagged per instruction):
two `.part` files from an interrupted `ukesm1-0-ll` historical tasmin
download --
`ukesm1-0-ll_r1i1p1f2_w5e5_historical_tasmin_global_daily_1991_2000.nc.part`
(2.087 GB) and `..._2001_2010.nc.part` (1.807 GB), 3.894 GB total. These are
partial downloads, not verified copies of anything -- cleanup candidates in
their own right (Parada B list), not tied to the sha256-verified-copy
condition above.

## Versioned example config

`config/paths.example.yaml` already exists, is git-tracked, and contains no
personal paths (placeholders only) -- it satisfies the "versioned example
config" requirement without creating a duplicate file. It does not need any
change from this command: it never listed the GEAR_framework paths as
required (`gem_file` etc. are documented there as optional-style entries
already, without example absolute paths tied to GEAR_framework).

## Parada A, second part: deletions executed (2026-09-30)

### (b) Staging leftovers -- deleted after cache verification

Verified both `ukesm1-0-ll_r1i1p1f2_w5e5_historical_tasmin_global_daily_
{1991_2000,2001_2010}.nc` exist in `isimip_global_cache_dir` with the
expected sizes (2,086,821,293 and 2,084,960,583 bytes) and are h5py-valid
(`lon`, `lat`, `time`, `tasmin` variables all open cleanly). Both matching
`.part` files deleted from `C:/Users/User/AppData/Local/CRAEI_staging`:
3.894 GB freed. Staging dir is now empty.

### (a) C: raw_dir origins -- deleted with carve-outs

**Cross-reference (manifest route x cache presence) for item 1 of the
carve-out**, via `c23e_cache_expected_vs_present.csv`:

| crop | manifest route | cache status |
|---|---|---|
| gfdl-esm4/historical/tasmax (BRA/IND/PRT) | `direct_download_crop_delete` | absent for all 4 historical chunks -- by design, source was never retained |
| gfdl-esm4/historical/tasmin (BRA/IND/PRT) | `direct_download_crop_keep_cache` | the `1981_1990` chunk is missing from the cache; `1991_2000`/`2001_2010`/`2011_2014` are present -- **unexplained gap**, this route was supposed to retain it |

Both sets (6 files, 0.284+0.284 GB -- 568.98 MB total) kept on C: per
instruction 1.

**Item 2 (no-GEAR-copy datasets), sizes reported before the decision:**
HydroBASINS 0.0366 GB, W5E5 2.6411 GB, REN/IPH ~0 GB (JSON, <1 MB), DGEG
~0 GB (<1 MB), ONS ENA 0.0028 GB, manifest.json 0.000276 GB -- **total
2.6811 GB, under the 3 GB threshold**, so all kept on C: as a second copy
per instruction (no stop needed).

**Item 3 (sha256 failures):** none -- 0 divergences project-wide, so no
exclusion triggered by this clause.

**Deletion procedure**: `scripts/c23b_delete_c_origins.py` re-hashed every
candidate file's *current* C: and D: copies immediately before deleting
(not reusing the earlier `c23b_copy_verification.csv` run), deleted file by
file (never a directory), and logged every outcome. Dry run first (0
unexpected results), then executed for real.

**Result**: 264 files deleted from C: raw_dir, 17.2917 GB freed, 0 failures.
103 files kept, 3.2494 GB (the 6 crops above + the five no-GEAR-copy
datasets + manifest.json). Full logs: `data/outputs/audit/c23/c23e/
c23b_deleted_from_c.csv` (264 rows: relpath, size, sha256 at deletion) and
`c23b_kept_on_c.csv` (103 rows: relpath, size, reason).

**Final C: raw_dir contents** (103 files, 3.2494 GB): `boundaries/
hydrobasins/*` (3), `climate/isimip3b/gfdl-esm4/historical/{tasmax,tasmin}/
*` (6), `climate/w5e5v2.0/{pr,tasmax,tasmin}/*` (48), `manifest.json` (1),
`validation/dgeg/*` (5), `validation/ons_ena/*` (27), `validation/ren_iph/*`
(13).

### (c) processed_dir / outputs_dir backup

Copied (not moved) to `D:/Douglas/OUTROS/CRAEI_backup/{processed,outputs}/`
via robocopy: `processed/` 25 files, 0.864 GB, 0 failures; `outputs/` 94
files, 0.00291 GB, 0 failures. sha256-verified all 119 files against the
C: originals: 0 mismatches. Originals on C: untouched (this is a backup,
not a move -- `config/paths.local.yaml`'s `processed_dir`/`outputs_dir`
still point at C:).

### Free space after this round

| | before this round | after |
|---|---|---|
| C: free | 14.1 GB | **35.3 GB** |
| D: free | 1229.2 GB | 1228.2 GB (-1.0 GB, the processed+outputs backup) |

### Re-verification after deletion

- Smoke test re-run: `raw_dir` and all six explicit keys resolve; all
  manifest entries re-hashed intact (0 not intact).
- Test suite re-run: 141 passed, 1 skipped (unchanged).

### RAW_ROOT/README.md warning, updated

The warning now explains, per item: which of the three kept-on-C:
categories exist, why each has no second copy besides C:, and that
everything else (264 files, GEM/Aqueduct/EM-DAT/GADM/Natural Earth/the
other 174 crops) was deleted from C: because GEAR_framework (for the four
imported datasets) or the verified-present cache (for the 174 crops)
remains their source of record.

## Bloc 2: processed/interim inventory and Parada B decision

`data/interim/` is empty, untouched. `data/processed/` inventoried (24
files, ~905 MB); classified by consumer (grep across `src/` and `scripts/`,
not by filename guess). Candidates were files consumed only by a closed,
one-off `audit_*` script -- none of the production chain (02-10) or the
validation-table generators (22/24/25/26) referenced any of them.

**Parada B decision: move, don't delete.** Six files moved (not deleted)
from `data/processed/` to `data/processed/archive/`:
`fd_2param_loglogistic_fallback.csv`, `fd_loglogistic_mle_vs_pwm.csv`,
`fd_pwm_vs_pearson3_sample.csv`, `temporal_pooling_fd_variants.csv`,
`temporal_pooling_variant_b_seasonal.csv`, `wet_day_sample_size.parquet`.

- sha256 identical before and after the move for all 6 files (verified by
  hashing each file at its old path immediately before moving it, then
  again at its new path immediately after -- 0 mismatches).
- Grepped `scripts/0*.py`, `scripts/22_*.py`, `scripts/24_*.py`,
  `scripts/25_*.py`, `scripts/26_*.py`, `scripts/c23*.py` for each of the 6
  filenames: **zero matches** -- no kept script references any moved file.
- `data/processed/archive/README.md` written: for each file, which closed
  decision (D42, D49, D50 x2, D53 x2) it supports and which archived script
  produced it, plus a note that the archived audit scripts will not run
  unless their output is moved back first.

**Kept in place, per instruction** (not moved, not deleted):
- `n360_pwm_vs_pearson3_gap.csv` -- read by the kept `c23_scope_audit.py`.
- `plant_hazards_r_d_baseline_zero.csv` -- written by active
  `09_consolidate.py`; it is the evidence for L19.

`interim_dir` stays empty, as instructed.

## Bloc 3: scripts archive

Rule applied: a script moves to `scripts/archive/` only if (a) nothing
executes it by import or `subprocess` call from a production script, test,
or config, AND (b) it does not generate any table kept in `data/outputs/
tables/`. Checked by reference (grep for actual `import`/`subprocess.run`
calls and for each script's own `to_csv`/`to_parquet` targets), not by name
or by docstring/comment mentions -- several hits from a plain filename grep
turned out to be comment-only (e.g. `c23_scope_audit.py` holds every script
name in a hardcoded list for its own scope report, which is data, not an
execution dependency) and were not treated as references.

**50 scripts total, 25 archived, 25 kept.**

### Archived (25) -- `scripts/archive/`

- `03_pilot_download.py` -- superseded: COMANDO 11's pilot script, replaced
  in production by `04_full_acquire.py` (COMANDO 12); not referenced by
  anything, generates no file the current pipeline reads.
- `11_compound.py` -- compound scope; its outputs (`compound.csv`,
  `compound_months.parquet`, `exposure_si.csv`) are themselves archived in
  Bloc 5.
- 13 `audit_*` scripts (`audit_fd_pwm_vs_pearson3`,
  `audit_local_data`, `audit_mle_loglogistic_and_2param_fallback`,
  `audit_n360_pwm_vs_pearson3_gap`, `audit_pearson3_bias_synthetic`,
  `audit_pool_granularity_sensitivity`, `audit_pool_size_synthetic_bias`,
  `audit_spei_fit_diagnostics`, `audit_spei_pwm_failure_causes`,
  `audit_temporal_pooling_variants`, `audit_temporal_variant_synthetic_bias`,
  `audit_wet_day_sample`, plus the two orphans `check_isimip_availability`
  and `debug_ren_iph_network`) -- closed one-off diagnostics; each either
  supports an already-`closed` decision (see `data/processed/archive/
  README.md` for the 6 whose CSV/parquet output also moved) or writes
  nothing persistent at all (pure read + print).
- `benchmark_spei_fitters.py` -- closed diagnostic (D45 COMANDO 17-E),
  read-only against `processed_dir`.
- 4 of 5 `c21_2_*` scripts (`c21_2_closure`, `c21_2_fix_blockers`,
  `c21_2_fix_final`, `c21_2_plant_subsystem_mapping`) -- superseded
  iterations of the COMANDO 21-2 fix sequence; `plant_subsystem_mapping.
  parquet` (their other target) does not exist in `data/processed/` today,
  and `emdat_events.parquet`'s authoritative generator is `c21_2_fix_emdat.
  py`, kept (see below; confirmed by mtime adjacency -- the file was
  written 13s after that script's own last edit, after the 3 archived
  variants' edits).
- 4 of 5 `c22*` scripts (`c22_compound_diagnosis`, `c22b_dependence_
  uncertainty`, `c22b_regional_compound`, `c22c_collective_tests`) --
  compound/regional-dependence diagnostic chain, terminal (nothing
  downstream reads their output); `c22b_regional_assignment.py` is the one
  exception, kept below.
- No IND/PRT-specific candidate scripts were found by name among the
  remaining files (none follow a `..._IND.py`/`..._PRT.py` pattern), so
  this candidate category is empty.

### Kept (25)

Production chain (02-10): `02_acquire.py`, `04_daily_indices.py`,
`04_full_acquire.py`, `05_plants.py`, `06_spatial.py`, `07_water_balance.py`,
`08_spei.py`, `09_consolidate.py`, `10_exposure.py`.

Validation-table generators and their active upstream producers:
`22_validate_ren_iph.py`, `24_w5e5_spei_validation.py` (produce
`ren_iph.parquet`, `spei_w5e5.parquet`, `water_balance_catchment_w5e5.
parquet`, all active), `25_validation_stats.py` (-> `validation.csv`),
`26_emdat_descriptive.py` (-> `emdat_descriptive.csv`).

All `c23*.py` scripts, per rule 3.3: `c23_code_audit.py`,
`c23_scope_audit.py`, `c23b_delete_c_origins.py`, `c23b_repoint_
manifest.py`, `c23b_verify_copy.py`, `c23c_checks.py`, `c23d_checks.py`,
`c23e_inventory.py`.

**Kept in doubt** (deviate from their candidate category -- reason given,
not auto-archived despite matching a named pattern):

| script | candidate category it matches | why kept instead |
|---|---|---|
| `22_audit.py` | none named, but a diagnostic-shaped script | it is the figure-readiness/plausibility gate for Phase 7 (not yet run); nothing currently reads its own output only because Phase 7 hasn't happened yet, not because it is unneeded |
| `audit_tx_tn_and_pet_truncation.py` | `audit_*` | sole generator of `truncated_pet_cells.parquet`, an active input `08_spei.py` reads in production |
| `c21_2_fix_emdat.py` | `c21_2_*` | sole surviving generator of the active `emdat_events.parquet` (no 02-10 script produces it; confirmed by mtime adjacency, see above) |
| `c22b_regional_assignment.py` | `c22*` | sole generator of `c22b_plant_region.parquet`, explicitly protected in the Bloc 5 instructions ("the regional map uses it") and read by the kept `c23_scope_audit.py` |

### Verification

Grepped `tests/*.py` for `import scripts`/`from scripts`: no hits -- no
test imports any script module. Re-ran the suite after the move: 141
passed, 1 skipped (unchanged).

## Pending

- C24 (docs rework), C25 (src/ cleanup) as already tracked in
  `PROGRESS.json`.
- C23-B Bloc 4 (src/ report-only) and Blocs 5-7 (outputs archive, docs
  archive, regression gate) not yet run -- next stop point is Parada C.

## C23-B finish (2026-09-30 21:38)
### Outputs moved to data/outputs/archive/ (sha256 verified)
- `diagnostics\c22_compound_diagnosis_alt_a_absolute.csv` -> `archive/diagnostics\c22_compound_diagnosis_alt_a_absolute.csv` (1 file(s), sha256 OK)
- `diagnostics\c22_compound_diagnosis_alt_b_absolute_freq.csv` -> `archive/diagnostics\c22_compound_diagnosis_alt_b_absolute_freq.csv` (1 file(s), sha256 OK)
- `diagnostics\c22_compound_diagnosis_percentile.csv` -> `archive/diagnostics\c22_compound_diagnosis_percentile.csv` (1 file(s), sha256 OK)
- `diagnostics\c22b_count_vs_ci_width.csv` -> `archive/diagnostics\c22b_count_vs_ci_width.csv` (1 file(s), sha256 OK)
- `diagnostics\c22b_dependence_uncertainty.csv` -> `archive/diagnostics\c22b_dependence_uncertainty.csv` (1 file(s), sha256 OK)
- `diagnostics\c22b_p1_out.txt` -> `archive/diagnostics\c22b_p1_out.txt` (1 file(s), sha256 OK)
- `diagnostics\c22b_p2a_out.txt` -> `archive/diagnostics\c22b_p2a_out.txt` (1 file(s), sha256 OK)
- `diagnostics\c22b_p2b_out.txt` -> `archive/diagnostics\c22b_p2b_out.txt` (1 file(s), sha256 OK)
- `diagnostics\c22b_regional_dependence_uncertainty.csv` -> `archive/diagnostics\c22b_regional_dependence_uncertainty.csv` (1 file(s), sha256 OK)
- `diagnostics\c22b_regional_fleet_inventory.csv` -> `archive/diagnostics\c22b_regional_fleet_inventory.csv` (1 file(s), sha256 OK)
- `diagnostics\c22c_p1_out.txt` -> `archive/diagnostics\c22c_p1_out.txt` (1 file(s), sha256 OK)
- `audit\audit_report.md` -> `archive/audit\audit_report.md` (1 file(s), sha256 OK)
- `audit\coverage.csv` -> `archive/audit\coverage.csv` (1 file(s), sha256 OK)
- `audit\figure_readiness.csv` -> `archive/audit\figure_readiness.csv` (1 file(s), sha256 OK)
- `audit\gap_actions.csv` -> `archive/audit\gap_actions.csv` (1 file(s), sha256 OK)
- `audit\plausibility_report.txt` -> `archive/audit\plausibility_report.txt` (1 file(s), sha256 OK)

### Docs copied to docs/archive/ (originals kept until C24)
- `docs/DECISIONS.md` -> `docs/archive/DECISIONS_v1_pre_rework.md` (sha256 OK)
- `docs/LIMITATIONS.md` -> `docs/archive/LIMITATIONS_v1_pre_rework.md` (sha256 OK)
- `docs/METHODS_SPEC.md` -> `docs/archive/METHODS_SPEC_v1_pre_rework.md` (sha256 OK)

### Pending
- C24: rewrite docs (SCOPE, METHODS_SPEC, DECISIONS, LIMITATIONS, work plan v2).
- C25: src/ cleanup (dead code, country/scope branches, lint).
- Kept in doubt (review in C25): 22_audit.py, audit_tx_tn_and_pet_truncation.py, c21_2_fix_emdat.py, c22b_regional_assignment.py.
- PROGRESS.json not edited here; superseded by CRAEI_work_plan_v2.
