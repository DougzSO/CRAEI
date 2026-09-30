"""Compound hydro-drought / thermal-heat metric (Spec §1.6, §3 Step 10; COMANDO 20).

Two national monthly series per country/model/scenario/period:

- S_hydro(m): share of the operating hydro fleet's capacity with catchment
  SPEI-12 <= `drought_spei_threshold` in month m.
- H_thermal(m): capacity-weighted mean monthly TX35 day count (`n35`,
  confirmed present in `indices_daily.parquet` before this module was
  written -- Action 1) across the operating thermal fleet in month m.

A compound month is one where both series exceed their own baseline
(1985-2014, same model) 90th percentile (`compound_baseline_percentile`).
When a series' baseline P90 is exactly zero (common for S_hydro, whose
baseline is mostly zero months), Spec §1.6's "any value above zero
qualifies" fallback is the same `>` comparison against a 0.0 threshold, so
no special-cased branch is needed -- `_baseline_thresholds` flags this case
for reporting only.

D63 (COMANDO 22) closes the metric as a percentage-point change
(`diff_pp`) plus a dependence check (`dependence_ratio` = observed future
compound frequency over the independence-implied frequency), not as the
single future/baseline likelihood ratio LR_C originally specified here --
see `compound_summary`'s docstring for why.

Restricted to the operating fleet: the Spec text does not split this
metric by fleet, and `compound.csv`'s schema (country, scenario, model,
f_baseline, f_future, lr_c) has no fleet column -- an author judgment call,
since the metric characterizes present-day system reliability, not the
planned pipeline (that is Figure 4 / C19's job).

A plant absent from `spei.parquet` for H2 (e.g. Nimoo Bazgo, L16) never
joins into S_hydro and is excluded from both its numerator and
capacity-weighted denominator; this module does not apply C19/D57's
not-exposed convention, which is specific to `exposure_summary.csv`.

Only `.groupby(...).agg()` reductions are used, never
`.transform()`/`.apply()`/`.rolling()` over the full climate tables
(CLAUDE.md Rule 11).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.hazards.consolidate import (
    BUCKET_HYDRO_RESERVOIR,
    BUCKET_HYDRO_ROR,
    BUCKET_THERMAL_AIR,
    BUCKET_THERMAL_WATER,
    _assign_bucket,
)

_HYDRO_BUCKETS = (BUCKET_HYDRO_RESERVOIR, BUCKET_HYDRO_ROR)
_THERMAL_BUCKETS = (BUCKET_THERMAL_WATER, BUCKET_THERMAL_AIR)

_SERIES_KEYS = ["country", "model", "scenario", "period", "month"]


def _with_bucket(plants: pd.DataFrame) -> pd.DataFrame:
    if "bucket" in plants.columns:
        return plants
    plants = plants.copy()
    plants["bucket"] = _assign_bucket(plants)
    return plants


def load_compound_inputs(processed_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the inputs Step 10 needs, from `paths.local.yaml:processed_dir` by default."""
    if processed_dir is None:
        processed_dir = Path(load_paths()["processed_dir"])
    return {
        "plants": pd.read_parquet(processed_dir / "plants.parquet"),
        "spei": pd.read_parquet(processed_dir / "spei.parquet"),
        "indices_daily": pd.read_parquet(processed_dir / "indices_daily.parquet"),
        "plant_cell": pd.read_parquet(processed_dir / "plant_cell.parquet"),
    }


def assert_n35_monthly(indices_daily: pd.DataFrame) -> None:
    """Action 1's stop condition: fail loudly if `n35` isn't a real monthly series.

    Spec §1.6's H_thermal needs a per-calendar-month TX35 day count, not the
    annual `tx35` total also in this table -- confirmed once, here, rather
    than assumed silently by the rest of this module.
    """
    n35 = indices_daily[indices_daily["index"] == "n35"]
    if n35.empty:
        raise ValueError(
            "indices_daily.parquet has no 'n35' index -- Spec §1.6 H_thermal needs a "
            "monthly TX35 day count. Stopping per COMANDO 20 Action 1."
        )
    if n35["month"].isna().all():
        raise ValueError(
            "indices_daily.parquet's 'n35' rows have no 'month' value -- this looks like "
            "the annual count, not the monthly series Spec §1.6 H_thermal requires. "
            "Stopping per COMANDO 20 Action 1."
        )


def national_hydro_series(
    plants: pd.DataFrame, spei: pd.DataFrame, spei_threshold: float
) -> pd.DataFrame:
    """S_hydro(m) per country/model/scenario/period/month (operating hydro fleet only)."""
    plants = _with_bucket(plants)
    hydro = plants[plants["bucket"].isin(_HYDRO_BUCKETS) & (plants["fleet"] == "operating")]
    hydro_key = hydro[["plant_uid", "country", "capacity_mw"]]

    # Pre-filter with `isin` before merging (CLAUDE.md Rule 11): `spei.parquet`
    # covers every plant/cell in the country, most of which no operating
    # hydro plant is linked to, so narrowing first keeps the merge small on
    # this project's ~6 GB RAM budget (same idiom as
    # `hazards.consolidate._f_d_r_d`).
    catchment = spei[(spei["scale"] == "catchment") & spei["id"].isin(set(hydro_key["plant_uid"]))]
    rel = catchment.merge(hydro_key, left_on="id", right_on="plant_uid", how="inner")
    rel = rel[rel["SPEI_12"].notna()].copy()
    rel["severe"] = rel["SPEI_12"] <= spei_threshold
    rel["weighted_cap"] = np.where(rel["severe"], rel["capacity_mw"], 0.0)

    agg = rel.groupby(_SERIES_KEYS, as_index=False).agg(
        weighted_cap=("weighted_cap", "sum"), total_cap=("capacity_mw", "sum")
    )
    agg["s_hydro"] = np.where(agg["total_cap"] > 0, agg["weighted_cap"] / agg["total_cap"], np.nan)
    return agg[_SERIES_KEYS + ["s_hydro"]]


def national_thermal_series(
    plants: pd.DataFrame, indices_daily: pd.DataFrame, plant_cell: pd.DataFrame
) -> pd.DataFrame:
    """H_thermal(m) per country/model/scenario/period/month (operating thermal fleet only)."""
    plants = _with_bucket(plants)
    thermal = plants[plants["bucket"].isin(_THERMAL_BUCKETS) & (plants["fleet"] == "operating")]
    thermal_key = thermal[["plant_uid", "country", "capacity_mw"]].merge(
        plant_cell[["plant_uid", "cell_lat", "cell_lon"]], on="plant_uid", how="inner"
    )

    # Same pre-filter idiom as `national_hydro_series` (and
    # `hazards.consolidate`'s cell-scale SPEI join): `indices_daily.parquet`
    # covers the full country grid, most of which no thermal plant links to.
    # A vectorized string key keeps this a cheap `isin`, not a Python-level
    # loop over ~17M rows.
    thermal_cell_keys = set(
        thermal_key["cell_lat"].astype(str) + "_" + thermal_key["cell_lon"].astype(str)
    )
    n35 = indices_daily[indices_daily["index"] == "n35"].copy()
    n35_cell_keys = n35["cell_lat"].astype(str) + "_" + n35["cell_lon"].astype(str)
    n35 = n35[n35_cell_keys.isin(thermal_cell_keys)]
    rel = n35.merge(thermal_key, on=["cell_lat", "cell_lon"], how="inner")
    rel = rel[rel["value"].notna()].copy()
    rel["weighted_value"] = rel["value"] * rel["capacity_mw"]

    agg = rel.groupby(_SERIES_KEYS, as_index=False).agg(
        weighted_sum=("weighted_value", "sum"), total_cap=("capacity_mw", "sum")
    )
    agg["h_thermal"] = np.where(
        agg["total_cap"] > 0, agg["weighted_sum"] / agg["total_cap"], np.nan
    )
    return agg[_SERIES_KEYS + ["h_thermal"]]


def build_compound_series(
    plants: pd.DataFrame,
    spei: pd.DataFrame,
    indices_daily: pd.DataFrame,
    plant_cell: pd.DataFrame,
    spei_threshold: float,
) -> pd.DataFrame:
    """Outer-join S_hydro and H_thermal onto one national monthly table."""
    hydro = national_hydro_series(plants, spei, spei_threshold)
    thermal = national_thermal_series(plants, indices_daily, plant_cell)
    return hydro.merge(thermal, on=_SERIES_KEYS, how="outer")


def baseline_thresholds(series: pd.DataFrame, percentile: float) -> pd.DataFrame:
    """Per (country, model): baseline P90 of S_hydro and H_thermal, and the P90=0 fallback flag.

    `period == "baseline"` rows always carry `scenario == "historical"`
    (same convention as `hazards.consolidate`), so grouping on
    (country, model) alone is unambiguous here.
    """
    baseline = series[series["period"] == "baseline"]

    def _p90(s: pd.Series) -> float:
        valid = s.dropna()
        return float(np.percentile(valid, percentile)) if len(valid) else np.nan

    thresh = baseline.groupby(["country", "model"], as_index=False).agg(
        s_hydro_p90=("s_hydro", _p90),
        h_thermal_p90=("h_thermal", _p90),
        n_baseline_months=("month", "size"),
    )
    thresh["s_hydro_p90_is_zero"] = thresh["s_hydro_p90"] == 0.0
    return thresh


def flag_compound_months(series: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    """Attach the per-(country, model) baseline thresholds and the compound-month flag.

    A month with either series missing (NaN) never flags as compound: a NaN
    comparison is always False, which is the intended behaviour here (not
    enough data to call a month compound, not silently compound).
    """
    merged = series.merge(
        thresholds[["country", "model", "s_hydro_p90", "h_thermal_p90", "s_hydro_p90_is_zero"]],
        on=["country", "model"],
        how="left",
    )
    merged["compound"] = (merged["s_hydro"] > merged["s_hydro_p90"]) & (
        merged["h_thermal"] > merged["h_thermal_p90"]
    )
    return merged


def compound_summary(flagged: pd.DataFrame) -> pd.DataFrame:
    """`compound.csv`: country, scenario, model, and the closed metric (D63).

    D63 supersedes the LR_C-as-headline design (D58/COMANDO 20): a
    diagnostic run (COMANDO 22) found that wherever a marginal series
    (S_hydro or H_thermal) exceeds its own baseline P90 in a majority of
    future months, the baseline-relative *ratio* LR_C is dominated by that
    mean shift, not by co-occurrence -- the two series behave close to
    independently there (`ratio_obs_to_indep` near 1.0), so a large LR_C in
    those cells is not evidence of coupling. The metric is therefore closed
    as two separate quantities instead of one ratio:

    - `diff_pp` = f_future_pct - f_baseline_pct: the change in compound-month
      frequency in percentage points. Immune to the baseline-instability and
      mean-shift inflation that broke LR_C, since it is a difference, not a
      ratio.
    - `dependence_ratio` = f_future / (f_s_above_future * f_h_above_future):
      observed future compound frequency over what independence of the two
      *future* marginals would predict. This isolates whether extra
      co-occurrence exists beyond each series' own marginal increase.
      `NaN` when the independence product is exactly zero (counted by the
      caller, not silently produced here, same convention as the old
      `lr_c` NaN handling).

    `lr_c` (`f_future / f_baseline`) is kept as a secondary, legacy column
    for continuity with COMANDO 20's original output -- it is not read by
    any figure or reported as the headline result (D63).

    `f_baseline_pct` does not vary by scenario (it comes from each model's
    own historical run) but is repeated once per scenario row, matching the
    Spec's stated output shape (one row per country x scenario x model).
    """
    baseline = flagged[flagged["period"] == "baseline"]
    f_baseline = baseline.groupby(["country", "model"], as_index=False).agg(
        f_baseline=("compound", "mean"), n_baseline_months=("compound", "size")
    )

    future = flagged.loc[flagged["period"] == "future"].copy()
    future["s_above"] = future["s_hydro"] > future["s_hydro_p90"]
    future["h_above"] = future["h_thermal"] > future["h_thermal_p90"]
    f_future = future.groupby(["country", "model", "scenario"], as_index=False).agg(
        f_future=("compound", "mean"),
        n_future_months=("compound", "size"),
        f_s_above_future=("s_above", "mean"),
        f_h_above_future=("h_above", "mean"),
    )

    out = f_future.merge(
        f_baseline[["country", "model", "f_baseline", "n_baseline_months"]],
        on=["country", "model"],
        how="left",
    )
    out["f_baseline_pct"] = out["f_baseline"] * 100
    out["f_future_pct"] = out["f_future"] * 100
    out["diff_pp"] = out["f_future_pct"] - out["f_baseline_pct"]

    out["f_compound_independence"] = out["f_s_above_future"] * out["f_h_above_future"]
    out["dependence_ratio"] = np.where(
        out["f_compound_independence"] > 0,
        out["f_future"] / out["f_compound_independence"],
        np.nan,
    )

    out["lr_c"] = np.where(out["f_baseline"] > 0, out["f_future"] / out["f_baseline"], np.nan)

    return out[
        [
            "country",
            "scenario",
            "model",
            "f_baseline_pct",
            "f_future_pct",
            "diff_pp",
            "f_s_above_future",
            "f_h_above_future",
            "f_compound_independence",
            "dependence_ratio",
            "n_baseline_months",
            "n_future_months",
            "lr_c",
            "f_baseline",
            "f_future",
        ]
    ]
