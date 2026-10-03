"""TH1: relative (baseline-percentile) heat threshold, robustness check (D91).

Per cell and GCM: threshold = 95th percentile of daily tasmax pooled over
every day of the baseline (1985-2014, Brazil only, cells used by some plant;
STUDY_COUNTRIES/unique_cells_by_country, no day-of-year window). The same
fixed threshold counts days at or above it in the baseline and in 2041-2070
of SSP126/370/585 of the same GCM. Not an operating limit; a check that the
H1 results do not depend on the absolute 35 degC cut.

Aborts before writing if: (a) the baseline fraction of days at/above the
threshold is outside [4.5%, 5.5%] in any cell/GCM (nominal 5%, since the
threshold IS the 95th percentile of that same baseline, by construction);
(b) replacing the threshold with a constant 35 degC, the same counting
function (heat_relative.annual_days_at_or_above) does not reproduce the
stored tx35 index (indices_daily.parquet) for every matched cell, GCM,
scenario, period and year, max |diff| <= 1e-6 days/yr.

Historical tasmax is read once per GCM and reused for both the baseline
counts and the 95th-percentile fit (no second read of the same file).
"""

import gc
import sys
from pathlib import Path

import pandas as pd

from craei.config import load_datasets, load_paths
from craei.hazards import heat_relative as hr
from craei.hazards.loading import period_years, tasmax_daily, unique_cells_by_country

COUNTRY = "BRA"
PERCENTILE = 95.0  # D91 definition, fixed; not a config param (robustness check, not headline)
GROUP = ["cell_lat", "cell_lon", "model"]
FRAC_LOW, FRAC_HIGH = 0.045, 0.055
GAP_TOL = 1e-6


def main():
    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    proc = Path(paths["processed_dir"])
    tab = Path(paths["outputs_tables_dir"])
    climate_dir = raw_dir / "climate" / "isimip3b"

    cells = unique_cells_by_country(proc)[COUNTRY]
    print(f"{COUNTRY}: {len(cells)} unique cells")

    count_frames, check35_frames, thr_frames, frac_frames = [], [], [], []
    hist_start, hist_end = period_years("historical", datasets_cfg)

    for model in datasets_cfg["models"]:
        hist_path = climate_dir / model / "historical" / "tasmax" / f"{model}_historical_tasmax_{COUNTRY}.nc"
        baseline = tasmax_daily(hist_path, cells, hist_start, hist_end).assign(model=model)

        thr = hr.baseline_percentile_threshold(baseline, PERCENTILE, GROUP)
        frac = hr.baseline_exceedance_fraction(baseline, thr, GROUP)
        thr_frames.append(thr.assign(percentile=PERCENTILE))
        frac_frames.append(frac)
        thr35 = thr[GROUP].assign(threshold_c=35.0)

        for scenario in datasets_cfg["scenarios"]:
            period = "baseline" if scenario == "historical" else "future"
            if scenario == "historical":
                daily = baseline
            else:
                start, end = period_years(scenario, datasets_cfg)
                path = climate_dir / model / scenario / "tasmax" / f"{model}_{scenario}_tasmax_{COUNTRY}.nc"
                daily = tasmax_daily(path, cells, start, end).assign(model=model)

            labeled = daily.assign(scenario=scenario, period=period)
            counts = hr.annual_days_at_or_above(labeled, thr, GROUP)
            counts["percentile"] = PERCENTILE
            count_frames.append(counts)

            counts35 = hr.annual_days_at_or_above(labeled, thr35, GROUP)
            check35_frames.append(counts35.rename(columns={"value": "value_fixed35"}))

            if scenario != "historical":
                del daily
            print(f"{model}/{scenario}: done")

        del baseline
        gc.collect()

    th1 = pd.concat(count_frames, ignore_index=True)
    check35 = pd.concat(check35_frames, ignore_index=True)
    fracs = pd.concat(frac_frames, ignore_index=True)
    thresholds = pd.concat(thr_frames, ignore_index=True)

    print(f"\ncheck (a) baseline exceedance fraction: min {fracs['fraction'].min():.4f}, "
          f"max {fracs['fraction'].max():.4f}, target [{FRAC_LOW}, {FRAC_HIGH}]")
    ok_a = bool(fracs["fraction"].between(FRAC_LOW, FRAC_HIGH).all())
    print(f"check (a): {'PASS' if ok_a else 'FAIL'}")

    tx35 = pd.read_parquet(proc / "indices_daily.parquet", filters=[("index", "==", "tx35")])
    tx35 = tx35.merge(cells, on=["cell_lat", "cell_lon"], how="inner")
    keys = ["cell_lat", "cell_lon", "model", "scenario", "period", "year"]
    m = check35.merge(tx35[keys + ["value"]], on=keys, how="inner", suffixes=("", "_tx35"))
    n_mine, n_matched = len(check35), len(m)
    worst_b = float((m["value_fixed35"] - m["value"]).abs().max()) if n_matched else float("nan")
    print(f"\ncheck (b) fixed-35 reproduction of tx35: matched {n_matched} of {n_mine} rows, "
          f"max|diff| {worst_b:.2e} days/yr")
    ok_b = n_matched == n_mine and worst_b <= GAP_TOL
    print(f"check (b): {'PASS' if ok_b else 'FAIL'}")

    if not (ok_a and ok_b):
        print("\nCHECK FAILED: TH1 not produced (D91)")
        sys.exit(1)
    print("\nchecks (a)-(b): PASS")

    th1.to_csv(tab / "th1_relative_threshold.csv", index=False)
    thresholds.to_csv(tab / "th1_thresholds.csv", index=False)
    fracs.to_csv(tab / "th1_baseline_exceedance.csv", index=False)
    print(f"\nwritten: th1_relative_threshold.csv ({len(th1)} rows), "
          f"th1_thresholds.csv ({len(thresholds)} rows), "
          f"th1_baseline_exceedance.csv ({len(fracs)} rows)")

    pd.set_option("display.width", 200)
    summary = th1.groupby(["model", "scenario", "period"])["value"].mean().round(2)
    print("\nTH1 mean days/yr over BRA plant cells, per model/scenario/period:")
    print(summary.to_string())
    print("\nthreshold_c (95th pct of baseline tasmax) by model, over cells (min/median/max):")
    print(thresholds.groupby("model")["threshold_c"].agg(["min", "median", "max"]).round(2).to_string())


if __name__ == "__main__":
    main()