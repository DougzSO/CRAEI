"""Shared loader: cropped ISIMIP tasmax/tasmin/pr files -> long per-cell daily frames.

Used by scripts/04_daily_indices.py (COMANDO 15), scripts/07_water_balance.py
(COMANDO 16) and the wet-day sample-size audit (COMANDO 15 follow-up).
Selects only the cells a plant actually uses (`craei.spatial.grid`/COMANDO 14
output), filtered by the caller to whichever year span its step needs (Spec
§1.3's baseline/future for indices, §3 Step 5's 1984-start window for the
water balance so a 12-month SPEI accumulation reaches January 1985), and
applies the two unit conversions ISIMIP's raw files need: temperature K -> C,
pr flux (kg m-2 s-1) -> mm d-1.
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


def cells_with_catchments_by_country(processed_dir: Path) -> dict[str, pd.DataFrame]:
    """Like `unique_cells_by_country`, plus every cell a hydro plant's upstream
    catchment weights (COMANDO 14's `catchment_weights.parquet`) reference.

    A catchment can span many cells beyond the plant's own nearest cell, so
    Step 5 (water balance, cell scale feeding both catchment-averaged hydro
    and cell-scale thermal SPEI) needs this superset; `unique_cells_by_country`
    alone (nearest-cell only) would silently drop catchment cells and produce
    an incomplete weighted average.
    """
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country"])
    plant_cell = pd.read_parquet(
        processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    weights = pd.read_parquet(
        processed_dir / "catchment_weights.parquet", columns=["plant_uid", "cell_lat", "cell_lon"]
    )
    nearest = plants.merge(plant_cell, on="plant_uid")[["country", "cell_lat", "cell_lon"]]
    catchment = plants.merge(weights, on="plant_uid")[["country", "cell_lat", "cell_lon"]]
    cells = pd.concat([nearest, catchment], ignore_index=True).drop_duplicates()
    return {
        country: g[["cell_lat", "cell_lon"]].reset_index(drop=True)
        for country, g in cells.groupby("country")
    }


def period_years(scenario: str, datasets_cfg: dict) -> tuple[int, int]:
    """Spec §1.3 study period for `scenario`: baseline 1985-2014, future 2041-2070."""
    key = "baseline" if scenario == "historical" else "future"
    span = datasets_cfg["periods"][key]
    return span["start"], span["end"]


def download_years_span(scenario: str, datasets_cfg: dict) -> tuple[int, int]:
    """Downloaded (not study-period-trimmed) span for `scenario`: historical
    starts a year earlier (1984) than the Spec §1.3 baseline (1985) — the
    extra year is needed so a 12-month SPEI accumulation (Spec §3 Step 6) has
    enough history to reach January 1985 (Spec §3 Step 5)."""
    key = "historical" if scenario == "historical" else "future"
    span = datasets_cfg["download_years"][key]
    return span["start"], span["end"]


def load_cell_series(
    nc_path: Path, cells: pd.DataFrame, value_col: str, start_year: int, end_year: int
) -> pd.DataFrame:
    """Point-select `cells` from `nc_path`, filtered to [`start_year`, `end_year`].

    Returns only (date, cell_lat, cell_lon, value_col) -- no model/scenario/
    period columns, so this frame stays as small as the raw grid selection
    itself; the caller attaches those constant labels after aggregating.
    """
    with xr.open_dataset(nc_path) as ds:
        variable = next(iter(ds.data_vars))
        lat_sel = xr.DataArray(cells["cell_lat"].to_numpy(), dims="cell")
        lon_sel = xr.DataArray(cells["cell_lon"].to_numpy(), dims="cell")
        time_ok = (ds["time.year"] >= start_year) & (ds["time.year"] <= end_year)
        selected = (
            ds[variable]
            .sel(lat=lat_sel, lon=lon_sel, method="nearest")
            .isel(time=time_ok.values)
            .load()
        )

    df = selected.to_dataframe(name=value_col).reset_index()
    df["cell_lat"] = cells["cell_lat"].to_numpy()[df["cell"].to_numpy()]
    df["cell_lon"] = cells["cell_lon"].to_numpy()[df["cell"].to_numpy()]
    df.rename(columns={"time": "date"}, inplace=True)  # in place: avoids a second full-frame copy
    return df[["date", "cell_lat", "cell_lon", value_col]]


def tasmax_daily(nc_path: Path, cells: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "tasmax_c", start_year, end_year)
    df["tasmax_c"] -= KELVIN_OFFSET_C
    return df


def tasmin_daily(nc_path: Path, cells: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "tasmin_c", start_year, end_year)
    df["tasmin_c"] -= KELVIN_OFFSET_C
    return df


def pr_daily(nc_path: Path, cells: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    df = load_cell_series(nc_path, cells, "pr_mm", start_year, end_year)
    df["pr_mm"] *= PR_FLUX_TO_MM_PER_DAY
    return df
