import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from craei.hazards import aqueduct as aq


def _synthetic_basins() -> gpd.GeoDataFrame:
    """Two unit-square basins with HYBAS_ID/PFAF_ID both present, as in real HydroBASINS."""
    rows = [
        {"HYBAS_ID": 10, "PFAF_ID": 111, "NEXT_DOWN": 0, "geometry": box(0, 0, 1, 1)},
        {"HYBAS_ID": 20, "PFAF_ID": 222, "NEXT_DOWN": 10, "geometry": box(1, 0, 2, 1)},
    ]
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def _write_aqueduct_csv(tmp_path, country_dir: str, pfaf_ids: list[int]) -> None:
    cols = {"pfaf_id": pfaf_ids}
    for scenario in ("bau", "opt", "pes"):
        for horizon in ("30", "50", "80"):
            prefix = f"{scenario}{horizon}_ws_x_"
            # Distinct values per scenario/horizon so misrouting is caught by tests.
            base = {"bau": 0.5, "opt": 0.05, "pes": 0.85}[scenario]
            cols[prefix + "r"] = [base] * len(pfaf_ids)
            cols[prefix + "s"] = [base * 5] * len(pfaf_ids)
            cols[prefix + "c"] = [2] * len(pfaf_ids)
            cols[prefix + "l"] = ["medium"] * len(pfaf_ids)
    df = pd.DataFrame(cols)
    out_dir = tmp_path / country_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "aqueduct_2050.csv", index=False)


def test_load_aqueduct_future_reshapes_2050_scenarios(tmp_path):
    _write_aqueduct_csv(tmp_path, "Brazil", pfaf_ids=[111, 222])

    out = aq.load_aqueduct_future(tmp_path, countries={"BRA": "Brazil"})

    assert len(out) == 2 * 3  # 2 pfaf_id x 3 scenarios
    assert set(out["scenario"]) == {"ssp126", "ssp370", "ssp585"}
    opt_row = out[(out["pfaf_id"] == 111) & (out["scenario"] == "ssp126")].iloc[0]
    assert opt_row["ws_raw"] == 0.05
    pes_row = out[(out["pfaf_id"] == 111) & (out["scenario"] == "ssp585")].iloc[0]
    assert pes_row["ws_raw"] == 0.85


def test_classify_ws_arid_low_water_use_not_reclassified_as_extremely_high():
    # Real-data pattern (D36): WRI sets raw=1.0 for cat=-1 basins, which would
    # otherwise fall in the >0.80 "extremely high" bucket by the Spec cutoffs alone.
    assert aq._classify_ws(1.0, wri_category=-1) == "arid_low_water_use"


def test_classify_ws_missing_wri_category_is_no_data_not_low():
    assert aq._classify_ws(float("nan"), wri_category=float("nan")) == "no_data"
    assert aq._classify_ws(0.05, wri_category=float("nan")) == "no_data"


def test_classify_ws_normal_value_still_uses_spec_cutoffs():
    assert aq._classify_ws(0.05, wri_category=1) == "low"
    assert aq._classify_ws(0.85, wri_category=4) == "extremely high"


def test_load_aqueduct_baseline_returns_none_when_missing():
    assert aq.load_aqueduct_baseline(None) is None
    assert aq.load_aqueduct_baseline("/does/not/exist.csv") is None


def test_load_aqueduct_baseline_dedups_string_id_split_rows(tmp_path):
    # string_id key with 2 rows sharing pfaf_id=111 (basin split across 2 sub-national
    # units), but identical bws_raw -- D38's real-data pattern: dedup, no weighting.
    df = pd.DataFrame(
        {
            "country": ["BRA", "BRA"],
            "string_id": ["111-BRA_1-0", "111-BRA_2-0"],
            "pfaf_id": [111, 111],
            "area_km2": [10.0, 20.0],
            "bws_raw": [0.3, 0.3],
            "bws_score": [1.5, 1.5],
            "bws_cat": [1, 1],
            "bws_label": ["Low-Medium", "Low-Medium"],
        }
    )
    path = tmp_path / "baseline_annual.csv"
    df.to_csv(path, index=False)

    out = aq.load_aqueduct_baseline(path)

    assert len(out) == 1
    assert out.iloc[0]["bws_raw"] == 0.3
    assert out.iloc[0]["bws_category_wri"] == 1


def test_load_aqueduct_baseline_raises_if_dedup_assumption_violated(tmp_path):
    # Divergent bws_raw within the same (country, pfaf_id) group would falsify D38.
    df = pd.DataFrame(
        {
            "country": ["BRA", "BRA"],
            "string_id": ["111-BRA_1-0", "111-BRA_2-0"],
            "pfaf_id": [111, 111],
            "area_km2": [10.0, 20.0],
            "bws_raw": [0.3, 0.6],
            "bws_score": [1.5, 3.0],
            "bws_cat": [1, 2],
        }
    )
    path = tmp_path / "baseline_annual.csv"
    df.to_csv(path, index=False)

    try:
        aq.load_aqueduct_baseline(path)
        assert False, "expected ValueError for divergent bws_raw within a group"
    except ValueError as exc:
        assert "D38" in str(exc)


def test_join_plants_to_pfaf_uses_basin_containing_point():
    basins = _synthetic_basins()
    plants = pd.DataFrame(
        {"plant_uid": ["p1", "p2"], "country": ["BRA", "BRA"], "lat": [0.5, 0.5], "lon": [0.5, 1.5]}
    )

    out = aq.join_plants_to_pfaf(
        plants,
        basins_by_region={"south_america": basins},
        region_by_country={"BRA": "south_america"},
    )

    assert out[out["plant_uid"] == "p1"]["pfaf_id"].iloc[0] == 111
    assert out[out["plant_uid"] == "p2"]["pfaf_id"].iloc[0] == 222


def test_join_plants_to_pfaf_rejects_distant_nearest_basin_fallback():
    # D37: a plant far outside any basin (e.g. an island region the HydroBASINS
    # file doesn't cover) must not silently snap to a distant unrelated basin.
    basins = _synthetic_basins()
    plants = pd.DataFrame(
        {"plant_uid": ["island"], "country": ["BRA"], "lat": [50.0], "lon": [50.0]}
    )

    out = aq.join_plants_to_pfaf(
        plants,
        basins_by_region={"south_america": basins},
        region_by_country={"BRA": "south_america"},
    )

    assert out["pfaf_id"].iloc[0] is pd.NA


def test_plant_aqueduct_exposure_classifies_and_leaves_baseline_nan(tmp_path):
    _write_aqueduct_csv(tmp_path, "Brazil", pfaf_ids=[111])
    future = aq.load_aqueduct_future(tmp_path, countries={"BRA": "Brazil"})
    plant_pfaf = pd.DataFrame({"plant_uid": ["p1"], "country": ["BRA"], "pfaf_id": [111]})

    out = aq.plant_aqueduct_exposure(plant_pfaf, future)

    assert len(out) == 3  # one row per scenario
    pes_row = out[out["scenario"] == "ssp585"].iloc[0]
    assert pes_row["ws_value"] == 0.85
    assert pes_row["ws_category"] == "extremely high"
    opt_row = out[out["scenario"] == "ssp126"].iloc[0]
    assert opt_row["ws_category"] == "low"
    assert out["bws_value"].isna().all()
    assert out["bws_category"].isna().all()
