"""W3f-3: paired scenario contrast of heat shares with the cell bootstrap (D86, O25).

Same resampling as W3d (cells, default_rng([seed, group index]), same call order), so
the draws are those of w3_heat_bootstrap_shares. The contrast is the median over GCMs
of the per-GCM difference between two scenarios (not the difference of medians). The
range is a sensitivity to fleet composition, not a confidence interval.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from craei.exposure.heat_bootstrap import CELL, _band, _matrices, _q, _shares
from craei.exposure.heat_table1 import MIN_CELLS

PAIRS = (("ssp585", "ssp126"), ("ssp370", "ssp126"), ("ssp585", "ssp370"))


def _contrast(obs, boot, loo, ia, ib, ok):
    d_obs = obs[0, :, ia, :] - obs[0, :, ib, :]
    med_boot = _q(np.median, boot[:, :, ia, :] - boot[:, :, ib, :], axis=2)
    med_loo = _q(np.median, loo[:, :, ia, :] - loo[:, :, ib, :], axis=2)
    p, nan_frac = _band(med_boot, ok)
    valid = ~np.isnan(med_boot)
    with np.errstate(divide="ignore", invalid="ignore"):
        prob = ((med_boot > 0) & valid).sum(axis=0) / valid.sum(axis=0)
    if not ok:
        prob = np.full(prob.shape, np.nan)
    lo, hi = _q(np.nanmin, med_loo, axis=0), _q(np.nanmax, med_loo, axis=0)
    return d_obs, p, nan_frac, prob, lo, hi


def _pair_rows(grp, t, pair, fleets, models, w, n_cells, res):
    d_obs, p, nan_frac, prob, lo, hi = res
    rows, gcm = [], []
    for fi, fleet in enumerate(fleets):
        d = d_obs[fi]
        n_fleet = int((w[fi].sum(axis=(0, 1)) > 0).sum())
        rows.append({
            "group": grp, "fleet": fleet, "pair": pair, "threshold": t,
            "n_cells": n_cells, "n_cells_fleet": n_fleet,
            "obs_median_diff": float(_q(np.median, d)),
            "obs_min_diff": float(np.min(d)), "obs_max_diff": float(np.max(d)),
            "n_gcm_pos": int((d > 0).sum()), "n_gcm": len(models),
            "boot_p025": p[0, fi], "boot_p50": p[1, fi], "boot_p975": p[2, fi],
            "prob_diff_gt0": prob[fi], "nan_frac": nan_frac[fi],
            "loo_min": lo[fi], "loo_max": hi[fi],
        })
        for mi, model in enumerate(models):
            gcm.append({"group": grp, "fleet": fleet, "pair": pair, "threshold": t,
                        "model": model, "diff_obs": float(d[mi])})
    return rows, gcm


def _ref_rows(grp, t, fleets, scens, boot, ok):
    p, _ = _band(_q(np.median, boot, axis=3), ok)
    return [
        {"group": grp, "fleet": fl, "scenario": sc, "threshold": t,
         "boot_p025": p[0, fi, si], "boot_p975": p[2, fi, si]}
        for fi, fl in enumerate(fleets) for si, sc in enumerate(scens)
    ]


def scenario_contrast(df, cells, group_col, thresholds=(20, 30, 40), n_boot=2000,
                      seed=86, pairs=PAIRS, min_cells=MIN_CELLS):
    """Return (contrast, by_gcm, ref). ref holds the per-scenario share bounds of W3d."""
    key = cells[["plant_uid", *CELL]].drop_duplicates("plant_uid")
    base = df.merge(key, on="plant_uid", how="left", validate="many_to_one")
    if base[CELL].isna().any().any():
        raise ValueError("some plants have no cell")
    base = base.assign(group=base[group_col] if group_col else "all_thermal")
    rows, by_gcm, ref = [], [], []
    for gi, grp in enumerate(sorted(base["group"].dropna().unique())):
        sub = base[base["group"] == grp]
        (fleets, scens, models), w, e_by_t, n_cells = _matrices(sub, thresholds)
        rng = np.random.default_rng([seed, gi])
        counts = rng.multinomial(n_cells, np.full(n_cells, 1.0 / n_cells), size=n_boot)
        ones, drop = np.ones((1, n_cells)), 1.0 - np.eye(n_cells)
        ok = n_cells >= 2
        for t in thresholds:
            obs, boot, loo = (_shares(c, w, e_by_t[t]) for c in (ones, counts, drop))
            ref += _ref_rows(grp, t, fleets, scens, boot, ok)
            for a, b in pairs:
                if a not in scens or b not in scens:
                    continue
                res = _contrast(obs, boot, loo, scens.index(a), scens.index(b), ok)
                r, g = _pair_rows(grp, t, f"{a}-{b}", fleets, models, w, n_cells, res)
                rows += r
                by_gcm += g
    out = pd.DataFrame(rows).assign(n_boot=n_boot, seed=seed)
    nan_frac = pd.to_numeric(out["nan_frac"], errors="coerce")
    ok_rows = (out["n_cells_fleet"] >= min_cells) & (nan_frac == 0)
    out["boot_reported"] = ok_rows
    out["boot_p025_pp"] = np.where(ok_rows, out["boot_p025"].round(0), np.nan)
    out["boot_p975_pp"] = np.where(ok_rows, out["boot_p975"].round(0), np.nan)
    out["label"] = np.where(ok_rows, "range_reported", "descriptive")
    return out, pd.DataFrame(by_gcm), pd.DataFrame(ref)