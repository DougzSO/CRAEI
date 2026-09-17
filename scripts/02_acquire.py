"""COMANDO 10: resumable acquisition of ISIMIP3b, W5E5 and auxiliary data.

Usage:
    python scripts/02_acquire.py --dry-run
    python scripts/02_acquire.py --model gfdl-esm4
"""

import argparse
from pathlib import Path

from craei.acquire import auxiliary, isimip, w5e5
from craei.config import load_datasets, load_paths
from craei.manifest import Manifest

COUNTRIES = ("BRA", "IND", "PRT")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Restrict ISIMIP3b/W5E5 jobs to one model (ISIMIP3b only).")
    parser.add_argument("--dry-run", action="store_true", help="List jobs without downloading.")
    return parser.parse_args()


def list_jobs(datasets_cfg: dict, model: str | None) -> tuple[list, list, list]:
    isimip_jobs = isimip.build_jobs(datasets_cfg)
    if model:
        isimip_jobs = [j for j in isimip_jobs if j.model == model]
    w5e5_jobs = w5e5.build_jobs(datasets_cfg)
    aux_jobs = auxiliary.build_jobs()
    return isimip_jobs, w5e5_jobs, aux_jobs


def main() -> None:
    args = parse_args()
    datasets_cfg = load_datasets()
    isimip_jobs, w5e5_jobs, aux_jobs = list_jobs(datasets_cfg, args.model)

    print(f"ISIMIP3b combinations: {len(isimip_jobs)}")
    for job in isimip_jobs:
        print(f"  {job.model} / {job.scenario} / {job.variable}")

    print(f"\nW5E5v2.0 variables: {len(w5e5_jobs)}")
    for job in w5e5_jobs:
        print(f"  {job.variable}")

    print(f"\nAuxiliary sources: {len(aux_jobs)}")
    for job in aux_jobs:
        print(f"  {job.name} ({job.kind})")

    if args.dry_run:
        print("\n--dry-run: no downloads performed.")
        return

    paths = load_paths()
    raw_dir = Path(paths["raw_dir"])
    manifest = Manifest(raw_dir / "manifest.json")

    from isimip_client.client import ISIMIPClient

    client = ISIMIPClient()

    for job in isimip_jobs:
        for country in COUNTRIES:
            isimip.run_job(client, manifest, job, country, datasets_cfg, raw_dir)

    for job in w5e5_jobs:
        for country in COUNTRIES:
            w5e5.run_job(client, manifest, job, country, datasets_cfg, raw_dir)

    auxiliary.run_hydrobasins(manifest, raw_dir)
    auxiliary.run_natural_earth(manifest, paths, raw_dir)
    auxiliary.run_ons_ena(manifest, raw_dir)
    auxiliary.run_ren_productivity(manifest, paths, raw_dir)
    auxiliary.import_existing_local_data(paths, manifest, raw_dir)


if __name__ == "__main__":
    main()
