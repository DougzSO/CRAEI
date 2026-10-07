"""E1 hydrothermal hedge metrics (D140, docs/article/E1_spec.md). Pure functions, no I/O.

A series x_t (share of hydro capacity in drought, share of thermal capacity under stress) becomes
an event e_t = 1[x_t > q]. Variant A: q is the baseline P90 of the same GCM, applied to every period.
Variant B: q is the P90 of the period's own series. From the two event series h_t and u_t:
P(H), P(T), P(H and T), P(T|H) and D = P(H and T) / (P(H) P(T)); undefined values are NaN, never 0.
Inference: moving-block bootstrap of the paired series and a circular-shift test of D > 1.
"""

import numpy as np

Q_EVENT = 0.9
METRICS = ("P_H", "P_T", "P_HT", "P_T_given_H", "D")


def weighted_share(flags, weights):
    """Capacity-weighted share per month: `flags` (n_units, n_months) bool, `weights` (n_units,)."""
    f = np.asarray(flags, dtype=float)
    w = np.asarray(weights, dtype=float)
    if f.ndim != 2 or f.shape[0] != w.shape[0]:
        raise ValueError("flags must be (n_units, n_months) and match weights")
    if np.isnan(f).any():
        raise ValueError("NaN in flags")
    if w.sum() <= 0:
        raise ValueError("weights must sum to a positive value")
    return (w[:, None] * f).sum(axis=0) / w.sum()


def p90_threshold(series, q=Q_EVENT):
    """Percentile q of a series (linear interpolation)."""
    return float(np.quantile(np.asarray(series, dtype=float), q))


def events(series, threshold):
    """Strict exceedance: x_t > threshold (a zero threshold means any positive value)."""
    return np.asarray(series, dtype=float) > threshold


def joint_metrics(h, u):
    """P(H), P(T), P(H and T), P(T|H), D from two boolean series (1-D or (n_sim, n))."""
    h = np.asarray(h, dtype=float)
    u = np.asarray(u, dtype=float)
    n = h.shape[-1]
    p_h, p_t = h.sum(axis=-1) / n, u.sum(axis=-1) / n
    p_ht = (h * u).sum(axis=-1) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        p_t_h = np.where(p_h > 0, p_ht / p_h, np.nan)
        d = np.where((p_h > 0) & (p_t > 0), p_ht / (p_h * p_t), np.nan)
    return {"P_H": p_h, "P_T": p_t, "P_HT": p_ht, "P_T_given_H": p_t_h, "D": d}


def decompose_delta(base, fut):
    """dP(HT) split into a marginal part and a dependence part (they sum to the change).

    marginal   = P_f(H) P_f(T) - P_b(H) P_b(T)
    dependence = (P_f(HT) - P_f(H) P_f(T)) - (P_b(HT) - P_b(H) P_b(T))
    """
    marg = fut["P_H"] * fut["P_T"] - base["P_H"] * base["P_T"]
    dep = (fut["P_HT"] - fut["P_H"] * fut["P_T"]) - (base["P_HT"] - base["P_H"] * base["P_T"])
    return {"dP_HT": fut["P_HT"] - base["P_HT"], "marginal": marg, "dependence": dep}


def mbb_indices(n, block, n_sim, rng):
    """Moving-block bootstrap indices, shape (n_sim, n): random block starts, blocks of `block`."""
    if block <= 0 or block > n:
        raise ValueError("block must be in 1..n")
    n_blocks = -(-n // block)
    starts = rng.integers(0, n - block + 1, size=(n_sim, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_sim, -1)
    return idx[:, :n]


def _metrics_from_series(hs, ts, qh, qt):
    """Metrics of resampled series; thresholds fixed (variant A) or per resample (None -> B)."""
    qh = np.quantile(hs, Q_EVENT, axis=-1, keepdims=True) if qh is None else qh
    qt = np.quantile(ts, Q_EVENT, axis=-1, keepdims=True) if qt is None else qt
    return joint_metrics(hs > qh, ts > qt)


def bootstrap_period(h_series, t_series, variant, q_h, q_t, block, n_sim, rng):
    """Bootstrap distribution of the metrics of one period (paired resampling of both series).

    variant "A": thresholds q_h, q_t are fixed (the baseline P90). Variant "B": recomputed on each
    resample from the resampled series.
    """
    h_series = np.asarray(h_series, dtype=float)
    t_series = np.asarray(t_series, dtype=float)
    idx = mbb_indices(len(h_series), block, n_sim, rng)
    hs, ts = h_series[idx], t_series[idx]
    if variant == "A":
        return _metrics_from_series(hs, ts, q_h, q_t)
    return _metrics_from_series(hs, ts, None, None)


def percentile_ci(values, level=95.0):
    """(lo, hi) percentile interval ignoring NaN; (NaN, NaN) if nothing is defined."""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size == 0:
        return (np.nan, np.nan)
    a = (100 - level) / 2
    return (float(np.percentile(v, a)), float(np.percentile(v, 100 - a)))


def circular_shift_pvalue(h, u, n_sim, rng, min_lag=12):
    """One-sided p-value of D > 1: shift u circularly by random lags in [min_lag, n - min_lag].

    The shift keeps the autocorrelation of both series and breaks their pairing.
    p = (1 + #{D_null >= D_obs}) / (1 + n_sim); NaN if D_obs is undefined.
    """
    h = np.asarray(h, dtype=bool)
    u = np.asarray(u, dtype=bool)
    n = len(h)
    d_obs = joint_metrics(h, u)["D"]
    if np.isnan(d_obs):
        return float("nan")
    lags = rng.integers(min_lag, n - min_lag + 1, size=n_sim)
    shifted = u[(np.arange(n)[None, :] + lags[:, None]) % n]
    d_null = joint_metrics(np.broadcast_to(h, shifted.shape), shifted)["D"]
    ge = np.nansum(d_null >= d_obs - 1e-12)
    return float((1 + ge) / (1 + n_sim))
