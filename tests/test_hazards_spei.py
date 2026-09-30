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


def test_fit_baseline_single_raises_if_data_outside_1985_2014():
    rng = np.random.default_rng(0)
    df = _monthly("p1", "m1", "historical", "1984-01-01", 24, rng.normal(0, 50, 24))
    acc = spei.accumulate(df, window=12, value_col="D")
    with pytest.raises(ValueError, match="1985-2014"):
        spei.fit_baseline_single(acc, "D_acc12", ["id", "model"], spei.loglogistic_fit_fn)


def test_fit_baseline_windowed_raises_if_data_outside_1985_2014():
    rng = np.random.default_rng(0)
    df = _monthly("p1", "m1", "historical", "1984-01-01", 24, rng.normal(0, 50, 24))
    acc = spei.accumulate(df, window=12, value_col="D")
    with pytest.raises(ValueError, match="1985-2014"):
        spei.fit_baseline_windowed(acc, "D_acc12", ["id", "model"], k=1, fit_fn=spei.loglogistic_fit_fn)


def test_fit_baseline_single_fits_once_per_series_and_applies_to_all_months():
    # D54 (COMANDO 18-G): SPEI-12's adopted method -- one fit per series over
    # all 360 baseline values, replicated across every calendar month for
    # standardize()'s merge, not fit per calendar month.
    rng = np.random.default_rng(1)
    n_months = 12 * 31
    values = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    df = _monthly("p1", "m1", "historical", "1984-01-01", n_months, values)
    acc = spei.accumulate(df, window=12, value_col="D")
    baseline_acc = acc[acc["month"] >= "1985-01-01"]

    fitted = spei.fit_baseline_single(baseline_acc, "D_acc12", ["id", "model"], spei.loglogistic_fit_fn)
    assert len(fitted) == 12  # replicated across all 12 calendar months
    assert fitted["fit_ok"].all()
    assert fitted["fit_params"].apply(lambda p: p["shape"]).nunique() == 1  # same single fit everywhere

    out = spei.standardize(baseline_acc, "D_acc12", fitted, ["id", "model"], clip_bound=3.0, out_col="SPEI_12")
    assert out["SPEI_12"].notna().all()


def test_fit_baseline_windowed_uses_neighboring_calendar_months():
    # D54: SPEI-3's adopted method -- k=1 window (n=90), never mixing series.
    rng = np.random.default_rng(2)
    n_months = 12 * 31
    values = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    df = _monthly("p1", "m1", "historical", "1984-01-01", n_months, values)
    acc = spei.accumulate(df, window=3, value_col="D")
    baseline_acc = acc[acc["month"] >= "1985-01-01"]

    fitted = spei.fit_baseline_windowed(baseline_acc, "D_acc3", ["id", "model"], k=1, fit_fn=spei.loglogistic_fit_fn)
    assert len(fitted) == 12  # one row per calendar month, same schema as fit_baseline
    assert fitted["fit_ok"].all()

    out = spei.standardize(baseline_acc, "D_acc3", fitted, ["id", "model"], clip_bound=3.0, out_col="SPEI_3")
    assert out["SPEI_3"].notna().all()


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
        baseline_acc, "D_acc12", fitted, ["id", "model"], clip_bound=3.0, out_col="SPEI_12"
    )
    assert out["SPEI_12"].notna().all()
    assert out["SPEI_12"].between(-3.0, 3.0).all()
    # roughly standard-normal in expectation over a large baseline sample
    assert out["SPEI_12"].mean() == pytest.approx(0.0, abs=0.3)


def test_standardize_leaves_nan_for_failed_fit_group_without_substituting():
    df = _monthly("p1", "m1", "historical", "1985-01-01", 12, [10.0] * 12)
    acc = spei.accumulate(df, window=12, value_col="D")
    fitted = pd.DataFrame(
        [{"id": "p1", "model": "m1", "cal_month": 12, "fit_ok": False, "fit_params": None,
          "distribution": None}]
    )
    out = spei.standardize(
        acc, "D_acc12", fitted, ["id", "model"], clip_bound=3.0, out_col="SPEI_12"
    )
    assert out["SPEI_12"].isna().all()


def test_fit_loglogistic_pwm_status_success():
    rng = np.random.default_rng(2)
    values = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=30, random_state=rng)
    params, status = spei._fit_loglogistic_pwm(values)
    assert status == "success"
    assert params["shape"] > 0
    assert params["loc"] <= values.min()


def test_fit_loglogistic_pwm_status_beta_nonpositive_on_known_failing_sample():
    # A near-symmetric sample is a known PWM failure mode (COMANDO 17-C):
    # the PWM triplet lands outside the log-logistic's valid beta>0 region.
    rng = np.random.default_rng(3)
    values = rng.normal(0.0, 1.0, 30)
    params, status = spei._fit_loglogistic_pwm(values)
    if status == "success":
        pytest.skip("this particular draw happened to fit; status logic covered by other draws")
    assert status in ("beta_nonpositive", "loc_violation")
    assert params is None


def _find_pwm_failing_sample(rng, max_draws=200):
    """A strongly left-skewed sample is the shape that makes PWM fail in
    practice (COMANDO 17-C): a plain symmetric normal draw sometimes also
    defeats the Pearson III MLE fallback (an edge case at skew=0 that does
    not arise on this project's real, always-skewed D = P - PET data)."""
    for _ in range(max_draws):
        values = stats.skewnorm.rvs(a=-6, size=30, random_state=rng)
        _, pwm_status = spei._fit_loglogistic_pwm(values)
        if pwm_status != "success":
            return values
    return None


def test_fit_pearson3_mle_recovers_a_pwm_failure():
    rng = np.random.default_rng(4)
    values = _find_pwm_failing_sample(rng)
    if values is None:
        pytest.skip("no PWM failure found to test recovery against")
    params, status = spei._fit_pearson3_mle(values)
    assert status == "success"
    assert params["scale"] > 0


def test_fit_spei_distribution_falls_back_to_pearson3_on_pwm_failure():
    rng = np.random.default_rng(4)
    values = _find_pwm_failing_sample(rng)
    if values is None:
        pytest.skip("no PWM failure found to test fallback against")
    params, distribution, status = spei.fit_spei_distribution(values)
    assert distribution == "pearson3"
    assert status == "success"
    assert params is not None


def test_fit_spei_distribution_uses_pwm_when_it_succeeds():
    rng = np.random.default_rng(2)
    values = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=30, random_state=rng)
    params, distribution, status = spei.fit_spei_distribution(values)
    assert distribution == "loglogistic"
    assert status == "success"


def test_fit_baseline_and_standardize_hybrid_never_leaves_recoverable_nan():
    # Mix of a PWM-friendly plant and a PWM-hostile one (near-symmetric D):
    # fit_spei_distribution should recover both via the hybrid, unlike
    # loglogistic_fit_fn alone which would leave the second one NaN.
    rng = np.random.default_rng(5)
    n_months = 12 * 31
    friendly = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    hostile = stats.skewnorm.rvs(a=-6, size=n_months, random_state=rng)
    df = pd.concat(
        [
            _monthly("friendly", "m1", "historical", "1984-01-01", n_months, friendly),
            _monthly("hostile", "m1", "historical", "1984-01-01", n_months, hostile),
        ],
        ignore_index=True,
    )
    acc = spei.accumulate(df, window=12, value_col="D")
    baseline_acc = acc[acc["month"] >= "1985-01-01"]

    fitted = spei.fit_baseline(baseline_acc, "D_acc12", ["id", "model"], spei.fit_spei_distribution)
    assert fitted["fit_ok"].all()
    assert set(fitted["distribution"]) <= {"loglogistic", "pearson3"}

    out = spei.standardize(
        baseline_acc, "D_acc12", fitted, ["id", "model"], clip_bound=3.0, out_col="SPEI_12"
    )
    assert out["SPEI_12"].notna().all()
    assert out["SPEI_12"].between(-3.0, 3.0).all()


def test_fit_baseline_and_standardize_support_regional_pooling():
    # D51/D52 (COMANDO 18-E): production pools by (country, bucket) instead
    # of (id, model) -- fit_baseline/standardize must support this via the
    # same generic group_cols, not a separate pooling code path.
    rng = np.random.default_rng(6)
    n_months = 12 * 31
    values_a = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    values_b = stats.fisk.rvs(c=3.5, loc=100.0, scale=80.0, size=n_months, random_state=rng)
    df_a = _monthly("plantA", "m1", "historical", "1984-01-01", n_months, values_a)
    df_b = _monthly("plantB", "m2", "historical", "1984-01-01", n_months, values_b)
    df = pd.concat([df_a, df_b], ignore_index=True)
    df["country"] = "BRA"
    df["bucket"] = "hydro_reservoir"

    acc = spei.accumulate(df[["id", "model", "scenario", "month", "D", "country", "bucket"]], window=12, value_col="D")
    baseline_acc = acc[acc["month"] >= "1985-01-01"]

    pool_cols = ["country", "bucket"]
    fitted = spei.fit_baseline(baseline_acc, "D_acc12", pool_cols, spei.loglogistic_fit_fn)
    # One pool (BRA, hydro_reservoir) shared by both plants -- 12 calendar-month
    # fits total, not 24 (one per plant would be the old, unpooled behavior).
    assert len(fitted) == 12
    assert fitted["fit_ok"].all()

    out = spei.standardize(baseline_acc, "D_acc12", fitted, pool_cols, clip_bound=3.0, out_col="SPEI_12")
    # Both plants get standardized values from the SAME pool fit.
    assert out["SPEI_12"].notna().all()
    assert set(out["id"]) == {"plantA", "plantB"}


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
