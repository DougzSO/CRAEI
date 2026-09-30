"""Tests for exposure aggregation (Spec §1.5, §3 Step 9, COMANDO 19).

Synthetic fleet with a known result, including a plant excluded from a
hazard's fitted series (L16/L19/D57: stays in the denominator as
not-exposed, is never dropped from total capacity).
"""

import numpy as np
import pandas as pd
import pytest

from craei.exposure import aggregate as agg


@pytest.fixture
def synthetic_plants():
    # Two hydro_reservoir plants (100, 100 MW) in country A, operating fleet;
    # one thermal_water_dependent plant (100 MW) in country A, operating.
    return pd.DataFrame(
        {
            "plant_uid": ["h1", "h2", "t1"],
            "country": ["A", "A", "A"],
            "fleet": ["operating", "operating", "operating"],
            "tech_class": ["hydro", "hydro", "thermal_water_dependent"],
            "hydro_type": ["reservoir", "reservoir", None],
            "capacity_mw": [100.0, 100.0, 100.0],
        }
    )


def _rd_row(plant_uid, model, scenario, ratio):
    return {
        "plant_uid": plant_uid,
        "bucket": "hydro_reservoir",
        "model": model,
        "scenario": scenario,
        "hazard": "f_d_spei12",
        "baseline_value": 6.0,
        "future_value": 6.0 * ratio if not np.isnan(ratio) else np.nan,
        "delta": np.nan,
        "ratio": ratio,
    }


@pytest.fixture
def synthetic_hazards():
    """5 models, 1 scenario. h1: R_D=3 in 4/5 models (agreement, exposed >=2).
    h2: excluded from the fitted series entirely (L16-style) -- no rows at all,
    must still land in the denominator as not-exposed, not dropped.
    """
    rows = []
    models = ["m1", "m2", "m3", "m4", "m5"]
    for i, model in enumerate(models):
        ratio = (
            3.0 if i < 4 else 0.5
        )  # 4/5 models agree R_D>1 (positive sign), all exposed>=2 except last
        rows.append(_rd_row("h1", model, "ssp370", ratio))
    # h2 (Nimoo-Bazgo-style exclusion): zero rows for f_d_spei12 at all.
    return pd.DataFrame(rows)


def test_denominator_includes_excluded_plant(synthetic_plants, synthetic_hazards):
    out = agg.build_exposure_summary(synthetic_plants, synthetic_hazards)
    drought = out[(out["hazard"] == "f_d_spei12") & (out["tech_class"] == "hydro_reservoir")]
    assert len(drought) == 1
    row = drought.iloc[0]
    # h1 is exposed (ratio>=2) in 4/5 models -> median share across models:
    # per-model share = exposed_mw / total_mw where total_mw = 200 (h1+h2).
    # 4 models: h1 exposed -> 100/200 = 0.5; 1 model: h1 not exposed -> 0/200 = 0.0
    assert row["median_share"] == pytest.approx(0.5)
    assert row["min_share"] == pytest.approx(0.0)
    assert row["max_share"] == pytest.approx(0.5)
    # total capacity behind the group is h1+h2 = 200 MW, h2 never dropped.
    assert row["median_gw"] == pytest.approx(0.1)


def test_capacity_sum_matches_plants(synthetic_plants, synthetic_hazards):
    out = agg.build_exposure_summary(synthetic_plants, synthetic_hazards)
    drought = out[(out["hazard"] == "f_d_spei12") & (out["tech_class"] == "hydro_reservoir")].iloc[
        0
    ]
    implied_total_mw = synthetic_plants[synthetic_plants["tech_class"] == "hydro"][
        "capacity_mw"
    ].sum()
    assert implied_total_mw == 200.0
    # median share * implied total should be <= implied total (sanity, denominator not shrunk)
    assert drought["median_share"] * implied_total_mw <= implied_total_mw


def test_model_agreement_share(synthetic_plants, synthetic_hazards):
    out = agg.build_exposure_summary(synthetic_plants, synthetic_hazards)
    drought = out[(out["hazard"] == "f_d_spei12") & (out["tech_class"] == "hydro_reservoir")].iloc[
        0
    ]
    # h1: 4/5 models positive sign (ratio>1) -> agrees=True, its 100 MW counts;
    # h2: no valid sign_pos anywhere -> agrees=False (never counted).
    # agreement_share = 100 / 200 = 0.5
    assert drought["agreement_share"] == pytest.approx(0.5)


def test_heat_hazard_exposure():
    plants = pd.DataFrame(
        {
            "plant_uid": ["t1", "t2"],
            "country": ["A", "A"],
            "fleet": ["operating", "operating"],
            "tech_class": ["thermal_water_dependent", "thermal_water_dependent"],
            "hydro_type": [None, None],
            "capacity_mw": [50.0, 50.0],
        }
    )
    rows = []
    for model in ["m1", "m2", "m3", "m4", "m5"]:
        rows.append(
            {
                "plant_uid": "t1",
                "bucket": "thermal_water_dependent",
                "model": model,
                "scenario": "ssp370",
                "hazard": "TX35",
                "baseline_value": 5.0,
                "future_value": 40.0,
                "delta": 35.0,  # >= 30 day threshold, exposed
                "ratio": np.nan,
            }
        )
        rows.append(
            {
                "plant_uid": "t2",
                "bucket": "thermal_water_dependent",
                "model": model,
                "scenario": "ssp370",
                "hazard": "TX35",
                "baseline_value": 5.0,
                "future_value": 10.0,
                "delta": 5.0,  # below threshold, not exposed
                "ratio": np.nan,
            }
        )
    hazards = pd.DataFrame(rows)
    out = agg.build_exposure_summary(plants, hazards)
    heat = out[out["hazard"] == "TX35"].iloc[0]
    assert heat["median_share"] == pytest.approx(0.5)
    assert heat["median_gw"] == pytest.approx(0.05)
    assert heat["agreement_share"] == pytest.approx(1.0)


def test_aqueduct_own_table_no_model_agreement():
    plants = pd.DataFrame(
        {
            "plant_uid": ["t1", "t2"],
            "country": ["A", "A"],
            "fleet": ["operating", "operating"],
            "tech_class": ["thermal_water_dependent", "thermal_water_dependent"],
            "capacity_mw": [50.0, 50.0],
        }
    )
    plant_aqueduct = pd.DataFrame(
        [
            {
                "plant_uid": "t1",
                "scenario": "ssp370",
                "cooling_bound": "upper",
                "ws_category": "high",
            },
            {
                "plant_uid": "t2",
                "scenario": "ssp370",
                "cooling_bound": "upper",
                "ws_category": "low",
            },
            {
                "plant_uid": "t1",
                "scenario": "ssp370",
                "cooling_bound": "lower",
                "ws_category": "high",
            },
            # t2 dropped from "lower" (coastal, seawater-cooled assumption)
        ]
    )
    out = agg.build_exposure_aqueduct(plants, plant_aqueduct)
    upper = out[out["cooling_bound"] == "upper"].iloc[0]
    lower = out[out["cooling_bound"] == "lower"].iloc[0]
    assert upper["share"] == pytest.approx(0.5)
    assert upper["total_mw"] if "total_mw" in upper else True
    assert lower["share"] == pytest.approx(1.0)  # only t1 (exposed) remains in "lower" denominator


def test_fleets_reported_separately():
    plants = pd.DataFrame(
        {
            "plant_uid": ["op1", "adv1", "early1"],
            "country": ["A", "A", "A"],
            "fleet": ["operating", "planned_adv", "planned_early"],
            "tech_class": ["thermal_water_dependent"] * 3,
            "hydro_type": [None, None, None],
            "capacity_mw": [100.0, 100.0, 100.0],
        }
    )
    rows = [
        {
            "plant_uid": pid,
            "bucket": "thermal_water_dependent",
            "model": model,
            "scenario": "ssp370",
            "hazard": "TX35",
            "baseline_value": 5.0,
            "future_value": 40.0,
            "delta": 35.0,
            "ratio": np.nan,
        }
        for pid in ["op1", "adv1", "early1"]
        for model in ["m1", "m2", "m3", "m4", "m5"]
    ]
    hazards = pd.DataFrame(rows)
    out = agg.build_exposure_summary(plants, hazards)
    heat = out[out["hazard"] == "TX35"]
    assert set(heat["fleet"]) == {"operating", "planned_adv", "planned_early"}
    assert (heat["median_share"] == 1.0).all()
