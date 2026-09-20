"""Aqueduct 4.0 chronic water stress join (Spec §1.4 H3, §3 Step 8; COMANDO 18).

Join skeleton only -- not yet wired to real data. See docs/DECISIONS.md D31/D32:

- `future_annual` `ws` (2050, `{bau|opt|pes}{30|50|80}` scenario/horizon codes)
  is available locally (`data/raw/aqueduct/aqueduct_2050.csv` via
  `config/paths.local.yaml:aqueduct_dir`), keyed by HydroBASINS `pfaf_id`.
- `baseline_annual` `bws` is a separate GEE collection, not yet acquired
  (D32, open) -- the classification step below cannot run until it lands.

The COMANDO 14 catchment build (`craei.spatial.catchments`) keys plants to
upstream basin sets by `HYBAS_ID`, not `pfaf_id`. HydroBASINS carries both
attributes on the same polygon, so the join is HYBAS_ID -> polygon ->
PFAF_ID -> aqueduct row, not a direct ID match; this still needs to be
implemented and verified against a few known basins once D32 unblocks the
rest of the pipeline (the join can be written and tested against `ws` alone
before that, but there is no reason to build it half-finished now).
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd


def load_aqueduct_future(csv_path: Path) -> pd.DataFrame:
    """Load the local Aqueduct 4.0 `future_annual` export (`ws`, pfaf_id-keyed)."""
    raise NotImplementedError("wire to aqueduct_2050.csv per-country files; see D31")


def load_aqueduct_baseline(path: Path) -> pd.DataFrame:
    """Load Aqueduct 4.0 `baseline_annual` (`bws`, pfaf_id-keyed). Blocked on D32."""
    raise NotImplementedError("baseline_annual not yet acquired -- see D32")


def join_pfaf_to_basins(basins: gpd.GeoDataFrame, aqueduct: pd.DataFrame) -> pd.DataFrame:
    """Map each HYBAS_ID basin to its PFAF_ID, then to its aqueduct row.

    `basins` is the HydroBASINS GeoDataFrame from
    `craei.spatial.catchments.load_hydrobasins`. `aqueduct` is keyed by
    `pfaf_id` (see `load_aqueduct_future`/`load_aqueduct_baseline`).
    """
    raise NotImplementedError("pending D32; see module docstring")


def plant_aqueduct_exposure(
    catchment_weights: pd.DataFrame, aqueduct_by_basin: pd.DataFrame
) -> pd.DataFrame:
    """Water-dependent thermal plant exposure to Aqueduct categories.

    Output shape per Spec §3 Step 8: `plant_uid`, `scenario`, `ws_value`,
    `ws_category` (baseline `bws_value`/`bws_category` columns added once
    D32 is resolved).
    """
    raise NotImplementedError("pending D32; see module docstring")
