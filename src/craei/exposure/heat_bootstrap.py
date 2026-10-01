"""Cell-cluster bootstrap and paired fleet difference for heat shares (W3d, D86).

Pure functions. The hazard is defined per 0.5-degree cell, so the cell is the resampling
unit. GEM is the whole inventory, so the percentile range is a sensitivity to fleet
composition, not a sampling error and not a confidence interval.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

CELL = ["cell_lat", "cell_lon"]
KEYS = ["fleet", "scenario", "model"]
PCT = (2.5, 50.0, 97.5)
OPERATING = "operating"


def _q(func, *args, **kwargs):
    """Call a numpy reducer with all-NaN warnings silenced (NaN is reported, not hidden)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return func(*args, **kwargs)


def _dense(sub: pd.DataFrame, values: pd.Series, idx: pd.MultiIndex, n_cells: int):
    grouper = [sub["fleet"], sub["scenario"], sub["model"], sub["cid"]]
    wide = values.groupby(grouper).sum().unstack("cid", fill_value=0.0)
    if len(wide) != len(idx):
        raise ValueError("incomplete fleet x scenario x GCM grid")
    wide = wide.reindex(index=idx, columns=range(n_cells), fill_value=0.0)
    shape = tuple(len(level) for level in idx.levels) + (n_cells,)
    return wide.to_numpy().reshape(shape)


def _matrices(sub: pd.DataFrame, thresholds: tuple[int, ...]):
    sub = sub.assign(cid=sub.groupby(CELL).ngroup())
    n_cells = int(sub["cid"].nunique())
    levels = [sorted(sub[k].unique()) for k in KEYS]
    idx = pd.MultiIndex.from_product(levels, names=KEYS)
    cap = sub["capacity_mw"]
    w = _dense(sub, cap, idx, n_cells)
    e = {t: _dense(sub, cap.where(sub["delta"] >= t, 0.0), idx, n_cells) for t in thresholds}
    return levels, w, e, n_cells


def _shares(counts: np.ndarray, w: np.ndarray, e: np.ndarray) -> np.ndarray:
    """Share of capacity exposed, shape (draws, fleet, scenario, GCM); NaN if no capacity."""
    den = np.einsum("bc,fsmc->bfsm", counts, w)
    num = np.einsum("bc,fsmc->bfsm", counts, e)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 1e-9, 100.0 * num / den, np.nan)


def _band(arr: np.ndarray, ok: bool):
    """Percentiles (2.5, 50, 97.5) over draws and the share of NaN draws."""
    shape = arr.shape[1:]
    if not ok:
        return np.full((3, *shape), np.nan), np.full(shape, np.nan)
    return _q(np.nanpercentile, arr, PCT, axis=0), np.isnan(arr).mean(axis=0)


def _share_rows(grp, t, fleets, scens, w, obs, boot, n_cells, ok) -> list[dict]:
    p, nan_frac = _band(boot, ok)
    rows = []
    for fi, fleet in enumerate(fleets):
        n_fleet = int((w[fi].sum(axis=(0, 1)) > 0).sum())
        for si, scen in enumerate(scens):
            rows.append({
                "group": grp, "fleet": fleet, "scenario": scen, "threshold": t,
                "n_cells": n_cells, "n_cells_fleet": n_fleet,
                "obs_median": obs[fi, si],
                "boot_p025": p[0, fi, si], "boot_p50": p[1, fi, si],
                "boot_p975": p[2, fi, si], "nan_frac": nan_frac[fi, si],
            })
    return rows


def _pair_rows(grp, t, fleets, scens, w, sh, n_cells, ok) -> list[dict]:
    if OPERATING not in fleets:
        return []
    sh_obs, sh_boot, sh_drop = sh
    fo = fleets.index(OPERATING)
    rows = []
    for fp, planned in enumerate(fleets):
        if not planned.startswith("planned"):
            continue
        d_obs = sh_obs[:, fp] - sh_obs[:, fo]
        obs = _q(np.median, d_obs, axis=2)[0]
        n_ge = (d_obs >= 0).sum(axis=2)[0]
        boot = _q(np.median, sh_boot[:, fp] - sh_boot[:, fo], axis=2)
        drop = _q(np.median, sh_drop[:, fp] - sh_drop[:, fo], axis=2)
        p, nan_frac = _band(boot, ok)
        valid = ~np.isnan(boot)
        with np.errstate(divide="ignore", invalid="ignore"):
            prob = ((boot > 0) & valid).sum(axis=0) / valid.sum(axis=0)
        lo, hi = _q(np.nanmin, drop, axis=0), _q(np.nanmax, drop, axis=0)
        n_planned = int((w[fp].sum(axis=(0, 1)) > 0).sum())
        for si, scen in enumerate(scens):
            rows.append({
                "planned_fleet": planned, "group": grp, "scenario": scen, "threshold": t,
                "n_cells": n_cells, "n_cells_planned": n_planned,
                "obs_median_diff": obs[si], "n_planned_ge_obs": int(n_ge[si]),
                "boot_p025": p[0, si], "boot_p50": p[1, si], "boot_p975": p[2, si],
                "prob_diff_gt0": prob[si] if ok else np.nan, "nan_frac": nan_frac[si],
                "loo_min": lo[si], "loo_max": hi[si],
            })
    return rows


def cell_bootstrap(
    df: pd.DataFrame,
    cells: pd.DataFrame,
    group_col: str | None,
    thresholds: tuple[int, ...] = (20, 30, 40),
    n_boot: int = 2000,
    seed: int = 86,
    min_cells: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cell bootstrap of the GCM-median share and of the paired planned-minus-operating
    median difference, plus the leave-one-cell-out range of that difference.

    Returns (shares, paired). Percentiles are NaN when a group has fewer than min_cells.
    """
    key = cells[["plant_uid", *CELL]].drop_duplicates("plant_uid")
    base = df.merge(key, on="plant_uid", how="left", validate="many_to_one")
    if base[CELL].isna().any().any():
        raise ValueError("some plants have no cell")
    base = base.assign(group=base[group_col] if group_col else "all_thermal")
    share_rows: list[dict] = []
    pair_rows: list[dict] = []
    for gi, grp in enumerate(sorted(base["group"].dropna().unique())):
        sub = base[base["group"] == grp]
        (fleets, scens, _models), w, e_by_t, n_cells = _matrices(sub, thresholds)
        rng = np.random.default_rng([seed, gi])
        counts = rng.multinomial(n_cells, np.full(n_cells, 1.0 / n_cells), size=n_boot)
        ones, drop = np.ones((1, n_cells)), 1.0 - np.eye(n_cells)
        ok = n_cells >= min_cells
        for t in thresholds:
            sh = tuple(_shares(c, w, e_by_t[t]) for c in (ones, counts, drop))
            med = [_q(np.median, s, axis=3) for s in sh]
            share_rows += _share_rows(
                grp, t, fleets, scens, w, med[0][0], med[1], n_cells, ok
            )
            pair_rows += _pair_rows(grp, t, fleets, scens, w, sh, n_cells, ok)
    return pd.DataFrame(share_rows), pd.DataFrame(pair_rows)