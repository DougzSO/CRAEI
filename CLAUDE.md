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
- `PROGRESS.json`: phase and command status.

## Rules

1. `docs/METHODS_SPEC.md` is the only methodological source. Code that
   diverges from it is a bug or a new decision logged in `DECISIONS.md`.
2. Only three support files: `DECISIONS.md`, `LIMITATIONS.md`,
   `PROGRESS.json`. No phase reports, session memories, or parallel
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

## Stack

Python 3.11, xarray, rioxarray, geopandas, scipy, pandas, pyarrow,
matplotlib, isimip-client, pytest, ruff.

## Conventions

- `plant_uid` = blake2s hash of `name|lat|lon`.
- Tabular data: parquet. Gridded data: NetCDF.
- Scripts: `NN_name.py`, numbered by spec step.

## Command flow

audit → implement → test → update `PROGRESS.json` → stop for review.
