"""COMANDO 15 follow-up: measure the wet-day sample size behind H4's P95 (O06).

The C15 exceedance-frequency check (4.99-5.25%, inside [4.5%, 5.5%]) confirms
arithmetic -- a pooled ratio against its own percentile lands near 5% almost
by definition. It says nothing about whether each cell/model's baseline
(1985-2014) has enough wet days for that P95 to be a stable estimate. This
script measures that directly: wet-day counts per country/model, and which
plants depend on the driest cells (< 300 wet days in 30 years). Prints only;
does not decide an exclusion or write a limitation (see O06 in DECISIONS.md).

Runs on `unique_cells_by_country` -- the same 1,871 plant-nearest-cell set
COMANDO 15 used (967 BRA + 862 IND + 42 PRT), not COMANDO 16's larger
3,202-cell union with hydro catchments (`cells_with_catchments_by_country`):
H4 (this audit's subject) is a per-plant local index, evaluated at each
plant's own nearest cell only -- a hydro plant's upstream catchment cells
play no part in it (see PROGRESS.json C15's Action-4 note, COMANDO 16
follow-up).
"""

from pathlib import Path

import pandas as pd

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_datasets, load_paths
from craei.hazards import precip
from craei.hazards.loading import period_years, pr_daily, unique_cells_by_country

CUTOFFS = (300, 500, 1000)


def main() -> None:
    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])
    climate_dir = raw_dir / "climate" / "isimip3b"

    cells_by_country = unique_cells_by_country(processed_dir)

    counts = []
    for country in STUDY_COUNTRIES:
        cells = cells_by_country[country]
        for model in datasets_cfg["models"]:
            hist_pr_path = climate_dir / model / "historical" / "pr" / f"{model}_historical_pr_{country}.nc"
            start_year, end_year = period_years("historical", datasets_cfg)
            hist_pr = pr_daily(hist_pr_path, cells, start_year, end_year)
            hist_pr["period"] = "baseline"
            wd = precip.wet_day_count(hist_pr)
            wd["country"], wd["model"] = country, model
            counts.append(wd)
            print(f"{country}/{model}: done")

    wet_days = pd.concat(counts, ignore_index=True)
    out_path = processed_dir / "wet_day_sample_size.parquet"
    wet_days.to_parquet(out_path, index=False)
    print(f"\nwrote {out_path}: {len(wet_days)} rows")

    print("\n=== Action 1: wet-day counts by country (all models pooled) ===")
    for country in STUDY_COUNTRIES:
        sub = wet_days[wet_days["country"] == country]["n_wet_days"]
        row = {
            "country": country,
            "min": sub.min(),
            "p5": sub.quantile(0.05),
            "median": sub.median(),
            "max": sub.max(),
        }
        for cutoff in CUTOFFS:
            row[f"n_below_{cutoff}"] = int((sub < cutoff).sum())
        print(row)

    print("\n=== 10 driest cell/model combinations ===")
    driest = wet_days.sort_values("n_wet_days").head(10)
    print(driest[["country", "model", "cell_lat", "cell_lon", "n_wet_days"]].to_string(index=False))

    print("\n=== Action 2: plants dependent on cells below 300 wet days ===")
    plants = pd.read_parquet(
        processed_dir / "plants.parquet",
        columns=["plant_uid", "country", "fleet", "tech_class", "capacity_mw"],
    )
    plant_cell = pd.read_parquet(
        processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    plants_cells = plants.merge(plant_cell, on="plant_uid")

    dry_cells = wet_days[wet_days["n_wet_days"] < 300][["country", "cell_lat", "cell_lon", "model", "n_wet_days"]]
    # A cell is only "affected" if at least one model has < 300 wet days there.
    dry_cell_keys = dry_cells[["country", "cell_lat", "cell_lon"]].drop_duplicates()
    affected = plants_cells.merge(dry_cell_keys, on=["country", "cell_lat", "cell_lon"])

    if affected.empty:
        print("no plants depend on a cell with < 300 baseline wet days in any model")
    else:
        summary = affected.groupby(["country", "fleet", "tech_class"], as_index=False).agg(
            n_plants=("plant_uid", "nunique"), capacity_mw=("capacity_mw", "sum")
        )
        print(summary.to_string(index=False))
        print(f"\ntotal affected plants: {affected['plant_uid'].nunique()}, "
              f"{affected.drop_duplicates('plant_uid')['capacity_mw'].sum():.1f} MW")


if __name__ == "__main__":
    main()
