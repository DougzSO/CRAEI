"""COMANDO 22-B Part 2, Actions 1-2: assign each plant to its GADM level-1 unit.

GADM level 1 (`ADM_ADM_1`) is already present locally in the same per-country
GeoPackages COMANDO 13/14 already used at level 0 (`gadm41_{ISO}.gpkg`,
`config/paths.local.yaml:gadm_dir`) -- no download needed, contrary to the
command's default assumption. Confirmed directly: `fiona.listlayers` on all
three files lists `ADM_ADM_1` already.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from craei.config import load_paths

GADM_DIR = Path("D:/ARTIGO RISK ASSESSMENT/GEAR_framework/data/raw/boundaries/gadm")
ISO3 = {"BRA": "BRA", "IND": "IND", "PRT": "PRT"}


def assign_region(plants: pd.DataFrame) -> pd.DataFrame:
    plants = plants.copy()
    plants["region_name"] = None
    plants["region_id"] = None
    for country, iso in ISO3.items():
        sub = plants[plants["country"] == country]
        if sub.empty:
            continue
        gdf = gpd.GeoDataFrame(
            sub, geometry=gpd.points_from_xy(sub["lon"], sub["lat"]), crs="EPSG:4326"
        )
        regions = gpd.read_file(GADM_DIR / f"gadm41_{iso}.gpkg", layer="ADM_ADM_1")
        regions = regions.to_crs("EPSG:4326")
        name_col = "NAME_1" if "NAME_1" in regions.columns else regions.columns[0]
        joined = gpd.sjoin(gdf, regions[[name_col, "geometry"]], how="left", predicate="within")
        plants.loc[sub.index, "region_name"] = joined[name_col].values
        plants.loc[sub.index, "region_id"] = country + "_" + joined[name_col].astype(str).values
    return plants


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])
    outputs_dir = Path(paths["outputs_dir"])
    plants = pd.read_parquet(processed_dir / "plants.parquet")

    out = assign_region(plants)

    n_unassigned = out["region_id"].isna().sum()
    print(
        f"Plants without a region assignment (point outside every polygon): "
        f"{n_unassigned} / {len(out)}"
    )
    if n_unassigned:
        unassigned = out.loc[out["region_id"].isna(), ["plant_uid", "country", "lat", "lon"]]
        print(unassigned.to_string(index=False))

    out.to_parquet(outputs_dir / "diagnostics" / "c22b_plant_region.parquet", index=False)

    # Action 2: fleet inventory by region.
    operating = out[out["fleet"] == "operating"].copy()
    operating["is_hydro"] = operating["tech_class"].str.startswith("hydro", na=False)
    operating["is_thermal_water"] = (operating["tech_class"] == "thermal_water_dependent")

    rows = []
    for (country, region_id, region_name), g in operating.groupby(
        ["country", "region_id", "region_name"], dropna=False
    ):
        hydro = g[g["is_hydro"]]
        thermal_w = g[g["is_thermal_water"]]
        rows.append(
            {
                "country": country,
                "region_id": region_id,
                "region_name": region_name,
                "n_hydro_plants": len(hydro),
                "hydro_capacity_mw": hydro["capacity_mw"].sum(),
                "n_thermal_water_plants": len(thermal_w),
                "thermal_water_capacity_mw": thermal_w["capacity_mw"].sum(),
                "has_both_fleets": len(hydro) > 0 and len(thermal_w) > 0,
            }
        )
    inv = pd.DataFrame(rows).sort_values(["country", "region_id"])
    inv.to_csv(outputs_dir / "diagnostics" / "c22b_regional_fleet_inventory.csv", index=False)

    print("\nRegional fleet inventory (operating fleet):")
    print(inv.to_string(index=False))

    n_both = inv["has_both_fleets"].sum()
    n_hydro_only = ((inv["n_hydro_plants"] > 0) & (inv["n_thermal_water_plants"] == 0)).sum()
    n_thermal_only = ((inv["n_thermal_water_plants"] > 0) & (inv["n_hydro_plants"] == 0)).sum()
    n_neither = ((inv["n_hydro_plants"] == 0) & (inv["n_thermal_water_plants"] == 0)).sum()
    print(
        f"\nRegions with both fleets: {n_both}; hydro-only: {n_hydro_only}; "
        f"thermal-only: {n_thermal_only}; neither: {n_neither}; total regions: {len(inv)}"
    )
    print(
        "Regions lacking one of the two fleets are excluded from the regional compound "
        "metric by definition (Part 2, Action 2)."
    )


if __name__ == "__main__":
    (Path(load_paths()["outputs_dir"]) / "diagnostics").mkdir(parents=True, exist_ok=True)
    main()
