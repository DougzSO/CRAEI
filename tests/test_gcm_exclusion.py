import pandas as pd
import pytest

from craei.hazards import gcm_exclusion as gx

MODELS = ["a", "b", "c", "d", "e"]


def _by_gcm(values, fleet="operating", group="g"):
    return pd.DataFrame({"group": group, "fleet": fleet, "scenario": "s",
                         "threshold": 30, "model": MODELS, "pct_gw": values})


def test_exclusion_sets_names_and_pair():
    sets = gx.exclusion_sets(MODELS, pair=("e", "d"))
    assert list(sets) == ["all5", "drop_a", "drop_b", "drop_c", "drop_d", "drop_e", "drop_e+d"]
    assert sets["drop_e+d"] == ["a", "b", "c"]
    with pytest.raises(ValueError):
        gx.exclusion_sets(MODELS, pair=("x", "a"))


def test_summarize_median_of_four_and_three():
    sets = gx.exclusion_sets(MODELS, pair=("d", "e"))
    s = gx.summarize_exclusions(_by_gcm([10, 20, 30, 40, 50]), sets).set_index("exclusion")
    assert s.loc["all5", "pct_median"] == 30
    assert s.loc["drop_e", "pct_median"] == 25 and s.loc["drop_e", "shift_pp"] == -5
    assert s.loc["drop_d+e", "pct_median"] == 20 and s.loc["drop_d+e", "n_gcm"] == 3


def test_contrast_sign_flag():
    by = pd.concat([_by_gcm([10] * 5), _by_gcm([5, 5, 5, 20, 20], fleet="planned_all")])
    sets = gx.exclusion_sets(MODELS, pair=("a", "b"))
    c = gx.contrast_exclusions(by, sets).set_index("exclusion")
    assert c.loc["all5", "diff_median"] == -5 and not c.loc["all5", "sign_changed"]
    assert c.loc["drop_a+b", "diff_median"] == 10 and c.loc["drop_a+b", "sign_changed"]
    assert c.loc["drop_a+b", "n_pos"] == 2


def test_fuel_ranking_order_and_change():
    rows = []
    for ex, bio, gas in [("all5", 30.0, 20.0), ("drop_e", 10.0, 20.0)]:
        for g, v in [("bioenergy", bio), ("gas", gas), ("g_other", 99.0)]:
            rows.append({"fleet": "operating", "scenario": "s", "threshold": 30,
                         "exclusion": ex, "group": g, "pct_median": v})
    r = gx.fuel_ranking(pd.DataFrame(rows)).set_index("exclusion")
    assert r.loc["all5", "order"] == "bioenergy > gas"
    assert r.loc["drop_e", "order"] == "gas > bioenergy"
    assert bool(r.loc["all5", "bio_gt_gas"]) and not bool(r.loc["drop_e", "bio_gt_gas"])
    assert bool(r.loc["drop_e", "order_changed"]) and not bool(r.loc["all5", "order_changed"])