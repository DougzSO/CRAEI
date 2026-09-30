"""Unit tests for audit coverage calculation (COMANDO 22, Action 1)."""

import pytest
import pandas as pd
import numpy as np

from craei.audit.coverage import compute_coverage
from craei.hazards.consolidate import (
    BUCKET_HYDRO_RESERVOIR,
    BUCKET_HYDRO_ROR,
    BUCKET_THERMAL_AIR,
    BUCKET_THERMAL_WATER,
)


def test_coverage_fraction_in_bounds():
    """All coverage_fraction values must be in [0, 1]."""
    # Create minimal test data
    plants = pd.DataFrame({
        "plant_uid": ["p1", "p2", "p3"],
        "plant_name": ["Plant 1", "Plant 2", "Plant 3"],
        "country": ["BRA", "BRA", "IND"],
        "tech_class": ["hydro", "thermal_water_dependent", "thermal_air_only"],
        "hydro_type": ["reservoir", np.nan, np.nan],
        "fleet": ["operating", "operating", "operating"],
        "capacity_mw": [100.0, 50.0, 25.0],
        "lat": [-10.0, -15.0, 20.0],
        "lon": [-55.0, -60.0, 75.0],
        "dist_coast_km": [100.0, 5.0, 500.0],
        "coastal_2km": [False, True, False],
        "coastal_5km": [False, True, False],
        "coastal_10km": [False, True, False],
        "water_dependent": [False, True, False],
        "basin_id": [123, 456, 789],
    })

    # Create hazard data with some NaNs
    plant_hazards = pd.DataFrame({
        "plant_uid": ["p1", "p1", "p2", "p2", "p3", "p3"],
        "bucket": [
            BUCKET_HYDRO_RESERVOIR,
            BUCKET_HYDRO_RESERVOIR,
            BUCKET_THERMAL_WATER,
            BUCKET_THERMAL_WATER,
            BUCKET_THERMAL_AIR,
            BUCKET_THERMAL_AIR,
        ],
        "model": ["model1", "model1", "model1", "model1", "model1", "model1"],
        "scenario": ["ssp126", "ssp126", "ssp126", "ssp126", "ssp126", "ssp126"],
        "hazard": ["f_d_spei12", "TX35", "TX35", "f_d_spei12", "TX35", "TX40"],
        "delta": [np.nan, 5.0, 10.0, np.nan, 8.0, np.nan],
        "ratio": [np.nan, np.nan, np.nan, 1.5, np.nan, np.nan],
        "baseline_value": [0.06, 30.0, 40.0, 0.08, 32.0, 38.0],
        "future_value": [0.12, 35.0, 50.0, 0.12, 40.0, 43.0],
    })

    plant_aqueduct = pd.DataFrame({
        "plant_uid": ["p2"],
        "scenario": ["ssp126"],
        "cooling_bound": ["upper"],
        "ws_category": ["high"],
        "ws_value": [50.0],
        "bws_value": [40.0],
        "bws_category": ["medium-high"],
    })

    result = compute_coverage(plants, plant_hazards, plant_aqueduct)

    # Check that all coverage_fraction values are in [0, 1]
    assert (result["coverage_fraction"] >= 0.0).all()
    assert (result["coverage_fraction"] <= 1.0).all()

    # Check specific values
    assert len(result) > 0
    assert "coverage_fraction" in result.columns
    assert "excluded_mw" in result.columns
    assert "absent_mw" in result.columns


def test_coverage_fraction_computation():
    """Test the numerator/denominator calculation is correct."""
    plants = pd.DataFrame({
        "plant_uid": ["p1", "p2"],
        "plant_name": ["Plant 1", "Plant 2"],
        "country": ["BRA", "BRA"],
        "tech_class": ["thermal_air_only", "thermal_air_only"],
        "hydro_type": [np.nan, np.nan],
        "fleet": ["operating", "operating"],
        "capacity_mw": [100.0, 50.0],
        "lat": [-10.0, -15.0],
        "lon": [-55.0, -60.0],
        "dist_coast_km": [100.0, 100.0],
        "coastal_2km": [False, False],
        "coastal_5km": [False, False],
        "coastal_10km": [False, False],
        "water_dependent": [False, False],
        "basin_id": [123, 456],
    })

    # p1 has TX35 data, p2 doesn't
    plant_hazards = pd.DataFrame({
        "plant_uid": ["p1"],
        "bucket": [BUCKET_THERMAL_AIR],
        "model": ["model1"],
        "scenario": ["ssp126"],
        "hazard": ["TX35"],
        "delta": [5.0],
        "ratio": [np.nan],
        "baseline_value": [30.0],
        "future_value": [35.0],
    })

    result = compute_coverage(plants, plant_hazards, None)

    tx35_row = result[
        (result["country"] == "BRA")
        & (result["metric"] == "TX35")
        & (result["bucket"] == BUCKET_THERMAL_AIR)
    ]

    if len(tx35_row) > 0:
        # Numerator should be 100 MW (only p1 has data)
        # Denominator should be 150 MW (p1 + p2, both in thermal_air_only)
        # Coverage should be 100/150 = 0.667
        assert abs(tx35_row.iloc[0]["coverage_fraction"] - 100.0/150.0) < 0.01
        assert tx35_row.iloc[0]["numerator_mw"] == pytest.approx(100.0)
        assert tx35_row.iloc[0]["denominator_mw"] == pytest.approx(150.0)
        assert tx35_row.iloc[0]["absent_plants"] == 1
        assert tx35_row.iloc[0]["absent_mw"] == pytest.approx(50.0)


if __name__ == "__main__":
    test_coverage_fraction_in_bounds()
    test_coverage_fraction_computation()
    print("All tests passed!")
