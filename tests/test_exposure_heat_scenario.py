import numpy as np
import pandas as pd

from craei.exposure.heat_scenario import scenario_contrast

PAIR = (("ssp585", "ssp126"),)


def _inputs(up=True, sizes=None):
    sizes = sizes or {"g1": 12, "g2": 3}
    lo, hi = (10.0, 35.0) if up else (35.0, 10.0)
    rows, cells = [], []
    for g, n in sizes.items():
        for c in range(n):
            uid = f"{g}-{c}"
            cells.append({"plant_uid": uid, "cell_lat": float(c),
                          "cell_lon": 1.0 if g == "g1" else 2.0})
            for scen, delta in (("ssp126", lo), ("ssp585", hi)):
                for m in ("m1", "m2", "m3"):
                    rows.append({"plant_uid": uid, "fuel_class": g, "fleet": "operating",
                                 "scenario": scen, "model": m, "delta": delta,
                                 "capacity_mw": 100.0})
    return pd.DataFrame(rows), pd.DataFrame(cells)


def _run(df, cells):
    return scenario_contrast(df, cells, "fuel_class", (30,), 50, 5, PAIR)


def test_contrast_values_and_o25_rule():
    con, gcm, _ = _run(*_inputs())
    g1 = con[con["group"] == "g1"].iloc[0]
    g2 = con[con["group"] == "g2"].iloc[0]
    assert g1["obs_median_diff"] == 100.0 and g1["n_gcm_pos"] == 3
    assert g1["boot_p025"] == 100.0 and g1["boot_p975"] == 100.0
    assert g1["boot_reported"] and g1["boot_p025_pp"] == 100.0
    assert not g2["boot_reported"] and np.isnan(g2["boot_p025_pp"])
    assert g2["boot_p025"] == 100.0 and g2["label"] == "descriptive"
    assert (gcm["diff_obs"] == 100.0).all()


def test_shapes_and_reproducibility():
    df, cells = _inputs()
    a = _run(df, cells)
    b = _run(df, cells)
    assert len(a[0]) == 2 and len(a[1]) == 6
    for x, y in zip(a, b):
        pd.testing.assert_frame_equal(x, y)


def test_negative_contrast_and_reference_bounds():
    con, _, ref = _run(*_inputs(up=False))
    g1 = con[con["group"] == "g1"].iloc[0]
    assert g1["obs_median_diff"] == -100.0 and g1["n_gcm_pos"] == 0
    assert g1["prob_diff_gt0"] == 0.0
    r = ref[(ref["group"] == "g1") & (ref["scenario"] == "ssp126")].iloc[0]
    assert r["boot_p025"] == 100.0
    r2 = ref[(ref["group"] == "g1") & (ref["scenario"] == "ssp585")].iloc[0]
    assert r2["boot_p975"] == 0.0