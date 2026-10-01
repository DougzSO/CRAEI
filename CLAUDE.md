# CRAEI: Climate Risk Assessment for Energy Infrastructure

Assesses climate hazard exposure (heat, drought, water stress) of power plant
fleets under ISIMIP3b scenarios. Package `craei`; methodology spec is the
single source of truth for all numeric choices and definitions.

## Sources of truth

- `docs/METHODS_SPEC.md`: the only methodological source. Code diverging from
  it is a bug, or a new decision logged in `docs/DECISIONS.md`.
- `config/params.yaml`: every numeric parameter, with `value`, `tier` (1/2/3),
  `source`. No methodological number is hardcoded.
- `docs/DECISIONS.md`: one line per decision.
- `docs/LIMITATIONS.md`: one line per limitation.
- `docs/CRAEI_work_plan_v2.md`: phase and command status.

## Rules

1. `docs/METHODS_SPEC.md` is the only methodological source. Code that
   diverges from it is a bug or a new decision logged in `DECISIONS.md`.
2. Only three support files: `DECISIONS.md`, `LIMITATIONS.md`,
   `docs/CRAEI_work_plan_v2.md`. No phase reports, session memories, or parallel
   changelogs.
3. Every numeric parameter lives in `config/params.yaml` with `value`,
   `tier` (1/2/3), and `source`. No hardcoded methodological numbers.
4. Baseline statistics (percentiles, distribution parameters) are estimated
   only on 1985-2014 of each model's own data. A test must fail if this is
   violated.
5. Data never enters git. Paths come from `config/paths.local.yaml`
   (gitignored).
6. Code, docstrings, and docs are in English (US). They describe current
   state, not changelog language.
7. No code, terms, or issue lists from GEM, GeoFREA, or geoworld_framework.
   Legacy repositories are read only when a command explicitly authorizes it.
8. Commit and push only with explicit author authorization, after the diff
   is shown. Review and commit are separate commands.
9. A methodological value with no source in the spec becomes an `O` line in
   `DECISIONS.md`, and work stops there.
10. Modules shared between the production pipeline and audit scripts take no
    flag for divergent behavior between the two. If an audit needs its own
    behavior, it gets its own code.
11. This machine has ~6 GB RAM, well under the Spec's assumed 8+ cores/32 GB
    (D41). Never call `groupby(...).transform(...)`, `groupby(...).apply(...)`,
    or `groupby(...).rolling(...)` over a full multi-country/model/scenario
    table: these materialize one object per group and concat them, which
    inflates memory far past the raw data size long before it as data grows
    (crashed this project once already, COMANDO 17, `docs/DECISIONS.md` D44).
    Use `craei.rolling.rolling_sum_by_group` (or an equally vectorized
    cumsum/cumcount approach) for a rolling aggregate, and process one
    country/model(/scenario) chunk at a time with explicit `del` +
    `gc.collect()` between chunks (COMANDOS 15/16/17 pattern) for anything
    else over the full climate data.
12. Comandos de auditoria e de decisão metodológica são executados pelo agente principal, 
não delegados. Subagente serve para tarefa mecânica com critério objetivo de conclusão.

## Stack

Python 3.11, xarray, rioxarray, geopandas, scipy, pandas, pyarrow,
matplotlib, isimip-client, pytest, ruff.

## Conventions

- `plant_uid` = blake2s hash of `name|lat|lon`.
- Tabular data: parquet. Gridded data: NetCDF.
- Scripts: `NN_name.py`, numbered by spec step.
- `outputs_dir` is never written to directly (COMANDO 22-B Part 3). It has
  exactly four subdirectories, each exposed by `config.load_paths()` as its
  own key so a script never builds the path by hand:
  - `outputs_tables_dir` (`tables/`): the article's own result tables --
    `exposure_*.csv`, `compound*.csv`, `validation.csv`, `emdat_descriptive.csv`.
  - `outputs_audit_dir` (`audit/`): `coverage.csv`, `figure_readiness.csv`,
    `plausibility_report.txt`, `gap_actions.csv`, `audit_report.md`.
  - `outputs_diagnostics_dir` (`diagnostics/`): one-off command diagnostics
    (e.g. `c22_*.csv`, `c22b_*.csv`) that back a `DECISIONS.md` entry but are
    not themselves read by any figure or production script.
  - `outputs_figures_dir` (`figures/`): Phase 7 rendered figures.
  A new command's writer script calls `load_paths()["outputs_<subdir>_dir"]`,
  never `load_paths()["outputs_dir"]` followed by a literal filename.

## Command flow

audit → implement → test → update `docs/CRAEI_work_plan_v2.md` → stop for review.

## Test floor and status (updated 2026-10-01, C29)

- Current pytest floor: 153 passed, 1 skipped (supersedes any earlier floor in this file).
- Status log: docs/STATUS_LOG.md (append-only). Plan: docs/CRAEI_work_plan_v2.md.

- Pytest floor after C25-S3: 143 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3a: 151 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3b: 154 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3c: 157 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3d: 161 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3e: 164 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3f-1: 167 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3f-3: 170 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3f-4: 173 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).

- Pytest floor after W3f-2: 176 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
