import numpy as np
import pandas as pd
import pytest

from craei.hazards import drought_levels as dl


def _rows(ks, n=20):
    out = np.zeros((len(ks), n))
    for i, k in enumerate(ks):
        out[i, :k] = -2.0
    return out


def test_classify_fd_edges_and_nan():
    v = [6, 6.01, 10, 10.01, 15, 15.01]
    c = [str(x) for x in dl.classify_fd(v, (6.0, 10.0, 15.0))]
    assert c == ["low", "medium", "medium", "high", "high", "extreme"]
    with pytest.raises(ValueError):
        dl.classify_fd([1.0, np.nan], (6.0, 10.0, 15.0))


def test_classify_rd_edges_and_undefined():
    v = [1.49, 1.5, 1.99, 2.0, 3.0, 5.0, np.nan]
    c = [str(x) for x in dl.classify_rd(v)]
    assert c == ["rd_lt1_5", "rd_1_5_2", "rd_1_5_2", "rd_2_3", "rd_ge3", "rd_ge3",
                 "rd_undefined"]


def test_null_fd_percentiles():
    t = dl.null_fd_percentiles(_rows([1, 1, 1, 1], 10), _rows([0, 1, 2, 3], 10), -1.5)
    t = t.set_index("percentile")
    assert t.loc[50, "fd_future_pct"] == pytest.approx(15.0)
    assert t.loc[50, "fd_baseline_pct"] == pytest.approx(10.0)
    cuts = dl.fd_cuts(t.reset_index(), (50, 90, 99))
    assert cuts[0] == pytest.approx(15.0) and cuts[2] > cuts[1] > cuts[0]


def test_null_class_shares():
    s = dl.null_class_shares(np.arange(1, 11, dtype=float), (2.0, 3.0, 4.0))
    assert s == {"low": 20.0, "medium": 10.0, "high": 10.0, "extreme": 60.0}


def test_rd_null_shares_denominators():
    base = _rows([0, 4, 2, 5])
    fut = _rows([3, 10, 5, 7])
    t = dl.rd_null_shares(base, fut, -1.5).set_index("rd_class")
    assert t.loc["rd_lt1_5", "null_pct"] == pytest.approx(100 / 3)
    assert t.loc["rd_2_3", "null_pct"] == pytest.approx(200 / 3)
    assert t.loc["rd_undefined", "null_pct"] == 25.0
    assert t.loc["rd_1_5_2", "null_pct_ge_lower"] == pytest.approx(200 / 3)
    assert (t["n_sim"].iloc[0], t["n_rd_defined"].iloc[0], t["n_rd_undefined"].iloc[0]) == (4, 3, 1)


def test_unit_drought_frame_missing_and_ok():
    units = pd.DataFrame({"uid": [0, 1], "itaipu": "na", "plant_uid": ["p", "q"],
                          "capacity_mw": [10.0, 20.0]})
    fd = pd.DataFrame({"plant_uid": ["p", "p", "q", "q"], "model": ["m1", "m2"] * 2,
                       "scenario": "s", "baseline_value": 6.0, "future_value": 9.0,
                       "ratio": 1.5})
    assert len(dl.unit_drought_frame(units, fd)) == 4
    with pytest.raises(ValueError):
        dl.unit_drought_frame(units, fd[fd["plant_uid"] == "p"])


def test_compare_fd_diff_and_nan_mismatch():
    k = {"plant_uid": ["p"], "model": ["m"], "scenario": ["s"]}
    mine = pd.DataFrame(dict(k, baseline_value=[5.0], future_value=[10.0], ratio=[2.0]))
    ref = pd.DataFrame(dict(k, baseline_value=[5.0], future_value=[10.5], ratio=[np.nan]))
    n, worst, nan_mm = dl.compare_fd(mine, ref)
    assert n == 1 and worst == pytest.approx(0.5) and nan_mm == 1


def test_find_plant_unique():
    p = pd.DataFrame({"plant_uid": ["a", "b", "c"], "country": "BRA",
                      "plant_name": ["Itaipu hydroelectric plant", "Itaipu small", "X"],
                      "capacity_mw": [14000.0, 100.0, 14000.0]})
    assert dl.find_plant(p, "BRA", "itaipu", 14000.0) == {"a"}
    with pytest.raises(ValueError):
        dl.find_plant(p, "BRA", "itaipu", 5.0)