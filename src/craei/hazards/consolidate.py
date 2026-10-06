"""Consolidate hazard indices by plant (Spec §1.4, §3 Step 7; COMANDO 18).

Joins the per-cell/per-catchment climate indices (`indices_daily.parquet`,
`spei.parquet`) onto `plants.parquet`, producing one long table of
(plant, model, scenario, bucket, hazard) -> baseline/future/delta/ratio.

Bucket assignment (Spec §1.4):
- hydro_reservoir: F_D, R_D of catchment-scale SPEI-12 only.
- hydro_run_of_river: same, plus catchment-scale SPEI-3 as an additional
  (not substitute) metric.
- thermal_water_dependent: cell-scale delta TX35/TX40, plus cell-scale F_D/
  R_D of SPEI-12 (SPEI, not SPI -- SPI-12 is COMANDO 22's sensitivity test).
- thermal_air_only: cell-scale delta TX35/TX40 only.
- solar/other: no H1/H2 metrics (solar's own SI temperature-loss metric is
  not computed here -- see docs/DECISIONS.md for the open item).
H4 (wet-day P95 exceedance ratio, Rx5day % change) is Supplementary
Information and is attached for every fleet that has a linked cell,
regardless of bucket.

All aggregation here is `groupby(...).mean()`/`.agg()` (a reduction, one
scalar per group), never `.transform()`/`.apply()`/`.rolling()` over the
full table (CLAUDE.md Rule 11) -- `spei.parquet` (28M rows) and
`indices_daily.parquet` (17M rows) are large enough that a per-group-object
pattern would repeat COMANDO 17's memory crash (docs/DECISIONS.md D44).
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_params, load_paths

# Public: the single source of truth for bucket name strings (COMANDO 18-B
# Action 4 -- previously only defined here with a leading underscore, while
# scripts/09_consolidate.py separately repeated the literals
# ["thermal_air_only", "solar", "other"]; centralized here, no other module
# now hardcodes a bucket name).
BUCKET_HYDRO_RESERVOIR = _BUCKET_HYDRO_RESERVOIR = "hydro_reservoir"
BUCKET_HYDRO_ROR = _BUCKET_HYDRO_ROR = "hydro_run_of_river"
BUCKET_THERMAL_WATER = _BUCKET_THERMAL_WATER = "thermal_water_dependent"
BUCKET_THERMAL_AIR = _BUCKET_THERMAL_AIR = "thermal_air_only"
BUCKET_SOLAR = _BUCKET_SOLAR = "solar"
BUCKET_OTHER = _BUCKET_OTHER = "other"

_SSP_SCENARIOS = ("ssp126", "ssp370", "ssp585")


def _assign_bucket(plants: pd.DataFrame) -> pd.Series:
    """Spec §1.4 only names two hydro buckets, reservoir and run-of-river.
    `plants.parquet`'s `hydro_type` has a third value, "pumped storage"
    (100 plants) -- not run-of-river, so it is grouped into
    `hydro_reservoir` here (catchment-scale SPEI-12 only, no SPEI-3), the
    closer of the two Spec buckets since pumped storage draws on a
    reservoir rather than run-of-river flow. Not a resolved methodological
    distinction; flagged as a judgment call, not silently assumed.
    """
    tech = plants["tech_class"]
    hydro_type = plants["hydro_type"]
    bucket = pd.Series(_BUCKET_OTHER, index=plants.index, dtype="object")
    is_hydro = tech == "hydro"
    bucket[is_hydro & (hydro_type == "run-of-river")] = _BUCKET_HYDRO_ROR
    bucket[is_hydro & (hydro_type != "run-of-river")] = _BUCKET_HYDRO_RESERVOIR
    bucket[tech == "thermal_water_dependent"] = _BUCKET_THERMAL_WATER
    bucket[tech == "thermal_air_only"] = _BUCKET_THERMAL_AIR
    bucket[tech == "solar_pv"] = _BUCKET_SOLAR
    return bucket


def load_plant_hazard_inputs(processed_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the inputs Step 7 needs, from `paths.local.yaml:processed_dir` by default."""
    if processed_dir is None:
        processed_dir = Path(load_paths()["processed_dir"])
    return {
        "plants": pd.read_parquet(processed_dir / "plants.parquet"),
        "indices_daily": pd.read_parquet(processed_dir / "indices_daily.parquet"),
        "spei": pd.read_parquet(processed_dir / "spei.parquet"),
        "plant_cell": pd.read_parquet(processed_dir / "plant_cell.parquet"),
    }


def _baseline_future(df: pd.DataFrame, keys: list[str], value_col: str) -> pd.DataFrame:
    """Reshape a (key..., scenario, period, value_col) table to one row per
    (key..., ssp scenario) with baseline_value/future_value columns.

    `period == "baseline"` rows always carry `scenario == "historical"`
    (verified against the real data: every model has exactly one
    historical/baseline block and 3 ssp*/future blocks, no other
    combination occurs). Baseline is broadcast to each of the 3 ssp
    scenarios sharing the same non-scenario keys (e.g. same id/model).
    """
    non_scenario_keys = [k for k in keys if k != "scenario"]
    baseline = df[df["period"] == "baseline"][non_scenario_keys + [value_col]].rename(
        columns={value_col: "baseline_value"}
    )
    future = df[df["period"] == "future"][keys + [value_col]].rename(
        columns={value_col: "future_value"}
    )
    return future.merge(baseline, on=non_scenario_keys, how="left")


def compute_heat_hazards(
    plants_thermal: pd.DataFrame, indices_daily: pd.DataFrame, plant_cell: pd.DataFrame
) -> pd.DataFrame:
    """ΔTX35 and ΔTX40 per thermal plant, model, ssp scenario (cell-scale, Spec H1)."""
    heat = indices_daily[indices_daily["index"].isin(["tx35", "tx40"])]
    agg = (
        heat.groupby(["cell_lat", "cell_lon", "model", "scenario", "period", "index"], as_index=False)
        .agg(value=("value", "mean"))
    )
    keys = ["cell_lat", "cell_lon", "model", "scenario", "index"]
    bf = _baseline_future(agg, keys, "value")
    bf["delta"] = bf["future_value"] - bf["baseline_value"]
    bf["ratio"] = np.nan

    plant_cells = plants_thermal.merge(plant_cell, on="plant_uid", how="left")
    plant_cells = plant_cells.dropna(subset=["cell_lat", "cell_lon"])
    out = plant_cells[["plant_uid", "bucket", "cell_lat", "cell_lon"]].merge(
        bf, on=["cell_lat", "cell_lon"], how="inner"
    )
    out["hazard"] = out["index"].str.upper()
    return out[
        ["plant_uid", "bucket", "model", "scenario", "hazard", "baseline_value", "future_value", "delta", "ratio"]
    ]


def _f_d_r_d(
    spei_scale: pd.DataFrame, plant_key: pd.DataFrame, spei_col: str, hazard_name: str, threshold: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """F_D (severe-drought month fraction) and R_D per (plant, model, ssp scenario).

    `plant_key` maps plant_uid/bucket -> the spei `id` value to join on
    (catchment: plant_uid itself; cell: "{cell_lat}_{cell_lon}" string,
    scripts/08_spei.py's own construction). Returns (hazard rows,
    R_D-baseline-zero rows for Action 2's report).

    Pre-filters to `plant_key["id"]` before the groupby: the cell-scale
    table (`spei.parquet` "cell" rows) covers every cell in the country
    grid, most of which no plant is linked to, and this project's ~6 GB
    RAM budget (CLAUDE.md Rule 11) makes it worth avoiding the full-table
    aggregation when a cheap `isin` filter narrows it first.
    """
    relevant = spei_scale[spei_scale["id"].isin(set(plant_key["id"]))]
    valid = relevant[relevant[spei_col].notna()].copy()
    valid["severe"] = valid[spei_col] <= threshold
    f_d = (
        valid.groupby(["id", "model", "scenario", "period"], as_index=False)
        .agg(f_d=("severe", "mean"), n_months=("severe", "size"))
    )
    f_d["f_d"] = f_d["f_d"] * 100.0

    bf = _baseline_future(f_d, ["id", "model", "scenario"], "f_d")
    bf["ratio"] = np.where(bf["baseline_value"] == 0, np.nan, bf["future_value"] / bf["baseline_value"])
    bf["delta"] = np.nan
    bf["hazard"] = hazard_name

    out = plant_key.merge(bf, on="id", how="inner")
    zero_rows = out[(out["baseline_value"] == 0)][
        ["plant_uid", "bucket", "model", "scenario"]
    ].assign(hazard=hazard_name, reason="baseline_zero")

    result = out[
        ["plant_uid", "bucket", "model", "scenario", "hazard", "baseline_value", "future_value", "delta", "ratio"]
    ]
    return result, zero_rows


def compute_drought_hazards(
    plants: pd.DataFrame, spei: pd.DataFrame, plant_cell: pd.DataFrame, threshold: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """F_D/R_D for SPEI-12 (all H2 buckets) and SPEI-3 (run-of-river only)."""
    results = []
    zero_reports = []

    hydro = plants[plants["bucket"].isin([_BUCKET_HYDRO_RESERVOIR, _BUCKET_HYDRO_ROR])]
    hydro_key = hydro[["plant_uid", "bucket"]].assign(id=hydro["plant_uid"])
    catchment_spei = spei[spei["scale"] == "catchment"]

    r, z = _f_d_r_d(catchment_spei, hydro_key, "SPEI_12", "f_d_spei12", threshold)
    results.append(r)
    zero_reports.append(z)

    r_spi, z_spi = _f_d_r_d(catchment_spei, hydro_key, "SPI_12", "f_d_spi12", threshold)
    results.append(r_spi)
    zero_reports.append(z_spi)

    ror_key = hydro_key[hydro_key["bucket"] == _BUCKET_HYDRO_ROR]
    r3, z3 = _f_d_r_d(catchment_spei, ror_key, "SPEI_3", "f_d_spei3", threshold)
    results.append(r3)
    zero_reports.append(z3)

    thermal_water = plants[plants["bucket"] == _BUCKET_THERMAL_WATER]
    tw_cells = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(
        subset=["cell_lat", "cell_lon"]
    )
    tw_key = tw_cells[["plant_uid", "bucket"]].assign(
        id=tw_cells["cell_lat"].astype(str) + "_" + tw_cells["cell_lon"].astype(str)
    )
    cell_spei = spei[spei["scale"] == "cell"]
    rt, zt = _f_d_r_d(cell_spei, tw_key, "SPEI_12", "f_d_spei12", threshold)
    results.append(rt)
    zero_reports.append(zt)

    rt_spi, zt_spi = _f_d_r_d(cell_spei, tw_key, "SPI_12", "f_d_spi12", threshold)
    results.append(rt_spi)
    zero_reports.append(zt_spi)

    return pd.concat(results, ignore_index=True), pd.concat(zero_reports, ignore_index=True)


def compute_h4_si(
    plants: pd.DataFrame, indices_daily: pd.DataFrame, plant_cell: pd.DataFrame
) -> pd.DataFrame:
    """H4 (Supplementary Information): P95 exceedance ratio and % change in Rx5day, all fleets."""
    h4 = indices_daily[indices_daily["index"].isin(["p95_exceedance_frequency", "rx5day"])]
    agg = (
        h4.groupby(["cell_lat", "cell_lon", "model", "scenario", "period", "index"], as_index=False)
        .agg(value=("value", "mean"))
    )
    keys = ["cell_lat", "cell_lon", "model", "scenario", "index"]
    bf = _baseline_future(agg, keys, "value")

    # Spec §1.4 H4: p95 exceedance is a ratio of exceedance frequency;
    # Rx5day's change metric is stated as a *percentage* change, not an
    # absolute delta -- (future - baseline) / baseline * 100, stored in the
    # `delta` column (the schema has no separate "% column"; `ratio` stays
    # NaN for this hazard since it is not expressed as a plain future/
    # baseline ratio).
    is_ratio = bf["index"] == "p95_exceedance_frequency"
    bf["ratio"] = np.where(
        is_ratio,
        np.where(bf["baseline_value"] == 0, np.nan, bf["future_value"] / bf["baseline_value"]),
        np.nan,
    )
    bf["delta"] = np.where(
        ~is_ratio,
        np.where(
            bf["baseline_value"] == 0,
            np.nan,
            (bf["future_value"] - bf["baseline_value"]) / bf["baseline_value"] * 100.0,
        ),
        np.nan,
    )
    bf["hazard"] = np.where(is_ratio, "h4_p95_ratio", "h4_rx5day_pct_change")

    plant_cells = plants.merge(plant_cell, on="plant_uid", how="left").dropna(
        subset=["cell_lat", "cell_lon"]
    )
    out = plant_cells[["plant_uid", "bucket", "cell_lat", "cell_lon"]].merge(
        bf, on=["cell_lat", "cell_lon"], how="inner"
    )
    return out[
        ["plant_uid", "bucket", "model", "scenario", "hazard", "baseline_value", "future_value", "delta", "ratio"]
    ]


def plant_hazards(
    plants: pd.DataFrame,
    indices_daily: pd.DataFrame,
    spei: pd.DataFrame,
    plant_cell: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Consolidate H1/H2/H4(SI) into one long table, keyed plant_uid/model/scenario/bucket/hazard.

    Returns (plant_hazards, r_d_baseline_zero_report) -- the second is
    Action 2's per-(plant, model, scenario, hazard) list of R_D left NaN
    because the baseline F_D was exactly zero.
    """
    params = load_params()
    threshold = params["drought_spei_threshold"]["value"]

    plants = plants.copy()
    plants["bucket"] = _assign_bucket(plants)

    thermal = plants[plants["bucket"].isin([_BUCKET_THERMAL_WATER, _BUCKET_THERMAL_AIR])]
    heat = compute_heat_hazards(thermal, indices_daily, plant_cell)
    gc.collect()
    drought, r_d_zero = compute_drought_hazards(plants, spei, plant_cell, threshold)
    gc.collect()
    h4 = compute_h4_si(plants, indices_daily, plant_cell)
    gc.collect()

    hazards = pd.concat([heat, drought, h4], ignore_index=True)
    return hazards, r_d_zero
