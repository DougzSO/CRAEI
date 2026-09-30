"""Tests for plant hazard consolidation (Spec §1.4/§3 Step 7, COMANDO 18)."""

import numpy as np
import pandas as pd
import pytest

from craei.hazards import consolidate


@pytest.fixture
def sample_plants():
    return pd.DataFrame(
        {
            "plant_uid": ["hydro_res", "hydro_ror", "thermal_wd", "thermal_air", "solar_1"],
            "tech_class": [
                "hydro",
                "hydro",
                "thermal_water_dependent",
                "thermal_air_only",
                "solar",
            ],
            "hydro_type": ["reservoir", "run-of-river", None, None, None],
        }
    )


def _heat_rows(cell_lat, cell_lon, model="gfdl-esm4"):
    rows = []
    for scenario, period, base_value in [
        ("historical", "baseline", 2.0),
        ("ssp126", "future", 10.0),
    ]:
        for year in range(1985, 1985 + 3):
            for index_type, val in [("tx35", base_value), ("tx40", base_value / 2)]:
                rows.append(
                    {
                        "cell_lat": cell_lat,
                        "cell_lon": cell_lon,
                        "model": model,
                        "scenario": scenario,
                        "period": period,
                        "index": index_type,
                        "year": float(year),
                        "month": pd.NaT,
                        "value": val,
                    }
                )
    for scenario, period, val in [
        ("historical", "baseline", 4.0),
        ("ssp126", "future", 2.0),
    ]:
        for index_type in ("p95_exceedance_frequency", "rx5day"):
            rows.append(
                {
                    "cell_lat": cell_lat,
                    "cell_lon": cell_lon,
                    "model": model,
                    "scenario": scenario,
                    "period": period,
                    "index": index_type,
                    "year": np.nan,
                    "month": pd.NaT,
                    "value": val,
                }
            )
    return rows


@pytest.fixture
def sample_indices_daily():
    return pd.DataFrame(_heat_rows(-33.75, -53.25))


@pytest.fixture
def sample_plant_cell():
    return pd.DataFrame(
        {
            "plant_uid": ["thermal_wd", "thermal_air"],
            "cell_lat": [-33.75, -33.75],
            "cell_lon": [-53.25, -53.25],
            "dist_to_cell_km": [5.0, 5.0],
        }
    )


def _spei_rows(id_val, scale, model="gfdl-esm4"):
    rows = []
    for scenario, period, spei_val in [
        ("historical", "baseline", -0.5),
        ("ssp126", "future", -2.0),
    ]:
        n = 30
        for m in range(n):
            month = pd.Timestamp("1985-01-01") + pd.DateOffset(months=m)
            rows.append(
                {
                    "id": id_val,
                    "model": model,
                    "scenario": scenario,
                    "period": period,
                    "scale": scale,
                    "month": month,
                    "SPEI_12": spei_val,
                    "SPEI_3": spei_val,
                    "distribution": "loglogistic",
                }
            )
    return rows


@pytest.fixture
def sample_spei():
    rows = _spei_rows("hydro_res", "catchment") + _spei_rows("hydro_ror", "catchment")
    rows += _spei_rows("-33.75_-53.25", "cell")
    return pd.DataFrame(rows)


def test_compute_heat_hazards_thermal_only(sample_plants, sample_indices_daily, sample_plant_cell):
    thermal = sample_plants[sample_plants["tech_class"].str.startswith("thermal")].assign(
        bucket=["thermal_water_dependent", "thermal_air_only"]
    )
    out = consolidate.compute_heat_hazards(thermal, sample_indices_daily, sample_plant_cell)
    assert set(out["plant_uid"]) == {"thermal_wd", "thermal_air"}
    assert out["ratio"].isna().all()
    assert set(out["hazard"]) == {"TX35", "TX40"}
    row = out[(out["plant_uid"] == "thermal_wd") & (out["hazard"] == "TX35")].iloc[0]
    assert row["baseline_value"] == pytest.approx(2.0)
    assert row["future_value"] == pytest.approx(10.0)
    assert row["delta"] == pytest.approx(8.0)


def test_compute_drought_hazards_ror_gets_spei3_reservoir_does_not(
    sample_plants, sample_spei, sample_plant_cell
):
    params_plants = sample_plants.copy()
    params_plants["bucket"] = [
        "hydro_reservoir",
        "hydro_run_of_river",
        "thermal_water_dependent",
        "thermal_air_only",
        "solar",
    ]
    drought, r_d_zeros = consolidate.compute_drought_hazards(
        params_plants, sample_spei, sample_plant_cell, threshold=-1.5
    )
    res_hazards = set(drought[drought["plant_uid"] == "hydro_res"]["hazard"])
    ror_hazards = set(drought[drought["plant_uid"] == "hydro_ror"]["hazard"])
    assert res_hazards == {"f_d_spei12"}
    assert ror_hazards == {"f_d_spei12", "f_d_spei3"}
    assert isinstance(r_d_zeros, pd.DataFrame)
    # baseline SPEI = -0.5 (> -1.5 threshold): F_D baseline = 0% -> R_D must be NaN, not a division.
    row = drought[(drought["plant_uid"] == "hydro_res") & (drought["hazard"] == "f_d_spei12")].iloc[0]
    assert row["baseline_value"] == pytest.approx(0.0)
    assert np.isnan(row["ratio"])
    assert len(r_d_zeros) > 0


def test_plant_hazards_no_bucket_metric_leakage(
    sample_plants, sample_indices_daily, sample_spei, sample_plant_cell
):
    hazards, r_d_zeros = consolidate.plant_hazards(
        sample_plants, sample_indices_daily, sample_spei, sample_plant_cell
    )
    # No non-thermal plant carries a TX35/TX40 row (Action 4 validation test).
    heat_plants = set(hazards[hazards["hazard"].isin(["TX35", "TX40"])]["plant_uid"])
    assert heat_plants <= {"thermal_wd", "thermal_air"}
    # No air-only or solar plant carries a drought (SPEI) row.
    drought_plants = set(hazards[hazards["hazard"].str.startswith("f_d_")]["plant_uid"])
    assert drought_plants <= {"hydro_res", "hydro_ror", "thermal_wd"}
    assert "solar_1" not in drought_plants
    assert "thermal_air" not in drought_plants
    required_cols = {
        "plant_uid",
        "bucket",
        "model",
        "scenario",
        "hazard",
        "baseline_value",
        "future_value",
        "delta",
        "ratio",
    }
    assert required_cols <= set(hazards.columns)
