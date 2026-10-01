import pandas as pd

from craei.exposure.heat_curves import curve_table, monotone_violations

TH = (20, 30, 60)
MED = (60.0, 40.0, 10.0)


def _row(th, **extra):
    base = {"group": "g1", "fleet": "operating", "scenario": "ssp126", "threshold": th}
    base.update(extra)
    return base


def _frames():
    summ = pd.DataFrame([
        _row(t, gw_total=10.0, n_units=5, n_plants=4, n_gcm=5, pct_min=m - 5,
             pct_median=m, pct_max=m + 5, gw_min=1.0, gw_median=2.0, gw_max=3.0)
        for t, m in zip(TH, MED)
    ])
    agr = pd.DataFrame([
        _row(t, k_min=k, pct_gw=m + 5 - 2 * (k - 1), gw_exposed=1.0)
        for t, m in zip(TH, MED) for k in range(1, 6)
    ])
    infl = pd.DataFrame([
        _row(t, n_cells=12, top_cell_gw_pct=8.0, loo_min=1.0, loo_max=2.0) for t in TH[:2]
    ])
    boot = pd.DataFrame([
        _row(t, n_cells_fleet=12, nan_frac=0.0, boot_p025=10.4, boot_p975=50.6)
        for t in TH[:2]
    ])
    return summ, agr, infl, boot


def test_labels_by_threshold_and_row_count():
    tab = curve_table(*_frames(), thresholds=TH)
    assert len(tab) == 3
    lab = tab.set_index("threshold")["label"]
    assert lab[20] == "range_reported" and lab[30] == "range_reported"
    assert lab[60] == "bootstrap_not_computed"


def test_monotone_ok_and_detects_violation():
    tab = curve_table(*_frames(), thresholds=TH)
    assert monotone_violations(tab) == 0
    bad = tab.copy()
    bad.loc[bad["threshold"] == 60, "pct_median"] = 99.0
    assert monotone_violations(bad) > 0


def test_curve_matches_table1_at_shared_thresholds():
    from craei.exposure.heat_table1 import build_table1

    full = curve_table(*_frames(), thresholds=TH).set_index("threshold")
    t1 = build_table1(*_frames(), thresholds=(20, 30)).set_index("threshold")
    for th in (20, 30):
        assert full.loc[th, "pct_median"] == t1.loc[th, "pct_median"]
        assert full.loc[th, "pct_gw_k5"] == t1.loc[th, "pct_gw_k5"]