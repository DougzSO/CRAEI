"""Aqueduct 4.0 chronic water stress join (Spec §1.4 H3, §3 Step 8; COMANDO 18).

Column semantics confirmed against the primary source: WRI's own data
dictionary, `docs/refs/aqueduct40_data_dictionary.md` (fetched from
github.com/wri/Aqueduct40, see DECISIONS.md D33). Status per D31-D35/O05:

- `future_annual` `ws` (2050, `{bau|opt|pes}{30|50|80}` scenario/horizon
  codes) is available locally (`data/raw/aqueduct/<Country>/aqueduct_2050.csv`
  via `config/paths.local.yaml:aqueduct_dir`), keyed by HydroBASINS
  `pfaf_id` (one row per basin, 1:1). This module joins and classifies it
  (`load_aqueduct_future`, `join_plants_to_pfaf`, `plant_aqueduct_exposure`).
  Suffix order `_r`/`_s`/`_l`/`_c` = raw / score (0-5) / label / category
  (D33) and `_x_` = absolute value, median of the underlying 5-GCM ensemble
  (D34 -- an ensemble internal to Aqueduct, distinct from this project's
  ISIMIP3b ensemble; see LIMITATIONS.md).
- `baseline_annual` `bws` is a separate GEE collection, not yet acquired
  (D32, open). Once acquired, it is NOT 1:1 with `pfaf_id`: its key is
  `string_id` (`pfaf_id-gid_1-aqid`, the union of basin, sub-national unit
  and aquifer geometries), so multiple rows can share one `pfaf_id` (O05,
  open -- author verdict needed on aggregation before `load_aqueduct_baseline`
  does anything beyond validating the schema).
- Baseline field names differ from future-annual for the two variability
  indicators: `iav`/`sev` (baseline) vs. `iv`/`sv` (future) refer to the
  same interannual/seasonal-variability concepts under different
  abbreviations (D35). This module does not currently read either, so there
  is no mapping in code to get wrong, but a future baseline/variability
  reader must not conflate the two prefixes.

The COMANDO 14 catchment build (`craei.spatial.catchments`) keys plants to
upstream basin sets by `HYBAS_ID` for hydro catchment delineation. Aqueduct
water stress is a point value, not a catchment average (Spec §3 Step 8:
"point extraction"), so here each plant is assigned to the single
HydroBASINS polygon containing its coordinate (`basin_containing_point`,
reused from `craei.spatial.catchments`) and joined via that basin's own
`PFAF_ID` attribute -- present on every HydroBASINS level-6 polygon
alongside `HYBAS_ID`.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from craei.inventory.plants import COUNTRY_NAMES
from craei.spatial.catchments import basin_containing_point

# Kuzma et al. 2023 Aqueduct 4.0 technical note; scenario code -> SSP mapping
# stated in Spec §1.4 H3.
_SCENARIO_TO_SSP = {"opt": "ssp126", "bau": "ssp370", "pes": "ssp585"}
_HORIZON_2050 = "50"
# D33: future_annual type suffixes, confirmed against docs/refs/aqueduct40_data_dictionary.md.
_WS_SUFFIXES = {"raw": "r", "score": "s", "category": "c", "label": "l"}

# Spec §1.4 H3 published category boundaries, applied to the raw ratio.
_CATEGORY_BOUNDS = [
    (0.10, "low"),
    (0.20, "low-medium"),
    (0.40, "medium-high"),
    (0.80, "high"),
    (float("inf"), "extremely high"),
]


def _classify_ws(raw_value: float, wri_category: float | None = None) -> str | None:
    """Spec §1.4 H3 category from `raw_value`, except WRI's own sentinels pass through.

    WRI's `_c`/`_cat` column uses -1 for "Arid and Low Water Use" -- basins
    where absolute water use is negligible, for which `_r`/`_raw` is set to a
    saturated placeholder (empirically 1.0 in the local future_annual export,
    D36) that would otherwise be misread as "extremely high" (>80%) by the
    Spec cutoffs below. NaN in `_c`/`_cat` means the basin has no Aqueduct
    match at all (e.g. small islands outside its HydroBASINS coverage, D37).
    Per COMANDO 18 instruction, neither is converted to a numeric category
    (not 0, not "low"): -1 maps to "arid_low_water_use", NaN to "no_data".
    """
    if wri_category is not None and not pd.isna(wri_category):
        if int(wri_category) == -1:
            return "arid_low_water_use"
    if pd.isna(raw_value) or (wri_category is not None and pd.isna(wri_category)):
        return "no_data"
    for upper, label in _CATEGORY_BOUNDS:
        if raw_value < upper:
            return label
    return _CATEGORY_BOUNDS[-1][1]


def load_aqueduct_future(
    aqueduct_dir: Path, countries: dict[str, str] = COUNTRY_NAMES
) -> pd.DataFrame:
    """Load and reshape the local Aqueduct 4.0 `future_annual` export.

    Returns one row per (country, pfaf_id, scenario) for the 2050 horizon
    only (`_HORIZON_2050`; the 2030/2080 columns in the file are not used by
    the Spec), with columns: country, pfaf_id, scenario (ssp code),
    ws_raw, ws_score, ws_category_wri, ws_label_wri.
    """
    frames = []
    for code, name in countries.items():
        df = pd.read_csv(Path(aqueduct_dir) / name / "aqueduct_2050.csv")
        for scenario_code, ssp in _SCENARIO_TO_SSP.items():
            prefix = f"{scenario_code}{_HORIZON_2050}_ws_x_"
            frames.append(
                pd.DataFrame(
                    {
                        "country": code,
                        "pfaf_id": df["pfaf_id"],
                        "scenario": ssp,
                        "ws_raw": df[prefix + _WS_SUFFIXES["raw"]],
                        "ws_score": df[prefix + _WS_SUFFIXES["score"]],
                        "ws_category_wri": df[prefix + _WS_SUFFIXES["category"]],
                        "ws_label_wri": df[prefix + _WS_SUFFIXES["label"]],
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def load_aqueduct_baseline(path: Path | None) -> pd.DataFrame | None:
    """Load Aqueduct 4.0 `baseline_annual` (`bws`), deduplicated to (country, pfaf_id).

    Returns None (not a raised error) so callers such as
    `plant_aqueduct_exposure` can proceed with `ws`-only output while D32
    (file not yet acquired) is open.

    `baseline_annual` is keyed by `string_id` (`pfaf_id-gid_1-aqid`, the
    union of basin/sub-national-unit/aquifer geometries), not 1:1 with
    `pfaf_id`. D38 (closing O05): in the real 3-country file, `bws_raw`
    (and `bws_score`/`bws_cat`) is identical across every row sharing a
    (country, pfaf_id) -- `bws` is a per-sub-basin indicator, replicated
    across the intersecting `gid_1`/`aqid` pieces of `string_id`, not a
    distinct value per piece. Verified empirically (0 basins with >1
    distinct `bws_raw` value across all 1,555 (country, pfaf_id) groups in
    BRA/IND/PRT) before choosing this, per instruction not to pick an
    aggregation rule before checking whether one is even needed. This is
    exact deduplication, not an estimate, so no `area_km2` weighting and no
    tier 3 (unlike D06/D07/D08-style author judgment calls).
    """
    if path is None or not Path(path).exists():
        return None
    df = pd.read_csv(path)
    required = {"string_id", "pfaf_id", "area_km2", "bws_raw", "bws_score", "bws_cat"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"baseline_annual file missing expected columns: {sorted(missing)}")
    group_cols = ["country", "pfaf_id"] if "country" in df.columns else ["pfaf_id"]
    nunique = df.groupby(group_cols)["bws_raw"].nunique()
    if (nunique > 1).any():
        raise ValueError(
            f"{(nunique > 1).sum()} {'/'.join(group_cols)} groups have >1 distinct bws_raw "
            "value -- D38's dedup-only aggregation no longer holds for this file, see O05 "
            "history in DECISIONS.md before changing this function."
        )
    keep_cols = group_cols + [
        c for c in ("bws_raw", "bws_score", "bws_cat", "bws_label") if c in df.columns
    ]
    deduped = df[keep_cols].drop_duplicates(subset=group_cols).reset_index(drop=True)
    return deduped.rename(columns={"bws_cat": "bws_category_wri", "bws_label": "bws_label_wri"})


# Max degrees from a plant to its assigned basin's own geometry before the
# match is rejected as a `basin_containing_point` nearest-fallback snapping
# to a distant, unrelated polygon rather than the plant's real basin (D37 --
# observed for Azores/Madeira, ~1000-1800 km outside HydroBASINS "eu" region
# coverage; the fallback silently picked a mainland Portugal basin ~9-17
# degrees away). 1 degree ~ 111 km at the equator, generous for a real
# coastline-snapping case while rejecting island/region gaps like this one.
_MAX_BASIN_SNAP_DEG = 1.0


def join_plants_to_pfaf(
    plants: pd.DataFrame,
    basins_by_region: dict[str, gpd.GeoDataFrame],
    region_by_country: dict[str, str],
) -> pd.DataFrame:
    """Map each plant's coordinate to the HydroBASINS polygon containing it, then its `PFAF_ID`.

    `plants` needs columns `plant_uid`, `country`, `lat`, `lon`. Returns
    `plant_uid`, `country`, `pfaf_id` (nullable Int64 -- `pd.NA` when the
    plant is farther than `_MAX_BASIN_SNAP_DEG` from any basin in its
    region, e.g. a coastline/island gap in the HydroBASINS coverage; see
    `_MAX_BASIN_SNAP_DEG` docstring, D37).
    """
    rows = []
    for _, plant in plants.iterrows():
        region = region_by_country[plant["country"]]
        basins = basins_by_region[region]
        point = gpd.GeoSeries(gpd.points_from_xy([plant["lon"]], [plant["lat"]]), crs="EPSG:4326")
        basin_id = basin_containing_point(basins, plant["lat"], plant["lon"])
        basin_row = basins.loc[basins["HYBAS_ID"] == basin_id].iloc[0]
        if basin_row["geometry"].distance(point.iloc[0]) > _MAX_BASIN_SNAP_DEG:
            pfaf_id = pd.NA
        else:
            pfaf_id = int(basin_row["PFAF_ID"])
        rows.append(
            {"plant_uid": plant["plant_uid"], "country": plant["country"], "pfaf_id": pfaf_id}
        )
    return pd.DataFrame(rows).astype({"pfaf_id": "Int64"})


def plant_aqueduct_exposure(
    plant_pfaf: pd.DataFrame,
    aqueduct_future: pd.DataFrame,
    aqueduct_baseline: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Water-dependent thermal plant exposure to Aqueduct categories.

    Output shape per Spec §3 Step 8: `plant_uid`, `scenario`, `ws_value`,
    `ws_category`. Baseline `bws_value`/`bws_category` columns are present
    but all-NaN until `aqueduct_baseline` is supplied (D32).

    Every plant gets exactly 3 output rows (one per SSP scenario), even if
    its `pfaf_id` has no match anywhere in `aqueduct_future` (D37 -- observed
    for some plants whose HydroBASINS polygon has no counterpart in the
    Aqueduct export, e.g. small islands): those rows get `ws_category`
    `"no_data"` rather than silently disappearing, which a plain merge on
    the already scenario-stacked `aqueduct_future` would do (a fully
    unmatched plant would contribute one NaN-scenario row instead of three
    "no_data" rows).
    """
    scenarios = pd.DataFrame({"scenario": sorted(set(_SCENARIO_TO_SSP.values()))})
    plant_scenario = plant_pfaf.merge(scenarios, how="cross")
    out = plant_scenario.merge(aqueduct_future, on=["country", "pfaf_id", "scenario"], how="left")
    out = out.rename(columns={"ws_raw": "ws_value"})
    out["ws_category"] = [
        _classify_ws(v, c) for v, c in zip(out["ws_value"], out["ws_category_wri"], strict=True)
    ]

    if aqueduct_baseline is not None:
        out = out.merge(
            aqueduct_baseline[["country", "pfaf_id", "bws_raw", "bws_category_wri"]],
            on=["country", "pfaf_id"],
            how="left",
        )
        out = out.rename(columns={"bws_raw": "bws_value"})
        out["bws_category"] = [
            _classify_ws(v, c)
            for v, c in zip(out["bws_value"], out["bws_category_wri"], strict=True)
        ]
    else:
        out["bws_value"] = pd.NA
        out["bws_category"] = pd.NA

    return out[
        ["plant_uid", "scenario", "ws_value", "ws_category", "bws_value", "bws_category"]
    ]
