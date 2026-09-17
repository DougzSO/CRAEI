"""ISIMIP3b climate input acquisition: cutout jobs per model/scenario/variable.

Each job cuts the 3 study-area bounding boxes (Brazil, India, Portugal) out of
the global bias-adjusted files, so 60 combinations (from `datasets.yaml`)
produce 180 registered files.

The ISIMIP data API's own `poll=True` recurses once per poll and overflows
Python's recursion limit on slow jobs (see COMANDO 08 finding in
`docs/DECISIONS.md`); `poll_job` below polls in a loop instead.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import requests
import xarray as xr

from craei.manifest import Manifest

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 900

ISIMIP_FILES_BASE = "https://files.isimip.org"
DOWNLOAD_CONNECTIONS = 8


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


def download_global_file(
    cache_dir: Path, repo_path: str, n_connections: int = DOWNLOAD_CONNECTIONS
) -> Path:
    """Download one whole global ISIMIP file into a permanent, reusable cache.

    Workaround for the cutout API's job queue being congested (jobs stuck
    "queued" for 30+ min with zero progress — see COMANDO 11 in
    docs/DECISIONS.md). Global files are large (~1-2 GB) but shared by every
    study country, so they are cached outside the project's own gitignored
    data folder and never re-downloaded once present.

    Splits the download across `n_connections` parallel HTTP Range requests:
    the server was measured to throttle per connection (~300-450 KB/s each)
    rather than per client, so N connections on one file gave ~2.7 MB/s
    aggregate against ~1 MB/s for a single stream (see DECISIONS.md).
    """
    local_path = cache_dir / repo_path
    if local_path.exists():
        return local_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = local_path.with_name(local_path.name + ".part")
    url = f"{ISIMIP_FILES_BASE}/{repo_path}"

    t0 = time.time()
    size, supports_ranges = _probe_file(url)
    if size and supports_ranges and n_connections > 1:
        _download_parallel_ranges(url, tmp_path, size, n_connections)
    else:
        _download_single_stream(url, tmp_path)

    tmp_path.rename(local_path)
    elapsed = time.time() - t0
    mb = local_path.stat().st_size / 1e6
    rate = mb / max(elapsed, 1)
    msg = f"  [cache] {local_path.name}: {mb:.0f} MB in {elapsed:.0f}s ({rate:.2f} MB/s)"
    print(msg, flush=True)
    return local_path


def download_global_files(
    cache_dir: Path, repo_paths: list[str], total_connections: int = DOWNLOAD_CONNECTIONS
) -> list[Path]:
    """Download several global files for one job concurrently, sharing `total_connections`.

    A job needing multiple decadal files (e.g. the historical period spans 4
    of them) was previously downloaded one file at a time, each internally
    parallel — leaving most of the connection budget idle while later files
    waited their turn. Splitting the budget across files instead keeps all
    connections busy for the whole job.
    """
    already_cached = [p for p in repo_paths if (cache_dir / p).exists()]
    to_fetch = [p for p in repo_paths if p not in already_cached]
    if not to_fetch:
        return [cache_dir / p for p in repo_paths]

    per_file_connections = max(1, total_connections // len(to_fetch))
    with ThreadPoolExecutor(max_workers=len(to_fetch)) as pool:
        fetched = list(
            pool.map(
                lambda p: download_global_file(cache_dir, p, per_file_connections), to_fetch
            )
        )
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


def _download_single_stream(url: str, tmp_path: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


RANGE_RETRIES = 5


def _download_parallel_ranges(url: str, tmp_path: Path, size: int, n_connections: int) -> None:
    with open(tmp_path, "wb") as f:
        f.truncate(size)

    boundaries = [size * i // n_connections for i in range(n_connections + 1)]
    byte_ranges = [(boundaries[i], boundaries[i + 1] - 1) for i in range(n_connections)]

    with ThreadPoolExecutor(max_workers=n_connections) as pool:
        for _ in pool.map(lambda r: _fetch_range(url, tmp_path, r[0], r[1]), byte_ranges):
            pass


def _fetch_range(url: str, tmp_path: Path, start: int, end: int) -> None:
    """Fetch bytes [start, end] and write them into `tmp_path`, retrying on drops.

    The connection was observed to (a) drop mid-transfer on large ranges
    (~150 MB chunks), each retry resuming from the last byte actually
    written instead of restarting the whole range, and (b) close cleanly
    with fewer bytes than requested without raising — checked explicitly
    below, since silently short ranges corrupt the file's HDF5 chunks
    without any exception (see COMANDO 11 in docs/DECISIONS.md).
    """
    pos = start
    expected = end - start + 1
    for attempt in range(RANGE_RETRIES):
        try:
            with requests.get(
                url, headers={"Range": f"bytes={pos}-{end}"}, stream=True, timeout=120
            ) as resp:
                resp.raise_for_status()
                with open(tmp_path, "r+b") as f:
                    f.seek(pos)
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                        pos += len(chunk)
            if pos - start == expected:
                return
            raise requests.exceptions.ChunkedEncodingError(
                f"range {start}-{end} ended short: got {pos - start}/{expected} bytes"
            )
        except requests.exceptions.RequestException:
            if attempt == RANGE_RETRIES - 1:
                raise
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
