> **Document role:** Working rules for AI-assisted sessions on this repository.
> **Contains:** process rules: ID hygiene, EOL/BOM handling, read-before-write discipline, environment checks, headline values.
> **Does NOT contain:** project methods or results (-> docs/METHODS_SPEC.md, docs/RESULTS_REGISTRY.md).
> **Status:** living.

---

# CRAEI: Climate Risk Assessment for Energy Infrastructure

Assesses climate hazard exposure (heat, drought, water stress) of power plant
fleets under ISIMIP3b scenarios. Package `craei` (`src/craei/`); methodology
spec is the single source of truth for all numeric choices and definitions.

## Sources of truth

- `docs/METHODS_SPEC.md`: the only methodological source. Code diverging from
  it is a bug, or a new decision logged in `docs/DECISIONS.md`.
- `config/params.yaml`: every numeric parameter, with `value`, `tier` (1/2/3),
  `source`. No methodological number is hardcoded.
- `docs/DECISIONS.md`: one line per decision (D).
- `docs/LIMITATIONS.md`: one line per limitation.
- `docs/OPEN_ITEMS.md`: open items (O).
- `docs/CRAEI_work_plan_v2.md`: phase and command status (C).
- `docs/STATUS_LOG.md`: append-only status log.
- `docs/HANDOFF_v46.md`: full context for the current round.

## Environment

- `data_root` is the sibling directory of the repo (`.../CLIMATE RISK FRAMEWORK/data`).
  Paths come from `config/paths.local.yaml` (gitignored).
- `raw_dir`: `D:/Douglas/OUTROS/CRAEI_raw_data/raw`.
- Article artifacts go to `data/outputs/article/{figures,tables}`, outside Git.
- Geometry only from the cache `data/external/geo/natural_earth_brazil.gpkg`;
  use `representative_point()` for labels.
- Machine has ~6.2 GB RAM, well under the Spec's assumed 8+ cores/32 GB (D41).
  `spei.parquet` (463 MB) is read only with selective column/row reads.
- Files are UTF-8 without BOM, LF line endings.

## General rules

1. `docs/METHODS_SPEC.md` is the only methodological source. Code that
   diverges from it is a bug or a new decision logged in `DECISIONS.md`.
2. Support files are the ones listed under Sources of truth. No phase reports,
   session memories, or parallel changelogs beyond them.
3. Every numeric parameter lives in `config/params.yaml` with `value`,
   `tier` (1/2/3), and `source`. No hardcoded methodological numbers.
4. Baseline statistics (percentiles, distribution parameters) are estimated
   only on 1985-2014 of each model's own data. A test must fail if this is
   violated.
5. Data never enters git.
6. Code, docstrings, and docs are in English (US) and describe current state,
   not changelog language. Exception: the "Permanent rules" section below is
   kept in Portuguese as written by the author.
7. No code, terms, or issue lists from GEM, GeoFREA, or geoworld_framework.
   Legacy repositories are read only when a command explicitly authorizes it.
8. Push only with explicit author confirmation. An end-of-phase commit needs
   no separate authorization when pytest is at or above the floor and
   `scripts/check_headlines.py` is all PASS (Permanent rule 11); the diff goes
   in the final phase report. If any check fails, stop. Review and commit
   of methodological changes stay separate commands.
9. A methodological value with no source in the spec becomes an `O` line in
   `OPEN_ITEMS.md` (value shown as "TO BE DEFINED"), and work stops there.
10. Modules shared between the production pipeline and audit scripts take no
    flag for divergent behavior between the two. If an audit needs its own
    behavior, it gets its own code.
11. Never call `groupby(...).transform(...)`, `groupby(...).apply(...)`, or
    `groupby(...).rolling(...)` over a full multi-country/model/scenario
    table: these materialize one object per group and concat them, which
    inflates memory far past the raw data size (crashed this project once
    already, COMANDO 17, `docs/DECISIONS.md` D44). Use
    `craei.rolling.rolling_sum_by_group` (or an equally vectorized
    cumsum/cumcount approach) for a rolling aggregate, and process one
    country/model(/scenario) chunk at a time with explicit `del` +
    `gc.collect()` between chunks (COMANDOS 15/16/17 pattern) for anything
    else over the full climate data.
12. Audit and methodological-decision commands are run by the main agent, not
    delegated. A subagent is for mechanical tasks with an objective
    completion criterion.

## Permanent rules (post-C87 round)

1. Nunca inventar números. Valor ausente = "TO BE DEFINED" + item O-xx.
2. Antes de criar IDs C/D/O: grep em docs/DECISIONS.md, docs/STATUS_LOG.md, docs/CRAEI_work_plan_v2.md, CLAUDE.md, docs/OPEN_ITEMS.md. Último commit C87, última decisão D133.
3. Antes de escrever lógica nova: grep por precedente em scripts/*.py e src/craei/. Quando o schema admite vários valores (threshold, null, scenario, fleet, itaipu, pool), usar o valor headline do script-fonte e citar arquivo:linha.
4. Headline: threshold=30 (scripts/w3_table1.py:35); null block12/block_bootstrap_12; itaipu=b (7.000 MW) para hidro, "na" para térmica; fleet operating; filtro precedente th1_fleet_gw.py:102. Hidro fora de H1 (scripts/archive/w3_heat_levels.py:43).
5. Funções a reutilizar: dl.find_plant (src/craei/hazards/drought_levels.py:18), hl.with_itaipu_versions (src/craei/exposure/heat_levels.py:43), scripts/article_map_utils.py.
6. Arquivo de produção: escrever em temporário, git --no-pager diff --no-index, promover só sem drift não explicado. UTF-8 sem BOM, LF.
7. Nenhum _tmp_* sobrevive ao fim da fase. Conferir git status.
8. Geometria só do cache data/external/geo/natural_earth_brazil.gpkg. representative_point() para rótulos.
9. Sem dependência nova por conveniência.
10. "PARE E PERGUNTE" = apresentar opções com números reais e esperar minha resposta. Pontos de julgamento científico nunca são decididos por você.
11. Fim de fase: pytest (>= piso), python scripts/check_headlines.py (todo PASS), registrar D/C, commit "C<n>: ..." sem pedir autorização, mostrar o diff no relatório final, git log -3 e git status. Se algum check falhar, PARE. Push só com minha confirmação.
12. Figuras: sempre abrir e inspecionar o PNG gerado antes de declarar pronto.
13. Respostas sucintas.

## Stack

Python 3.11, xarray, rioxarray, geopandas, scipy, pandas, pyarrow,
matplotlib, isimip-client, pytest, ruff.

## Conventions

- `plant_uid` = blake2s hash of `name|lat|lon`.
- Tabular data: parquet. Gridded data: NetCDF.
- Scripts: `NN_name.py`, numbered by spec step.
- Article figures and tables are built only by `scripts/article/` (`python scripts/article/build_all.py [--out DIR]`, D134); never hand-made or `_tmp_*`.
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
  Article artifacts (see Environment) are the exception and go under
  `data/outputs/article/`.

## Command flow

grep precedent/IDs -> audit -> implement -> test -> update
`docs/CRAEI_work_plan_v2.md` -> stop for review.

## Test floor

- Current pytest floor: 225 passed, 1 skipped (measured 2026-10-07 at C87, commit 51e48e4).
  Update this line on each new floor; append the superseded one to the history below.

## Test floor history

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
- Pytest floor after W4a: 184 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after W3f-6: 188 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after C44: 188 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after C45: 188 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after W3g: 195 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after C47: 203 passed, 1 skipped (measured 2026-10-01; supersedes the floor above).
- Pytest floor after C48: 211 passed, 1 skipped (measured 2026-10-02; supersedes the floor above).
- Pytest floor after C51: 215 passed, 1 skipped (measured 2026-10-02; supersedes the floor above).
- Pytest floor after C52: 215 passed, 1 skipped (measured 2026-10-02; supersedes the floor above).
- Pytest floor after C60: 220 passed, 1 skipped (measured 2026-10-03; supersedes the floor above).
- Pytest floor after C62: 225 passed, 1 skipped (measured 2026-10-05; supersedes the floor above).
