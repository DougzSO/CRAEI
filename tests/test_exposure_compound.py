"""Tests for the compound hydro-drought/thermal-heat metric (Spec §1.6, COMANDO 20)."""

import numpy as np
import pandas as pd
import pytest

from craei.exposure import compound


def test_assert_n35_monthly_passes_on_real_shape():
    df = pd.DataFrame(
        {
            "index": ["n35", "n35", "tx35"],
            "month": pd.to_datetime(["1985-01-01", "1985-02-01", pd.NaT]),
        }
    )
    compound.assert_n35_monthly(df)  # no raise


def test_assert_n35_monthly_stops_if_missing():
    df = pd.DataFrame({"index": ["tx35"], "month": [pd.NaT]})
    with pytest.raises(ValueError, match="no 'n35' index"):
        compound.assert_n35_monthly(df)


def test_assert_n35_monthly_stops_if_all_null_month():
    df = pd.DataFrame({"index": ["n35", "n35"], "month": [pd.NaT, pd.NaT]})
    with pytest.raises(ValueError, match="no 'month' value"):
        compound.assert_n35_monthly(df)


@pytest.fixture
def synthetic_plants():
    return pd.DataFrame(
        {
            "plant_uid": ["h1", "h2", "t1", "t2", "planned_h"],
            "country": ["A", "A", "A", "A", "A"],
            "fleet": ["operating", "operating", "operating", "operating", "planned_adv"],
            "tech_class": [
                "hydro",
                "hydro",
                "thermal_water_dependent",
                "thermal_water_dependent",
                "hydro",
            ],
            "hydro_type": ["reservoir", "reservoir", None, None, "reservoir"],
            "capacity_mw": [100.0, 100.0, 100.0, 100.0, 999.0],
        }
    )


@pytest.fixture
def synthetic_plant_cell():
    return pd.DataFrame(
        {
            "plant_uid": ["t1", "t2"],
            "cell_lat": [-10.0, -10.0],
            "cell_lon": [-40.0, -40.0],
        }
    )


def _spei_rows(plant_uid, model, scenario, period, months, values):
    return [
        {
            "id": plant_uid,
            "model": model,
            "scenario": scenario,
            "period": period,
            "month": m,
            "SPEI_12": v,
            "scale": "catchment",
        }
        for m, v in zip(months, values, strict=True)
    ]


@pytest.fixture
def synthetic_spei():
    baseline_months = pd.date_range("1985-01-01", periods=12, freq="MS")
    future_months = pd.date_range("2041-01-01", periods=3, freq="MS")

    # h1: severe (<=-1.5) in exactly 1/12 baseline months (P90 of a 0/1 series with
    # 1 event over 12 months is 0, since the 90th percentile of mostly-zero data is 0).
    h1_baseline_vals = [-2.0] + [0.0] * 11
    h2_baseline_vals = [0.0] * 12  # never severe at baseline

    rows = []
    rows += _spei_rows("h1", "m1", "historical", "baseline", baseline_months, h1_baseline_vals)
    rows += _spei_rows("h2", "m1", "historical", "baseline", baseline_months, h2_baseline_vals)
    # planned_h excluded: only operating fleet feeds the compound metric.
    rows += _spei_rows("planned_h", "m1", "historical", "baseline", baseline_months, [-3.0] * 12)

    # Future ssp370: h1 severe in all 3 months, h2 never severe.
    rows += _spei_rows("h1", "m1", "ssp370", "future", future_months, [-2.0, -2.0, -2.0])
    rows += _spei_rows("h2", "m1", "ssp370", "future", future_months, [0.0, 0.0, 0.0])

    return pd.DataFrame(rows)


def _n35_rows(cell_lat, cell_lon, model, scenario, period, months, values):
    return [
        {
            "index": "n35",
            "cell_lat": cell_lat,
            "cell_lon": cell_lon,
            "model": model,
            "scenario": scenario,
            "period": period,
            "month": m,
            "value": v,
        }
        for m, v in zip(months, values, strict=True)
    ]


@pytest.fixture
def synthetic_indices_daily():
    baseline_months = pd.date_range("1985-01-01", periods=12, freq="MS")
    future_months = pd.date_range("2041-01-01", periods=3, freq="MS")
    # thermal fleet t1+t2 share a cell: month 1 has a heat spike (day count 20),
    # others near zero, at baseline. P90 of mostly-low series with 1 high month
    # over 12 is 0 too (same 1/12 edge case as hydro, by construction).
    baseline_vals = [20.0] + [0.0] * 11
    future_vals = [25.0, 0.0, 0.0]
    rows = []
    rows += _n35_rows(-10.0, -40.0, "m1", "historical", "baseline", baseline_months, baseline_vals)
    rows += _n35_rows(-10.0, -40.0, "m1", "ssp370", "future", future_months, future_vals)
    return pd.DataFrame(rows)


def test_national_hydro_series_excludes_non_operating_and_missing(synthetic_plants, synthetic_spei):
    out = compound.national_hydro_series(synthetic_plants, synthetic_spei, spei_threshold=-1.5)
    baseline = out[(out["period"] == "baseline") & (out["country"] == "A")]
    # month 1: h1 severe (100 MW), h2 not (100 MW) -> s_hydro = 100/200 = 0.5
    month1 = baseline[baseline["month"] == pd.Timestamp("1985-01-01")].iloc[0]
    assert month1["s_hydro"] == pytest.approx(0.5)
    # month 2: neither severe -> 0.0; denominator is h1+h2 = 200 MW only (planned_h excluded)
    month2 = baseline[baseline["month"] == pd.Timestamp("1985-02-01")].iloc[0]
    assert month2["s_hydro"] == pytest.approx(0.0)


def test_national_thermal_series_capacity_weighted(
    synthetic_plants, synthetic_indices_daily, synthetic_plant_cell
):
    out = compound.national_thermal_series(
        synthetic_plants, synthetic_indices_daily, synthetic_plant_cell
    )
    month1 = out[out["month"] == pd.Timestamp("1985-01-01")].iloc[0]
    # both t1, t2 (100 MW each) share the cell with value=20 -> weighted mean = 20
    assert month1["h_thermal"] == pytest.approx(20.0)


def test_compound_baseline_p90_zero_fallback(
    synthetic_plants, synthetic_spei, synthetic_indices_daily, synthetic_plant_cell
):
    series = compound.build_compound_series(
        synthetic_plants,
        synthetic_spei,
        synthetic_indices_daily,
        synthetic_plant_cell,
        spei_threshold=-1.5,
    )
    thresholds = compound.baseline_thresholds(series, percentile=90)
    row = thresholds[(thresholds["country"] == "A") & (thresholds["model"] == "m1")].iloc[0]
    # 1 event in 12 months -> 90th percentile of a mostly-zero series is 0.
    assert row["s_hydro_p90"] == pytest.approx(0.0)
    assert row["s_hydro_p90_is_zero"]
    assert row["h_thermal_p90"] == pytest.approx(0.0)


def test_compound_summary_closed_metric_and_baseline_frequency(
    synthetic_plants, synthetic_spei, synthetic_indices_daily, synthetic_plant_cell
):
    """D63: compound_summary reports diff_pp and dependence_ratio, not LR_C, as the headline."""
    series = compound.build_compound_series(
        synthetic_plants,
        synthetic_spei,
        synthetic_indices_daily,
        synthetic_plant_cell,
        spei_threshold=-1.5,
    )
    thresholds = compound.baseline_thresholds(series, percentile=90)
    flagged = compound.flag_compound_months(series, thresholds)
    summary = compound.compound_summary(flagged)

    row = summary[
        (summary["country"] == "A") & (summary["model"] == "m1") & (summary["scenario"] == "ssp370")
    ]
    assert len(row) == 1
    row = row.iloc[0]

    # Baseline: month 1 has s_hydro=0.5>0 and h_thermal=20>0 -> compound; the other
    # 11 months have s_hydro=0 (not >0) -> not compound. f_baseline_pct = 100/12.
    assert row["f_baseline_pct"] == pytest.approx(100 / 12)

    # Future ssp370: all 3 months have h1 severe (s_hydro=0.5>0); h_thermal>0 only
    # in month 1 (25>0), months 2-3 have h_thermal=0 (not >0). f_future_pct = 100/3.
    assert row["f_future_pct"] == pytest.approx(100 / 3)
    assert row["diff_pp"] == pytest.approx(100 / 3 - 100 / 12)

    # Marginals (future, relative to baseline P90): s_above in all 3 months (0.5>0),
    # h_above only in month 1 (25>0) -> f_s_above=1.0, f_h_above=1/3.
    assert row["f_s_above_future"] == pytest.approx(1.0)
    assert row["f_h_above_future"] == pytest.approx(1 / 3)
    assert row["f_compound_independence"] == pytest.approx(1.0 * (1 / 3))
    assert row["dependence_ratio"] == pytest.approx((1 / 3) / (1.0 * (1 / 3)))

    # Legacy lr_c retained, not the headline (D63).
    assert row["lr_c"] == pytest.approx((1 / 3) / (1 / 12))


def test_diff_pp_and_dependence_ratio_nan_when_denominators_zero():
    series = pd.DataFrame(
        {
            "country": ["B"] * 4,
            "model": ["m1"] * 4,
            "scenario": ["historical", "historical", "ssp370", "ssp370"],
            "period": ["baseline", "baseline", "future", "future"],
            "month": pd.to_datetime(["1985-01-01", "1985-02-01", "2041-01-01", "2041-02-01"]),
            "s_hydro": [0.0, 0.0, 0.0, 0.0],
            "h_thermal": [0.0, 0.0, 0.0, 0.0],
        }
    )
    thresholds = compound.baseline_thresholds(series, percentile=90)
    flagged = compound.flag_compound_months(series, thresholds)
    summary = compound.compound_summary(flagged)
    row = summary.iloc[0]
    assert row["f_baseline_pct"] == 0.0
    assert row["diff_pp"] == 0.0  # difference stays well-defined, unlike the old lr_c ratio
    assert np.isnan(row["dependence_ratio"])  # independence product is 0/0
    assert np.isnan(row["lr_c"])  # legacy column keeps its old NaN behaviour
