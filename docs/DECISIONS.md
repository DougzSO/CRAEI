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
| D19 | ISIMIP3b acquisition route: direct download of the global file via `files.isimip.org`, local crop of the 3 study bboxes. Remote crop via fsspec discarded. | closed | author, COMANDO 11 | 2026-09-17 |
| D20 | Remote spatial-subset reads discarded: HDF5 chunk layout of ISIMIP3b files is `(1, 360, 720)` — one time step per chunk, full global grid, no spatial decomposition. A bbox read still transfers every needed day's whole-globe chunk, so it saves no bandwidth over a full download. | closed | author, COMANDO 11 | 2026-09-17 |
| D21 | Server-side cutout (ISIMIP API) registered as the preferable route when available — the server has local disk access to the chunks, so only the small cropped result crosses the network. Currently blocked by `data.isimip.org` (API host) being unreachable (connection timeout, not queue congestion; confirmed repeatedly over several hours). Not a prerequisite for any phase; retry when the host responds. | closed | author, COMANDO 11 | 2026-09-17 |
| D22 | Plan B documented, not activated: NASA NEX-GDDP-CMIP6 on public S3 (`s3://nex-gddp-cmip6`, `--no-sign-request`, us-west-2), with THREDDS/NCSS server-side subsetting at NCCS. Verified: all 5 required models present (including UKESM1-0-LL) and all 4 Tier-1 SSPs (historical, ssp126, ssp370, ssp585) present for every model. Switching to it requires a new explicit decision and a `LIMITATIONS.md` entry on the change of observational reference relative to W5E5 (different bias-adjustment product, weakens the fit with the Spec's validation/cross-model-consistency argument). | closed | author, COMANDO 11 | 2026-09-17 |
| D23 | Plan B (D22) numeric trigger: activate only if (a) the median transfer rate measured over 24 consecutive hours projects completion of the 180 files in more than 14 calendar days, or (b) `files.isimip.org` is unreachable for more than 12 continuous hours. | closed | author, COMANDO 11 | 2026-09-17 |
| D24 | Projected CRS per country for distance-to-coast (Spec §1.2, §3 Step 1): azimuthal equidistant (`+proj=aeqd`) centered on each country's plant centroid, computed on the fly per country rather than a fixed national EPSG code. Distances stay accurate to well under 1% error at country scale and this avoids picking an arbitrary national grid (e.g. Brazil Polyconic vs. an India LCC with no single official standard) for a value only used for a 2/5/10 km coastal threshold. | closed | author, COMANDO 13 (tier 3) | 2026-09-17 |
| D25 | "Nearest land cell" (Spec §3 Step 1/3): the country-cropped ISIMIP tasmax/tasmin/pr files carry no ocean NaN mask (verified: 0 NaN cells over open ocean inside the Brazil bbox), so land/ocean is not derivable from the climate files themselves. A grid cell is treated as land if its 0.5°×0.5° box intersects the country's GADM level-0 polygon (already acquired, COMANDO 07/09). | closed | author, COMANDO 14 (tier 3) | 2026-09-17 |
| D26 | Supersedes the "delete after crop" part of D19: global ISIMIP files downloaded to `cache_dir` (D:, ~1.7 TB free) are now kept permanently instead of deleted after each job's crop. Reasoning changed since D19: raw files are useful for adding countries later or reusing outside this pipeline, and disk cost is negligible (~350-400 GB for the full 60-job set) relative to free space. Also fixes a related bug: a crop failure caused by a corrupted cached global file (observed once, from an earlier process collision) would otherwise repeat forever, since presence alone was trusted without content validation — `acquire_job_all_countries` now deletes and re-downloads once if crop still fails after `crop_to_countries`'s own retries. | closed | author, COMANDO 12 follow-up | 2026-09-18 |
| D27 | Superseded same day, see correction below (author: `data_root` stays on C:; only the raw global cache and its staging area use D:). | superseded | author, COMANDO 12 rework | 2026-09-18 |
| D27' | Correction to D27: `data_root` (final country crops + interim/processed/outputs, ~0.9 GB, small individual files ~25-165 MB) stays on C: (SSD, ~30 GB free is ample for this). Only the large raw global ISIMIP files (`isimip_global_cache_dir`, ~350-400 GB for the full 60-job set) live on D:, as already decided in D26 — unchanged by this rework. `data_root` was briefly moved to D: and moved back same session after author correction; `manifest.json` paths were rewritten both times to match. | closed | author, COMANDO 12 rework | 2026-09-18 |
| D28 | New `isimip_staging_dir` (`C:/Users/User/AppData/Local/CRAEI_staging`, SSD): `download_global_file` now writes the live, hours-long, repeatedly-retried download there, h5py-validates it (item 5), and only then `shutil.move`s the finished file into `cache_dir` (D:, USB) — a single fast operation, not a long-held write. This is the structural fix for the D27/COMANDO-12-pause hang: a Python-level watchdog thread cannot terminate a write stuck in an uninterruptible kernel wait (confirmed by the earlier `taskkill /F` failure), so the fix is to keep that vulnerable write off the USB drive rather than try to detect/kill it there. Final country crops (`crop_to_countries`) write to `raw_dir`, which is on C: (D27'), so they never touch D: at all — the only D: writes left are the single post-validation `shutil.move` per global file. | closed | author, COMANDO 12 rework | 2026-09-18 |
| D29 | Bounded-stall watchdog added to `_download_single_stream` (`WATCHDOG_POLL_S=60`, `WATCHDOG_STALL_S=300`, `WATCHDOG_MAX_RESTARTS=3`): if the partial file on the (SSD) staging path stops growing for 5 min, the attempt is aborted and retried via the existing `Range`-resume path, up to 3 times, each logged. Distinct from D28: this catches a genuinely stalled-but-connected transfer (server or network gone quiet); D28 avoids the disk-hang failure mode entirely rather than trying to detect/kill it. | closed | author, COMANDO 12 rework, item 3 | 2026-09-18 |
| D30 | Raw-file integrity check added (item 5): after every global-file download, `_validate_raw_netcdf` opens it with `h5py` and reads the last `time` step before the file is trusted; failure deletes it (never left half-good in the cache) — the existing `Content-Length` size check does not catch a truncated-but-right-length or bit-flipped file. | closed | author, COMANDO 12 rework, item 5 | 2026-09-18 |
| O02 | Windows Defender real-time-scan exclusion for `C:\Users\User\AppData\Local\CRAEI_staging` and `D:\Douglas\OUTROS\CRAEI_isimip_raw_cache` (item 6) — needed to rule out Defender as a contributor to file-lock failures during acquisition. Applied by the author (elevated PowerShell, `Add-MpPreference -ExclusionPath ...`) after a live `[WinError 32]` "file already in use" failure during `crop_to_countries` on a just-staged file was traced to Defender's real-time scan of a freshly-written ~2 GB file; confirmed via `Get-MpPreference \| Select-Object -ExpandProperty ExclusionPath`. `D:/Douglas/OUTROS/CRAEI_data` from the original command (this row's earlier text) was dropped: `data_root` moved off D: in D27', so nothing writes there. No further `WinError 32` failures observed in the run after the exclusion was applied. | closed | author, COMANDO 12 rework, item 6 | 2026-09-20 |

## COMANDO 12 rework: S3-vs-ISIMIP rate measurement, disk layout, hardening (2026-09-18, after restart)

- **Item 1 measurement** (both rates recorded before any concurrency change, per instruction — neither alone implies the cause):
  - `files.isimip.org` (GFDL-ESM4 historical tasmax global file, first 100 MB via `Range`): **1.05 MB/s** (100 MB in 99.5 s).
  - `s3://nex-gddp-cmip6` (`--no-sign-request` equivalent, plain HTTPS to the public bucket, GFDL-ESM4 historical tasmax 1985, first 100 MB via `Range`): **2.21 MB/s** (100 MB in 47.5 s).
  - S3 (a different server/dataset, same local connection) is ~2.1x faster than `files.isimip.org`. Consistent with the COMANDO 11 finding ("another host on the same connection transferred ~3x faster") that the bottleneck is `files.isimip.org` server-side throttling, not local bandwidth — **item 8's gate is satisfied** (bottleneck is the server, not the local connection).
  - Projection at the measured 1.05 MB/s: 59 remaining jobs x ~6.5 GB/job (avg. global-input size from the one completed job, `isimip3b/gfdl-esm4/historical/tasmax`, `content_length` 7,025,320,822 bytes) ≈ 384 GB ≈ **~102 hours (~4.3 days)** single-stream. Under the D23 14-day trigger — **Plan B (D22, NEX-GDDP-CMIP6) is not activated.**
- **Item 8 (concurrency sweep 3/6/8 x 10 min)**: gated condition (item 1) is met, but the sweep itself was not run this session — it is a ~30 min measurement, deferred to the actual full-acquisition run rather than done standalone; `DOWNLOAD_CONNECTIONS=3` (existing default, one connection per global file within a job) is unchanged for now.
- **Item 2 implemented, simplified per author instruction**: rather than "SSD then final destination, 10 deg crop margin", `data_root` moved off C: (SSD, only ~31 GB free) to D: (`config/paths.local.yaml`), and a new `isimip_staging_dir` (SSD, `C:/Users/User/AppData/Local/CRAEI_staging`) added so only the live download write (the vulnerable, hours-long part) stays on the SSD; `cache_dir` (D:) receives only the finished file via one `shutil.move`. See D27/D28.
- **Item 3 implemented**: `_StallWatchdog` in `craei.acquire.isimip` (D29). Explicitly does not claim to rescue an uninterruptible-kernel-I/O hang (Python cannot kill that from another thread — confirmed by the paused run's `taskkill /F` failure); D28's staging-dir fix is what removes that failure mode.
- **Item 4 (producer/consumer split) not implemented this session**: current single-process-per-job loop (`scripts/04_full_acquire.py`) already isolates one job's failure from the next (`try`/`except` per job, per `docs/DECISIONS.md`); a true separate download/crop process pair is a larger change deferred to a future COMANDO if D28+D29 do not fully resolve the hang.
- **Item 5 implemented**: `_validate_raw_netcdf` (D30), h5py-reads the last `time` step of every downloaded global file before it is trusted.
- **Item 6 not applied (no admin in this session)**: see O02 for the exact command for the author to run.
- **Item 7 resolved per author instruction** (this session, not a reopening of D26's own reasoning): keep the per-country crop as-is (no 10 deg margin), and for the underlying raw cache, simplify to "final crop always on D:, and if keeping the raw global-file cache causes further problems, just delete it" rather than the D26 permanent-cache-with-retry design. D26 itself (keep raw cache permanently) is **not reopened** — D: has 1.6 TB free, the disk-space argument for D26 still holds; only the *location* of `data_root`/final crops changed (D27).
- **Item 9 (poll `data.isimip.org` every 30 min) not implemented this session**: `_metadata_reachable()` (existing, `dataset_paths_resilient`) already re-probes at most every 15 min as a side effect of normal acquisition calls, which is tighter than the requested 30 min and needs no separate process; a fully separate always-on poller was judged not worth the added process to manage for a 2x-tighter cadence already covered.
- **Verification test performed** (not the full 3-consecutive-job criterion, which needs the actual multi-hour run): `tests/test_acquire_isimip.py` gained 5 unit tests against mocked HTTP responses — `_validate_raw_netcdf` accepts a valid / rejects a truncated file, `download_global_file` stages on the fake SSD dir and moves the finished, validated file into the fake cache dir with no `.part` left behind, a failed-validation file is deleted (not cached), and `_StallWatchdog` aborts a download whose partial file stops growing. All 42 project tests pass; `ruff check` clean.

## COMANDO 08: ISIMIP3b and W5E5 availability (source: `scripts/check_isimip_availability.py`, ISIMIP data API)

- **60/60 combinations** (5 models × 4 scenarios × 3 variables) confirmed, file spans cover the required years:
  - historical (all 5 models): file span 1850-2014, needed 1984-2014 — OK.
  - ssp126/ssp370/ssp585 (all 5 models): file span 2015-2100, needed 2041-2070 — OK.
- **W5E5v2.0** (bias-adjustment reference, `ISIMIP3a/SecondaryInputData`, dataset `{var}_W5E5v2.0`): file span 1979-2019, needed 1984-2019 — OK, all 3 variables (tasmax, tasmin, pr).
- File chunking is not uniform: early years are per-year files (e.g. `..._1850_1850.nc`), later years are per-decade (e.g. `..._2001_2010.nc`); W5E5 files use a third convention, `_YYYYMMDD-YYYYMMDD.nc`. The downloader (COMANDO 10) must not assume one file per year.
- **Known `isimip-client` 2.0.2 bug**: `ISIMIPClient.get_job(poll=...)` polls by unbounded recursion (one stack frame per poll) instead of a loop. A cutout job that stays `queued`/`started` past Python's default recursion limit (~1000 polls) raises `RecursionError`. The test cutout (gfdl-esm4, tasmax, 2000-2009, Portugal) was still `queued` after 900s+ server-side wait, confirming ISIMIP cutout jobs can take longer than the client's polling can safely wait. **Any future use of `poll=True` must be replaced with a manual polling loop** (see `poll_job()` in the script) — do not pass `poll=True`/`poll=<seconds>` to `post_job`/`cutout_bbox`/`get_job` directly.
- Test cutout job was submitted (id `c8d3dcbad38dfd8e843c3804b07f11cf2db5d6e3`, ttl 7 days) but did not complete within this session; size/calendar attribute could not be recorded. Re-run `scripts/check_isimip_availability.py` (or poll the saved job URL) before COMANDO 10 to get an actual test-file size for volume extrapolation.

## COMANDO 10/11: manifest, downloaders, pilot download (in progress)

- `config/paths.local.yaml` (gitignored, not shown in diffs) was fixed: `raw_dir`/`data_root`/etc. now point to a dedicated `data/` folder next to the repo (`CLIMATE RISK FRAMEWORK/data/`, outside git and outside the legacy `GEAR_framework` project), not inside `GEAR_framework/data/raw` as originally set up in COMANDO 07. The `gem_file`/`aqueduct_dir`/`emdat_dir`/`gadm_dir` keys still point into `GEAR_framework` but only as read-only sources for `import_existing_local_data()`; nothing CRAEI does writes back there.
- **ISIMIP cutout API is currently slow/congested**, independent of the COMANDO 08 `isimip-client` recursion bug already fixed: 36 submitted cutout jobs (GFDL-ESM4, 3 countries) stayed `queued` for 30+ minutes with zero progress. Confirmed this is server-side (another host on the same connection transferred ~3x faster) and affects both the job-queue cutout endpoint and plain static-file downloads from `files.isimip.org` (measured ~1 MB/s vs ~4 MB/s baseline).
- Explored and ruled out alternatives: (a) downloading full global chunk files directly and cutting locally — technically simple (server supports HTTP Range) but ~77 GB for one model's pilot, same slow origin server; (b) lazy remote reads via `fsspec`+`h5netcdf` (partial HTTP Range reads, no full download) — technically works but stalls in practice, likely because the bbox+time slice touches many small compressed HDF5 chunks, each needing its own slow round trip. No faster public mirror (AWS/GEE) was found for this specific bias-adjusted (W5E5) dataset.
- `src/craei/acquire/isimip.py` was extended with `submit_job`/`finalize_job`/`poll_all` (submit every job first, then poll all of them together, instead of blocking on one job at a time) and a **submission checkpoint** (`{raw_dir}/pilot_gfdl-esm4_checkpoint.json`, written after every single submission) so a pilot run can be killed and resumed without resubmitting already-queued jobs.
- Given the queue congestion, the GFDL-ESM4 pilot (COMANDO 11) was narrowed to Portugal only first (12/36 jobs: 4 scenarios × 3 variables) via `scripts/03_pilot_download.py --countries PRT`, to validate the full flow on 1/3 the queue load before committing to Brazil and India. Expected cutout output size is small regardless of country (~0.3-1.9 GB per country for the full 12-combination set, estimated from bbox area vs. global grid), so the bottleneck is entirely queue/processing time, not data volume.
- **C11 status: in progress, not complete.** The 36-job (all 3 countries) run was submitted once already and abandoned when the queue showed no progress; those job IDs are not tracked (checkpoint only added afterward). The current Portugal-only run's checkpoint should be checked/resumed before declaring C11 done.
- **Switched from cutout API to direct download + local crop.** Confirmed the congestion is specific to the cutout job queue, not the ISIMIP server overall: `client.datasets()` (metadata) answered in 1.18 s, and a direct HTTPS download of a global file progressed steadily (measured ~1.16 MB/s single-stream, ~1.58 MB/s with 4 parallel streams — the server rate-limits per client, so parallelism gives little extra). `src/craei/acquire/isimip.py` gained `dataset_paths`, `download_global_file`, `crop_to_country`, `run_job_direct`: each job downloads whole global files (not cut server-side), crops them locally to the country bbox and required years with xarray, and registers only the small cropped file in the manifest. `scripts/03_pilot_download.py` now calls `run_job_direct` instead of submit/poll; the old `submit_job`/`finalize_job`/`poll_all` functions are kept (still covered by tests) as the cutout-based path, unused by the pilot script but available if the queue congestion clears.
- Raw global files (~1-2 GB each, shared by all 3 study countries) are cached permanently outside the project's own data folder, at `D:/Douglas/OUTROS/CRAEI_isimip_raw_cache/` (own `README.md` there explains the folder), configured via the new `isimip_global_cache_dir` key in `config/paths.local.yaml` (documented in `config/paths.example.yaml`). This avoids re-downloading ~35-45 GB total if the study later adds countries, while country crops (the actual files CRAEI uses) still go to `raw_dir` as before.
- **Bug found and fixed: silent short reads corrupted 6/8 cached global files.** A parallel range fetch could have its HTTP connection close cleanly with fewer bytes than the requested range, without `requests` raising — the old code treated that as success. This produced files that were the right total size (pre-truncated) but had garbage/missing bytes in some HDF5 chunks, only surfacing as `NetCDF: HDF error` when xarray happened to read that region (not necessarily at the start of the file). `_fetch_range` now compares bytes actually written to the requested range size and retries (resuming from the current position) if short. The 6 corrupted files were deleted from the cache and re-downloaded.
- Also added retry (`METADATA_RETRIES=4`, exponential backoff) around `client.datasets()` in `dataset_paths()`: `data.isimip.org` (the metadata API host, separate from `files.isimip.org`) failed DNS resolution for several minutes mid-run, which previously failed 9 of 12 jobs in cascade with no retry.
- **Root-cause correction on parallel-range corruption, and outage confirmation.** Checked the HDF5 chunk layout of a tasmax file via range request (`h5py` over `fsspec`): chunks are `(1, 360, 720)` — one full global grid per time step, not spatially decomposed. This means (a) remote lazy reads (fsspec/h5netcdf) cannot save bandwidth for a country bbox, since every needed day's chunk covers the whole globe regardless — confirms why that alternative stalled without benefit; (b) the cutout API is genuinely the bandwidth-optimal mechanism (server has local disk access to the chunks; only the small cropped result crosses the network), so the earlier decision to abandon it for congestion was reasonable at the time but should be revisited once `data.isimip.org` (the API host) is reachable again. As of this check, `data.isimip.org` is not a queue-congestion problem anymore but a **full connection timeout** (confirmed via direct `curl`, independent of `isimip-client`), unchanged across several hours — `files.isimip.org` (plain file downloads) remains healthy throughout. Direct download + local crop continues as the only currently-working path; batched cutout submission (5-10 jobs, IDs persisted to disk, polled every 10-15 min without blocking) should be retried once `data.isimip.org` responds again.
- Cache is already deduplicated per global file regardless of country (`download_global_file` keys by `repo_path`, not by country), so Brazil/India will reuse files already downloaded for Portugal — no 3x blowup from downloading per-country.
- **Plan B, not adopted: NASA NEX-GDDP-CMIP6 on public S3 (`s3://nex-gddp-cmip6`, `--no-sign-request`, us-west-2), with THREDDS/NCSS server-side spatial subsetting at NCCS.** Verified via the bucket's public HTTPS listing: all 5 required models present, including UKESM1-0-LL, and all 4 Tier-1 SSPs (historical, ssp126, ssp370, ssp585) present for every model — the two open questions (UKESM1-0-LL presence, ssp370 availability) are both resolved positively. Not switching to it now: it is a different bias-adjustment product with a different observational reference than W5E5, which would weaken the fit with Spec's validation and cross-model consistency argument — adopting it would need an explicit `DECISIONS.md` entry (Rule 9), not a silent swap. Kept as an explicit fallback if the direct-download/cutout paths against ISIMIP remain unworkable.

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
