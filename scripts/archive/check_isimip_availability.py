"""COMANDO 08: confirm ISIMIP3b and W5E5 availability before implementing download.

Queries the ISIMIP data API for the 60 combinations (5 models x 4 scenarios x
3 variables) plus W5E5, checks year coverage against config/datasets.yaml,
and runs one test cutout to record size and calendar attribute.
"""

import re
import time
from pathlib import Path

from isimip_client.client import ISIMIPClient

from craei.config import load_datasets, load_paths

# isimip-client's own poll=True recurses once per poll instead of looping,
# which hits Python's recursion limit on jobs that take >~1000 s. Poll
# manually in a loop instead.
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 900


def poll_job(client: ISIMIPClient, job: dict) -> dict:
    elapsed = 0
    while job and job["status"] in ("queued", "started") and elapsed < POLL_TIMEOUT_S:
        time.sleep(POLL_INTERVAL_S)
        elapsed += POLL_INTERVAL_S
        job = client.get_job(job["job_url"], poll=None)
    return job

# Two naming conventions seen in ISIMIP filelists: "_YYYY_YYYY.nc" (ISIMIP3b
# climate input) and "_YYYYMMDD-YYYYMMDD.nc" (W5E5 observational reference).
YEAR_RANGE_RE = re.compile(r"_(\d{4})_(\d{4})\.nc$")
DATE_RANGE_RE = re.compile(r"_(\d{4})\d{4}-(\d{4})\d{4}\.nc$")


def file_year_span(dataset: dict) -> tuple[int, int] | None:
    years = []
    for f in dataset.get("files", []):
        m = YEAR_RANGE_RE.search(f["name"]) or DATE_RANGE_RE.search(f["name"])
        if m:
            years.append((int(m.group(1)), int(m.group(2))))
    if not years:
        return None
    return min(y[0] for y in years), max(y[1] for y in years)


def required_span(scenario: str, datasets_cfg: dict) -> tuple[int, int]:
    if scenario == "historical":
        d = datasets_cfg["download_years"]["historical"]
    else:
        d = datasets_cfg["download_years"]["future"]
    return d["start"], d["end"]


def main() -> None:
    datasets_cfg = load_datasets()
    paths = load_paths()
    client = ISIMIPClient()

    models = datasets_cfg["models"]
    scenarios = datasets_cfg["scenarios"]
    variables = datasets_cfg["variables"]

    rows = []
    missing = []
    for model in models:
        for scenario in scenarios:
            for variable in variables:
                result = client.datasets(
                    simulation_round="ISIMIP3b",
                    climate_scenario=scenario,
                    climate_forcing=model,
                    climate_variable=variable,
                    bias_adjustment="w5e5",
                )
                need_start, need_end = required_span(scenario, datasets_cfg)
                if not result:
                    rows.append((model, scenario, variable, "NO DATASET", None, None))
                    missing.append((model, scenario, variable, "no dataset returned"))
                    continue
                ds = result[0]
                span = file_year_span(ds)
                if span is None:
                    rows.append((model, scenario, variable, "NO FILES", None, None))
                    missing.append((model, scenario, variable, "dataset has no per-year files"))
                    continue
                covered = span[0] <= need_start and span[1] >= need_end
                status = "OK" if covered else "PARTIAL"
                rows.append((model, scenario, variable, status, span, (need_start, need_end)))
                if not covered:
                    reason = f"file span {span} vs needed {(need_start, need_end)}"
                    missing.append((model, scenario, variable, reason))

    print(f"\n{'model':<16}{'scenario':<12}{'variable':<10}{'status':<10}{'file span':<16}needed")
    for model, scenario, variable, status, span, needed in rows:
        print(f"{model:<16}{scenario:<12}{variable:<10}{status:<10}{str(span):<16}{needed}")

    print(f"\n{len(rows) - len(missing)}/{len(rows)} combinations cover required years.")
    if missing:
        print("\nMissing/partial (register as O in DECISIONS.md):")
        for m in missing:
            print(f"  {m}")

    # W5E5v2.0 (observational reference used for bias adjustment / validation baseline).
    print("\n=== W5E5v2.0 ===")
    w5e5_need = datasets_cfg["w5e5"]["years"]
    for variable in variables:
        result = client.datasets(climate_forcing="w5e5v2.0", climate_variable=variable)
        if not result:
            print(f"  {variable}: NO DATASET FOUND")
            continue
        span = file_year_span(result[0])
        covered = span and span[0] <= w5e5_need["start"] and span[1] >= w5e5_need["end"]
        name = result[0]["name"]
        print(f"  {variable}: dataset={name} span={span} needed={w5e5_need} covered={covered}")

    # Single test cutout: 1 model, 1 variable, 1 decade, Portugal.
    print("\n=== Test cutout (gfdl-esm4, tasmax, 2000-2009, Portugal) ===")
    result = client.datasets(
        simulation_round="ISIMIP3b",
        climate_scenario="historical",
        climate_forcing="gfdl-esm4",
        climate_variable="tasmax",
        bias_adjustment="w5e5",
    )
    ds = result[0]
    year_re = re.compile(r"_(\d{4})_(\d{4})\.nc$")
    decade_files = []
    for f in ds["files"]:
        m = year_re.search(f["name"])
        if m and 2000 <= int(m.group(1)) <= 2009:
            decade_files.append(f)
    target_paths = [f["path"] for f in decade_files]
    print(f"Test decade files: {[f['name'] for f in decade_files]}")
    bbox = datasets_cfg["bboxes"]["PRT"]
    west, east, south, north = bbox
    job = client.cutout_bbox(target_paths, west, east, south, north, poll=None)
    print(f"job submitted: status={job.get('status') if job else None}")
    response = poll_job(client, job)
    print(f"cutout response: {response}")

    out_dir = Path(paths["interim_dir"]) / "isimip_test_cutout"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_url = response.get("file_url") if response else None
    if file_url:
        local_path = client.download(file_url, path=str(out_dir), validate=True, extract=True)
        print(f"Downloaded test cutout to: {local_path}")
    else:
        print(f"No file_url in response (status={response.get('status') if response else None}); "
              "job may still be processing server-side.")


if __name__ == "__main__":
    main()
