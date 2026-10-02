import numpy as np
import pytest

from craei.hazards import null_emulator as ne


def _pool(n=4, seed=1):
    return np.random.default_rng(seed).normal(20.0, 60.0, size=(n, 360))


def test_accumulate_values_and_length():
    out = ne.accumulate(np.arange(24))
    assert len(out) == 13
    assert out[0] == 66.0


def test_resample_year_blocks_are_whole_years():
    src = np.arange(360.0)
    out = ne.resample_months(src, 31, "year", np.random.default_rng(2))
    assert out.size == 372
    for b in out.reshape(31, 12):
        assert b[0] % 12 == 0
        assert np.array_equal(b, np.arange(b[0], b[0] + 12))


def test_resample_anystart_blocks_are_contiguous():
    src = np.arange(360.0)
    out = ne.resample_months(src, 30, "anystart", np.random.default_rng(3))
    assert out.size == 360
    for b in out.reshape(30, 12):
        assert b[0] <= 348
        assert np.array_equal(b, np.arange(b[0], b[0] + 12))


def test_resample_unknown_variant():
    with pytest.raises(ValueError):
        ne.resample_months(np.arange(360.0), 3, "other", np.random.default_rng(1))


def test_fit_window_is_standardised():
    acc = ne.accumulate(_pool()[0])
    params, dist, _ = ne.fit_quiet(acc[1:])
    z = ne.standardize_acc(acc[1:], dist, params)
    assert abs(float(np.mean(z))) < 0.3


def test_simulate_reproducible_and_bounded():
    a = ne.simulate_emulated(_pool(), "year", 20, np.random.default_rng(5))
    b = ne.simulate_emulated(_pool(), "year", 20, np.random.default_rng(5))
    assert np.array_equal(a["fd_fut"], b["fd_fut"])
    assert len(a["fd_base"]) + a["n_fail"] == 20
    assert np.all((a["fd_base"] >= 0) & (a["fd_base"] <= 100))


def test_rd_rates_known_case():
    rates, undef = ne.rd_rates([5, 5, 0, 10], [10, 5, 3, 40])
    assert rates == pytest.approx([66.67, 66.67, 33.33])
    assert undef == 25.0


def test_passes_validation_rule():
    assert ne.passes_validation(1.42, -0.723, 1.23, -0.797)
    assert not ne.passes_validation(1.59, -0.687, 1.23, -0.797)