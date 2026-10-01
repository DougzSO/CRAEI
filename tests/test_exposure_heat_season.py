"""Hand-computed checks for craei.exposure.heat_season."""
from __future__ import annotations

import pandas as pd
import pytest

from craei.exposure import heat_season as hs

BASE = {"A": {1: (0.0, 2.0), 7: (4.0, 6.0)}, "B": {1: (0.0, 0.0), 7: (2.0, 2.0)}}
FUT = {"A": {1: (3.0, 5.0), 7: (10.0, 12.0)}, "B": {1: (1.0, 1.0), 7: (8.0, 10.0)}}
COORD = {"A": (-1.0, -1.0), "B": (-2.0, -2.0)}
COLS = ["cell_lat", "cell_lon", "model", "scenario", "period", "year", "month", "value"]


def _n35(models: tuple[tuple[str, float], ...] = (("m1", 1.0),)) -> pd.DataFrame:
    rows = []
    for model, mult in models:
        for cell, (lat, lon) in COORD.items():
            specs = (
                ("baseline", "historical", BASE, 2000, 1.0),
                ("future", "ssp126", FUT, 2050, mult),
            )
            for period, scen, src, y0, factor in specs:
                for mo, vals in src[cell].items():
                    for i, v in enumerate(vals):
                        stamp = pd.Timestamp(y0 + i, mo, 1)
                        rows.append(
                            (lat, lon, model, scen, period, y0 + i, stamp, v * factor)
                        )
    return pd.DataFrame(rows, columns=COLS)


def _weights() -> pd.DataFrame:
    return pd.DataFrame(
        {"cell_lat": [-1.0, -2.0], "cell_lon": [-1.0, -2.0], "mw": [100.0, 300.0]}
    )


def test_profile_is_capacity_weighted_and_sums_to_annual() -> None:
    prof = hs.monthly_profile(_n35(), _weights())
    jan = prof[prof["month"] == 1].iloc[0]
    jul = prof[prof["month"] == 7].iloc[0]
    assert (jan["delta_n35"], jan["base_n35"], jan["fut_n35"]) == pytest.approx(
        (1.5, 0.25, 1.75)
    )
    assert (jul["delta_n35"], jul["base_n35"], jul["fut_n35"]) == pytest.approx(
        (6.75, 2.75, 9.5)
    )
    assert jan["gw"] == pytest.approx(0.4)
    assert jan["n_cells"] == 2
    assert jan["delta_annual"] == pytest.approx(8.25)
    assert jan["share_of_annual"] == pytest.approx(1.5 / 8.25)


def test_rejects_weight_cell_without_n35_rows() -> None:
    w = pd.concat(
        [_weights(), pd.DataFrame({"cell_lat": [-3.0], "cell_lon": [-3.0], "mw": [5.0]})],
        ignore_index=True,
    )
    with pytest.raises(ValueError, match="without n35"):
        hs.monthly_profile(_n35(), w)


def test_summary_over_gcms() -> None:
    prof = hs.monthly_profile(_n35((("m1", 1.0), ("m2", 2.0))), _weights())
    s = hs.summarise_gcms(prof)
    jan = s[s["month"] == 1].iloc[0]
    assert jan["n_gcm"] == 2
    assert (jan["delta_min"], jan["delta_median"], jan["delta_max"]) == pytest.approx(
        (1.5, 2.375, 3.25)
    )
    assert jan["share_min"] == pytest.approx(3.25 / 19.5)
    assert jan["share_max"] == pytest.approx(1.5 / 8.25)