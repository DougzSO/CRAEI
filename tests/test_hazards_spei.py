import numpy as np
import pandas as pd
import pytest
from scipy import stats

from craei.hazards import spei


def _monthly(id_, model, scenario, start, n_months, values):
    months = pd.date_range(start, periods=n_months, freq="MS")
    return pd.DataFrame(
        {"id": id_, "model": model, "scenario": scenario, "month": months, "D": values}
    )


def test_accumulate_rolling_sum_and_min_periods_nan():
    df = _monthly("p1", "m1", "historical", "1984-01-01", 14, [1.0] * 14)
    out = spei.accumulate(df, window=12, value_col="D")
    assert out["D_acc12"].isna().sum() == 11  # first 11 months have < 12 months of history
    assert out["D_acc12"].iloc[11] == pytest.approx(12.0)
    assert out["D_acc12"].iloc[13] == pytest.approx(12.0)


def test_fit_baseline_raises_if_data_outside_1985_2014():
    rng = np.random.default_rng(0)
    df = _monthly("p1", "m1", "historical", "1984-01-01", 24, rng.normal(0, 50, 24))
    acc = spei.accumulate(df, window=12, value_col="D")
    with pytest.raises(ValueError, match="1985-2014"):
        spei.fit_baseline(acc, "D_acc12", ["id", "model"], spei.loglogistic_fit_fn)


def test_fit_baseline_and_standardize_roundtrip_gives_finite_clipped_index():
    rng = np.random.default_rng(1)
    # 1984 extra history year + full 1985-2014 baseline. Drawn from a
    # log-logistic distribution itself (not e.g. normal) so the PWM fit has
    # a sample it can actually recover -- accumulated water-balance deficits
    # in practice are the skewed shape this index assumes, not symmetric.
    n_months = 12 * 31
    values = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    df = _monthly("p1", "m1", "historical", "1984-01-01", n_months, values)
    acc = spei.accumulate(df, window=12, value_col="D")
    baseline_acc = acc[acc["month"] >= "1985-01-01"]

    fitted = spei.fit_baseline(baseline_acc, "D_acc12", ["id", "model"], spei.loglogistic_fit_fn)
    assert fitted["fit_ok"].all()

    out = spei.standardize(
        baseline_acc, "D_acc12", fitted, ["id", "model"], stats.fisk, clip_bound=3.0, out_col="SPEI_12"
    )
    assert out["SPEI_12"].notna().all()
    assert out["SPEI_12"].between(-3.0, 3.0).all()
    # roughly standard-normal in expectation over a large baseline sample
    assert out["SPEI_12"].mean() == pytest.approx(0.0, abs=0.3)


def test_standardize_leaves_nan_for_failed_fit_group_without_substituting():
    df = _monthly("p1", "m1", "historical", "1985-01-01", 12, [10.0] * 12)
    acc = spei.accumulate(df, window=12, value_col="D")
    fitted = pd.DataFrame(
        [{"id": "p1", "model": "m1", "cal_month": 12, "fit_ok": False, "fit_params": None}]
    )
    out = spei.standardize(acc, "D_acc12", fitted, ["id", "model"], stats.fisk, clip_bound=3.0, out_col="SPEI_12")
    assert out["SPEI_12"].isna().all()


def test_severe_drought_frequency_counts_at_or_below_threshold():
    df = pd.DataFrame(
        {
            "id": ["p1"] * 5,
            "model": ["m1"] * 5,
            "SPEI_12": [-2.0, -1.5, -1.0, np.nan, 0.5],
        }
    )
    out = spei.severe_drought_frequency(df, "SPEI_12", threshold=-1.5, group_cols=["id", "model"])
    row = out.iloc[0]
    assert row["n_months"] == 4  # NaN excluded
    assert row["n_severe"] == 2  # -2.0 and -1.5
    assert row["F_D"] == pytest.approx(0.5)
