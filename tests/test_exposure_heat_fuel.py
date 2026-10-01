"""Hand-computed checks for craei.exposure.heat_fuel."""
from __future__ import annotations

import pandas as pd
import pytest

from craei.exposure import heat_fuel as hf


def _units() -> pd.DataFrame:
    rows = [
        ("A", "BRA", "operating", "gas", 100.0),
        ("B", "BRA", "operating", "gas", 300.0),
        ("B", "BRA", "planned_adv", "gas", 200.0),
        ("C", "BRA", "operating", "coal", 50.0),
        ("D", "PRT", "operating", "gas", 999.0),
        ("A", "BRA", "operating", "hydro", 777.0),
    ]
    cols = ["plant_uid", "country", "fleet", "fuel_class", "capacity_mw"]
    return pd.DataFrame(rows, columns=cols)


def _hazards(drop_plant: str | None = None) -> pd.DataFrame:
    delta = {
        "m1": {"A": 40, "B": 10, "C": 30, "D": 99},
        "m2": {"A": 20, "B": 35, "C": 0, "D": 0},
    }
    rows = [
        (p, m, "ssp126", "TX35", float(d))
        for m, v in delta.items()
        for p, d in v.items()
        if p != drop_plant
    ]
    rows.append(("A", "m1", "ssp126", "TX40", 999.0))
    cols = ["plant_uid", "model", "scenario", "hazard", "delta"]
    return pd.DataFrame(rows, columns=cols)


def _df() -> pd.DataFrame:
    return hf.build_unit_hazard(_units(), _hazards())


def test_build_filters_country_fuel_and_hazard() -> None:
    df = _df()
    assert len(df) == 8
    assert set(df["country"]) == {"BRA"}
    assert set(df["fuel_class"]) == {"gas", "coal"}
    assert df["delta"].max() == 40.0


def test_build_rejects_plant_without_hazard_and_duplicates() -> None:
    with pytest.raises(ValueError, match="no TX35 row"):
        hf.build_unit_hazard(_units(), _hazards(drop_plant="C"))
    dup = pd.concat([_hazards(), _hazards().iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        hf.build_unit_hazard(_units(), dup)


def test_curves_are_capacity_weighted_and_threshold_is_inclusive() -> None:
    c = hf.exposure_curves(_df(), "fuel_class", thresholds=(30,))
    gas = c[(c["group"] == "gas") & (c["fleet"] == "operating")].set_index("model")
    assert gas.loc["m1", "pct_gw"] == pytest.approx(25.0)
    assert gas.loc["m2", "pct_gw"] == pytest.approx(75.0)
    assert gas.loc["m1", "gw_total"] == pytest.approx(0.4)
    coal = c[(c["group"] == "coal") & (c["fleet"] == "operating")].set_index("model")
    assert coal.loc["m1", "pct_gw"] == pytest.approx(100.0)
    assert coal.loc["m2", "pct_gw"] == pytest.approx(0.0)


def test_all_thermal_group_and_gcm_summary() -> None:
    c = hf.exposure_curves(_df(), None, thresholds=(30,))
    op = c[c["fleet"] == "operating"].set_index("model")
    assert op.loc["m1", "pct_gw"] == pytest.approx(100.0 * 150 / 450)
    assert op.loc["m2", "pct_gw"] == pytest.approx(100.0 * 300 / 450)
    s = hf.summarise_gcms(hf.exposure_curves(_df(), "fuel_class", thresholds=(30,)))
    row = s[(s["group"] == "gas") & (s["fleet"] == "operating")].iloc[0]
    assert (row["pct_min"], row["pct_median"], row["pct_max"]) == (25.0, 50.0, 75.0)
    assert row["n_gcm"] == 2


def test_leave_one_gcm_out_range() -> None:
    c = hf.exposure_curves(_df(), "fuel_class", thresholds=(30,))
    r = hf.leave_one_gcm_out(c)
    row = r[(r["group"] == "gas") & (r["fleet"] == "operating")].iloc[0]
    assert (row["loo_min"], row["loo_max"]) == (25.0, 75.0)


def test_planned_vs_operating_counts_gcms() -> None:
    df = hf.add_pooled_planned(_df())
    c = hf.exposure_curves(df, "fuel_class", thresholds=(30,))
    s = hf.planned_vs_operating(c)
    assert set(s["group"]) == {"gas"}
    row = s.iloc[0]
    assert row["gw_planned"] == pytest.approx(0.2)
    assert (row["diff_min"], row["diff_median"], row["diff_max"]) == (-25.0, 0.0, 25.0)
    assert row["n_planned_ge"] == 1
    


def test_counts_plants_and_units() -> None:
    c = hf.exposure_curves(_df(), "fuel_class", thresholds=(30,))
    gas = c[(c["group"] == "gas") & (c["fleet"] == "operating")]
    assert set(gas["n_plants"]) == {2}
    assert set(gas["n_units"]) == {2}
    s = hf.summarise_gcms(c)
    coal = s[(s["group"] == "coal") & (s["fleet"] == "operating")].iloc[0]
    assert (coal["n_units"], coal["n_plants"]) == (1, 1)


def test_wide_by_gcm_has_one_column_per_model() -> None:
    c = hf.exposure_curves(_df(), "fuel_class", thresholds=(30,))
    w = hf.wide_by_gcm(c)
    row = w[(w["group"] == "gas") & (w["fleet"] == "operating")].iloc[0]
    assert row["pct_m1"] == pytest.approx(25.0)
    assert row["pct_m2"] == pytest.approx(75.0)