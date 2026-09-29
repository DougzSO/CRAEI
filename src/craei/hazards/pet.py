"""Potential evapotranspiration (Hargreaves-Samani) and monthly water balance
(Spec §1.4 H2, §3 Step 5; COMANDO 16).

    PET_d = 0.0023 * 0.408 * Ra_d * (T_mean_d + 17.8) * (TX_d - TN_d)^0.5

Ra (extraterrestrial radiation, MJ m-2 d-1) is FAO-56 Eq. 21. Inputs to
`hargreaves_pet` are degrees Celsius; ISIMIP tasmax/tasmin arrive in Kelvin
and must be converted by the caller (`KELVIN_OFFSET_C` below).

Two data conditions are real, not hypothetical (COMANDO 16), and are handled
without raising:

- `TX < TN` on a small fraction of days, from ISIMIP3b's bias adjustment
  being applied per variable independently. `count_tx_below_tn` counts these
  before any treatment so the caller can enforce Spec's 0.1%-of-days stop
  threshold per model/scenario/country; `daily_pet` then clips TN to TX for
  the PET calculation itself (a zero, not negative, diurnal range).
- Negative Hargreaves PET at very cold `T_mean` (< -17.8 degC): expected at
  high-altitude cells in India's bbox. `daily_pet` truncates to zero and
  flags each truncated day (`pet_truncated`); not an error (`docs/LIMITATIONS.md`).
"""

import numpy as np
import pandas as pd

SOLAR_CONSTANT_MJ_M2_MIN = 0.0820  # Gsc, FAO-56 Eq. 21
KELVIN_OFFSET_C = 273.15


def extraterrestrial_radiation(
    lat_deg: float | np.ndarray, day_of_year: int | np.ndarray
) -> np.ndarray:
    """Daily extraterrestrial radiation Ra (MJ m-2 d-1), FAO-56 Eq. 21-25.

    `lat_deg` is signed (negative = Southern Hemisphere). `day_of_year` is
    1-365/366 (Julian day within the calendar year).
    """
    lat_rad = np.radians(lat_deg)
    day_of_year = np.asarray(day_of_year, dtype=float)

    dr = 1.0 + 0.033 * np.cos(2.0 * np.pi / 365.0 * day_of_year)  # Eq. 23
    decl = 0.409 * np.sin(2.0 * np.pi / 365.0 * day_of_year - 1.39)  # Eq. 24
    sunset_angle = np.arccos(np.clip(-np.tan(lat_rad) * np.tan(decl), -1.0, 1.0))  # Eq. 25

    return (
        (24.0 * 60.0 / np.pi)
        * SOLAR_CONSTANT_MJ_M2_MIN
        * dr
        * (
            sunset_angle * np.sin(lat_rad) * np.sin(decl)
            + np.cos(lat_rad) * np.cos(decl) * np.sin(sunset_angle)
        )
    )


def hargreaves_pet(
    tmax_c: np.ndarray, tmin_c: np.ndarray, ra: np.ndarray
) -> np.ndarray:
    """Daily PET (mm d-1) via Hargreaves-Samani. Raises if any `tmax_c < tmin_c`."""
    tmax_c = np.asarray(tmax_c, dtype=float)
    tmin_c = np.asarray(tmin_c, dtype=float)
    if np.any(tmax_c < tmin_c):
        raise ValueError("hargreaves_pet: tmax_c must be >= tmin_c for every entry")

    tmean_c = (tmax_c + tmin_c) / 2.0
    return 0.0023 * 0.408 * ra * (tmean_c + 17.8) * np.sqrt(tmax_c - tmin_c)


def count_tx_below_tn(
    daily: pd.DataFrame, tmax_col: str = "tasmax_c", tmin_col: str = "tasmin_c"
) -> pd.DataFrame:
    """Count of days with `tmax_col` < `tmin_col`, per group (every other column).

    Called before `daily_pet` so the caller can report and enforce Spec's
    0.1%-of-days stop threshold on the untreated data.
    """
    group_cols = [c for c in daily.columns if c not in ("date", tmax_col, tmin_col)]
    d = daily.copy()
    d["tx_below_tn"] = d[tmax_col] < d[tmin_col]
    return d.groupby(group_cols, as_index=False).agg(
        n_days=(tmax_col, "size"), n_tx_below_tn=("tx_below_tn", "sum")
    )


def daily_pet(
    daily: pd.DataFrame,
    tmax_col: str = "tasmax_c",
    tmin_col: str = "tasmin_c",
    lat_col: str = "cell_lat",
    date_col: str = "date",
) -> pd.DataFrame:
    """Daily PET (mm d-1), added as `pet_mm`, from a per-cell tasmax/tasmin/lat frame.

    Two treatments applied silently here (counted separately, not raised as
    errors — see module docstring): `TN` is clipped to `TX` wherever `TX <
    TN` (zero, not negative, diurnal range), and the resulting PET is
    truncated to zero where negative, flagged in the added `pet_truncated`
    column so the caller can count occurrences.
    """
    d = daily.copy()
    day_of_year = d[date_col].dt.dayofyear.to_numpy()
    ra = extraterrestrial_radiation(d[lat_col].to_numpy(), day_of_year)

    tmax = d[tmax_col].to_numpy(dtype=float)
    tmin = np.minimum(d[tmin_col].to_numpy(dtype=float), tmax)
    pet = hargreaves_pet(tmax, tmin, ra)

    d["pet_truncated"] = pet < 0.0
    d["pet_mm"] = np.clip(pet, 0.0, None)
    return d


def catchment_water_balance(cell_balance: pd.DataFrame, weights: pd.DataFrame) -> pd.DataFrame:
    """Weight-average monthly P/PET from `cell_balance` (cell_lat, cell_lon, ...,
    month, P, PET) to catchment level via `weights` (plant_uid, cell_lat,
    cell_lon, weight; COMANDO 14's `catchment_weights.parquet`), then
    recompute D = P - PET at the catchment level.

    Grouping keys are every `cell_balance` column except cell_lat/cell_lon/P/PET
    (e.g. model, scenario, month), plus `plant_uid` from `weights`. Weights
    are expected to already sum to 1 per plant_uid over the cells present in
    `cell_balance` (Spec §3 Step 3); the caller verifies this, since a
    mismatch here silently produces an under-weighted average, not an error.
    """
    merged = weights.merge(cell_balance, on=["cell_lat", "cell_lon"])
    group_cols = [c for c in cell_balance.columns if c not in ("cell_lat", "cell_lon", "P", "PET")]
    merged["P_w"] = merged["P"] * merged["weight"]
    merged["PET_w"] = merged["PET"] * merged["weight"]
    out = merged.groupby(["plant_uid", *group_cols], as_index=False).agg(
        P=("P_w", "sum"), PET=("PET_w", "sum")
    )
    out["D"] = out["P"] - out["PET"]
    return out.rename(columns={"plant_uid": "id"})


def monthly_water_balance(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly P, PET, D = P - PET, grouped by every column except `date`/`p_mm`/`pet_mm`.

    `daily` needs columns `date` (datetime64), `p_mm`, `pet_mm`, plus whatever
    grouping keys the caller wants preserved (e.g. `id`, `model`, `scenario`).
    Spec §3 Step 5: `water_balance_cell.parquet`/`water_balance_catchment.parquet`
    (id, model, scenario, month, P, PET, D) are exactly this shape.
    """
    group_cols = [c for c in daily.columns if c not in ("date", "p_mm", "pet_mm")]
    monthly = daily.copy()
    monthly["month"] = monthly["date"].values.astype("datetime64[M]")
    out = monthly.groupby(group_cols + ["month"], as_index=False).agg(
        P=("p_mm", "sum"), PET=("pet_mm", "sum")
    )
    out["D"] = out["P"] - out["PET"]
    return out
