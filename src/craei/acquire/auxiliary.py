"""Auxiliary and validation data acquisition (Spec §1.7, §5; COMANDO 09).

Four sources, matching the COMANDO 09 audit in `docs/DECISIONS.md`:

- HydroBASINS level 6 (download): one zip per country's continent region.
- Natural Earth coastline/rivers (import): already present as local files
  (see `config/paths.local.yaml`); copied into `raw_dir` and registered.
- ONS ENA diario por subsistema (download): one CSV per year, 2000-present.
- REN hydroelectric productivity index (import): no confirmed API endpoint
  (COMANDO 09 finding); expects a manually exported file at
  `paths.local.yaml: ren_file`. Skipped with a warning if that key is absent.

`import_existing_local_data` separately copies the GEM/GADM/EM-DAT/Aqueduct
files already audited in COMANDO 07 into `raw_dir`, registering each in the
manifest.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path

import requests

from craei.manifest import Manifest

HYDROBASINS_REGIONS = {"BRA": "sa", "IND": "as", "PRT": "eu"}
HYDROBASINS_URL = "https://data.hydrosheds.org/file/hydrobasins/standard/hybas_{region}_lev06_v1c.zip"
ONS_ENA_PACKAGE_URL = "https://dados.ons.org.br/api/3/action/package_show?id=ena-diario-por-subsistema"


@dataclass(frozen=True)
class AuxJob:
    name: str
    kind: str  # "download" or "import"


def build_jobs() -> list[AuxJob]:
    return [
        AuxJob(name="hydrobasins", kind="download"),
        AuxJob(name="natural_earth", kind="import"),
        AuxJob(name="ons_ena", kind="download"),
        AuxJob(name="ren_productivity", kind="import"),
    ]


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def run_hydrobasins(manifest: Manifest, raw_dir: Path) -> list[dict]:
    registered = []
    for iso, region in HYDROBASINS_REGIONS.items():
        key = f"hydrobasins/{iso}"
        if manifest.is_intact(key):
            continue
        url = HYDROBASINS_URL.format(region=region)
        dest = raw_dir / "boundaries" / "hydrobasins" / f"hybas_{region}_lev06_v1c.zip"
        _download(url, dest)
        registered.append(manifest.register(key, dest, origin=url))
    return registered


def run_natural_earth(manifest: Manifest, local_paths: dict, raw_dir: Path) -> list[dict]:
    registered = []
    sources = (("coastline", "natural_earth_coastline"), ("rivers", "natural_earth_rivers"))
    for name, local_key in sources:
        source = local_paths.get(local_key)
        if not source:
            continue
        source = Path(source)
        key = f"natural_earth/{name}"
        if manifest.is_intact(key):
            continue
        dest = raw_dir / "boundaries" / source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Shapefiles need their sidecar files (.dbf/.shx/.prj/...) alongside
        # the .shp to be readable; copy every file sharing the same stem.
        for sidecar in source.parent.glob(f"{source.stem}.*"):
            shutil.copy2(sidecar, dest.parent / sidecar.name)
        registered.append(manifest.register(key, dest, origin=str(source)))
    return registered


def run_ons_ena(manifest: Manifest, raw_dir: Path) -> list[dict]:
    response = requests.get(ONS_ENA_PACKAGE_URL, timeout=30)
    response.raise_for_status()
    resources = response.json()["result"]["resources"]

    registered = []
    for resource in resources:
        if resource.get("format") != "CSV":
            continue
        name = resource["name"]  # e.g. "ENA_Diario_por_Subsistema-2020"
        key = f"ons_ena/{name}"
        if manifest.is_intact(key):
            continue
        url = resource["url"]
        dest = raw_dir / "validation" / "ons_ena" / f"{name}.csv"
        _download(url, dest)
        registered.append(manifest.register(key, dest, origin=url))
    return registered


def run_ren_productivity(manifest: Manifest, local_paths: dict, raw_dir: Path) -> dict | None:
    source = local_paths.get("ren_file")
    if not source:
        return None
    source = Path(source)
    key = "ren_productivity"
    if manifest.is_intact(key):
        return None
    dest = raw_dir / "validation" / source.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return manifest.register(key, dest, origin=str(source))


_LOCAL_DATASET_KEYS = ("gem_file", "aqueduct_dir", "emdat_dir", "gadm_dir")


def import_existing_local_data(local_paths: dict, manifest: Manifest, raw_dir: Path) -> list[dict]:
    """Copy the GEM/Aqueduct/EM-DAT/GADM files audited in COMANDO 07 into `raw_dir`."""
    registered = []
    for local_key in _LOCAL_DATASET_KEYS:
        source = local_paths.get(local_key)
        if not source:
            continue
        source = Path(source)
        if source.is_file():
            files = [source]
        else:
            files = sorted(p for p in source.rglob("*") if p.is_file())
        for f in files:
            key = f"local/{local_key}/{f.name}"
            if manifest.is_intact(key):
                continue
            dest = raw_dir / local_key.removesuffix("_file").removesuffix("_dir") / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            registered.append(manifest.register(key, dest, origin=str(f)))
    return registered
