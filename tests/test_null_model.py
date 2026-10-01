import numpy as np
import pandas as pd
import pytest

from craei.hazards import null_model as nm


def _row(k, n=10, v=-2.0):
    r = np.zeros(n)
    r[:k] = v
    return r


def test_block_bootstrap_blocks_are_contiguous():
    pool = [np.arange(400, dtype=float)]
    base, fut = nm.simulate_block_bootstrap(pool, 5, 360, 12, np.random.default_rng(1))
    assert base.shape == fut.shape == (5, 360)
    for arr in (base, fut):
        assert np.all(np.diff(arr.reshape(5, 30, 12), axis=2) == 1.0)


def test_block_bootstrap_requires_divisible_block():
    with pytest.raises(ValueError):
        nm.simulate_block_bootstrap([np.zeros(400)], 1, 360, 7, np.random.default_rng(1))


def test_block_bootstrap_draw_order_baseline_then_future():
    pool = [np.arange(400, dtype=float), np.arange(400, dtype=float) * 2]
    base, fut = nm.simulate_block_bootstrap(pool, 3, 360, 12, np.random.default_rng(5))
    rng = np.random.default_rng(5)
    for i in range(3):
        assert np.array_equal(base[i], nm.block_series(pool, 360, 12, rng))
        assert np.array_equal(fut[i], nm.block_series(pool, 360, 12, rng))


def test_white_noise_series_standardized():
    base, fut = nm.simulate_white_noise(20, 360, 12, np.random.default_rng(2))
    for a in (base, fut):
        assert np.allclose(a.mean(axis=1), 0.0, atol=1e-12)
        assert np.allclose(a.std(axis=1), 1.0, atol=1e-12)


def test_ar1_recovers_phi_and_unit_variance():
    base, _ = nm.simulate_ar1(200, 360, 0.8, np.random.default_rng(3))
    assert abs(nm.estimate_phi(list(base)) - 0.8) < 0.03
    assert abs(base.std() - 1.0) < 0.05


def test_ar1_rejects_nonstationary_phi():
    with pytest.raises(ValueError):
        nm.simulate_ar1(2, 10, 1.0, np.random.default_rng(1))


def test_rate_table_explicit_denominator():
    base = np.array([_row(0), _row(1), _row(2), _row(1)])
    fut = np.array([_row(5), _row(2), _row(3), _row(1)])
    r = nm.null_rate_table(base, fut, [-1.5], [2.0]).iloc[0]
    assert (r.n_sim, r.n_rd_defined, r.n_rd_undefined, r.n_rd_ge) == (4, 3, 1, 1)
    assert r.pct_rd_ge == pytest.approx(100 / 3)
    assert r.pct_fd_baseline_zero == 25.0
    assert r.mean_fd_baseline_pct == pytest.approx(10.0)


def test_build_series_pool_last_n_months_and_filters():
    months = pd.date_range("1984-01-01", periods=362, freq="MS")
    vals = np.arange(362, dtype=float)
    vals[:2] = np.nan
    full = pd.DataFrame({"id": "a", "model": "m1", "month": months, "SPEI_12": vals})
    short = pd.DataFrame({"id": "a", "model": "m3", "month": months[:100],
                          "SPEI_12": np.arange(100, dtype=float)})
    df = pd.concat([full, full.assign(model="m2"), short, full.assign(id="z")])
    df = df.sample(frac=1.0, random_state=0)
    pool, keys = nm.build_series_pool(df, ["a"], 360)
    assert keys == [("a", "m1"), ("a", "m2")]
    assert np.array_equal(pool[0], np.arange(2, 362, dtype=float))