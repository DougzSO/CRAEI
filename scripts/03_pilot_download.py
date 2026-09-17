"""COMANDO 11: pilot download of GFDL-ESM4 (4 scenarios x 3 variables x 3 countries).

Downloads the full GFDL-ESM4 set via craei.acquire.isimip, opens each file
with xarray to check variable, units, calendar, date range and bbox, then
reports actual size and extrapolates total volume for all 5 models.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import xarray as xr
from isimip_client.client import ISIMIPClient

from craei.acquire import isimip
from craei.config import load_datasets, load_paths
from craei.manifest import Manifest

MODEL = "gfdl-esm4"
COUNTRIES = ("BRA", "IND", "PRT")
EXPECTED_UNITS = {"tasmax": "K", "tasmin": "K", "pr": "kg m-2 s-1"}
POLL_ALL_TIMEOUT_S = 3 * 3600  # cutout jobs on the shared ISIMIP queue can take a long time
POLL_ROUND_INTERVAL_S = 20
CHECKPOINT_NAME = "pilot_gfdl-esm4_checkpoint.json"


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(path: Path, checkpoint: dict) -> None:
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True), encoding="utf-8")


def check_file(path: Path, job: isimip.IsimipJob, country: str, datasets_cfg: dict) -> dict:
    row = {
        "model": job.model,
        "scenario": job.scenario,
        "variable": job.variable,
        "country": country,
        "path": str(path),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "ok": False,
        "error": None,
    }
    try:
        with xr.open_dataset(path) as ds:
            if job.variable not in ds.variables:
                have = list(ds.data_vars)
                raise ValueError(f"variable '{job.variable}' not in dataset (has {have})")
            da = ds[job.variable]
            units = da.attrs.get("units")
            calendar = ds["time"].encoding.get("calendar") or ds["time"].attrs.get("calendar")
            time_vals = ds["time"].values
            start, end = str(time_vals.min())[:10], str(time_vals.max())[:10]
            lat_range = (float(ds["lat"].min()), float(ds["lat"].max()))
            lon_range = (float(ds["lon"].min()), float(ds["lon"].max()))

            need_start, need_end = isimip.required_years(job, datasets_cfg)
            years_present = {int(t[:4]) for t in time_vals.astype(str)}
            full_years = all(y in years_present for y in range(need_start, need_end + 1))

            row.update(
                units=units,
                calendar=calendar,
                start=start,
                end=end,
                lat_range=lat_range,
                lon_range=lon_range,
                full_years=full_years,
                expected_units=EXPECTED_UNITS[job.variable],
                units_ok=(units == EXPECTED_UNITS[job.variable]),
            )
            row["ok"] = full_years and row["units_ok"]
            if not row["ok"]:
                row["error"] = (
                    f"full_years={full_years} units_ok={row['units_ok']} (got units={units!r})"
                )
    except Exception as exc:  # noqa: BLE001 - report and continue with remaining files
        row["error"] = str(exc)
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--countries",
        nargs="+",
        default=list(COUNTRIES),
        choices=list(COUNTRIES),
        help="Restrict to a subset of countries (default: all 3). Smaller bboxes finish faster.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    countries = tuple(args.countries)

    datasets_cfg = load_datasets()
    paths = load_paths()
    raw_dir = Path(paths["raw_dir"])
    manifest = Manifest(raw_dir / "manifest.json")
    client = ISIMIPClient()

    jobs = [j for j in isimip.build_jobs(datasets_cfg) if j.model == MODEL]
    n_files = len(jobs) * len(countries)
    print(f"Pilot download: {len(jobs)} jobs x {len(countries)} countries = {n_files} files")

    t0 = time.time()
    checkpoint_path = raw_dir / CHECKPOINT_NAME
    checkpoint = load_checkpoint(checkpoint_path)

    # Submit everything up front so all jobs queue on the server at once
    # (sequential submit-and-block was tested and left single jobs "queued"
    # for 15+ minutes without even reaching "started" — see DECISIONS.md).
    # Every job_url is written to a checkpoint file immediately, so a second
    # run resumes polling existing jobs instead of resubmitting from zero.
    already_done = []
    pending = []
    for job in jobs:
        for country in countries:
            key = f"{job.key_prefix}/{country}"
            if manifest.is_intact(key):
                already_done.append({"job": job, "country": country, "key": key})
                checkpoint.pop(key, None)
                continue

            if key in checkpoint:
                pending.append(
                    {"job": job, "country": country, "key": key,
                     "submitted": {"status": "queued", "job_url": checkpoint[key]}}
                )
                print(f"[{time.time() - t0:7.1f}s] resuming {key}", flush=True)
                continue

            try:
                submission = isimip.submit_job(client, manifest, job, country, datasets_cfg)
            except Exception as exc:  # noqa: BLE001 - keep going, report at the end
                print(f"SUBMIT FAILED {key}: {exc}", flush=True)
                continue
            checkpoint[key] = submission["submitted"]["job_url"]
            save_checkpoint(checkpoint_path, checkpoint)
            print(f"[{time.time() - t0:7.1f}s] submitted {key}", flush=True)
            pending.append(submission)

    print(
        f"\n{len(pending)} jobs pending, {len(already_done)} already intact; polling"
        f" (checkpoint: {checkpoint_path})...",
        flush=True,
    )

    elapsed = 0
    active = ("queued", "started")
    while elapsed < POLL_ALL_TIMEOUT_S:
        still_pending = [p for p in pending if p["submitted"]["status"] in active]
        if not still_pending:
            break
        for p in still_pending:
            p["submitted"] = client.get_job(p["submitted"]["job_url"], poll=None)
        counts = {}
        for p in pending:
            counts[p["submitted"]["status"]] = counts.get(p["submitted"]["status"], 0) + 1
        print(f"[{time.time() - t0:7.1f}s] status: {counts}", flush=True)
        time.sleep(POLL_ROUND_INTERVAL_S)
        elapsed += POLL_ROUND_INTERVAL_S

    rows = []
    for entry in already_done:
        path = Path(manifest.entries[entry["key"]]["path"])
        rows.append(check_file(path, entry["job"], entry["country"], datasets_cfg))

    for submission in pending:
        job, country = submission["job"], submission["country"]
        status = submission["submitted"]["status"]
        print(f"[{time.time() - t0:7.1f}s] {submission['key']}: {status}", flush=True)
        if status != "finished":
            rows.append(
                {
                    "model": job.model, "scenario": job.scenario, "variable": job.variable,
                    "country": country, "ok": False, "error": f"job did not finish: {status}",
                }
            )
            continue
        try:
            entry = isimip.finalize_job(client, manifest, submission, raw_dir)
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            print(f"  DOWNLOAD FAILED: {exc}", flush=True)
            rows.append(
                {
                    "model": job.model, "scenario": job.scenario, "variable": job.variable,
                    "country": country, "ok": False, "error": f"download failed: {exc}",
                }
            )
            continue
        checkpoint.pop(submission["key"], None)
        save_checkpoint(checkpoint_path, checkpoint)
        row = check_file(Path(entry["path"]), job, country, datasets_cfg)
        rows.append(row)

    print("\n=== Checkup table ===")
    cols = ["scenario", "variable", "country", "ok", "size_MB", "units", "calendar", "dates"]
    widths = [12, 10, 8, 6, 10, 12, 12, 0]
    print("".join(c.ljust(w) for c, w in zip(cols, widths, strict=True)))
    total_bytes = 0
    n_ok = 0
    for r in rows:
        size_mb = (r.get("size_bytes") or 0) / 1e6
        total_bytes += r.get("size_bytes") or 0
        n_ok += 1 if r["ok"] else 0
        dates = f"{r.get('start', '?')} to {r.get('end', '?')}"
        print(
            f"{r['scenario']:<12}{r['variable']:<10}{r['country']:<8}{str(r['ok']):<6}"
            f"{size_mb:<10.2f}{str(r.get('units')):<12}{str(r.get('calendar')):<12}{dates}"
        )
        if r["error"]:
            print(f"    error: {r['error']}")

    print(f"\n{n_ok}/{len(rows)} conjuntos abertos sem erro, anos completos, unidades esperadas.")
    print(f"Total downloaded (GFDL-ESM4, 36 files): {total_bytes / 1e6:.1f} MB")
    if n_ok:
        avg = total_bytes / len(rows)
        print(f"Average file size: {avg / 1e6:.2f} MB")
        print(f"Extrapolated total for 5 models: {avg * len(rows) * 5 / 1e9:.2f} GB")

    if n_ok < len(rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
