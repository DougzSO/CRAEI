"""ISIMIP3b climate input acquisition: cutout jobs per model/scenario/variable.

Each job cuts the 3 study-area bounding boxes (Brazil, India, Portugal) out of
the global bias-adjusted files, so 60 combinations (from `datasets.yaml`)
produce 180 registered files.

The ISIMIP data API's own `poll=True` recurses once per poll and overflows
Python's recursion limit on slow jobs (see COMANDO 08 finding in
`docs/DECISIONS.md`); `poll_job` below polls in a loop instead.
"""

import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests
import xarray as xr

from craei.manifest import Manifest

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 900
PROGRESS_REPORT_INTERVAL_S = 300

ISIMIP_FILES_BASE = "https://files.isimip.org"
ISIMIP_METADATA_BASE = "https://data.isimip.org"
DOWNLOAD_CONNECTIONS = 3
MIN_FREE_SPACE_BYTES = 20 * 1024**3
STUDY_COUNTRIES = ("BRA", "IND", "PRT")


@dataclass(frozen=True)
class IsimipJob:
    model: str
    scenario: str
    variable: str

    @property
    def key_prefix(self) -> str:
        return f"isimip3b/{self.model}/{self.scenario}/{self.variable}"


def build_jobs(datasets_cfg: dict) -> list[IsimipJob]:
    return [
        IsimipJob(model=model, scenario=scenario, variable=variable)
        for model in datasets_cfg["models"]
        for scenario in datasets_cfg["scenarios"]
        for variable in datasets_cfg["variables"]
    ]


def poll_job(client, job: dict) -> dict:
    elapsed = 0
    while job and job["status"] in ("queued", "started") and elapsed < POLL_TIMEOUT_S:
        time.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
        job = client.get_job(job["job_url"], poll=None)
    return job


def poll_all(client, pending_jobs: list[dict], timeout_s: int, interval_s: int = 15) -> list[dict]:
    """Round-robin poll many submitted jobs at once until all finish or `timeout_s` elapses.

    Mutates and returns `pending_jobs`, updating each entry's "submitted"
    status in place as jobs complete.
    """
    elapsed = 0
    while elapsed < timeout_s:
        active_statuses = ("queued", "started")
        still_pending = [p for p in pending_jobs if p["submitted"]["status"] in active_statuses]
        if not still_pending:
            break
        for pending in still_pending:
            pending["submitted"] = client.get_job(pending["submitted"]["job_url"], poll=None)
        time.sleep(interval_s)
        elapsed += interval_s
    return pending_jobs


def required_years(job: IsimipJob, datasets_cfg: dict) -> tuple[int, int]:
    key = "historical" if job.scenario == "historical" else "future"
    span = datasets_cfg["download_years"][key]
    return span["start"], span["end"]


def submit_job(
    client,
    manifest: Manifest,
    job: IsimipJob,
    country: str,
    datasets_cfg: dict,
) -> dict | None:
    """Submit `job`'s cutout to `country`'s bbox without waiting for it to finish.

    Returns None if the file is already registered and intact (skip), or a
    dict with the submitted job info and enough context to finalize it later
    via `finalize_job`. Submitting (rather than submit-and-block) lets many
    jobs sit in the ISIMIP server's queue at once instead of one at a time —
    cutting a full historical/future global file can take the server a long
    time, and jobs queued together finish far sooner in aggregate than jobs
    submitted and awaited one by one (see COMANDO 11 finding in DECISIONS.md).
    """
    key = f"{job.key_prefix}/{country}"
    if manifest.is_intact(key):
        return None

    result = client.datasets(
        simulation_round="ISIMIP3b",
        climate_scenario=job.scenario,
        climate_forcing=job.model,
        climate_variable=job.variable,
        bias_adjustment="w5e5",
    )
    if not result:
        raise ValueError(f"no ISIMIP dataset found for {job}")
    dataset = result[0]

    start_year, end_year = required_years(job, datasets_cfg)
    target_paths = [
        f["path"]
        for f in dataset["files"]
        if _file_overlaps(f["name"], start_year, end_year)
    ]
    if not target_paths:
        raise ValueError(f"no files cover {start_year}-{end_year} for {job}")

    west, east, south, north = datasets_cfg["bboxes"][country]
    submitted = client.cutout_bbox(target_paths, west, east, south, north, poll=None)
    return {"key": key, "job": job, "country": country, "submitted": submitted}


def finalize_job(client, manifest: Manifest, pending: dict, raw_dir: Path) -> dict:
    """Poll a job submitted by `submit_job` to completion, download, and register it."""
    job, key = pending["job"], pending["key"]
    finished = poll_job(client, pending["submitted"])
    if not finished or not finished.get("file_url"):
        raise RuntimeError(f"cutout job did not produce a file for {key}: {finished}")

    out_dir = raw_dir / "climate" / "isimip3b" / job.model / job.scenario / job.variable
    out_dir.mkdir(parents=True, exist_ok=True)
    file_url = finished["file_url"]
    local_path = client.download(file_url, path=str(out_dir), validate=True, extract=True)
    return manifest.register(key, local_path, origin=file_url)


def run_job(
    client,
    manifest: Manifest,
    job: IsimipJob,
    country: str,
    datasets_cfg: dict,
    raw_dir: Path,
) -> dict | None:
    """Submit and block until `job`'s cutout for `country` is done, then register it.

    Returns None if the file was already registered and intact (skip), or
    the manifest entry for the newly downloaded file otherwise. For many
    jobs at once, prefer `submit_job` + `finalize_job` so jobs queue in
    parallel server-side.
    """
    pending = submit_job(client, manifest, job, country, datasets_cfg)
    if pending is None:
        return None
    return finalize_job(client, manifest, pending, raw_dir)


def _file_overlaps(filename: str, start_year: int, end_year: int) -> bool:
    m = re.search(r"_(\d{4})_(\d{4})\.nc$", filename)
    if not m:
        return False
    file_start, file_end = int(m.group(1)), int(m.group(2))
    return file_start <= end_year and file_end >= start_year


METADATA_RETRIES = 4


def dataset_paths(client, job: IsimipJob, datasets_cfg: dict) -> list[str]:
    """List ISIMIP repository paths of the global files covering `job`'s required years.

    Retries the metadata call: `data.isimip.org` was observed to fail DNS
    resolution/connect for several minutes during an otherwise-healthy run
    (see COMANDO 11 in docs/DECISIONS.md), which is a transient network
    condition, not a permanently missing dataset.
    """
    result = None
    for attempt in range(METADATA_RETRIES):
        try:
            result = client.datasets(
                simulation_round="ISIMIP3b",
                climate_scenario=job.scenario,
                climate_forcing=job.model,
                climate_variable=job.variable,
                bias_adjustment="w5e5",
            )
            break
        except requests.exceptions.RequestException:
            if attempt == METADATA_RETRIES - 1:
                raise
            time.sleep(15 * (attempt + 1))
    if not result:
        raise ValueError(f"no ISIMIP dataset found for {job}")
    start_year, end_year = required_years(job, datasets_cfg)
    return [
        f["path"] for f in result[0]["files"] if _file_overlaps(f["name"], start_year, end_year)
    ]


def _decade_ranges(
    start_year: int, end_year: int, dataset_end: int | None
) -> list[tuple[int, int]]:
    aligned_start = start_year - ((start_year - 1) % 10)
    ranges = []
    y = aligned_start
    while y <= end_year:
        d_end = y + 9
        if dataset_end is not None and d_end > dataset_end:
            d_end = dataset_end
        ranges.append((y, d_end))
        y += 10
    return ranges


def dataset_paths_by_pattern(job: IsimipJob, datasets_cfg: dict) -> list[str]:
    """Build global file paths from the known ISIMIP3b decade-file naming
    convention, without querying the metadata API.

    Fallback for when `data.isimip.org` is unreachable (see COMANDO 11 in
    docs/DECISIONS.md). Each candidate path is HEAD-verified against
    `files.isimip.org` so a wrong guess raises instead of silently acquiring
    the wrong (or no) data. `historical` is capped at 2014 (the ISIMIP3b
    historical run's actual end, shorter than a full decade) — confirmed
    empirically; future scenarios use plain decade boundaries.
    """
    start_year, end_year = required_years(job, datasets_cfg)
    dataset_end = 2014 if job.scenario == "historical" else None
    model_dir = job.model.upper()
    paths = []
    for d_start, d_end in _decade_ranges(start_year, end_year, dataset_end):
        filename = (
            f"{job.model}_r1i1p1f1_w5e5_{job.scenario}_{job.variable}"
            f"_global_daily_{d_start}_{d_end}.nc"
        )
        path = (
            "ISIMIP3b/InputData/climate/atmosphere/bias-adjusted/global/daily/"
            f"{job.scenario}/{model_dir}/{filename}"
        )
        resp = requests.head(f"{ISIMIP_FILES_BASE}/{path}", timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            raise ValueError(f"pattern-guessed path not found (HTTP {resp.status_code}): {path}")
        paths.append(path)
    return paths


_metadata_status = {"reachable": None, "checked_at": 0.0}
METADATA_RECHECK_INTERVAL_S = 900


def _metadata_reachable() -> bool:
    """Probe `data.isimip.org` at most once per `METADATA_RECHECK_INTERVAL_S`.

    Doubles as the "check every 15 min whether the API recovered" cadence:
    a long-running acquisition loop calling `dataset_paths_resilient` picks
    up the API again automatically once it responds.
    """
    now = time.time()
    stale = now - _metadata_status["checked_at"] >= METADATA_RECHECK_INTERVAL_S
    if stale or _metadata_status["reachable"] is None:
        try:
            requests.head(f"{ISIMIP_METADATA_BASE}/api/v1/datasets/", timeout=10)
            _metadata_status["reachable"] = True
        except requests.exceptions.RequestException:
            _metadata_status["reachable"] = False
        _metadata_status["checked_at"] = now
    return _metadata_status["reachable"]


def dataset_paths_resilient(client, job: IsimipJob, datasets_cfg: dict) -> list[str]:
    """`dataset_paths` when the metadata API is reachable, else `dataset_paths_by_pattern`."""
    if _metadata_reachable():
        try:
            return dataset_paths(client, job, datasets_cfg)
        except requests.exceptions.RequestException:
            pass
    return dataset_paths_by_pattern(job, datasets_cfg)


class _ProgressTracker:
    """Thread-safe byte counters for one or more concurrent downloads, with periodic prints.

    Without this, a multi-file/multi-connection job gave no signal between
    "started" and "done" (often 20+ min for a single 2 GB file), so a hung
    or slow download was indistinguishable from a working one.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._totals: dict[str, int] = {}
        self._done: dict[str, int] = {}
        self._stop = threading.Event()

    def add(self, name: str, total: int) -> None:
        with self._lock:
            self._totals[name] = total
            self._done[name] = 0

    def advance(self, name: str, n: int) -> None:
        with self._lock:
            self._done[name] += n

    def report_forever(self, interval_s: float) -> None:
        while not self._stop.wait(interval_s):
            with self._lock:
                parts = [
                    f"{name}={self._done[name] / 1e6:.0f}/{total / 1e6:.0f} MB"
                    for name, total in self._totals.items()
                ]
            if parts:
                print(f"  [progress] {', '.join(parts)}", flush=True)

    def stop(self) -> None:
        self._stop.set()


def download_global_file(
    cache_dir: Path,
    repo_path: str,
    progress: "_ProgressTracker | None" = None,
) -> Path:
    """Download one whole global ISIMIP file into a permanent, reusable cache.

    Workaround for the cutout API's job queue being congested (jobs stuck
    "queued" for 30+ min with zero progress — see COMANDO 11 in
    docs/DECISIONS.md). Global files are large (~1-2 GB) but shared by every
    study country, so they are cached outside the project's own gitignored
    data folder and never re-downloaded once present.

    Downloads as a single sequential stream. Splitting one file across
    parallel Range requests was tried and dropped after it corrupted
    downloaded files (see `download_global_files`); concurrency comes only
    from downloading several files at once, each its own safe single stream.
    """
    local_path = cache_dir / repo_path
    if local_path.exists():
        return local_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = local_path.with_name(local_path.name + ".part")
    url = f"{ISIMIP_FILES_BASE}/{repo_path}"

    t0 = time.time()
    size, _ = _probe_file(url)
    if progress is not None and size:
        progress.add(local_path.name, size)
    _download_single_stream(url, tmp_path, progress, local_path.name)

    actual_size = tmp_path.stat().st_size
    if size and actual_size != size:
        tmp_path.unlink()
        raise OSError(f"{repo_path}: downloaded {actual_size} bytes, expected {size}")

    tmp_path.rename(local_path)
    elapsed = time.time() - t0
    mb = local_path.stat().st_size / 1e6
    rate = mb / max(elapsed, 1)
    msg = f"  [cache] {local_path.name}: {mb:.0f} MB in {elapsed:.0f}s ({rate:.2f} MB/s)"
    print(msg, flush=True)
    return local_path


def download_global_files(
    cache_dir: Path, repo_paths: list[str], max_parallel_files: int = DOWNLOAD_CONNECTIONS
) -> list[Path]:
    """Download several global files for one job concurrently, one connection per file.

    Splitting a single file's download across parallel Range requests was
    tried (see `_download_parallel_ranges`) but corrupted 100% of files in
    one run and 6/8 in another, even after fixing a silent-short-read bug —
    the exact cause (concurrent same-file writes vs. the server mishandling
    Range requests under concurrent load) was not pinned down given the time
    already spent debugging it. Each file is now a single, safe sequential
    stream; concurrency instead comes only from downloading multiple files
    at once (each to its own file, no shared-write risk). See COMANDO 11 in
    docs/DECISIONS.md.
    """
    already_cached = [p for p in repo_paths if (cache_dir / p).exists()]
    to_fetch = [p for p in repo_paths if p not in already_cached]
    if not to_fetch:
        return [cache_dir / p for p in repo_paths]

    progress = _ProgressTracker()
    reporter = threading.Thread(
        target=progress.report_forever, args=(PROGRESS_REPORT_INTERVAL_S,), daemon=True
    )
    reporter.start()
    workers = min(max_parallel_files, len(to_fetch))
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fetched = list(
                pool.map(lambda p: download_global_file(cache_dir, p, progress), to_fetch)
            )
    finally:
        progress.stop()
    fetched_by_path = dict(zip(to_fetch, fetched, strict=True))
    return [cache_dir / p if p in already_cached else fetched_by_path[p] for p in repo_paths]


def _probe_file(url: str) -> tuple[int, bool]:
    """Return (content_length, accepts_range_requests), falling back to (0, False)."""
    try:
        resp = requests.head(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        return 0, False
    size = int(resp.headers.get("Content-Length", 0))
    return size, resp.headers.get("Accept-Ranges") == "bytes"


DOWNLOAD_RETRIES = 5


def _download_single_stream(
    url: str,
    tmp_path: Path,
    progress: "_ProgressTracker | None" = None,
    progress_name: str = "",
) -> None:
    """Download `url` to `tmp_path` as one sequential stream, retrying on drops.

    On retry, resumes via `Range` from the last byte actually written
    instead of restarting — a connection was observed to drop mid-transfer
    on ~1-2 GB files (see COMANDO 11 in docs/DECISIONS.md).
    """
    pos = tmp_path.stat().st_size if tmp_path.exists() else 0
    mode = "r+b" if pos else "wb"
    for attempt in range(DOWNLOAD_RETRIES):
        headers = {"Range": f"bytes={pos}-"} if pos else {}
        try:
            with requests.get(url, headers=headers, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                with open(tmp_path, mode) as f:
                    if pos:
                        f.seek(pos)
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                        pos += len(chunk)
                        if progress is not None:
                            progress.advance(progress_name, len(chunk))
            return
        except requests.exceptions.RequestException:
            if attempt == DOWNLOAD_RETRIES - 1:
                raise
            mode = "r+b"
            time.sleep(2**attempt)


def crop_to_country(
    global_paths: list[Path], job: IsimipJob, country: str, datasets_cfg: dict, out_dir: Path
) -> Path:
    """Crop cached global file(s) to `country`'s bbox and required years, save one NetCDF."""
    west, east, south, north = datasets_cfg["bboxes"][country]
    start_year, end_year = required_years(job, datasets_cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{job.model}_{job.scenario}_{job.variable}_{country}.nc"
    with xr.open_mfdataset([str(p) for p in global_paths], combine="by_coords") as ds:
        lat_ok = (ds["lat"] >= south) & (ds["lat"] <= north)
        lon_ok = (ds["lon"] >= west) & (ds["lon"] <= east)
        cropped = ds.isel(lat=lat_ok.values, lon=lon_ok.values)
        cropped = cropped.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))
        cropped.load().to_netcdf(out_path)
    return out_path


def run_job_direct(
    client,
    manifest: Manifest,
    job: IsimipJob,
    country: str,
    datasets_cfg: dict,
    cache_dir: Path,
    raw_dir: Path,
) -> dict | None:
    """Direct-download + local-crop path, bypassing the congested cutout API queue.

    Returns None if already registered and intact, else the manifest entry.
    See `download_global_file` and `crop_to_country` for the two steps.
    """
    key = f"{job.key_prefix}/{country}"
    if manifest.is_intact(key):
        return None

    repo_paths = dataset_paths(client, job, datasets_cfg)
    local_globals = download_global_files(cache_dir, repo_paths)

    out_dir = raw_dir / "climate" / "isimip3b" / job.model / job.scenario / job.variable
    cropped_path = crop_to_country(local_globals, job, country, datasets_cfg, out_dir)
    origin = ",".join(f"{ISIMIP_FILES_BASE}/{p}" for p in repo_paths)
    return manifest.register(key, cropped_path, origin=origin)


def _check_free_space(path: Path, min_bytes: int = MIN_FREE_SPACE_BYTES) -> None:
    path.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(path).free
    if free < min_bytes:
        raise OSError(f"only {free / 1e9:.1f} GB free at {path}, need >= {min_bytes / 1e9:.0f} GB")


CROP_RETRIES = 4


def crop_to_countries(
    global_paths: list[Path],
    job: IsimipJob,
    countries: list[str],
    datasets_cfg: dict,
    out_dir: Path,
) -> dict[str, Path]:
    """Crop cached global file(s) to each of `countries` in one open+read pass.

    Opening the (multi-GB) global files once and cropping every country from
    the same in-memory dataset avoids re-reading them per country.

    Retries on OSError/RuntimeError (observed as a transient HDF5 "Permission
    denied" a few seconds after a multi-GB file finished downloading, almost
    certainly Windows Defender's real-time scan briefly locking the file it
    just wrote; see COMANDO 12 follow-up in docs/DECISIONS.md). The global
    files are already fully downloaded and cached, so a retry costs only the
    crop, not the download.
    """
    start_year, end_year = required_years(job, datasets_cfg)
    out_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(CROP_RETRIES):
        try:
            out_paths = {}
            with xr.open_mfdataset([str(p) for p in global_paths], combine="by_coords") as ds:
                ds_time = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))
                for country in countries:
                    west, east, south, north = datasets_cfg["bboxes"][country]
                    lat_ok = (ds_time["lat"] >= south) & (ds_time["lat"] <= north)
                    lon_ok = (ds_time["lon"] >= west) & (ds_time["lon"] <= east)
                    cropped = ds_time.isel(lat=lat_ok.values, lon=lon_ok.values)
                    out_path = out_dir / f"{job.model}_{job.scenario}_{job.variable}_{country}.nc"
                    cropped.load().to_netcdf(out_path)
                    out_paths[country] = out_path
            return out_paths
        except (OSError, RuntimeError):
            if attempt == CROP_RETRIES - 1:
                raise
            time.sleep(10 * (attempt + 1))
    raise AssertionError("unreachable")


def acquire_job_all_countries(
    client,
    manifest: Manifest,
    job: IsimipJob,
    datasets_cfg: dict,
    cache_dir: Path,
    raw_dir: Path,
    countries: tuple[str, ...] = STUDY_COUNTRIES,
) -> dict[str, dict | None]:
    """Download a job's global file(s) once, crop all `countries` in one pass.

    The global files are kept in `cache_dir` as a permanent, reusable cache
    (D26 in docs/DECISIONS.md, superseding the "delete after crop" part of
    D19-D23): they are useful for adding countries later or for reuse outside
    this pipeline, and `cache_dir` has ample free space.

    If `crop_to_countries` still fails after its own retries, one global
    file being genuinely corrupt (not just transiently locked) is the
    remaining suspect (observed once: a stale file from an earlier run's
    process collision, silently reused forever because presence alone was
    trusted). As a last resort, the cached files for this job are deleted
    and re-downloaded once before giving up.
    """
    missing = [c for c in countries if not manifest.is_intact(f"{job.key_prefix}/{c}")]
    if not missing:
        return dict.fromkeys(countries)

    repo_paths = dataset_paths_resilient(client, job, datasets_cfg)
    _check_free_space(cache_dir)
    out_dir = raw_dir / "climate" / "isimip3b" / job.model / job.scenario / job.variable

    local_globals = download_global_files(cache_dir, repo_paths, DOWNLOAD_CONNECTIONS)
    try:
        cropped = crop_to_countries(local_globals, job, missing, datasets_cfg, out_dir)
    except (OSError, RuntimeError):
        for p in local_globals:
            p.unlink(missing_ok=True)
        local_globals = download_global_files(cache_dir, repo_paths, DOWNLOAD_CONNECTIONS)
        cropped = crop_to_countries(local_globals, job, missing, datasets_cfg, out_dir)

    content_length = sum(p.stat().st_size for p in local_globals)
    origin = ",".join(f"{ISIMIP_FILES_BASE}/{p}" for p in repo_paths)
    results: dict[str, dict | None] = dict.fromkeys(countries)
    for country, path in cropped.items():
        key = f"{job.key_prefix}/{country}"
        results[country] = manifest.register(
            key,
            path,
            origin=origin,
            content_length=content_length,
            route="direct_download_crop_keep_cache",
        )
    return results


def verify_pending_checksums(manifest: Manifest) -> dict[str, int]:
    """Try to record source-file checksums for manifest entries still "pending".

    `data.isimip.org/api/v1/files/` provides an authoritative checksum per
    ISIMIP-hosted file, but only for the original global files, not for the
    country crops this project registers — a crop's own SHA-256 can never
    equal a global file's checksum, since they are different files. This
    therefore records each entry's source checksums for provenance rather
    than flipping "pending" into a pass/fail verdict. Non-blocking: any
    lookup failure (e.g. the metadata API being unreachable for hours, as
    observed in COMANDO 11) leaves the entry pending for a later call.
    """
    counts = {"checked": 0, "still_pending": 0}
    for entry in manifest.entries.values():
        if entry.get("server_checksum") != "pending":
            continue
        source_urls = [u for u in entry.get("origin", "").split(",") if u]
        source_checksums = {}
        for url in source_urls:
            repo_path = url.replace(f"{ISIMIP_FILES_BASE}/", "")
            try:
                resp = requests.get(
                    f"{ISIMIP_METADATA_BASE}/api/v1/files/",
                    params={"path": repo_path},
                    timeout=20,
                )
                resp.raise_for_status()
                payload = resp.json()
                rows = payload.get("results", payload) if isinstance(payload, dict) else payload
                if rows:
                    source_checksums[url] = rows[0].get("checksum")
            except requests.exceptions.RequestException:
                pass
        if source_checksums:
            entry["source_checksums"] = source_checksums
            entry["server_checksum"] = "checked"
            counts["checked"] += 1
        else:
            counts["still_pending"] += 1
    manifest.save()
    return counts


def inspect_cropped_file(path: Path) -> dict:
    """Read only metadata from a cropped file: variable, units, calendar, first/last
    time step and bbox. Never loads the full time series — COMANDO 12 is a metadata
    check, run separately after acquisition, not interleaved with it.
    """
    with xr.open_dataset(path) as ds:
        variable = next(iter(ds.data_vars))
        da = ds[variable]
        time_vals = ds["time"].values
        return {
            "variable": variable,
            "units": da.attrs.get("units"),
            "calendar": ds["time"].encoding.get("calendar") or ds["time"].attrs.get("calendar"),
            "first": str(time_vals[0])[:10],
            "last": str(time_vals[-1])[:10],
            "lat_range": (float(ds["lat"].min()), float(ds["lat"].max())),
            "lon_range": (float(ds["lon"].min()), float(ds["lon"].max())),
        }
