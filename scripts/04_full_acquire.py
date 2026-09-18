"""COMANDO 12: full ISIMIP3b acquisition (5 models x 4 scenarios x 3 variables x 3 countries).

Downloads each job's global file(s) once, crops all 3 study countries in the
same pass, registers each crop in the manifest, and deletes the global
file(s) — see `craei.acquire.isimip.acquire_job_all_countries` and COMANDO 11
in docs/DECISIONS.md for why (chunk layout rules out remote cropping; keeping
global files around is unneeded once every country is cropped in one pass).

Resumable: a job whose 3 country crops are already registered and intact is
skipped. Progress prints every `PROGRESS_REPORT_INTERVAL_S` (5 min) via the
shared tracker in `craei.acquire.isimip`; per-job failures are caught and
reported at the end, not fatal to the run.
"""

import time
from pathlib import Path

from isimip_client.client import ISIMIPClient

from craei.acquire import isimip
from craei.config import load_datasets, load_paths
from craei.manifest import Manifest


def main() -> None:
    datasets_cfg = load_datasets()
    paths = load_paths()
    raw_dir = Path(paths["raw_dir"])
    cache_dir = Path(paths["isimip_global_cache_dir"])
    manifest = Manifest(raw_dir / "manifest.json")
    client = ISIMIPClient()

    jobs = isimip.build_jobs(datasets_cfg)
    print(f"Full acquisition: {len(jobs)} jobs x 3 countries = {len(jobs) * 3} files", flush=True)

    t0 = time.time()
    ok, failed = 0, []
    for i, job in enumerate(jobs, 1):
        already = all(
            manifest.is_intact(f"{job.key_prefix}/{c}") for c in isimip.STUDY_COUNTRIES
        )
        if already:
            ok += 1
            continue
        tag = f"[{time.time() - t0:7.0f}s] ({i}/{len(jobs)})"
        print(f"{tag} starting {job.key_prefix}", flush=True)
        try:
            isimip.acquire_job_all_countries(
                client, manifest, job, datasets_cfg, cache_dir, raw_dir
            )
            ok += 1
            print(f"{tag} done {job.key_prefix}", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            failed.append((job.key_prefix, str(exc)))
            print(f"{tag} FAILED {job.key_prefix}: {exc}", flush=True)

    elapsed = time.time() - t0
    print(f"\n{ok}/{len(jobs)} jobs complete (3 files each) in {elapsed / 3600:.1f}h", flush=True)
    if failed:
        print(f"{len(failed)} jobs failed:", flush=True)
        for key, err in failed:
            print(f"  {key}: {err}", flush=True)


if __name__ == "__main__":
    main()
