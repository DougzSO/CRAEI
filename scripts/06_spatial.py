"""COMANDO 14: grid and catchment mapping (Spec §3 Step 3).

Associates each plant to its nearest 0.5° land cell (D25: GADM-derived land
mask) and, for hydro plants, builds the upstream catchment from HydroBASINS
level 6 (NEXT_DOWN traversal) with per-cell area weights.
"""

from pathlib import Path

import pandas as pd

from craei.acquire.auxiliary import HYDROBASINS_REGIONS
from craei.config import load_paths
from craei.spatial import catchments as cat
from craei.spatial import grid

# One ISIMIP grid template per country (job 1, already acquired in C11/C12).
_TASMAX_TEMPLATE = (
    "climate/isimip3b/gfdl-esm4/historical/tasmax/gfdl-esm4_historical_tasmax_{iso}.nc"
)


def main() -> None:
    paths = load_paths()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])

    plants = pd.read_parquet(processed_dir / "plants.parquet")
    countries = sorted(plants["country"].unique())

    nc_paths = {iso: raw_dir / _TASMAX_TEMPLATE.format(iso=iso) for iso in countries}
    gadm_paths = {iso: raw_dir / "gadm" / f"gadm41_{iso}.gpkg" for iso in countries}
    cells_by_country = {iso: grid.land_cells(nc_paths[iso], gadm_paths[iso]) for iso in countries}

    plant_cell = grid.build_plant_cell(plants, nc_paths, gadm_paths)
    plant_cell.to_parquet(processed_dir / "plant_cell.parquet", index=False)
    print(f"plant_cell: {len(plant_cell)} rows, {plant_cell['plant_uid'].nunique()} plants")
    assert plant_cell["plant_uid"].nunique() == len(plants), "not 100% of plants got a cell"
    print(f"max dist_to_cell_km: {plant_cell['dist_to_cell_km'].max():.2f}")

    hydro_plants = plants[plants["tech_class"] == "hydro"].copy()
    hydrobasins_dir = raw_dir / "boundaries" / "hydrobasins"
    basins_by_region = {
        region: cat.load_hydrobasins(hydrobasins_dir / f"hybas_{region}_lev06_v1c.zip")
        for region in set(HYDROBASINS_REGIONS.values())
    }

    weights, validation = cat.build_catchment_weights(
        hydro_plants, basins_by_region, HYDROBASINS_REGIONS, cells_by_country
    )
    weights.to_parquet(processed_dir / "catchment_weights.parquet", index=False)
    validation.to_csv(processed_dir / "catchment_validation.csv", index=False)

    sums = weights.groupby("plant_uid")["weight"].sum()
    bad_sums = (sums - 1.0).abs() > 1e-6
    n_hydro, n_bad = len(hydro_plants), bad_sums.sum()
    print(f"catchment weights: {n_hydro} hydro plants, weights sum!=1 for {n_bad}")

    exceptions = validation[validation["pct_diff_up_area"] >= 1.0]
    print(f"UP_AREA validation: {len(validation) - len(exceptions)}/{len(validation)} within 1%")
    if len(exceptions):
        print(exceptions.to_string(index=False))


if __name__ == "__main__":
    main()
