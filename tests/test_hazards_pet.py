import numpy as np
import pandas as pd
import pytest

from craei.hazards import pet


def test_extraterrestrial_radiation_matches_fao56_example():
    # FAO-56 Example 8: 20°S, 3 September (day of year 246) -> Ra = 32.2 MJ m-2 d-1.
    # Author-confirmed reference value pending; flagged for verdict alongside
    # COMANDO 16's full-data close (see pet.py module docstring).
    ra = pet.extraterrestrial_radiation(lat_deg=-20.0, day_of_year=246)
    assert ra == pytest.approx(32.2, abs=0.1)


def test_hargreaves_pet_zero_range_gives_zero():
    ra = pet.extraterrestrial_radiation(lat_deg=0.0, day_of_year=180)
    result = pet.hargreaves_pet(tmax_c=25.0, tmin_c=25.0, ra=ra)
    assert result == pytest.approx(0.0)


def test_hargreaves_pet_positive_for_typical_conditions():
    ra = pet.extraterrestrial_radiation(lat_deg=-15.0, day_of_year=15)
    result = pet.hargreaves_pet(tmax_c=32.0, tmin_c=20.0, ra=ra)
    assert result > 0


def test_hargreaves_pet_rejects_tmax_below_tmin():
    ra = pet.extraterrestrial_radiation(lat_deg=0.0, day_of_year=1)
    with pytest.raises(ValueError, match="tmax_c must be >= tmin_c"):
        pet.hargreaves_pet(tmax_c=np.array([18.0, 30.0]), tmin_c=np.array([20.0, 15.0]), ra=ra)


def test_monthly_water_balance_aggregates_and_computes_deficit():
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2000-01-01", "2000-01-02", "2000-02-01"]),
            "id": ["cellA", "cellA", "cellA"],
            "model": ["gfdl-esm4"] * 3,
            "scenario": ["historical"] * 3,
            "p_mm": [5.0, 3.0, 10.0],
            "pet_mm": [2.0, 2.0, 4.0],
        }
    )
    out = pet.monthly_water_balance(daily)

    assert len(out) == 2
    jan = out[out["month"] == np.datetime64("2000-01")].iloc[0]
    assert jan["P"] == pytest.approx(8.0)
    assert jan["PET"] == pytest.approx(4.0)
    assert jan["D"] == pytest.approx(4.0)


def test_count_tx_below_tn_counts_correctly():
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2000-01-01", "2000-01-02", "2000-01-03"]),
            "cell_lat": [10.0, 10.0, 10.0],
            "model": ["gfdl-esm4"] * 3,
            "tasmax_c": [30.0, 18.0, 25.0],
            "tasmin_c": [20.0, 20.0, 15.0],  # row 2 (18 < 20) is TX < TN
        }
    )
    out = pet.count_tx_below_tn(daily)
    row = out.iloc[0]
    assert row["n_days"] == 3
    assert row["n_tx_below_tn"] == 1


def test_daily_pet_clips_tx_below_tn_instead_of_raising():
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2000-01-15"]),
            "cell_lat": [10.0],
            "tasmax_c": [18.0],
            "tasmin_c": [20.0],  # TX < TN
        }
    )
    out = pet.daily_pet(daily)  # must not raise
    # zero diurnal range (clipped) -> PET is not positive-range-driven
    assert out.iloc[0]["pet_mm"] >= 0.0


def test_daily_pet_truncates_negative_and_flags():
    # Very cold T_mean (well below -17.8 degC) with a real diurnal range
    # forces the Hargreaves term negative before truncation.
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2000-06-15"]),
            "cell_lat": [30.0],
            "tasmax_c": [-25.0],
            "tasmin_c": [-30.0],
        }
    )
    out = pet.daily_pet(daily)
    assert out.iloc[0]["pet_truncated"]
    assert out.iloc[0]["pet_mm"] == pytest.approx(0.0)


def test_catchment_water_balance_weighted_average_and_deficit():
    cell_balance = pd.DataFrame(
        {
            "cell_lat": [10.0, 11.0, 10.0, 11.0],
            "cell_lon": [20.0, 20.0, 20.0, 20.0],
            "model": ["gfdl-esm4"] * 4,
            "scenario": ["historical"] * 4,
            "month": pd.to_datetime(["2000-01-01", "2000-01-01", "2000-02-01", "2000-02-01"]),
            "P": [10.0, 20.0, 5.0, 15.0],
            "PET": [2.0, 4.0, 1.0, 3.0],
        }
    )
    weights = pd.DataFrame(
        {
            "plant_uid": ["p1", "p1"],
            "cell_lat": [10.0, 11.0],
            "cell_lon": [20.0, 20.0],
            "weight": [0.25, 0.75],
        }
    )
    out = pet.catchment_water_balance(cell_balance, weights)
    jan = out[out["month"] == pd.Timestamp("2000-01-01")].iloc[0]
    assert jan["id"] == "p1"
    assert jan["P"] == pytest.approx(0.25 * 10.0 + 0.75 * 20.0)
    assert jan["PET"] == pytest.approx(0.25 * 2.0 + 0.75 * 4.0)
    assert jan["D"] == pytest.approx(jan["P"] - jan["PET"])
