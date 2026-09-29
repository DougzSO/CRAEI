"""Memory-safe rolling sums per group, shared by SPEI/SPI (COMANDO 17) and
Rx5day (COMANDO 15).

`groupby(group_cols)[value_col].transform(lambda s: s.rolling(window,
min_periods=window).sum())` looks like the obvious way to write this, but it
materializes one `Series` per group and concatenates them; with tens of
thousands of groups (id/model/scenario/period, or cell/model/scenario) that
concat overhead crashed this project's ~6 GB machine with a `MemoryError`
well before the raw data size itself would (COMANDO 17 follow-up). See
CLAUDE.md's memory-discipline rule and `docs/DECISIONS.md` for the decision
this fix was logged under.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_sum_by_group(
    df: pd.DataFrame, group_cols: list[str], order_col: str, value_col: str, window: int
) -> np.ndarray:
    """`window`-row rolling sum of `value_col`, `NaN` under `min_periods=window`.

    `df` must already be sorted by `group_cols + [order_col]` (the caller's
    job, since callers usually want to reuse that same sorted frame). Returns
    a plain `np.ndarray` aligned to `df`'s row order, not a new column,  so a
    caller with several windows to compute (e.g. SPEI-12 and SPEI-3) can call
    this repeatedly on the same sorted frame without re-sorting.

    Vectorized via two global cumulative sums (values and a finite-value
    mask), not a per-group Python loop or `groupby(...).transform(...)`: a
    row's position within its group (`groupby(...).cumcount()`) is enough to
    know whether its `window` preceding rows stay inside its own group,
    since groups are contiguous after the sort -- no per-group Series or
    concat is needed. `roll_count == window` reproduces pandas'
    `min_periods=window` (NaN if any value inside the window is missing),
    not just "window rows of any value exist".
    """
    vals = df[value_col].to_numpy(dtype=float)
    pos_in_group = df.groupby(group_cols, sort=False).cumcount().to_numpy()

    finite = np.isfinite(vals)
    cumsum = np.concatenate(([0.0], np.cumsum(np.where(finite, vals, 0.0))))
    cumcount = np.concatenate(([0], np.cumsum(finite.astype(np.int64))))

    out = np.full(len(vals), np.nan)
    if len(vals) >= window:
        roll_sum = cumsum[window:] - cumsum[:-window]
        roll_count = cumcount[window:] - cumcount[:-window]
        valid = (pos_in_group[window - 1 :] >= window - 1) & (roll_count == window)
        out[window - 1 :] = np.where(valid, roll_sum, np.nan)
    return out
