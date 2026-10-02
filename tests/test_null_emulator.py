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

def test_percentile_row_keys_and_values():
    row = ne.percentile_row(np.arange(101.0))
    assert list(row) == ["p50", "p75", "p90", "p95", "p99"]
    assert row["p90"] == pytest.approx(90.0)


def test_rd_bins_known_case():
    out = ne.rd_bins([5, 5, 0, 10], [10, 5, 3, 40])
    assert out["n_defined"] == 3
    assert out["undefined_pct"] == 25.0
    assert out["rd_lt_1p5"] == pytest.approx(33.33)
    assert out["rd_1p5_2"] == 0.0
    assert out["rd_2_3"] == pytest.approx(33.33)
    assert out["rd_ge_3"] == pytest.approx(33.33)
    assert out["rd_ge_2"] == pytest.approx(66.67)


def test_real_baseline_stats_halves():
    z = np.random.default_rng(3).normal(size=(3, 372))
    z[:, :11] = np.nan
    tot, h1, h2 = ne.real_baseline_stats(z)
    assert tot == pytest.approx((z[:, 12:] <= -1.5).mean(axis=1) * 100)
    assert h1 == pytest.approx((z[:, 12:192] <= -1.5).mean(axis=1) * 100)
    assert h2 == pytest.approx((z[:, 192:] <= -1.5).mean(axis=1) * 100)


def test_fidelity_stats_self_consistent():
    d_all = np.random.default_rng(7).normal(20.0, 60.0, size=(3, 372))
    stored, labels = [], []
    for d in d_all:
        acc = ne.accumulate(d)
        params, dist, _ = ne.fit_quiet(acc[1:])
        stored.append(np.concatenate([np.full(11, np.nan),
                                      ne.standardize_acc(acc, dist, params)]))
        labels.append(dist)
    n_fail, n_label, max_z, max_fd = ne.fidelity_stats(d_all, stored, labels)
    assert (n_fail, n_label) == (0, 0)
    assert max_z < 1e-9
    assert max_fd < 1e-9