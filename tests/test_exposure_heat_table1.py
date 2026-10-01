import numpy as np
import pandas as pd
import pytest

from craei.exposure.heat_table1 import build_table1

KEYS = [("g1", 30), ("g2", 30), ("g1", 60)]


def _row(g, th, **extra):
    base = {"group": g, "fleet": "operating", "scenario": "ssp126", "threshold": th}
    base.update(extra)
    return base


def _frames(nan_frac=0.0):
    summ = pd.DataFrame([
        _row(g, th, gw_total=10.0, n_units=5, n_plants=4, n_gcm=5, pct_min=10.0,
             pct_median=20.0, pct_max=30.0, gw_min=1.0, gw_median=2.0, gw_max=3.0)
        for g, th in KEYS
    ])
    agr = pd.DataFrame([
        _row(g, th, k_min=k, pct_gw=50.0 - 5 * k, gw_exposed=5.0 - k)
        for g, th in KEYS for k in range(1, 6)
    ])
    infl = pd.DataFrame([
        _row(g, th, n_cells=12, top_cell_gw_pct=8.0, loo_min=15.0, loo_max=25.0)
        for g, th in KEYS[:2]
    ])
    boot = pd.DataFrame([
        _row(g, th, n_cells_fleet=n, nan_frac=nan_frac, boot_p025=12.4, boot_p975=31.6)
        for (g, th), n in zip(KEYS[:2], (12, 3))
    ])
    return summ, agr, infl, boot


def test_table1_filters_thresholds_and_pivots_agreement():
    tab = build_table1(*_frames())
    assert len(tab) == 2
    assert set(tab["threshold"]) == {30}
    row = tab[tab["group"] == "g1"].iloc[0]
    assert row["pct_gw_k1"] == 45.0
    assert row["pct_gw_k5"] == 25.0
    assert row["n_cells"] == 12


def test_table1_applies_o25_rule():
    tab = build_table1(*_frames())
    g1 = tab[tab["group"] == "g1"].iloc[0]
    g2 = tab[tab["group"] == "g2"].iloc[0]
    assert g1["boot_reported"] and g1["label"] == "range_reported"
    assert g1["boot_p025_pp"] == 12.0 and g1["boot_p975_pp"] == 32.0
    assert not g2["boot_reported"] and g2["label"] == "descriptive"
    assert np.isnan(g2["boot_p025_pp"])
    tab2 = build_table1(*_frames(nan_frac=0.1))
    assert not tab2["boot_reported"].any()


def test_table1_rejects_duplicated_keys():
    summ, agr, infl, boot = _frames()
    infl = pd.concat([infl, infl.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        build_table1(summ, agr, infl, boot)