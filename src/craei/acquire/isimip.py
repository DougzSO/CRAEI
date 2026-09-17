"""ISIMIP3b climate input acquisition: cutout jobs per model/scenario/variable.

Each job cuts the 3 study-area bounding boxes (Brazil, India, Portugal) out of
the global bias-adjusted files, so 60 combinations (from `datasets.yaml`)
produce 180 registered files.

The ISIMIP data API's own `poll=True` recurses once per poll and overflows
Python's recursion limit on slow jobs (see COMANDO 08 finding in
`docs/DECISIONS.md`); `poll_job` below polls in a loop instead.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from craei.manifest import Manifest

POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 900


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
    import re

    m = re.search(r"_(\d{4})_(\d{4})\.nc$", filename)
    if not m:
        return False
    file_start, file_end = int(m.group(1)), int(m.group(2))
    return file_start <= end_year and file_end >= start_year
