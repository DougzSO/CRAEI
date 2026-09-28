"""Shared loader: cropped ISIMIP tasmax/pr files -> long per-cell daily frames.

Used by scripts/04_daily_indices.py (COMANDO 15) and by the wet-day sample-size
audit (COMANDO 15 follow-up). Selects only the cells a plant actually uses
(`craei.spatial.grid`/COMANDO 14 output), filtered to the scenario's study
period (Spec §1.3), and applies the two unit conversions ISIMIP's raw files
need: tasmax K -> C, pr flux (kg m-2 s-1) -> mm d-1.
"""

from pathlib import Path

import pandas as pd
import xarray as xr

from craei.hazards.pet import KELVIN_OFFSET_C

PR_FLUX_TO_MM_PER_DAY = 86400.0  # kg m-2 s-1 -> mm d-1


def unique_cells_by_country(processed_dir: Path) -> dict[str, pd.DataFrame]:
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country"])
    plant_cell = pd.read_parquet(
        processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    merged = plants.merge(plant_cell, on="plant_uid")
    cells = merged[["country", "cell_lat", "cell_lon"]].drop_duplicates()
    return {
        country: g[["cell_lat", "cell_lon"]].reset_index(drop=True)
        for country, g in cells.groupby("country")
    }


def load_cell_series(
    nc_path: Path, cells: pd.DataFrame, value_col: str, scenario: str, datasets_cfg: dict
) -> pd.DataFrame:
    """Point-select `cells` from `nc_path`, filtered to the scenario's study period.

    Returns only (date, cell_lat, cell_lon, value_col) -- no model/scenario/
    period columns, so this frame stays as small as the raw grid selection
    itself; the caller attaches those constant labels after aggregating.
    """
    period_key = "baseline" if scenario == "historical" else "future"
    span = datasets_cfg["periods"][period_key]

    with xr.open_dataset(nc_path) as ds:
        variable = next(iter(ds.data_vars))
        lat_sel = xr.DataArray(cells["cell_lat"].to_numpy(), dims="cell")
        lon_sel = xr.DataArray(cells["cell_lon"].to_numpy(), dims="cell")
        time_ok = (ds["time.year"] >= span["start"]) & (ds["time.year"] <= span["end"])
        selected = (
            ds[variable]
            .sel(lat=lat_sel, lon=lon_sel, method="nearest")
            .isel(time=time_ok.values)
            .load()
        )

    df = selected.to_dataframe(name=value_col).reset_index()
    df["cell_lat"] = cells["cell_lat"].to_numpy()[df["cell"].to_numpy()]
    df["cell_lon"] = cells["cell_lon"].to_numpy()[df["cell"].to_numpy()]
    return df[["time", "cell_lat", "cell_lon", value_col]].rename(columns={"time": "date"})


def tasmax_daily(
    nc_path: Path, cells: pd.DataFrame, scenario: str, datasets_cfg: dict
) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "tasmax_c", scenario, datasets_cfg)
    df["tasmax_c"] -= KELVIN_OFFSET_C
    return df


def pr_daily(nc_path: Path, cells: pd.DataFrame, scenario: str, datasets_cfg: dict) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "pr_mm", scenario, datasets_cfg)
    df["pr_mm"] *= PR_FLUX_TO_MM_PER_DAY
    return df
