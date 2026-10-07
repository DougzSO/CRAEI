"""Tests of craei.exposure.hedge (E1, D140) on synthetic series."""

import numpy as np
import pytest

from craei.exposure import hedge


def _ar1(n, phi, rng):
    x = np.empty(n)
    x[0] = rng.normal()
    for t in range(1, n):
        x[t] = phi * x[t - 1] + np.sqrt(1 - phi**2) * rng.normal()
    return x


def test_weighted_share_capacity_weights():
    flags = np.array([[1, 0, 1], [0, 0, 1]])
    s = hedge.weighted_share(flags, [3.0, 1.0])
    assert s == pytest.approx([0.75, 0.0, 1.0])


def test_weighted_share_rejects_nan_and_shape():
    with pytest.raises(ValueError):
        hedge.weighted_share(np.array([[np.nan, 1.0]]), [1.0])
    with pytest.raises(ValueError):
        hedge.weighted_share(np.ones((2, 3)), [1.0])


def test_events_strict_and_zero_threshold():
    x = np.array([0.0, 0.0, 0.2, 0.5])
    assert hedge.events(x, 0.0).tolist() == [False, False, True, True]
    assert hedge.events(x, 0.2).tolist() == [False, False, False, True]


def test_perfect_dependence_metrics():
    rng = np.random.default_rng(1)
    x = rng.normal(size=360)
    h = hedge.events(x, hedge.p90_threshold(x))
    m = hedge.joint_metrics(h, h)
    assert m["P_T_given_H"] == pytest.approx(1.0)
    assert m["D"] == pytest.approx(1.0 / m["P_H"])  # P(HT)/(P(H)P(T)) with u = h


def test_independent_series_D_near_one_and_circular_p_large():
    rng = np.random.default_rng(2)
    n = 360 * 20  # long series: D concentrates around 1
    h = rng.random(n) < 0.1
    u = rng.random(n) < 0.1
    m = hedge.joint_metrics(h, u)
    assert m["D"] == pytest.approx(1.0, abs=0.35)
    p = hedge.circular_shift_pvalue(h, u, 500, np.random.default_rng(3))
    assert p > 0.05


def test_circular_p_small_for_dependent_series():
    rng = np.random.default_rng(4)
    x = _ar1(360, 0.6, rng)
    y = 0.8 * x + 0.6 * _ar1(360, 0.6, rng)
    h = hedge.events(x, hedge.p90_threshold(x))
    u = hedge.events(y, hedge.p90_threshold(y))
    assert hedge.joint_metrics(h, u)["D"] > 2
    assert hedge.circular_shift_pvalue(h, u, 1000, np.random.default_rng(5)) < 0.05


def test_undefined_metrics_are_nan_not_zero():
    h = np.zeros(10, dtype=bool)
    u = np.array([1, 0] * 5, dtype=bool)
    m = hedge.joint_metrics(h, u)
    assert np.isnan(m["P_T_given_H"]) and np.isnan(m["D"])
    assert np.isnan(hedge.circular_shift_pvalue(h, u, 10, np.random.default_rng(0), min_lag=2))


def test_decomposition_sums_to_change():
    base = {"P_H": 0.10, "P_T": 0.10, "P_HT": 0.02}
    fut = {"P_H": 0.30, "P_T": 0.25, "P_HT": 0.12}
    d = hedge.decompose_delta(base, fut)
    assert d["dP_HT"] == pytest.approx(0.10)
    assert d["marginal"] + d["dependence"] == pytest.approx(d["dP_HT"])
    assert d["marginal"] == pytest.approx(0.30 * 0.25 - 0.10 * 0.10)


def test_mbb_indices_shape_and_blocks():
    idx = hedge.mbb_indices(360, 12, 50, np.random.default_rng(6))
    assert idx.shape == (50, 360)
    assert idx.min() >= 0 and idx.max() < 360
    assert (np.diff(idx[:, :12], axis=1) == 1).all()  # first block is contiguous
    with pytest.raises(ValueError):
        hedge.mbb_indices(10, 11, 5, np.random.default_rng(0))


def test_bootstrap_variant_a_ci_covers_estimate_and_b_fixes_marginals():
    rng = np.random.default_rng(7)
    x = _ar1(360, 0.5, rng)
    y = 0.7 * x + 0.7 * _ar1(360, 0.5, rng)
    qx, qy = hedge.p90_threshold(x), hedge.p90_threshold(y)
    obs = hedge.joint_metrics(hedge.events(x, qx), hedge.events(y, qy))
    boot = hedge.bootstrap_period(x, y, "A", qx, qy, 12, 500, np.random.default_rng(8))
    lo, hi = hedge.percentile_ci(boot["P_HT"])
    assert lo <= obs["P_HT"] <= hi
    boot_b = hedge.bootstrap_period(x, y, "B", None, None, 12, 200, np.random.default_rng(9))
    assert np.nanmedian(boot_b["P_H"]) == pytest.approx(0.10, abs=0.03)


def test_percentile_ci_all_nan():
    lo, hi = hedge.percentile_ci([np.nan, np.nan])
    assert np.isnan(lo) and np.isnan(hi)
