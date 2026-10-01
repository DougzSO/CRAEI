"""Hand-computed checks for craei.exposure.heat_influence."""
from __future__ import annotations

import pandas as pd
import pytest

from craei.exposure import heat_influence as hi


def _df() -> pd.DataFrame:
    rows = [
        ("A", "gas", 100.0),
        ("B", "gas", 300.0),
        ("C", "gas", 250.0),
        ("D", "coal", 100.0),
    ]
    units = pd.DataFrame(rows, columns=["plant_uid", "fuel_class", "capacity_mw"])
    units["fleet"] = "operating"
    delta = {
        "m1": {"A": 40.0, "B": 10.0, "C": 40.0, "D": 40.0},
        "m2": {"A": 20.0, "B": 35.0, "C": 31.0, "D": 0.0},
    }
    haz = [(p, m, "ssp126", d) for m, v in delta.items() for p, d in v.items()]
    haz = pd.DataFrame(haz, columns=["plant_uid", "model", "scenario", "delta"])
    return units.merge(haz, on="plant_uid")


def _cells(drop: str | None = None) -> pd.DataFrame:
    rows = [("A", -1.0, -1.0), ("B", -2.0, -2.0), ("C", -3.0, -3.0), ("D", -4.0, -4.0)]
    cells = pd.DataFrame(rows, columns=["plant_uid", "cell_lat", "cell_lon"])
    return cells[cells["plant_uid"] != drop]


def _row(out: pd.DataFrame, group: str) -> pd.Series:
    return out[(out["group"] == group) & (out["fleet"] == "operating")].iloc[0]


def test_leave_one_cell_out_values_and_top_cell() -> None:
    out = hi.leave_one_cell_out(_df(), _cells(), "fuel_class")
    gas = _row(out, "gas")
    assert gas["n_cells"] == 3
    assert gas["gw_total"] == pytest.approx(0.65)
    assert gas["pct_median"] == pytest.approx(900.0 / 13.0)
    assert gas["loo_min"] == pytest.approx(50.0)
    assert gas["loo_max"] == pytest.approx(600.0 / 7.0)
    assert gas["top_cell_lat"] == -3.0
    assert gas["top_shift_pp"] == pytest.approx(50.0 - 900.0 / 13.0)
    assert gas["top_cell_gw_pct"] == pytest.approx(100.0 * 250.0 / 650.0)


def test_single_cell_group_is_undefined_not_an_error() -> None:
    out = hi.leave_one_cell_out(_df(), _cells(), "fuel_class")
    coal = _row(out, "coal")
    assert coal["n_cells"] == 1
    assert pd.isna(coal["loo_min"]) and pd.isna(coal["loo_max"])


def test_rejects_plant_without_cell() -> None:
    with pytest.raises(ValueError, match="no cell"):
        hi.leave_one_cell_out(_df(), _cells(drop="D"), "fuel_class")