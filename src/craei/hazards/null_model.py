"""Null models for the R_D >= 2 false-positive rate (W4a; D76, D83).

Pure functions, no I/O. Every simulation draws the baseline series first and the
future series second, per simulation, exactly as scripts/c23d_checks.py did, so
that default_rng(23) reproduces the c23d rates (block 12: 18.88%, white noise 1.80%).
"""

import numpy as np
import pandas as pd


def build_series_pool(spei_baseline, ids, n_months, value_col="SPEI_12"):
    """Pool of (id, model) series: NaN dropped, last n_months kept, short ones skipped.

    `spei_baseline` must already be restricted to the baseline period.
    Returns (list of 1D arrays, list of (id, model) keys), in sorted key order.
    """
    sub = spei_baseline[spei_baseline["id"].isin(set(ids))]
    pool, keys = [], []
    for (sid, model), g in sub.groupby(["id", "model"]):
        x = g.sort_values("month")[value_col].to_numpy(dtype=float)
        x = x[~np.isnan(x)]
        if len(x) >= n_months:
            pool.append(x[-n_months:])
            keys.append((sid, model))
    return pool, keys


def _check_block(n_months, block):
    if block <= 0 or n_months % block != 0:
        raise ValueError(f"block {block} must divide n_months {n_months}")


def block_series(pool, n_months, block, rng):
    """One series: a random pool member, resampled in contiguous blocks."""
    base_series = pool[rng.integers(0, len(pool))]
    n_blocks = n_months // block
    starts = rng.integers(0, len(base_series) - block + 1, size=n_blocks)
    return np.concatenate([base_series[s:s + block] for s in starts])


def white_noise_series(n_months, window, rng):
    """Standardized moving sum (length `window`) of white noise."""
    noise = rng.normal(0, 1, size=n_months + window - 1)
    roll = np.convolve(noise, np.ones(window), mode="valid")
    return (roll - roll.mean()) / roll.std()


def simulate_block_bootstrap(pool, n_sim, n_months, block, rng):
    """(baseline, future) arrays, each (n_sim, n_months)."""
    _check_block(n_months, block)
    base = np.empty((n_sim, n_months))
    fut = np.empty((n_sim, n_months))
    for i in range(n_sim):
        base[i] = block_series(pool, n_months, block, rng)
        fut[i] = block_series(pool, n_months, block, rng)
    return base, fut


def simulate_white_noise(n_sim, n_months, window, rng):
    """(baseline, future) arrays of standardized moving sums of white noise."""
    base = np.empty((n_sim, n_months))
    fut = np.empty((n_sim, n_months))
    for i in range(n_sim):
        base[i] = white_noise_series(n_months, window, rng)
        fut[i] = white_noise_series(n_months, window, rng)
    return base, fut


def estimate_phi(pool):
    """Mean lag-1 autocorrelation over the series in the pool."""
    return float(np.mean([np.corrcoef(x[:-1], x[1:])[0, 1] for x in pool]))


def _ar1(n_series, n_months, phi, rng):
    sd = np.sqrt(1.0 - phi**2)
    x = np.empty((n_series, n_months))
    x[:, 0] = rng.normal(0.0, 1.0, size=n_series)
    eps = rng.normal(0.0, sd, size=(n_series, n_months))
    for t in range(1, n_months):
        x[:, t] = phi * x[:, t - 1] + eps[:, t]
    return x


def simulate_ar1(n_sim, n_months, phi, rng):
    """Stationary AR(1), unit variance, no climate change: (baseline, future)."""
    if not 0.0 <= phi < 1.0:
        raise ValueError("phi must be in [0, 1)")
    base = _ar1(n_sim, n_months, phi, rng)
    fut = _ar1(n_sim, n_months, phi, rng)
    return base, fut


def null_rate_table(base, fut, spei_thresholds, rd_thresholds):
    """Share of simulations with R_D >= rd_threshold, explicit denominator.

    R_D is undefined when baseline F_D is 0; those simulations are excluded
    from the denominator and counted in n_rd_undefined.
    """
    n_sim, n_months = base.shape
    rows = []
    for th in spei_thresholds:
        fd_b = (base <= th).sum(axis=1) / n_months
        fd_f = (fut <= th).sum(axis=1) / n_months
        defined = fd_b > 0
        rd = fd_f[defined] / fd_b[defined]
        for rth in rd_thresholds:
            n_ge = int((rd >= rth).sum())
            rows.append({
                "spei_threshold": float(th), "rd_threshold": float(rth),
                "n_sim": int(n_sim), "n_rd_defined": int(defined.sum()),
                "n_rd_undefined": int((~defined).sum()), "n_rd_ge": n_ge,
                "pct_rd_ge": 100.0 * n_ge / int(defined.sum()) if defined.any() else np.nan,
                "mean_fd_baseline_pct": 100.0 * float(fd_b.mean()),
                "pct_fd_baseline_zero": 100.0 * float((~defined).mean()),
            })
    return pd.DataFrame(rows)