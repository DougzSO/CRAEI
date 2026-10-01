"""COMANDO 11: pilot download of GFDL-ESM4 (4 scenarios x 3 variables x 3 countries).

Downloads the full GFDL-ESM4 set via craei.acquire.isimip, opens each file
with xarray to check variable, units, calendar, date range and bbox, then
reports actual size and extrapolates total volume for all 5 models.

Uses direct HTTPS download of global files + local crop with xarray
(`isimip.run_job_direct`), not the ISIMIP cutout API: that API's job queue
was found congested (jobs stuck "queued" for 30+ min, confirmed server-side,
not a local network issue) while plain file downloads and metadata calls
respond normally. See COMANDO 11 in docs/DECISIONS.md.
"""

import argparse
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
    cache_dir = Path(paths["isimip_global_cache_dir"])
    manifest = Manifest(raw_dir / "manifest.json")
    client = ISIMIPClient()

    jobs = [j for j in isimip.build_jobs(datasets_cfg) if j.model == MODEL]
    n_files = len(jobs) * len(countries)
    print(f"Pilot download: {len(jobs)} jobs x {len(countries)} countries = {n_files} files")

    t0 = time.time()
    rows = []
    for job in jobs:
        for country in countries:
            key = f"{job.key_prefix}/{country}"
            if manifest.is_intact(key):
                path = Path(manifest.entries[key]["path"])
                print(f"[{time.time() - t0:7.1f}s] {key}: already intact", flush=True)
                rows.append(check_file(path, job, country, datasets_cfg))
                continue
            try:
                entry = isimip.run_job_direct(
                    client, manifest, job, country, datasets_cfg, cache_dir, raw_dir
                )
            except Exception as exc:  # noqa: BLE001 - keep going, report at the end
                print(f"[{time.time() - t0:7.1f}s] {key}: FAILED ({exc})", flush=True)
                rows.append(
                    {
                        "model": job.model, "scenario": job.scenario, "variable": job.variable,
                        "country": country, "ok": False, "error": str(exc),
                    }
                )
                continue
            print(f"[{time.time() - t0:7.1f}s] {key}: done", flush=True)
            rows.append(check_file(Path(entry["path"]), job, country, datasets_cfg))

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
