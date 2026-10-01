import numpy as np
import pandas as pd
import pytest

from craei.exposure import heat_levels as hl


def _frame():
    rows = []
    for m, lv1 in (("m1", "low"), ("m2", "high")):
        for uid, mw, lv in ((1, 100.0, lv1), (2, 50.0, "low")):
            rows.append({"group": "g", "fleet": "f", "itaipu": "na", "scenario": "ssp370",
                         "model": m, "uid": uid, "capacity_mw": mw,
                         "level_fut": lv, "level_base": "low"})
    return pd.DataFrame(rows)


CATS = {"level_fut": hl.LEVEL_LABELS, "level_base": hl.LEVEL_LABELS}


def test_classify_edges_and_nan():
    v = [0, 9.99, 10, 29.99, 30, 59.99, 60, 365]
    c = [str(x) for x in hl.classify(v, hl.LEVEL_CUTS, hl.LEVEL_LABELS)]
    assert c == ["low", "low", "medium", "medium", "high", "high", "extreme", "extreme"]
    with pytest.raises(ValueError):
        hl.classify([1.0, np.nan], hl.LEVEL_CUTS, hl.LEVEL_LABELS)


def test_cell_values_mean_delta_and_missing_baseline():
    base = {"cell_lat": 1.0, "cell_lon": 2.0, "model": "m"}
    rows = [dict(base, period="baseline", scenario="historical", value=v) for v in (10, 20)]
    rows += [dict(base, period="future", scenario="ssp126", value=v) for v in (40, 50)]
    ix = pd.DataFrame(rows)
    out = hl.cell_values(ix)
    assert out["base"].iloc[0] == 15 and out["fut"].iloc[0] == 45 and out["delta"].iloc[0] == 30
    with pytest.raises(ValueError):
        hl.cell_values(ix[ix["period"] == "future"])


def test_itaipu_versions():
    u = pd.DataFrame({"plant_uid": ["i", "i", "t"],
                      "tech_class": ["hydro", "hydro", "thermal_air_only"],
                      "capacity_mw": [8000.0, 6000.0, 100.0]})
    s = hl.with_itaipu_versions(u, {"i"}).groupby("itaipu")["capacity_mw"].sum()
    assert s["a"] == 14000 and s["b"] == 7000 and s["na"] == 100


def test_gw_by_gcm_zero_fill_sums_and_range():
    t = hl.gw_by_gcm(_frame(), ["level_fut"], CATS)
    assert len(t) == 2 * 4
    assert hl.class_sum_gap(t) == 0.0
    s = hl.summarise_gw(t, ["level_fut"]).set_index("level_fut")
    assert s.loc["high", "gw_min"] == 0.0 and s.loc["high", "gw_max"] == pytest.approx(0.1)
    assert s.loc["high", "gw_median"] == pytest.approx(0.05)
    assert s.loc["high", "pct_max"] == pytest.approx(100 * 100 / 150)
    assert s.loc["low", "gw_total"] == pytest.approx(0.15)


def test_agreement_k_not_exclusive():
    rows = []
    for m, a, b in (("m1", "extreme", "extreme"), ("m2", "extreme", "low"),
                    ("m3", "high", "low")):
        for uid, mw, lv in ((1, 100.0, a), (2, 50.0, b)):
            rows.append({"group": "g", "fleet": "f", "itaipu": "na", "scenario": "s",
                         "model": m, "uid": uid, "capacity_mw": mw, "level_fut": lv})
    k = hl.agreement_k(pd.DataFrame(rows), "level_fut", ks=(1, 2, 3)).set_index("cls")
    assert k.loc["extreme", "gw_k1"] == pytest.approx(0.15)
    assert k.loc["extreme", "gw_k2"] == pytest.approx(0.10)
    assert k.loc["extreme", "gw_k3"] == 0.0
    assert k.loc["extreme", "pct_k2"] == pytest.approx(100 * 100 / 150)


def test_level_classes_table_shape():
    t = hl.level_classes_table(_frame())
    assert len(t) == 8 and set(t["period"]) == {"future", "baseline"}
    assert set(t.loc[t["period"] == "baseline", "scenario"]) == {"baseline"}
    hi = t[(t["period"] == "future") & (t["class"] == "high")].iloc[0]
    assert hi["gw_k1"] == pytest.approx(0.1) and hi["gw_k5"] == 0.0


def test_cell_class_table_median_class_and_agreement():
    fut = [5, 12, 35, 65, 70]
    cv = pd.DataFrame({"cell_lat": 1.0, "cell_lon": 2.0, "scenario": "s",
                       "model": list("abcde"), "base": 0.0, "fut": fut,
                       "delta": [float(x) for x in fut]})
    r = hl.cell_class_table(cv).iloc[0]
    assert r["class_median"] == "high" and r["n_gcm_same"] == 1
    assert r["base_class_median"] == "low" and r["delta_class_median"] == "d_ge30"