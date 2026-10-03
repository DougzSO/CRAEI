"""Tests for craei.hazards.heat_relative (TH1, D91)."""

import pandas as pd
import pytest

from craei.hazards import heat_relative as hr

GROUP = ["cell_lat", "cell_lon", "model"]


def _daily(values, cell=(1.0, 2.0), model="m1", start="2000-01-01"):
    dates = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({
        "date": dates, "cell_lat": cell[0], "cell_lon": cell[1],
        "model": model, "tasmax_c": values,
    })


def test_baseline_percentile_threshold_simple():
    df = _daily(list(range(1, 101)))  # 1..100, p95 of 1..100 (linear interp)
    thr = hr.baseline_percentile_threshold(df, 95.0, GROUP)
    assert len(thr) == 1
    assert thr.loc[0, "threshold_c"] == pytest.approx(df["tasmax_c"].quantile(0.95))


def test_annual_days_at_or_above_counts_correctly():
    df = _daily([10.0] * 5 + [40.0] * 3 + [10.0] * 2)  # 3 days >= 40 in one year
    thr = pd.DataFrame({"cell_lat": [1.0], "cell_lon": [2.0], "model": ["m1"],
                         "threshold_c": [40.0]})
    out = hr.annual_days_at_or_above(df.assign(scenario="s", period="p"), thr, GROUP)
    assert len(out) == 1
    assert out.loc[0, "value"] == 3


def test_annual_days_at_or_above_raises_on_missing_threshold():
    df = _daily([10.0, 20.0], model="unknown")
    thr = pd.DataFrame({"cell_lat": [1.0], "cell_lon": [2.0], "model": ["m1"],
                         "threshold_c": [15.0]})
    with pytest.raises(ValueError, match="without a matching threshold"):
        hr.annual_days_at_or_above(df.assign(scenario="s", period="p"), thr, GROUP)


def test_baseline_exceedance_fraction_matches_definition():
    df = _daily([10.0] * 95 + [40.0] * 5)  # 100 days, 5 at/above 40 -> 5%
    thr = pd.DataFrame({"cell_lat": [1.0], "cell_lon": [2.0], "model": ["m1"],
                         "threshold_c": [40.0]})
    out = hr.baseline_exceedance_fraction(df, thr, GROUP)
    assert out.loc[0, "fraction"] == pytest.approx(0.05)


def test_annual_days_at_or_above_reproduces_fixed_threshold_logic():
    """Same logic as craei.hazards.heat.annual_hot_day_counts with a fixed cut,
    expressed as a per-group threshold of the same constant value."""
    from craei.hazards import heat

    df = _daily([30.0, 36.0, 34.0, 37.0, 20.0])
    direct = heat.annual_hot_day_counts(df, 35.0)
    thr = pd.DataFrame({"cell_lat": [1.0], "cell_lon": [2.0], "model": ["m1"],
                         "threshold_c": [35.0]})
    via_group = hr.annual_days_at_or_above(df.assign(scenario="s", period="p"), thr, GROUP)
    assert direct["value"].iloc[0] == via_group["value"].iloc[0]