"""Emulated drought null (O34): resample D, refit SPEI-12, score baseline and future.

Mimics the real pipeline: the distribution is fitted once on the last 360 months of
the 372-month baseline accumulation and applied unchanged to baseline and future.
Exposure only; this is a null of internal variability without climate change.
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy.stats import norm

from craei.hazards.spei import DIST_BY_NAME, fit_spei_distribution

THRESHOLD = -1.5
WINDOW = 12
N_BASE_BLOCKS = 31
N_FUT_BLOCKS = 30
VARIANTS = ("year", "anystart")
SD_TOL = 0.20
CORR_TOL = 0.10


def accumulate(d):
    """12-month rolling sum, valid windows only (len(d) - 11 values)."""
    return np.convolve(np.asarray(d, dtype=float), np.ones(WINDOW), "valid")


def fit_quiet(x):
    """fit_spei_distribution without warnings; returns (params, dist, info)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fit_spei_distribution(np.asarray(x, dtype=float))


def standardize_acc(acc, dist, params):
    """Standard-normal score of accumulated D under a fitted distribution."""
    cdf = DIST_BY_NAME[dist].cdf(acc, params["shape"], params["loc"], params["scale"])
    return norm.ppf(np.clip(cdf, 1e-10, 1 - 1e-10))


def fd_pct(z, threshold=THRESHOLD):
    """Percent of finite values at or below the threshold."""
    z = np.asarray(z, dtype=float)
    z = z[np.isfinite(z)]
    if z.size == 0:
        return float("nan")
    return float((z <= threshold).mean() * 100)


def resample_months(src, n_blocks, variant, rng):
    """Concatenate n_blocks blocks of 12 months drawn from src (len multiple of 12)."""
    src = np.asarray(src, dtype=float)
    if variant == "year":
        years = src.reshape(-1, WINDOW)
        return years[rng.integers(0, years.shape[0], size=n_blocks)].reshape(-1)
    if variant == "anystart":
        starts = rng.integers(0, src.size - WINDOW + 1, size=n_blocks)
        return np.concatenate([src[s:s + WINDOW] for s in starts])
    raise ValueError(f"unknown variant: {variant}")


def emulate_series(d_base, d_fut):
    """Fit on baseline (drop first valid window), score both periods.

    Returns (fd_base, fd_fut, fd_half1, fd_half2) in percent, or None if the fit fails.
    """
    acc_b, acc_f = accumulate(d_base), accumulate(d_fut)
    params, dist, _ = fit_quiet(acc_b[1:])
    if params is None:
        return None
    zb = standardize_acc(acc_b, dist, params)[1:]
    zf = standardize_acc(acc_f, dist, params)
    half = zb.size // 2
    return fd_pct(zb), fd_pct(zf), fd_pct(zb[:half]), fd_pct(zb[half:])


def simulate_emulated(pool, variant, n_sim, rng):
    """pool: (n_series, 360) monthly D of 1985-2014. One random series per draw."""
    rows, n_fail = [], 0
    for _ in range(n_sim):
        i = int(rng.integers(0, pool.shape[0]))
        res = emulate_series(
            resample_months(pool[i], N_BASE_BLOCKS, variant, rng),
            resample_months(pool[i], N_FUT_BLOCKS, variant, rng),
        )
        if res is None:
            n_fail += 1
        else:
            rows.append((i,) + res)
    arr = np.array(rows, dtype=float).reshape(-1, 5)
    return {"series": arr[:, 0].astype(int), "fd_base": arr[:, 1], "fd_fut": arr[:, 2],
            "fd_h1": arr[:, 3], "fd_h2": arr[:, 4], "n_fail": n_fail}


def validation_metrics(sim):
    """(sd of baseline F_D across draws, corr between its two halves)."""
    sd = float(np.std(sim["fd_base"], ddof=1))
    corr = float(np.corrcoef(sim["fd_h1"], sim["fd_h2"])[0, 1])
    return sd, corr


def passes_validation(sd, corr, real_sd, real_corr):
    """Rule fixed before running: |d sd| <= 0.20 and |d corr| <= 0.10."""
    return abs(sd - real_sd) <= SD_TOL and abs(corr - real_corr) <= CORR_TOL


def rd_rates(fd_base, fd_fut, ks=(1.5, 2.0, 3.0)):
    """% of defined draws with R_D >= k, and % undefined (baseline F_D == 0)."""
    fd_base, fd_fut = np.asarray(fd_base, float), np.asarray(fd_fut, float)
    ok = fd_base > 0
    ratio = fd_fut[ok] / fd_base[ok]
    rates = [round(float((ratio >= k).mean() * 100), 2) for k in ks]
    return rates, round(float((~ok).mean() * 100), 2)