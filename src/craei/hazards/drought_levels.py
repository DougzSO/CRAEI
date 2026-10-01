"""Drought level classes against the no-change null (W4g; D88, O29). Pure functions.

F_D values are in percent of months with SPEI-12 <= threshold. Null arrays are
(n_sim, n_months) simulated SPEI-12 series (craei.hazards.null_model).
"""

import numpy as np
import pandas as pd

FD_LABELS = ("low", "medium", "high", "extreme")
PCTLS = (50, 75, 90, 95, 99)
CUTSETS = {"p50_p90_p99": (50, 90, 99), "p50_p75_p95": (50, 75, 95)}
RD_EDGES = (1.5, 2.0, 3.0)
RD_LABELS = ("rd_lt1_5", "rd_1_5_2", "rd_2_3", "rd_ge3", "rd_undefined")
KEY = ["plant_uid", "model", "scenario"]


def find_plant(plants, country, name_part, mw, tol=1e-6):
    """uid set of the single plant of `country` whose name has `name_part` and `mw` MW."""
    sel = plants[(plants["country"] == country)
                 & plants["plant_name"].str.contains(name_part, case=False, na=False)]
    big = sel[(sel["capacity_mw"] - mw).abs() < tol]
    if len(big) != 1:
        raise ValueError(f"{name_part}: expected one plant of {mw} MW, found {len(big)}")
    return set(big["plant_uid"])


def fd_pct(sims, threshold):
    """F_D (%) of each simulated series."""
    return 100.0 * (np.asarray(sims) <= threshold).mean(axis=1)


def null_fd_percentiles(base, fut, threshold, pctls=PCTLS):
    """Percentiles of the simulated F_D, future and baseline."""
    fb, ff = fd_pct(base, threshold), fd_pct(fut, threshold)
    return pd.DataFrame({
        "percentile": list(pctls),
        "fd_future_pct": np.percentile(ff, list(pctls)),
        "fd_baseline_pct": np.percentile(fb, list(pctls)),
    })


def fd_cuts(percentile_table, cutset):
    """F_D values (%) at the percentiles of `cutset`, from the future null."""
    t = percentile_table.set_index("percentile")["fd_future_pct"]
    return tuple(float(t.loc[p]) for p in cutset)


def classify_fd(values, cuts):
    """low <= c1 < medium <= c2 < high <= c3 < extreme. NaN raises."""
    v = np.asarray(values, dtype=float)
    if np.isnan(v).any():
        raise ValueError("NaN F_D to classify")
    idx = np.searchsorted(np.asarray(cuts, dtype=float), v, side="left")
    lab = np.asarray(FD_LABELS, dtype=object)[idx]
    return pd.Categorical(lab, categories=list(FD_LABELS))


def null_class_shares(null_fd_future, cuts):
    """Share (%) of null simulations falling in each class for the same cuts."""
    v = np.asarray(null_fd_future, dtype=float)
    idx = np.searchsorted(np.asarray(cuts, dtype=float), v, side="left")
    share = 100.0 * np.bincount(idx, minlength=len(FD_LABELS)) / len(v)
    return dict(zip(FD_LABELS, share))


def classify_rd(ratio):
    """R_D classes; NaN (baseline F_D = 0) is its own class."""
    r = np.asarray(ratio, dtype=float)
    nan = np.isnan(r)
    idx = np.searchsorted(np.asarray(RD_EDGES), np.where(nan, 0.0, r), side="right")
    idx = np.where(nan, len(RD_EDGES) + 1, idx)
    lab = np.asarray(RD_LABELS, dtype=object)[idx]
    return pd.Categorical(lab, categories=list(RD_LABELS))


def rd_null_shares(base, fut, threshold):
    """Null share per R_D class among simulations with R_D defined.

    The rd_undefined row is the share of all simulations with baseline F_D = 0.
    null_pct_ge_lower is the share with R_D at or above the lower edge of the class.
    """
    b, f = np.asarray(base), np.asarray(fut)
    n_sim = b.shape[0]
    fb = (b <= threshold).mean(axis=1)
    ff = (f <= threshold).mean(axis=1)
    ok = fb > 0
    n_def = int(ok.sum())
    rd = ff[ok] / fb[ok]
    idx = np.searchsorted(np.asarray(RD_EDGES), rd, side="right")
    share = 100.0 * np.bincount(idx, minlength=4) / n_def if n_def else np.full(4, np.nan)
    ge = share[::-1].cumsum()[::-1]
    rows = []
    for i, lab in enumerate(RD_LABELS[:4]):
        rows.append({"rd_class": lab, "null_pct": share[i], "null_pct_ge_lower": ge[i]})
    rows.append({"rd_class": "rd_undefined", "null_pct": 100.0 * (n_sim - n_def) / n_sim,
                 "null_pct_ge_lower": np.nan})
    out = pd.DataFrame(rows)
    return out.assign(n_sim=n_sim, n_rd_defined=n_def, n_rd_undefined=n_sim - n_def)


def unit_drought_frame(units, fd):
    """Unit x (GCM, scenario) rows with the F_D of the plant. Missing plants or NaN raise."""
    cols = KEY + ["baseline_value", "future_value", "ratio"]
    if fd.duplicated(KEY).any():
        raise ValueError("duplicate (plant_uid, model, scenario) rows in F_D")
    absent = set(units["plant_uid"]) - set(fd["plant_uid"])
    if absent:
        raise ValueError(f"{len(absent)} plants without F_D")
    out = units.merge(fd[cols], on="plant_uid", how="inner")
    if out[["baseline_value", "future_value"]].isna().any().any():
        raise ValueError("NaN F_D among the selected plants")
    if out.groupby(["uid", "itaipu"]).size().nunique() != 1:
        raise ValueError("units differ in number of GCM x scenario rows")
    return out


def compare_fd(mine, ref):
    """(rows matched, max |diff|, NaN mismatches) over baseline, future and ratio."""
    m = mine.merge(ref, on=KEY, how="inner", suffixes=("", "_r"))
    worst, nan_mismatch = 0.0, 0
    for c in ("baseline_value", "future_value", "ratio"):
        a, b = m[c], m[c + "_r"]
        nan_mismatch += int((a.isna() != b.isna()).sum())
        both = a.notna() & b.notna()
        if both.any():
            worst = max(worst, float((a[both] - b[both]).abs().max()))
    return len(m), worst, nan_mismatch