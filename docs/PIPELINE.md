> **Document role:** Pipeline design and script classification for `main.py <COUNTRY>` (Phase 7, D156).
> **Contains:** how to run, phases, completion criterion, country interface, script classification, findings.
> **Does NOT contain:** methods (-> docs/METHODS_SPEC.md) or numeric results (-> docs/RESULTS_REGISTRY.md).
> **Status:** implemented (C109); the authors' decisions of Phase 7 are applied.

---

## 1. Running

```text
python main.py BRA                      # every phase except the long ones; completed phases are skipped
python main.py Brazil --dry-run         # print the plan, run nothing
python main.py BRA --only w3,w4         # only these phases (long phases included) plus headlines
python main.py BRA --force coexposure   # re-run a phase although its hash is unchanged
python main.py BRA --adopt              # record hashes of outputs that already exist (first use on an existing tree)
python main.py BRA --list               # phases
```

- `BRA` and `Brazil` are accepted. `PRT` and `IND` stop at once with `ERRO: país não implementado: PRT`
  (exit 2) before any phase runs; nothing is executed partially.
- Phases that are complete print `[SKIP] <phase>: saídas presentes, hash igual`. Long phases
  (`acquire`, `indices`, `hydro`) never run unless named with `--only` or `--force`; the default run only
  reports whether they are current (`[LONG] ... saídas presentes, hash igual` or `STALE`).
- `headlines` (`scripts/check_headlines.py`) is always the last phase and is never skipped; a failure stops with
  exit 1.
- State: `<interim_dir>/pipeline_state_<ISO>.json` (hash of each completed phase, cache of file hashes by
  size and modification time). Outside Git.

## 2. Completion criterion

A phase is complete when all its declared outputs exist and the recorded hash equals the current one. The hash
covers the declared inputs, the phase's scripts (and `watch` files), `config/countries/<ISO>.yaml`,
`config/params.yaml` and `config/pipeline.yaml`. A changed hash re-runs the phase; downstream phases see an
upstream re-run through the hash of its outputs (`phase:<name>` inputs), so they re-run only if the outputs
changed. Input tokens (`config/pipeline.yaml`, `src/craei/pipeline.py`):

| Token | Meaning |
|---|---|
| `processed:` `tables:` `geo:` `article:` | file under that root |
| `raw:GLOB` | raw files hashed directly |
| `rawcov:GLOB` | raw files that **must** be in `raw/manifest.json`; the manifest sha256 is the hash (the files are not read again). A file read outside the manifest raises an error |
| `phase:NAME` | all declared outputs of an earlier phase |

Long phases `indices` and `hydro` use `rawcov:` (ISIMIP3b `tasmax`, `tasmin`, `pr` for the country).

## 3. Phases (config/pipeline.yaml)

| # | Phase | Scripts | Long |
|---|---|---|---|
| 0 | acquire | 02_acquire, 04_full_acquire | yes |
| 1 | geo | geo_base | |
| 2 | inventory | 05_plants, 05b_plant_units | |
| 3 | spatial | 06_spatial | |
| 4 | indices | 04_daily_indices | yes |
| 5 | hydro | 07_water_balance, 08_spei | yes |
| 6 | hazards | 09_consolidate | |
| 7 | w5e5 | 24_w5e5_spei_validation, e1_w5e5_inputs | |
| 8 | w3 | w3_heat_fuel ... w3_curves, th1_fleet_gw, w3g_heat_levels | |
| 9 | w4 | w4_null ... w4f_threshold_grid, w4r_emulator_check, w4g_drought_levels, w4h_coexposure | |
| 10 | coexposure | w3h_state_coexposure, w5_table3_gcm_mean, w5_sensitivity | |
| 11 | e1 | e1_hedge, e1_colocation | |
| 12 | e3 | e3_ena_validation, e3_hit_rate | |
| 13 | w6 | w6_gcm_subset, w6_nonmonotonicity | |
| 14 | validation (supplementary) | 25_validation_stats | |
| 15 | article | article/build_all.py --promote | |
| 16 | headlines | check_headlines | always |

PRT phase (not implemented, outside the BRA run): `22_validate_ren_iph.py` (REN IPH hydropower validation),
kept in `scripts/`.

## 4. Country interface

`config/countries/<ISO>.yaml` (BRA implemented; PRT and IND with `implemented: false`): ISO, aliases,
geometry file and layer names (Natural Earth gpkg name unchanged, GADM gpkg, layers, postal column, map
extent), Itaipu special case, filters, macro-region map (key in `params.yaml`), submarket approximation.
`craei.countries.iso()` returns the country of the run (`CRAEI_COUNTRY`, set by `main.py`; BRA when a script runs
alone); `COUNTRY = "BRA"` and the `== "BRA"` filters of the production scripts read it. `base_brazil_map` is
`base_country_map` (alias kept); file and layer names come from the country YAML.
Library defaults in `src/craei/` (`country="BRA"` argument defaults) and the Portugal/Brazil validation lists
of `24_w5e5_spei_validation.py` are left as they are.

## 5. Script classification (decisions of Phase 7)

| Class | Scripts |
|---|---|
| Production (scripts/, in main.py) | 02, 04_full, 04_daily, 05, 05b, 06, 07, 08, 09, 24, 25, geo_base, th1_fleet_gw, w3_*, w3f7, **w3g_heat_levels**, w3h_state_coexposure, w4_null, w4b, w4c_null_spi, w4c_null_thermal, w4c_spi_vs_spei, w4d, w4f, w4r_emulator_check, **w4g_drought_levels**, **w4h_coexposure**, w5_sensitivity, w5_table3_gcm_mean, w6_*, e1_*, e3_*, check_headlines |
| PRT (not implemented) | 22_validate_ren_iph |
| Article | scripts/article/*, article_map_utils.py |
| Utility | log_step |
| Archive (git mv to scripts/archive/) | 10_exposure (C19, legacy: METHODS_SPEC step 9 marked), 26_emdat_descriptive and c21_2_fix_emdat (EM-DAT feeds no row of the claims register), w3h_state_summary, c29_fleet_table, c23b_* (4), c23c_checks, c23d_checks, c23e_inventory, c27b_cleanup, audit_tx_tn_and_pet_truncation |
| Promoted from archive (bold above) | w3_heat_levels -> w3g_heat_levels, w4_drought_levels -> w4g_drought_levels, w4h_coexposure |

## 6. Findings of the audit

1. Three article inputs had their only producer in scripts/archive/ (w3g, w4g, w4h): promoted.
2. `w4c_spi_vs_spei.py` wrote only `_tmp_w4c_spi_vs_spei_v2.csv` (the O43 promotion was manual): it now writes
   `w4c_spi_vs_spei.csv` after checks A-D pass. A clean run could not produce the Fig 4 / register CSV before.
3. Raw manifest coverage (checked once): the 60 ISIMIP3b `*_BRA.nc` files read by `indices` and `hydro` and the
   27 ONS ENA files are all in `raw/manifest.json`. The 36 W5E5 `.nc` files read by `w5e5` are **not**: the
   manifest registers the downloaded `isimip-download-*.zip`, not the extracted files. `w5e5` therefore hashes
   them directly (2.5 GB, cached by size and time); registering the extracted files in the manifest is left to
   a data-layer decision. Author decision (C110): keep the direct hash of the extracted `.nc` files; the manifest is
   not changed. The five older ruff errors (imports in `src/` and `tests/`) are left for Phase 8.
4. EM-DAT: `26_emdat_descriptive.py` feeds no row of the claims register (DECISION_MEMO_F5.md): both EM-DAT scripts
   archived, `emdat_events.parquet` stays as an existing processed file.
5. `audit_tx_tn_and_pet_truncation.py` (archived) is only an optional diagnostic of `08_spei.py` (the message
   points to its new path); it feeds no output.
6. `--adopt` was added to the specified flags: on the existing tree every phase would otherwise count as never
   run and the first `main.py BRA` would recompute all of them.
