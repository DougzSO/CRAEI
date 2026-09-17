"""W5E5v2.0 observational reference acquisition (validation baseline, Spec §1.7).

One cutout per variable per country: 3 variables x 3 countries = 9 files.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from craei.acquire.isimip import poll_job
from craei.manifest import Manifest

DATE_RANGE_RE = re.compile(r"_(\d{4})\d{4}-(\d{4})\d{4}\.nc$")


@dataclass(frozen=True)
class W5e5Job:
    variable: str

    @property
    def key_prefix(self) -> str:
        return f"w5e5v2.0/{self.variable}"


def build_jobs(datasets_cfg: dict) -> list[W5e5Job]:
    return [W5e5Job(variable=variable) for variable in datasets_cfg["variables"]]


def run_job(
    client,
    manifest: Manifest,
    job: W5e5Job,
    country: str,
    datasets_cfg: dict,
    raw_dir: Path,
) -> dict | None:
    key = f"{job.key_prefix}/{country}"
    if manifest.is_intact(key):
        return None

    result = client.datasets(climate_forcing="w5e5v2.0", climate_variable=job.variable)
    if not result:
        raise ValueError(f"no W5E5v2.0 dataset found for {job}")
    dataset = result[0]

    need = datasets_cfg["w5e5"]["years"]
    target_paths = [
        f["path"] for f in dataset["files"] if _file_overlaps(f["name"], need["start"], need["end"])
    ]
    if not target_paths:
        raise ValueError(f"no W5E5 files cover {need} for {job}")

    west, east, south, north = datasets_cfg["bboxes"][country]
    submitted = client.cutout_bbox(target_paths, west, east, south, north, poll=None)
    finished = poll_job(client, submitted)
    if not finished or not finished.get("file_url"):
        raise RuntimeError(f"cutout job did not produce a file for {job}/{country}: {finished}")

    out_dir = raw_dir / "climate" / "w5e5v2.0" / job.variable
    out_dir.mkdir(parents=True, exist_ok=True)
    file_url = finished["file_url"]
    local_path = client.download(file_url, path=str(out_dir), validate=True, extract=True)
    return manifest.register(key, local_path, origin=file_url)


def _file_overlaps(filename: str, start_year: int, end_year: int) -> bool:
    m = DATE_RANGE_RE.search(filename)
    if not m:
        return False
    file_start, file_end = int(m.group(1)), int(m.group(2))
    return file_start <= end_year and file_end >= start_year
