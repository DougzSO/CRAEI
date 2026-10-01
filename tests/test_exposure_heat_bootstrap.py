"""Hand-computed checks for craei.exposure.heat_bootstrap."""
from __future__ import annotations

import pandas as pd
import pytest

from craei.exposure import heat_bootstrap as hb

COLS = ["plant_uid", "fleet", "fuel_class", "capacity_mw"]


def _df(delta: dict[str, dict[str, float]] | None = None) -> pd.DataFrame:
    rows = [
        ("A", "operating", "gas", 100.0),
        ("B", "operating", "gas", 300.0),
        ("C", "operating", "gas", 250.0),
        ("B", "planned_adv", "gas", 200.0),
        ("D", "operating", "coal", 100.0),
    ]
    delta = delta or {
        "m1": {"A": 40.0, "B": 10.0, "C": 40.0, "D": 40.0},
        "m2": {"A": 20.0, "B": 35.0, "C": 31.0, "D": 0.0},
    }
    haz = [(p, m, "ssp126", d) for m, v in delta.items() for p, d in v.items()]
    haz = pd.DataFrame(haz, columns=["plant_uid", "model", "scenario", "delta"])
    return pd.DataFrame(rows, columns=COLS).merge(haz, on="plant_uid")


def _cells() -> pd.DataFrame:
    rows = [("A", -1.0, -1.0), ("B", -2.0, -2.0), ("C", -3.0, -3.0), ("D", -4.0, -4.0)]
    return pd.DataFrame(rows, columns=["plant_uid", "cell_lat", "cell_lon"])


def _run(df=None, **kw):
    kw = {"thresholds": (30,), "n_boot": 200, **kw}
    return hb.cell_bootstrap(df if df is not None else _df(), _cells(), "fuel_class", **kw)


def test_observed_share_and_paired_difference() -> None:
    shares, paired = _run()
    op = shares[(shares["group"] == "gas") & (shares["fleet"] == "operating")].iloc[0]
    assert op["obs_median"] == pytest.approx(900.0 / 13.0)
    assert (op["n_cells"], op["n_cells_fleet"], op["nan_frac"]) == (3, 3, 0.0)
    pl = shares[(shares["group"] == "gas") & (shares["fleet"] == "planned_adv")].iloc[0]
    assert (pl["obs_median"], pl["n_cells_fleet"]) == (pytest.approx(50.0), 1)
    row = paired[paired["group"] == "gas"].iloc[0]
    assert row["obs_median_diff"] == pytest.approx(-250.0 / 13.0)
    assert (row["n_planned_ge_obs"], row["n_cells_planned"]) == (1, 1)
    assert 0.0 < row["nan_frac"] < 1.0


def test_one_cell_group_has_observed_value_but_no_percentiles() -> None:
    shares, _ = _run()
    coal = shares[(shares["group"] == "coal") & (shares["fleet"] == "operating")].iloc[0]
    assert coal["n_cells"] == 1
    assert coal["obs_median"] == pytest.approx(50.0)
    assert pd.isna(coal["boot_p025"]) and pd.isna(coal["boot_p975"])


def test_same_seed_reproduces_and_percentiles_are_ordered() -> None:
    a_shares, a_pair = _run()
    b_shares, b_pair = _run()
    pd.testing.assert_frame_equal(a_shares, b_shares)
    pd.testing.assert_frame_equal(a_pair, b_pair)
    g = a_shares.dropna(subset=["boot_p025"])
    assert (g["boot_p025"] <= g["boot_p50"]).all()
    assert (g["boot_p50"] <= g["boot_p975"]).all()


def test_uniform_exposure_gives_a_degenerate_band() -> None:
    delta = {m: {p: 40.0 for p in "ABCD"} for m in ("m1", "m2")}
    shares, _ = _run(_df(delta))
    op = shares[(shares["group"] == "gas") & (shares["fleet"] == "operating")].iloc[0]
    assert op["boot_p025"] == op["boot_p975"] == 100.0