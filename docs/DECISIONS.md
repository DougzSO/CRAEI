| ID  | Decision | Status | Tier/Source | Date |
|---|---|---|---|---|
| D01 | Climate data: ISIMIP3b bias-adjusted, 5 primary GCMs | closed | Spec §1.3 | 2026-09-16 |
| D02 | Baseline 1985-2014, future 2041-2070, SSP1-2.6/3-7.0/5-8.5 | closed | Spec §1.3 | 2026-09-16 |
| D03 | Main hazards H1 heat, H2 SPEI-12 Hargreaves, H3 Aqueduct bws; H4 precip and solar in SI | closed | Spec §1.4 | 2026-09-16 |
| D04 | Wind power excluded | closed | Spec §0, §1.4 | 2026-09-16 |
| D05 | No composite score | closed | Spec §0, §1.5 | 2026-09-16 |
| D06 | Coastal buffer 5 km | closed | Spec §1.2 (tier 3) | 2026-09-16 |
| D07 | Heat class ΔTX35 ≥ 30 days/yr | closed | Spec §1.4 (tier 3) | 2026-09-16 |
| D08 | Drought class R_D ≥ 2 | closed | Spec §1.4 (tier 3) | 2026-09-16 |
| D09 | Compound metric baseline P90 | closed | Spec §1.6 | 2026-09-16 |
| D10 | Validation against ONS ENA and REN | closed | Spec §1.7 | 2026-09-16 |
| D11 | Hydro with no type treated as reservoir | closed | Spec §1.2 | 2026-09-16 |
| D12 | ERA5 gust, IBTrACS and legacy rasters not used | closed | Spec §0 | 2026-09-16 |
| D13 | Repository license MIT, visibility public | closed | author | 2026-09-16 |
| O01 | Repository license and visibility | open → D13 | author | 2026-09-16 |
| D15 | GEM technology string mapping to classes (see table below) | closed | author | 2026-09-16 |
| D16 | GEM status values for operating/planned_adv/planned_early (see table below) | closed | author | 2026-09-16 |
| D17 | Environment manager: conda-forge via `environment.yml` | closed | author | 2026-09-16 |
| D14 | Aqueduct: acquire Aqueduct 4.0 with baseline in Phase 2 (local file only has 2050, non-`bws` fields) | closed | author | 2026-09-16 |
| D18 | REN hydroelectric productivity index has years before 2015 in the queryable series (author confirmed manually); overlap with W5E5 ≤2019 exceeds the 15-year floor in COMANDO 09 | closed | author | 2026-09-16 |

## COMANDO 08: ISIMIP3b and W5E5 availability (source: `scripts/check_isimip_availability.py`, ISIMIP data API)

- **60/60 combinations** (5 models × 4 scenarios × 3 variables) confirmed, file spans cover the required years:
  - historical (all 5 models): file span 1850-2014, needed 1984-2014 — OK.
  - ssp126/ssp370/ssp585 (all 5 models): file span 2015-2100, needed 2041-2070 — OK.
- **W5E5v2.0** (bias-adjustment reference, `ISIMIP3a/SecondaryInputData`, dataset `{var}_W5E5v2.0`): file span 1979-2019, needed 1984-2019 — OK, all 3 variables (tasmax, tasmin, pr).
- File chunking is not uniform: early years are per-year files (e.g. `..._1850_1850.nc`), later years are per-decade (e.g. `..._2001_2010.nc`); W5E5 files use a third convention, `_YYYYMMDD-YYYYMMDD.nc`. The downloader (COMANDO 10) must not assume one file per year.
- **Known `isimip-client` 2.0.2 bug**: `ISIMIPClient.get_job(poll=...)` polls by unbounded recursion (one stack frame per poll) instead of a loop. A cutout job that stays `queued`/`started` past Python's default recursion limit (~1000 polls) raises `RecursionError`. The test cutout (gfdl-esm4, tasmax, 2000-2009, Portugal) was still `queued` after 900s+ server-side wait, confirming ISIMIP cutout jobs can take longer than the client's polling can safely wait. **Any future use of `poll=True` must be replaced with a manual polling loop** (see `poll_job()` in the script) — do not pass `poll=True`/`poll=<seconds>` to `post_job`/`cutout_bbox`/`get_job` directly.
- Test cutout job was submitted (id `c8d3dcbad38dfd8e843c3804b07f11cf2db5d6e3`, ttl 7 days) but did not complete within this session; size/calendar attribute could not be recorded. Re-run `scripts/check_isimip_availability.py` (or poll the saved job URL) before COMANDO 10 to get an actual test-file size for volume extrapolation.

## COMANDO 09: auxiliary and validation data

| Source | URL | Period | Format |
|---|---|---|---|
| HydroBASINS level 6 (standard, with lakes) | `https://data.hydrosheds.org/file/hydrobasins/standard/hybas_{sa,as,eu}_lev06_v1c.zip` (sa=Brazil, as=India, eu=Portugal; all 3 URLs return HTTP 200) | n/a (static topology) | Shapefile (.shp/.dbf/.shx/.sbn/.sbx), WGS84 |
| ONS ENA diário por subsistema | `https://dados.ons.org.br/dataset/ena-diario-por-subsistema` (official CKAN API confirmed) | 2000-01-01 to present (2026), one file per year | CSV, XLSX; Parquet from 2021 |
| REN índice de produtibilidade hidroelétrica | `https://datahub.ren.pt/pt/eletricidade/regimes/` | Monthly resolution; series confirmed by author (manual check) to include years before 2015 — overlap with W5E5 (≤2019) exceeds the 15-year floor (D18) | Not confirmed programmatically (site is a JS SPA; REN DataHub API base is `https://servicebus.ren.pt/datahubapi/`, JSON, but the specific endpoint for this index was not identified — download will need a manual export or a located endpoint in COMANDO 20) |
| GADM / Natural Earth / EM-DAT / GEM | — | — | Already audited in COMANDO 07 |

- `NEXT_DOWN` and `UP_AREA` **confirmed present** in the standard HydroBASINS attribute schema (fixed across all levels/continents): `HYBAS_ID, NEXT_DOWN, NEXT_SINK, MAIN_BAS, DIST_SINK, DIST_MAIN, SUB_AREA, UP_AREA, PFAF_ID, ENDO, COAST` (not verified by opening the actual level-6 shapefile locally — files were not downloaded, only URL reachability was checked; verify field names on ingestion in COMANDO 13-14).
- ONS: 4 subsystems confirmed by inspecting an actual 2020 CSV — `N` (Norte), `NE` (Nordeste), `S` (Sul), `SE` (Sudeste). Overlap with W5E5 (1984-2019): **2000-2019 = 20 years ≥ 15 → no O needed for Brazil.**
- REN: DataHub UI selector only exposed 2015-2026, but author manually confirmed the series has years before 2015 → 15-year floor satisfied (D18).
- India has no validation source in Spec §1.7 (already documented as L02/L09); not applicable to COMANDO 09.

## COMANDO 07 audit tables (source: local files under `config/paths.local.yaml`; see `scripts/audit_local_data.py`)

Values listed only, not mapped to classes. Per-country row counts match file/subset totals (criterion met).

### GEM Global Integrated Power Tracker (sheet "Power facilities", snapshot 9 Aug 2026)

- 182,592 rows total (global); 0 rows without coordinates; 0 rows without capacity.
- Country subset counts: Brazil 10,414; India 8,306; Portugal 798.
- `Status` (10 values, all 3 countries): announced, cancelled, cancelled - inferred 4 y, construction, mothballed, operating, pre-construction, retired, shelved, shelved - inferred 2 y. Portugal has no "mothballed".
- `Type` per country:
  - Brazil: bioenergy, coal, hydropower, nuclear, oil/gas, utility-scale solar, wind
  - India: bioenergy, coal, hydropower, nuclear, oil/gas, utility-scale solar, wind
  - Portugal: bioenergy, coal, geothermal, hydropower, oil/gas, utility-scale solar, wind
- `Technology` per country (hydro/thermal subtypes live here, not in `Type`):
  - Brazil: Assumed PV, ICCC, Offshore hard mount, Offshore mount unknown, Onshore, PV, combined cycle, conventional and run-of-river, conventional storage, gas turbine, internal combustion, pressurized water reactor, run-of-river, steam turbine, subcritical, supercritical, unknown
  - India: adds IGCC, Solar Thermal, Unknown, boiling water reactor, fast breeder reactor, pressurized heavy water reactor, pumped storage, ultra-supercritical (relative to Brazil's set)
  - Portugal: Assumed PV, ICCC, Offshore floating, Onshore, PV, binary cycle, combined cycle, conventional storage, gas turbine, pumped storage, run-of-river, subcritical, unknown
- `Fuel (combustion only)` has 425 distinct combined strings globally (blend percentages included); per-country lists are shorter (Brazil 31, India 28, Portugal 9) — see script output, not reproduced here in full.
- Note: hydro subtype (reservoir/run-of-river/pumped storage per Spec §1.2) is not a single field; it must be derived from `Technology` (e.g. "conventional and run-of-river" vs "conventional and pumped storage" vs "run-of-river" vs "pumped storage") with fallback to reservoir when absent, per D11.

### WRI Aqueduct (per-country CSV, Google Earth Engine export)

- Only `aqueduct_2050.csv` exists locally for Brazil (1,118 rows), India (403 rows), Portugal (13 rows). No baseline file.
- No column named `bws`. Water-stress fields follow the pattern `{scenario}{horizon}_ws_x_{l|r|s|c}` where scenario ∈ {bau, opt, pes} (business-as-usual/optimistic/pessimistic — plausibly mapping to SSP3-7.0/SSP1-2.6/SSP5-8.5 per Spec §1.4) and horizon ∈ {30, 50, 80} (likely 2030/2050/2080, not just 2050). Suffixes: `_l` = label (category string, e.g. "Extremely high (>80%)"), `_c` = category code (-1..4), `_r`/`_s` = numeric raw/score values.
- This is Aqueduct 3.x-style column naming (`ws` = "water stress"), not the `bws` ("baseline water stress") naming from Aqueduct 4.0 referenced in Spec §1.4. Needs author verdict: re-download Aqueduct 4.0 with baseline, or confirm this file already contains an equivalent baseline column under one of the other `x` slots.

### EM-DAT (per-country CSV)

- Brazil: 239 rows, 1948-2024. India: 622 rows, 1900-2024. Portugal: 38 rows, 1941-2024.
- 47 columns each; `Disaster Type` unique values (same across all 3 countries): Drought, Extreme temperature, Flood, Storm.

### D16: GEM `Status` → fleet mapping

| GEM `Status` | Fleet |
|---|---|
| operating | operating |
| construction, pre-construction | planned, advanced |
| announced | planned, early |
| shelved, shelved - inferred 2 y, cancelled, cancelled - inferred 4 y, mothballed, retired | excluded |

### D15: GEM `Type`/`Technology` → technology class mapping

- `Type` = wind → excluded (D04). `Type` = geothermal → excluded (out of Spec §1.2 scope; see `docs/LIMITATIONS.md`).
- `Type` = hydropower → **Hydro**, subtype from `Technology`:
  - "run-of-river", "conventional and run-of-river" → run-of-river
  - "pumped storage", "conventional and pumped storage" → pumped storage
  - "conventional storage", "unknown" → reservoir (per D11)
- `Type` ∈ {coal, oil/gas, bioenergy} → **Thermal**, split by `Technology`:
  - "gas turbine", "internal combustion" → air-only (heat hazards only)
  - "combined cycle", "steam turbine", "subcritical", "supercritical", "ultra-supercritical", "ICCC", "IGCC", "unknown"/"Unknown" → water-dependent (default on unknown; consistent with D11's conservative-default pattern)
- `Type` = nuclear → **Thermal, water-dependent** (Spec §1.2, explicit).
- `Type` = utility-scale solar → **Solar PV** (Supplementary Information only, Spec §1.2).

### GADM (per-country GeoPackage, v4.1)

- Brazil (`gadm41_BRA.gpkg`): layers ADM_ADM_0/1/2; finest layer ADM_ADM_2 has 5,572 features.
- India (`gadm41_IND.gpkg`): layers ADM_ADM_0/1/2/3; finest layer ADM_ADM_3 has 2,347 features.
- Portugal (`gadm41_PRT.gpkg`): layers ADM_ADM_0/1/2/3; finest layer ADM_ADM_3 has 4,259 features.
- Admin depth is not uniform across countries (Brazil stops at level 2).
