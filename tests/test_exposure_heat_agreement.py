"""Hand-computed checks for craei.exposure.heat_agreement."""
from __future__ import annotations

import pandas as pd
import pytest

from craei.exposure import heat_agreement as ha


def _df() -> pd.DataFrame:
    rows = [
        ("A", "operating", "gas", 100.0),
        ("B", "operating", "gas", 100.0),
        ("B", "operating", "gas", 200.0),
    ]
    units = pd.DataFrame(
        rows, columns=["plant_uid", "fleet", "fuel_class", "capacity_mw"]
    )
    delta = {
        "m1": {"A": 40.0, "B": 10.0},
        "m2": {"A": 20.0, "B": 35.0},
        "m3": {"A": 40.0, "B": 5.0},
    }
    haz = [(p, m, "ssp126", d) for m, v in delta.items() for p, d in v.items()]
    haz = pd.DataFrame(haz, columns=["plant_uid", "model", "scenario", "delta"])
    return units.merge(haz, on="plant_uid")


def _pct(out: pd.DataFrame, k: int, group: str = "gas") -> float:
    row = out[(out["group"] == group) & (out["k_min"] == k)]
    return float(row["pct_gw"].iloc[0])


def test_agreement_counts_gcms_per_plant_once() -> None:
    out = ha.agreement_gw(_df(), "fuel_class", thresholds=(30,))
    gas = out[out["k_min"] == 1].iloc[0]
    assert gas["gw_total"] == pytest.approx(0.4)
    assert gas["n_plants"] == 2
    assert _pct(out, 1) == pytest.approx(100.0)
    assert _pct(out, 2) == pytest.approx(25.0)
    assert _pct(out, 3) == pytest.approx(0.0)


def test_threshold_is_inclusive_and_all_group() -> None:
    out = ha.agreement_gw(_df(), None, thresholds=(40,))
    assert _pct(out, 1, "all_thermal") == pytest.approx(25.0)
    assert _pct(out, 2, "all_thermal") == pytest.approx(25.0)
    assert _pct(out, 3, "all_thermal") == pytest.approx(0.0)


def test_rejects_plant_missing_a_gcm() -> None:
    df = _df()
    df = df[~((df["plant_uid"] == "A") & (df["model"] == "m3"))]
    with pytest.raises(ValueError, match="missing"):
        ha.agreement_gw(df, "fuel_class")