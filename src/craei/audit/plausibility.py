"""Plausibility checks on exposure and LR_C (COMANDO 22, Action 3).

Checks:
1. Exposure at 0% or 100% for all scenarios/models in any country x bucket
2. LR_C out of [0.1, 20], with baseline frequency and absolute month counts
3. Buckets with < 5 plants by country
4. Scenario ordering: exposure should increase SSP1 -> SSP3 -> SSP5 (where physically expected)
"""

from pathlib import Path

import pandas as pd
import numpy as np

from craei.config import load_paths


def _assign_bucket(plants: pd.DataFrame) -> pd.Series:
    """Assign plant_hazards bucket to each plant. Copied from consolidate.py."""
    from craei.hazards.consolidate import (
        BUCKET_HYDRO_RESERVOIR,
        BUCKET_HYDRO_ROR,
        BUCKET_THERMAL_AIR,
        BUCKET_THERMAL_WATER,
        BUCKET_SOLAR,
    )

    tech = plants["tech_class"]
    hydro_type = plants["hydro_type"]
    bucket = pd.Series("other", index=plants.index, dtype="object")
    is_hydro = tech == "hydro"
    bucket[is_hydro & (hydro_type == "run-of-river")] = BUCKET_HYDRO_ROR
    bucket[is_hydro & (hydro_type != "run-of-river")] = BUCKET_HYDRO_RESERVOIR
    bucket[tech == "thermal_water_dependent"] = BUCKET_THERMAL_WATER
    bucket[tech == "thermal_air_only"] = BUCKET_THERMAL_AIR
    bucket[tech == "solar_pv"] = BUCKET_SOLAR
    return bucket


def check_plausibility(
    exposure_summary: pd.DataFrame,
    compound: pd.DataFrame,
    plants: pd.DataFrame,
) -> dict[str, list[str]]:
    """Run plausibility checks. Returns dict with keys: PASS, WARN, FAIL."""
    # Add bucket column if not present
    if "bucket" not in plants.columns:
        plants = plants.copy()
        plants["bucket"] = _assign_bucket(plants)

    checks = {"PASS": [], "WARN": [], "FAIL": []}

    # Check 1: Exposure at extremes (0% or 100%)
    checks["WARN"].append("CHECK: Exposure extremes")
    extremes = exposure_summary[
        (exposure_summary["median_share"] == 0.0)
        | (exposure_summary["median_share"] == 1.0)
    ]
    if len(extremes) > 0:
        grouped = extremes.groupby(
            ["country", "tech_class", "hazard"]
        ).size()
        extreme_cases = []
        for (country, tech, hazard), count in grouped.items():
            extreme_cases.append(
                f"{country} {tech} {hazard}: {count} scenario/model combos at 0% or 100%"
            )
        if extreme_cases:
            checks["WARN"].extend(extreme_cases)
        else:
            checks["PASS"].append("No exposure at extremes across all countries/buckets")
    else:
        checks["PASS"].append("No exposure at extremes")

    # Check 2 (retired by D63/COMANDO 22-B): the old LR_C in [0.1, 20] bound
    # check is gone. D63 dropped LR_C as the headline compound quantity
    # because that bound was routinely broken by cells where a marginal
    # series exceeds its own baseline P90 in a majority of future months
    # (mean-shift, not implausibility) -- see docs/DECISIONS.md D63. The
    # replacement quantities (`diff_pp`, always well-defined; `dependence_ratio`,
    # only meaningful where both marginals still discriminate) need a
    # block-bootstrap CI to judge reportability, which is expensive enough
    # (10,000 resamples/cell) that it is run as its own one-off diagnostic
    # (`scripts/c22b_dependence_uncertainty.py`, `docs/DECISIONS.md` D65/O12),
    # not inlined into this fast structural check. This check now only
    # confirms the closed-metric schema is present.
    missing_cols = {"diff_pp", "dependence_ratio"} - set(compound.columns)
    if missing_cols:
        checks["FAIL"].append(
            f"compound.csv is missing closed-metric columns {sorted(missing_cols)} "
            "(D63) -- rerun scripts/11_compound.py"
        )
    else:
        checks["PASS"].append(
            "compound.csv has the D63 closed-metric columns (diff_pp, dependence_ratio); "
            "dependence_ratio reportability is judged separately by "
            "scripts/c22b_dependence_uncertainty.py's block-bootstrap CI, not by this check"
        )

    # Check 3: Bucket sample size
    checks["WARN"].append("CHECK: Bucket sample size >= 5 plants")
    plants_by_country_bucket = (
        plants.groupby(["country", "bucket"]).size().reset_index(name="n_plants")
    )
    small_buckets = plants_by_country_bucket[
        plants_by_country_bucket["n_plants"] < 5
    ]
    if len(small_buckets) > 0:
        for _, row in small_buckets.iterrows():
            checks["WARN"].append(
                f"{row['country']} {row['bucket']}: only {row['n_plants']} plants"
            )
    else:
        checks["PASS"].append("All country × bucket groups have >= 5 plants")

    # Check 4: Scenario ordering
    checks["WARN"].append("CHECK: Scenario ordering (SSP1 -> SSP3 -> SSP5 monotonic increase)")

    # For each country × hazard, check if median exposure increases or stays stable
    scenario_order = {"ssp126": 1, "ssp370": 2, "ssp585": 3}
    ordering_issues = []

    for country in exposure_summary["country"].unique():
        for hazard in exposure_summary["hazard"].unique():
            subset = exposure_summary[
                (exposure_summary["country"] == country)
                & (exposure_summary["hazard"] == hazard)
            ].copy()
            if len(subset) == 0:
                continue

            for tech in subset["tech_class"].unique():
                tech_subset = subset[subset["tech_class"] == tech]
                # Get median share per scenario
                scenario_medians = {}
                for scenario in ["ssp126", "ssp370", "ssp585"]:
                    data = tech_subset[tech_subset["scenario"] == scenario]
                    if len(data) > 0:
                        scenario_medians[scenario] = data["median_share"].median()

                # Check ordering
                if (
                    "ssp126" in scenario_medians
                    and "ssp370" in scenario_medians
                    and scenario_medians["ssp126"] > scenario_medians["ssp370"]
                ):
                    ordering_issues.append(
                        f"{country} {tech} {hazard}: SSP1-2.6 ({scenario_medians['ssp126']:.1%}) "
                        f"> SSP3-7.0 ({scenario_medians['ssp370']:.1%})"
                    )
                if (
                    "ssp370" in scenario_medians
                    and "ssp585" in scenario_medians
                    and scenario_medians["ssp370"] > scenario_medians["ssp585"]
                ):
                    ordering_issues.append(
                        f"{country} {tech} {hazard}: SSP3-7.0 ({scenario_medians['ssp370']:.1%}) "
                        f"> SSP5-8.5 ({scenario_medians['ssp585']:.1%})"
                    )

    if ordering_issues:
        checks["WARN"].extend(ordering_issues)
    else:
        checks["PASS"].append("Scenario ordering consistent (monotonic or near-flat)")

    return checks


def load_and_check_plausibility(outputs_dir: Path | None = None) -> dict[str, list[str]]:
    """Load data and run plausibility checks.

    `outputs_dir` here means `load_paths()["outputs_tables_dir"]` by default
    (COMANDO 22-B Part 3) -- exposure_summary.csv/compound.csv live there.
    """
    paths = load_paths()
    if outputs_dir is None:
        outputs_dir = Path(paths["outputs_tables_dir"])

    processed_dir = Path(paths["processed_dir"])

    exposure_summary = pd.read_csv(outputs_dir / "exposure_summary.csv")
    compound = pd.read_csv(outputs_dir / "compound.csv")
    plants = pd.read_parquet(processed_dir / "plants.parquet")

    return check_plausibility(exposure_summary, compound, plants)


def format_plausibility_report(checks: dict[str, list[str]]) -> str:
    """Format checks dict into a readable report."""
    lines = []

    for status in ["PASS", "FAIL", "WARN"]:
        if checks[status]:
            lines.append(f"\n{status}:")
            for check in checks[status]:
                lines.append(f"  {check}")

    return "\n".join(lines)
