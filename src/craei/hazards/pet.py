"""Potential evapotranspiration (Hargreaves-Samani) and monthly water balance
(Spec §1.4 H2, §3 Step 5; COMANDO 16).

    PET_d = 0.0023 * 0.408 * Ra_d * (T_mean_d + 17.8) * (TX_d - TN_d)^0.5

Ra (extraterrestrial radiation, MJ m-2 d-1) is FAO-56 Eq. 21. Inputs to
`hargreaves_pet` are degrees Celsius; ISIMIP tasmax/tasmin arrive in Kelvin
and must be converted by the caller (`KELVIN_OFFSET_C` below).

COMANDO 12 (full ISIMIP acquisition) is not complete at the time this module
was written (18/60 jobs; only gfdl-esm4 has all 4 scenarios, ipsl-cm6a-lr
only historical+ssp126) — see PROGRESS.json C16 for the exact resume point.
The functions here are acquisition-independent and fully tested against
synthetic series and the FAO-56 worked example; what remains once C12
finishes is running the real 5-model dataset through `monthly_water_balance`
and closing the command's criteria (zero negative PET, zero NaN outside
ocean cells) against it.
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
