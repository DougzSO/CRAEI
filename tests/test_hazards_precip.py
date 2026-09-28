import numpy as np
import pandas as pd
import pytest

from craei.hazards import precip


def _baseline_and_future(pr_values):
    n = len(pr_values)
    dates = pd.date_range("2000-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "cell_lat": ["A"] * n,
            "cell_lon": ["A"] * n,
            "model": ["gfdl-esm4"] * n,
            "scenario": ["historical"] * n,
            "period": ["baseline"] * n,
            "pr_mm": pr_values,
        }
    )


def test_wet_day_p95_ignores_dry_days():
    wet = list(range(1, 101))  # 1..100 mm, all wet
    dry = [0.0, 0.5, 0.9]  # below the 1mm wet-day threshold
    daily = _baseline_and_future(dry + wet)

    out = precip.wet_day_p95(daily, percentile=95)
    p95 = out.iloc[0]["p95_mm"]
    assert p95 == pytest.approx(np.percentile(wet, 95))


def test_wet_day_p95_unaffected_by_future_rows():
    wet = list(range(1, 101))
    baseline = _baseline_and_future(wet)
    before = precip.wet_day_p95(baseline, percentile=95).iloc[0]["p95_mm"]

    future = baseline.copy()
    future["period"] = "future"
    future["pr_mm"] = future["pr_mm"] * 1000.0  # wildly different future values
    combined = pd.concat([baseline, future], ignore_index=True)

    after = precip.wet_day_p95(combined, percentile=95).iloc[0]["p95_mm"]
    assert after == before


def test_exceedance_frequency_near_five_percent_by_construction():
    wet = list(range(1, 101))
    baseline = _baseline_and_future(wet)
    p95 = precip.wet_day_p95(baseline, percentile=95)

    out = precip.exceedance_frequency(baseline, p95)
    freq = out.iloc[0]["exceedance_frequency"]
    assert 0.04 <= freq <= 0.06


def test_annual_rx5day_picks_max_five_day_window():
    values = [0.0] * 10
    values[3:8] = [10.0, 20.0, 5.0, 5.0, 5.0]  # window sum = 45, the max window
    daily = _baseline_and_future(values)

    out = precip.annual_rx5day(daily)
    assert out.iloc[0]["value"] == 45.0
