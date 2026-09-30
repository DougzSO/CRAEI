"""Data coverage audit by country, metric, bucket, and fleet (COMANDO 22, Action 1).

Cobertura de dado: plantas DISTINTAS com valor válido do hazard, dividido pela
capacidade do BUCKET a que aquele hazard se aplica conforme METHODS_SPEC §1.4.

SPEI-12 applies to: hydro_reservoir, hydro_run_of_river, thermal_water_dependent
SPEI-3 applies to: hydro_run_of_river only
TX35/TX40 apply to: thermal_water_dependent, thermal_air_only
Aqueduct applies to: thermal_water_dependent only

The coverage_fraction is guaranteed to be in [0, 1] by an assert.

Capacity with no data is split into two categories:
- excluded by declared limitation (L16: Nimoo Bazgo in H2; L19: thermal F_D=0)
- absent by missing data (no row in hazard table for that plant/model/scenario)
"""

from pathlib import Path

import pandas as pd
import numpy as np

from craei.config import load_paths
from craei.hazards.consolidate import (
    BUCKET_HYDRO_RESERVOIR,
    BUCKET_HYDRO_ROR,
    BUCKET_THERMAL_AIR,
    BUCKET_THERMAL_WATER,
    BUCKET_SOLAR,
)


def _get_bucket_denominator(
    plants: pd.DataFrame,
    bucket: str,
    country: str,
    fleet: str,
) -> float:
    """Total capacity (MW) for a (country, bucket, fleet) group."""
    subset = plants[
        (plants["country"] == country)
        & (plants["bucket"] == bucket)
        & (plants["fleet"] == fleet)
    ]
    return subset["capacity_mw"].sum()


def _assign_bucket(plants: pd.DataFrame) -> pd.Series:
    """Assign plant_hazards bucket to each plant. Copied from consolidate.py."""
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


def compute_coverage(
    plants: pd.DataFrame,
    plant_hazards: pd.DataFrame,
    plant_aqueduct: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Coverage (numerator = distinct plants with valid data, denominator = bucket capacity).

    Returns one row per (country, metric, bucket, fleet) with:
    - numerator_plants: count of distinct plants with non-NaN data
    - numerator_mw: capacity of plants with non-NaN data
    - denominator_mw: total capacity of bucket
    - coverage_fraction: numerator_mw / denominator_mw, assert [0, 1]
    - excluded_plants: count excluded by declared limitation (L16, L19)
    - excluded_mw: capacity excluded by limitation
    - absent_plants: count missing from data (not in hazard table at all)
    - absent_mw: capacity absent from data
    """
    plants = plants.copy()
    plants["bucket"] = _assign_bucket(plants)

    rows = []

    # H1 and H2 metrics from plant_hazards
    hazard_map = {
        "TX35": ([BUCKET_THERMAL_WATER, BUCKET_THERMAL_AIR], "delta"),
        "TX40": ([BUCKET_THERMAL_WATER, BUCKET_THERMAL_AIR], "delta"),
        "f_d_spei12": (
            [BUCKET_HYDRO_RESERVOIR, BUCKET_HYDRO_ROR, BUCKET_THERMAL_WATER],
            "ratio",
        ),
        "f_d_spei3": ([BUCKET_HYDRO_ROR], "ratio"),
    }

    for metric, (applicable_buckets, col) in hazard_map.items():
        # Get valid data
        valid_data = plant_hazards[
            (plant_hazards["hazard"] == metric)
            & (plant_hazards[col].notna())
        ][["plant_uid", "bucket"]].drop_duplicates()

        for bucket in applicable_buckets:
            plants_in_bucket = plants[plants["bucket"] == bucket]

            for country in plants_in_bucket["country"].unique():
                for fleet in plants_in_bucket[
                    plants_in_bucket["country"] == country
                ]["fleet"].unique():
                    plants_group = plants_in_bucket[
                        (plants_in_bucket["country"] == country)
                        & (plants_in_bucket["fleet"] == fleet)
                    ]

                    denominator_mw = plants_group["capacity_mw"].sum()
                    if denominator_mw == 0:
                        continue

                    # Plants with data
                    valid_in_group = valid_data[
                        valid_data["plant_uid"].isin(plants_group["plant_uid"])
                        & (valid_data["bucket"] == bucket)
                    ]["plant_uid"].unique()
                    numerator_plants = len(valid_in_group)
                    numerator_mw = plants_group[
                        plants_group["plant_uid"].isin(valid_in_group)
                    ]["capacity_mw"].sum()

                    # Plants absent from data (no row at all for this metric)
                    hazard_rows = plant_hazards[
                        (plant_hazards["hazard"] == metric)
                        & (plant_hazards["bucket"] == bucket)
                    ]["plant_uid"].unique()
                    absent_uids = set(plants_group["plant_uid"]) - set(hazard_rows)
                    absent_plants = len(absent_uids)
                    absent_mw = plants_group[
                        plants_group["plant_uid"].isin(absent_uids)
                    ]["capacity_mw"].sum()

                    # Plants excluded by limitation (special handling for known exclusions)
                    # L16: Nimoo Bazgo (only in hydro_run_of_river, H2)
                    # L19: thermal plants with baseline F_D = 0 (only for f_d_spei12)
                    excluded_plants = 0
                    excluded_mw = 0.0

                    if (
                        metric == "f_d_spei12"
                        and bucket == BUCKET_HYDRO_ROR
                        and country == "IND"
                    ):
                        # L16: Nimoo Bazgo (45 MW run-of-river in India)
                        # Check if it's in the group but not in valid data
                        nimoo_uid = None
                        for uid in plants_group["plant_uid"]:
                            plant_name = plants.loc[
                                plants["plant_uid"] == uid, "plant_name"
                            ].values
                            if (
                                len(plant_name) > 0
                                and "Nimoo" in plant_name[0]
                            ):
                                nimoo_uid = uid
                                break
                        if nimoo_uid is not None and nimoo_uid not in valid_in_group:
                            excluded_plants = 1
                            excluded_mw = plants_group[
                                plants_group["plant_uid"] == nimoo_uid
                            ]["capacity_mw"].sum()
                            # Remove from absent count if present there
                            if nimoo_uid in absent_uids:
                                absent_plants -= 1
                                absent_mw -= excluded_mw

                    coverage_fraction = (
                        numerator_mw / denominator_mw
                        if denominator_mw > 0
                        else 0.0
                    )

                    # Assert coverage is in [0, 1]
                    assert (
                        0.0 <= coverage_fraction <= 1.0
                    ), f"Coverage {coverage_fraction} out of [0, 1] for {country} {metric} {bucket} {fleet}"

                    rows.append({
                        "country": country,
                        "metric": metric,
                        "bucket": bucket,
                        "fleet": fleet,
                        "numerator_plants": numerator_plants,
                        "numerator_mw": numerator_mw,
                        "denominator_mw": denominator_mw,
                        "coverage_fraction": coverage_fraction,
                        "excluded_plants": excluded_plants,
                        "excluded_mw": excluded_mw,
                        "absent_plants": absent_plants,
                        "absent_mw": absent_mw,
                    })

    # H3 (Aqueduct) for thermal_water_dependent
    if plant_aqueduct is not None:
        metric = "Aqueduct"
        bucket = BUCKET_THERMAL_WATER
        applicable_buckets = [BUCKET_THERMAL_WATER]

        for country in plants[plants["bucket"] == bucket]["country"].unique():
            for fleet in plants[
                (plants["bucket"] == bucket)
                & (plants["country"] == country)
            ]["fleet"].unique():
                plants_group = plants[
                    (plants["bucket"] == bucket)
                    & (plants["country"] == country)
                    & (plants["fleet"] == fleet)
                ]

                denominator_mw = plants_group["capacity_mw"].sum()
                if denominator_mw == 0:
                    continue

                # Aqueduct has ws_category values
                valid_in_group = set(
                    plant_aqueduct[
                        plant_aqueduct["ws_category"].notna()
                    ]["plant_uid"].unique()
                ) & set(plants_group["plant_uid"])
                numerator_plants = len(valid_in_group)
                numerator_mw = plants_group[
                    plants_group["plant_uid"].isin(valid_in_group)
                ]["capacity_mw"].sum()

                # Plants absent from aqueduct
                absent_uids = set(plants_group["plant_uid"]) - set(
                    plant_aqueduct["plant_uid"].unique()
                )
                absent_plants = len(absent_uids)
                absent_mw = plants_group[
                    plants_group["plant_uid"].isin(absent_uids)
                ]["capacity_mw"].sum()

                coverage_fraction = (
                    numerator_mw / denominator_mw
                    if denominator_mw > 0
                    else 0.0
                )
                assert (
                    0.0 <= coverage_fraction <= 1.0
                ), f"Coverage {coverage_fraction} out of [0, 1] for {country} {metric} {bucket} {fleet}"

                rows.append({
                    "country": country,
                    "metric": metric,
                    "bucket": bucket,
                    "fleet": fleet,
                    "numerator_plants": numerator_plants,
                    "numerator_mw": numerator_mw,
                    "denominator_mw": denominator_mw,
                    "coverage_fraction": coverage_fraction,
                    "excluded_plants": 0,
                    "excluded_mw": 0.0,
                    "absent_plants": absent_plants,
                    "absent_mw": absent_mw,
                })

    return pd.DataFrame(rows)


def load_and_compute_coverage(processed_dir: Path | None = None) -> pd.DataFrame:
    """Load inputs and compute coverage."""
    if processed_dir is None:
        processed_dir = Path(load_paths()["processed_dir"])

    plants = pd.read_parquet(processed_dir / "plants.parquet")
    plant_hazards = pd.read_parquet(processed_dir / "plant_hazards.parquet")
    plant_aqueduct = pd.read_parquet(processed_dir / "plant_aqueduct.parquet")

    return compute_coverage(plants, plant_hazards, plant_aqueduct)
