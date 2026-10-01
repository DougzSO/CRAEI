"""Exposure aggregation and model agreement (Spec §1.5, §3 Step 9; COMANDO 19).

Turns `plant_hazards.parquet` (H1/H2/H4-SI) and `plant_aqueduct.parquet` (H3)
into the capacity-share/GW tables behind Figures 1, 2 and 4.

Denominator rule (Spec §1.5, `docs/LIMITATIONS.md` L16/L19, `docs/DECISIONS.md`
D57): every plant in a (country, bucket, fleet) group stays in the capacity
denominator, including plants excluded from a given hazard's fitted series
(L16's Nimoo Bazgo) or with an undefined R_D because baseline F_D = 0 (L19).
Such plants count as NOT exposed to that hazard, not as removed from total
capacity -- this is applied identically for H1/H2 (this module) and is not a
per-figure choice.

Headline exposure classes (ΔTX35 >= `heat_class_dtx35_days_per_yr`, R_D >=
`drought_class_rd_ratio`) come from `config/params.yaml`, never hardcoded.
Model agreement is a plant-level flag (>= `model_agreement_fraction` of the
5 GCMs agreeing on the sign of change), aggregated to a capacity share.

This module only performs `.groupby(...).agg()` reductions, never
`.transform()`/`.apply()`/`.rolling()` over the full hazard table (CLAUDE.md
Rule 11).
"""

from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_params, load_paths
from craei.hazards.consolidate import (
    BUCKET_HYDRO_RESERVOIR,
    BUCKET_HYDRO_ROR,
    BUCKET_THERMAL_AIR,
    BUCKET_THERMAL_WATER,
)

# Spec §1.4: ΔTX35 is the H1 headline metric (thermal buckets); f_d_spei12's
# ratio column is R_D, the H2 headline metric (hydro + thermal_water_dependent).
_HEADLINE_HEAT_HAZARD = "TX35"
_HEADLINE_DROUGHT_HAZARD = "f_d_spei12"

# H4 (Supplementary Information) and solar's own SI metric are not part of
# exposure_summary.csv / exposure_si.csv's H1/H2 columns; SI-bound hazards
# get their own table (Action 6).
_SI_HAZARDS = ("h4_p95_ratio", "h4_rx5day_pct_change")

_H1_BUCKETS = (BUCKET_THERMAL_WATER, BUCKET_THERMAL_AIR)
_H2_BUCKETS = (BUCKET_HYDRO_RESERVOIR, BUCKET_HYDRO_ROR, BUCKET_THERMAL_WATER)

# "tech_class" in the aggregation grouping is the plant_hazards *bucket*
# (hydro_reservoir, hydro_run_of_river, thermal_water_dependent,
# thermal_air_only), not `plants.parquet`'s coarser `tech_class` column --
# Figure 4 and the Spec's H2 hydro-type distinction both need the finer
# split, so this module groups on `bucket` and reports it under a
# `tech_class` column in the output for readability.
_GROUP_KEYS = ["country", "bucket", "fleet", "scenario", "cooling_bound"]


def _with_bucket(plants: pd.DataFrame) -> pd.DataFrame:
    """Assign the plant_hazards bucket (Spec §1.4) if `plants` doesn't already carry it."""
    if "bucket" in plants.columns:
        return plants
    from craei.hazards.consolidate import _assign_bucket

    plants = plants.copy()
    plants["bucket"] = _assign_bucket(plants)
    return plants


def load_exposure_inputs(processed_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the inputs Step 9 needs, from `paths.local.yaml:processed_dir` by default."""
    if processed_dir is None:
        processed_dir = Path(load_paths()["processed_dir"])
    return {
        "plants": pd.read_parquet(processed_dir / "plants.parquet"),
        "plant_hazards": pd.read_parquet(processed_dir / "plant_hazards.parquet"),
        "plant_aqueduct": pd.read_parquet(processed_dir / "plant_aqueduct.parquet"),
    }


def _exposed_flags(
    plants: pd.DataFrame, hazards: pd.DataFrame, hazard_name: str, value_col: str, threshold: float
) -> pd.DataFrame:
    """One row per (plant_uid, model, scenario) with `exposed` (bool) and `sign_pos` (bool | NaN).

    Only plants actually present for `hazard_name` in `hazards` get a row
    here (a plant excluded from H2's fitted series, or with baseline F_D = 0,
    has no `f_d_spei12` row at all for the affected model/scenario -- L16/L19).
    Every plant in `plants["bucket"]`'s H1/H2-relevant set is later
    left-joined onto this by the caller so excluded plants land as
    `exposed = False` (D57), not dropped from the denominator.
    """
    rows = hazards[hazards["hazard"] == hazard_name].copy()
    rows["exposed"] = rows[value_col] >= threshold
    rows["sign_pos"] = np.where(rows[value_col].isna(), np.nan, rows[value_col] > 0)
    return rows[["plant_uid", "bucket", "model", "scenario", "exposed", "sign_pos"]]


def _model_agreement(flagged: pd.DataFrame, min_fraction: float) -> pd.DataFrame:
    """Per (plant_uid, scenario): share of models with sign_pos == True (NaN-safe), agree flag."""
    valid = flagged[flagged["sign_pos"].notna()]
    agg = valid.groupby(["plant_uid", "bucket", "scenario"], as_index=False).agg(
        n_models=("sign_pos", "size"), n_pos=("sign_pos", "sum")
    )
    agg["agree_frac"] = np.where(
        agg["n_models"] > 0,
        np.maximum(agg["n_pos"], agg["n_models"] - agg["n_pos"]) / agg["n_models"],
        np.nan,
    )
    agg["agrees"] = agg["agree_frac"] >= min_fraction
    return agg[["plant_uid", "bucket", "scenario", "agrees"]]


def _capacity_table(
    plants: pd.DataFrame, bucket_subset: tuple[str, ...], hazard_name: str, models: pd.Index
) -> pd.DataFrame:
    """Cross-join every plant in `bucket_subset` with every model, as the full denominator base."""
    base = plants[plants["bucket"].isin(bucket_subset)][
        ["plant_uid", "country", "fleet", "bucket", "capacity_mw"]
    ].copy()
    model_df = pd.DataFrame({"model": models})
    return base.merge(model_df, how="cross")


def _summarize_hazard(
    plants: pd.DataFrame,
    hazards: pd.DataFrame,
    bucket_subset: tuple[str, ...],
    hazard_name: str,
    value_col: str,
    threshold: float,
    agreement_fraction: float,
) -> pd.DataFrame:
    """Median/min/max share and GW across models, plus agreement share, per group x hazard.

    L16/L19/D57: plants with no row for `hazard_name` at a given
    (model, scenario) -- excluded from the fitted series, or undefined R_D --
    are filled `exposed = False` here via the left join onto the full
    plant x model cross-join, so they stay in the denominator as not-exposed
    rather than shrinking it.
    """
    models = hazards.loc[hazards["hazard"] == hazard_name, "model"].dropna().unique()
    models = pd.Index(sorted(models))
    if len(models) == 0:
        return pd.DataFrame(
            columns=["country", "tech_class", "fleet", "scenario", "cooling_bound"]
            + [
                "hazard",
                "median_share",
                "min_share",
                "max_share",
                "median_gw",
                "min_gw",
                "max_gw",
                "agreement_share",
            ]
        )

    scenarios = hazards.loc[hazards["hazard"] == hazard_name, "scenario"].dropna().unique()
    full = pd.concat(
        [
            _capacity_table(plants, bucket_subset, hazard_name, models).assign(scenario=s)
            for s in scenarios
        ],
        ignore_index=True,
    )

    flags = _exposed_flags(plants, hazards, hazard_name, value_col, threshold)
    merged = full.merge(
        flags[["plant_uid", "model", "scenario", "exposed", "sign_pos"]],
        on=["plant_uid", "model", "scenario"],
        how="left",
    )
    merged["exposed"] = merged["exposed"].eq(True)
    merged["cooling_bound"] = "n/a"

    group_keys = _GROUP_KEYS + ["model"]
    merged["exposed_mw"] = np.where(merged["exposed"], merged["capacity_mw"], 0.0)
    per_model = merged.groupby(group_keys, as_index=False).agg(
        exposed_mw=("exposed_mw", "sum"),
        total_mw=("capacity_mw", "sum"),
    )
    per_model["share"] = np.where(
        per_model["total_mw"] > 0, per_model["exposed_mw"] / per_model["total_mw"], np.nan
    )
    per_model["gw"] = per_model["exposed_mw"] / 1000.0

    summary = per_model.groupby(_GROUP_KEYS, as_index=False).agg(
        median_share=("share", "median"),
        min_share=("share", "min"),
        max_share=("share", "max"),
        median_gw=("gw", "median"),
        min_gw=("gw", "min"),
        max_gw=("gw", "max"),
    )

    agreement = _model_agreement(flags, agreement_fraction)
    agree_with_cap = merged[
        ["plant_uid", "bucket", "country", "fleet", "scenario", "capacity_mw"]
    ].drop_duplicates(subset=["plant_uid", "scenario"])
    agree_with_cap = agree_with_cap.merge(
        agreement, on=["plant_uid", "bucket", "scenario"], how="left"
    )
    agree_with_cap["agrees"] = agree_with_cap["agrees"].eq(True)
    agree_with_cap["agree_mw"] = np.where(
        agree_with_cap["agrees"], agree_with_cap["capacity_mw"], 0.0
    )
    agree_group = agree_with_cap.groupby(
        ["country", "bucket", "fleet", "scenario"], as_index=False
    ).agg(
        agree_mw=("agree_mw", "sum"),
        total_mw2=("capacity_mw", "sum"),
    )
    agree_group["agreement_share"] = np.where(
        agree_group["total_mw2"] > 0, agree_group["agree_mw"] / agree_group["total_mw2"], np.nan
    )
    agree_group["cooling_bound"] = "n/a"

    summary = summary.merge(
        agree_group[["country", "bucket", "fleet", "scenario", "cooling_bound", "agreement_share"]],
        on=_GROUP_KEYS,
        how="left",
    )
    summary["hazard"] = hazard_name
    summary = summary.rename(columns={"bucket": "tech_class"})
    return summary[
        ["country", "tech_class", "fleet", "scenario", "cooling_bound"]
        + [
            "hazard",
            "median_share",
            "min_share",
            "max_share",
            "median_gw",
            "min_gw",
            "max_gw",
            "agreement_share",
        ]
    ]


def build_exposure_summary(plants: pd.DataFrame, plant_hazards: pd.DataFrame) -> pd.DataFrame:
    """Main-text exposure_summary.csv: H1 (ΔTX35) and H2 (R_D) by group x fleet x scenario x model.

    H1 covers thermal_water_dependent + thermal_air_only; H2 covers
    hydro_reservoir + hydro_run_of_river + thermal_water_dependent (Spec
    §1.4 H2). Excludes H3 (own table, Action 5) and H4/solar (SI, Action 6).
    """
    plants = _with_bucket(plants)
    params = load_params()
    heat_threshold = params["heat_class_dtx35_days_per_yr"]["value"]
    drought_threshold = params["drought_class_rd_ratio"]["value"]
    agreement_fraction = params["model_agreement_fraction"]["value"]

    heat = _summarize_hazard(
        plants,
        plant_hazards,
        _H1_BUCKETS,
        _HEADLINE_HEAT_HAZARD,
        "delta",
        heat_threshold,
        agreement_fraction,
    )
    drought = _summarize_hazard(
        plants,
        plant_hazards,
        _H2_BUCKETS,
        _HEADLINE_DROUGHT_HAZARD,
        "ratio",
        drought_threshold,
        agreement_fraction,
    )
    parts = [d for d in (heat, drought) if len(d)]
    out = pd.concat(parts, ignore_index=True) if parts else heat.copy()
    return out.drop(columns=["cooling_bound"])


def build_exposure_aqueduct(plants: pd.DataFrame, plant_aqueduct: pd.DataFrame) -> pd.DataFrame:
    """H3 (Aqueduct) exposure_aqueduct.csv: own table, both cooling bounds, no model agreement.

    Exposure is capacity in "high" or "extremely high" `ws_category`
    (Spec §1.4 H3). No median/min/max across models: Aqueduct's
    `future_annual ws` is already the median of an internal 5-GCM ensemble
    distinct from this project's ISIMIP3b ensemble, with no per-model
    breakdown available (Spec §1.4 H3, L13), so there is nothing to take an
    ensemble range or agreement fraction over here.
    """
    water_dep = plants[plants["tech_class"] == "thermal_water_dependent"][
        ["plant_uid", "country", "tech_class", "fleet", "capacity_mw"]
    ]
    full = water_dep.merge(pd.DataFrame({"cooling_bound": ["upper", "lower"]}), how="cross").merge(
        pd.DataFrame({"scenario": sorted(plant_aqueduct["scenario"].dropna().unique())}),
        how="cross",
    )
    merged = full.merge(
        plant_aqueduct[["plant_uid", "scenario", "cooling_bound", "ws_category"]],
        on=["plant_uid", "scenario", "cooling_bound"],
        how="left",
    )
    # Spec §1.4 H3: for the "lower" bound, a coastal plant is dropped from
    # plant_aqueduct.parquet entirely (assumed seawater-cooled); such a
    # plant is not in the H3 denominator for "lower" at all (H3 has no
    # L16/L19-style not-exposed convention -- the exclusion here is a
    # cooling-technology assumption, not a fitting failure).
    merged = merged[merged["ws_category"].notna() | (merged["cooling_bound"] == "upper")]
    merged["exposed"] = merged["ws_category"].isin(["high", "extremely high"])

    merged["exposed_mw"] = np.where(merged["exposed"], merged["capacity_mw"], 0.0)
    summary = merged.groupby(
        ["country", "tech_class", "fleet", "scenario", "cooling_bound"], as_index=False
    ).agg(exposed_mw=("exposed_mw", "sum"), total_mw=("capacity_mw", "sum"))
    summary["share"] = np.where(
        summary["total_mw"] > 0, summary["exposed_mw"] / summary["total_mw"], np.nan
    )
    summary["gw"] = summary["exposed_mw"] / 1000.0
    return summary[["country", "tech_class", "fleet", "scenario", "cooling_bound", "share", "gw"]]


def build_exposure_si(plants: pd.DataFrame, plant_hazards: pd.DataFrame) -> pd.DataFrame:
    """Supplementary material: H4 (extreme precipitation, all buckets) and solar.

    H4's two hazards have different change-metric semantics (Spec §1.4 H4):
    `h4_p95_ratio` is an exceedance-frequency ratio (>1 = more frequent),
    `h4_rx5day_pct_change` is a percentage change in mean annual Rx5day.
    Neither has a Spec-defined exposure class/threshold, so this table
    reports the ensemble median/min/max of the raw metric per group, not a
    capacity share above a class -- unlike exposure_summary.csv's H1/H2.
    """
    h4 = plant_hazards[plant_hazards["hazard"].isin(_SI_HAZARDS)].copy()
    h4["metric"] = np.where(h4["hazard"] == "h4_p95_ratio", h4["ratio"], h4["delta"])

    with_meta = h4.merge(
        plants[["plant_uid", "country", "tech_class", "fleet", "capacity_mw"]],
        on="plant_uid",
        how="left",
    )
    with_meta = with_meta[with_meta["metric"].notna()].copy()
    with_meta["weighted_metric"] = with_meta["metric"] * with_meta["capacity_mw"]
    model_group = ["country", "tech_class", "fleet", "scenario", "hazard", "model"]
    agg = with_meta.groupby(model_group, as_index=False).agg(
        weighted_sum=("weighted_metric", "sum"), cap_sum=("capacity_mw", "sum")
    )
    agg["capacity_weighted_mean"] = np.where(
        agg["cap_sum"] > 0, agg["weighted_sum"] / agg["cap_sum"], np.nan
    )
    per_model = agg
    summary = per_model.groupby(
        ["country", "tech_class", "fleet", "scenario", "hazard"], as_index=False
    ).agg(
        median_value=("capacity_weighted_mean", "median"),
        min_value=("capacity_weighted_mean", "min"),
        max_value=("capacity_weighted_mean", "max"),
    )
    return summary
