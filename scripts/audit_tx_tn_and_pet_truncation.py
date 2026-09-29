"""COMANDO 16 follow-up: audit the TX<TN guard and PET-truncation detail.

Two things the COMANDO 16 run reported only in aggregate (min/max, totals) get
inspected here at finer grain, per the author's request:

1. TX == TN (as opposed to TX < TN, already reported as 0 everywhere): counted
   the same way, on the same pre-treatment merged tasmax/tasmin frame
   `scripts/07_water_balance.py`'s `build_daily` uses before calling
   `pet.daily_pet`. If any exist, checks what Hargreaves actually produces on
   those days and whether that is distinguishable from a genuinely negative,
   truncated PET day. ISIMIP3b's tasmax/tasmin are stored (and loaded here) as
   float32, not float64: exact `==` is not numerically implausible at that
   precision, so a second, tolerance-based near-equal count (|TX-TN| <= 1e-6,
   compared in float64) is also computed, per COMANDO 16 follow-up Action 1.
2. For the 50,221 truncated-PET cell-days (all in India, per COMANDO 16):
   which distinct cells, their latitude range, and whether those cells feed
   any hydro catchment in `catchment_weights.parquet`.

Per CLAUDE.md rule 10, this diagnostic logic lives here, not as a flag on
`craei.hazards.pet` or `craei.hazards.loading`'s production functions.
Prints only; does not change any pipeline output.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd

NEAR_EQUAL_TOLERANCE = 1e-6  # Action 1, COMANDO 16 follow-up: TX/TN are float32 on disk

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_datasets, load_paths
from craei.hazards import pet
from craei.hazards.loading import cells_with_catchments_by_country, download_years_span, tasmax_daily, tasmin_daily


def main() -> None:
    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])
    climate_dir = raw_dir / "climate" / "isimip3b"

    cells_by_country = cells_with_catchments_by_country(processed_dir)
    weights = pd.read_parquet(processed_dir / "catchment_weights.parquet")
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country"])

    truncated_cells = []  # accumulate distinct (country, cell_lat, cell_lon) with >=1 truncated day
    equal_summary = []
    tmean_stats = []  # per-day T_mean on truncated days only (small: bounded by the 50,221 total)

    for country in STUDY_COUNTRIES:
        cells = cells_by_country[country]
        for model in datasets_cfg["models"]:
            for scenario in datasets_cfg["scenarios"]:
                start_year, end_year = download_years_span(scenario, datasets_cfg)
                tasmax_path = climate_dir / model / scenario / "tasmax" / f"{model}_{scenario}_tasmax_{country}.nc"
                tasmin_path = climate_dir / model / scenario / "tasmin" / f"{model}_{scenario}_tasmin_{country}.nc"

                tasmax = tasmax_daily(tasmax_path, cells, start_year, end_year)
                tasmin = tasmin_daily(tasmin_path, cells, start_year, end_year)
                # tasmax_daily/tasmin_daily select the same cells and time span from
                # matching grids, so rows are already aligned -- a direct column
                # assignment avoids a hash-join's indexer arrays, which repeatedly
                # hit MemoryError on this machine for Brazil's ~22.5M-row frames
                # even though scripts/07_water_balance.py's equivalent merge (same
                # data) succeeded earlier in this session (transient system memory,
                # not a logic difference). Verified aligned before assigning.
                assert len(tasmax) == len(tasmin)
                assert (tasmax["date"].to_numpy() == tasmin["date"].to_numpy()).all()
                assert (tasmax["cell_lat"].to_numpy() == tasmin["cell_lat"].to_numpy()).all()
                assert (tasmax["cell_lon"].to_numpy() == tasmin["cell_lon"].to_numpy()).all()
                temps = tasmax
                temps["tasmin_c"] = tasmin["tasmin_c"].to_numpy()
                del tasmax, tasmin
                gc.collect()

                # Same operator/point in the flow as scripts/07_water_balance.py's
                # build_daily: on the merged, pre-treatment frame, before daily_pet.
                below = temps["tasmax_c"] < temps["tasmin_c"]
                equal = temps["tasmax_c"] == temps["tasmin_c"]
                diff_f64 = np.abs(
                    temps["tasmax_c"].to_numpy(dtype=np.float64)
                    - temps["tasmin_c"].to_numpy(dtype=np.float64)
                )
                near_equal = diff_f64 <= NEAR_EQUAL_TOLERANCE
                n_days, n_below, n_equal = len(temps), int(below.sum()), int(equal.sum())
                n_near_equal = int(near_equal.sum())
                equal_summary.append(
                    {"country": country, "model": model, "scenario": scenario,
                     "n_days": n_days, "n_below": n_below, "n_equal": n_equal,
                     "n_near_equal_1e-6": n_near_equal}
                )

                if n_equal > 0:
                    eq_rows = temps[equal]
                    eq_pet = pet.daily_pet(eq_rows)
                    all_zero = (eq_pet["pet_mm"] == 0.0).all()
                    any_flagged_truncated = eq_pet["pet_truncated"].any()
                    print(
                        f"{country}/{model}/{scenario}: {n_equal} TX==TN days -> "
                        f"Hargreaves pet_mm all zero: {all_zero}; "
                        f"any flagged pet_truncated (i.e. raw PET < 0): {any_flagged_truncated}"
                    )

                # Full-frame PET, to find which cells have >=1 truncated day.
                pet_df = pet.daily_pet(temps)
                del temps
                gc.collect()
                trunc_rows = pet_df.loc[pet_df["pet_truncated"], ["cell_lat", "cell_lon", "tasmax_c", "tasmin_c"]]
                trunc_cells = trunc_rows[["cell_lat", "cell_lon"]].drop_duplicates()
                if len(trunc_cells):
                    trunc_cells = trunc_cells.copy()
                    trunc_cells["country"] = country
                    truncated_cells.append(trunc_cells)
                if len(trunc_rows):
                    tmean_on_trunc_days = (trunc_rows["tasmax_c"] + trunc_rows["tasmin_c"]) / 2.0
                    per_cell_tmean = pd.DataFrame(
                        {"cell_lat": trunc_rows["cell_lat"], "cell_lon": trunc_rows["cell_lon"], "tmean_c": tmean_on_trunc_days}
                    )
                    tmean_stats.append(per_cell_tmean)
                del pet_df
                gc.collect()

        print(f"{country}: done (all models/scenarios)")

    print("\n=== Action 1: TX<TN, TX==TN and near-equal (tol=1e-6), per country/model/scenario ===")
    summary_df = pd.DataFrame(equal_summary)
    print(summary_df.to_string(index=False))
    print(f"\nTotal TX<TN across all combinations: {summary_df['n_below'].sum()}")
    print(f"Total TX==TN across all combinations: {summary_df['n_equal'].sum()}")
    print(f"Total |TX-TN|<=1e-6 across all combinations: {summary_df['n_near_equal_1e-6'].sum()}")

    print("\n=== Action 2: distinct cells with >=1 truncated-PET day ===")
    if not truncated_cells:
        print("no truncated-PET cells found")
        return

    all_trunc = pd.concat(truncated_cells, ignore_index=True).drop_duplicates()
    print(f"distinct (country, cell) with truncated PET: {len(all_trunc)}")
    print(all_trunc.groupby("country").size())

    lat_bins = pd.cut(all_trunc["cell_lat"], bins=range(0, 40, 5))
    print("\nlatitude distribution of truncated cells (5-degree bins):")
    print(all_trunc.groupby(lat_bins, observed=True).size())

    catchment_hit = weights.merge(plants, on="plant_uid")  # plant_uid, cell_lat, cell_lon, weight, country
    catchment_hit = catchment_hit.merge(
        all_trunc, on=["cell_lat", "cell_lon"], suffixes=("", "_trunc_cell")
    )
    mismatch = int((catchment_hit["country"] != catchment_hit["country_trunc_cell"]).sum())
    n_plants = catchment_hit["plant_uid"].nunique()
    print(f"\ntruncated cells that are also catchment-weight cells: {len(catchment_hit)} rows")
    print(f"distinct hydro plants whose catchment includes a truncated-PET cell: {n_plants}")
    print(f"plant-country vs. truncated-cell-country mismatches: {mismatch} (expect 0)")
    if n_plants:
        print(catchment_hit.groupby("country")["plant_uid"].nunique())

    print("\n=== Action 2 (2026-09-29 follow-up): T_mean on truncated days, per cell ===")
    all_tmean = pd.concat(tmean_stats, ignore_index=True)
    per_cell = all_tmean.groupby(["cell_lat", "cell_lon"], as_index=False).agg(
        tmean_min=("tmean_c", "min"), tmean_mean=("tmean_c", "mean"), tmean_max=("tmean_c", "max"),
        n_days=("tmean_c", "size"),
    )
    print(f"cells summarized: {len(per_cell)} (expect 51)")
    print(f"per-cell mean T_mean: min={per_cell['tmean_mean'].min():.2f}, "
          f"median={per_cell['tmean_mean'].median():.2f}, max={per_cell['tmean_mean'].max():.2f} degC")
    above_threshold = per_cell[per_cell["tmean_mean"] >= -17.8]
    print(f"cells whose mean T_mean on truncated days is NOT below -17.8 degC: {len(above_threshold)}")
    print(f"overall max single-day T_mean among all truncated days: {all_tmean['tmean_c'].max():.2f} degC "
          f"(every truncated day is < -17.8 degC by construction of the Hargreaves formula: "
          f"PET_raw < 0 requires (T_mean+17.8) < 0 whenever the diurnal range > 0)")
    print(per_cell.sort_values("tmean_mean", ascending=False).head(5).to_string(index=False))


if __name__ == "__main__":
    main()
