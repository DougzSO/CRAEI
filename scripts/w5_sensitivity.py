"""W5 sensitivity table: collects cross-analysis sensitivity findings into
a single table, scenario by scenario, sourced from already-produced CSVs
(no new hazard computation here). See docs/METHODS_SPEC.md Section 9 and
DECISIONS.md D101 (W3f7 source), D102 (W4b source), D107 (this schema).

Run: python scripts/w5_sensitivity.py
Writes: w5_sensitivity.csv in outputs_tables_dir.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from craei.config import load_paths

EPS = 1e-9


def sign_changed_flag(headline, alternative, eps=EPS):
    """True/False only for a clean negative<->positive crossing.
    NA if either side is (numerically) zero -- not a clean fact."""
    if abs(headline) < eps or abs(alternative) < eps:
        return "NA"
    return "True" if (headline > 0) != (alternative > 0) else "False"


def main():
    paths = load_paths()
    tables = Path(paths["outputs_tables_dir"])

    w3f7 = pd.read_csv(tables / "w3f7_planned_vs_operating.csv")
    w4b = pd.read_csv(tables / "w4b_excess_over_null.csv")

    assert len(w3f7) == 1296, f"w3f7 row count changed: {len(w3f7)}"
    assert len(w4b) == 108, f"w4b row count changed: {len(w4b)}"

    scenarios = ["ssp126", "ssp370", "ssp585"]

    # ---- W3f7 base filter: all_thermal, planned_all, threshold=30 ----
    base = w3f7[
        (w3f7["group"] == "all_thermal")
        & (w3f7["planned_fleet"] == "planned_all")
        & (w3f7["threshold"] == 30)
    ]

    def w3f7_value(choice, scenario):
        row = base[(base["choice"] == choice) & (base["scenario"] == scenario)]
        assert len(row) == 1, f"expected 1 row for {choice}/{scenario}, got {len(row)}"
        return float(row["diff_median"].iloc[0])

    # Fixed, independently-verified values (D101, C63), used only to assert
    # the CSV has not drifted since this table was built -- not the source.
    ref_check = {
        ("reference", "ssp126"): -7.158109208893068,
        ("reference", "ssp370"): -0.11849284190007836,
        ("reference", "ssp585"): 1.3542632270698363,
        ("weight_plant_count", "ssp126"): 12.06545776205219,
        ("weight_plant_count", "ssp370"): 7.978770455550638,
        ("weight_plant_count", "ssp585"): 9.871738168951786,
        ("metric_TX40", "ssp126"): 0.0,
        ("metric_TX40", "ssp370"): -0.010908739998573473,
        ("metric_TX40", "ssp585"): -2.1285376996049648,
    }
    for (choice, scen), expected in ref_check.items():
        got = w3f7_value(choice, scen)
        assert abs(got - expected) < 1e-6, (
            f"w3f7 value drifted for {choice}/{scen}: expected {expected}, got {got}"
        )

    rows = []
    for scen in scenarios:
        h = w3f7_value("reference", scen)
        a = w3f7_value("weight_plant_count", scen)
        rows.append(dict(
            family="W3f7_weight", choice_headline="reference_weight_GW",
            choice_alternative="weight_plant_count",
            metric="planned_minus_operating_diff_median_pp", scenario=scen,
            headline_value=h, alternative_value=a, delta=a - h,
            delta_unit="pp", sign_changed=sign_changed_flag(h, a),
            flag="conditional_on_weight",
            source_table="w3f7_planned_vs_operating.csv", decision_id="D101",
        ))

    # Per-row flag here, not per-family: ssp585 sign-flips (+1.35 -> -2.13),
    # while ssp126/ssp370 keep the same sign with smaller magnitude. A
    # single family-level flag would misstate ssp585 (caught before commit,
    # see D107).
    tx40_flags = {
        "ssp126": "smaller_magnitude_same_sign",
        "ssp370": "smaller_magnitude_same_sign",
        "ssp585": "sign_flip_larger_magnitude",
    }
    for scen in scenarios:
        h = w3f7_value("reference", scen)
        a = w3f7_value("metric_TX40", scen)
        rows.append(dict(
            family="W3f7_metric", choice_headline="reference_TX35",
            choice_alternative="metric_TX40",
            metric="planned_minus_operating_diff_median_pp", scenario=scen,
            headline_value=h, alternative_value=a, delta=a - h,
            delta_unit="pp", sign_changed=sign_changed_flag(h, a),
            flag=tx40_flags[scen],
            source_table="w3f7_planned_vs_operating.csv", decision_id="D101",
        ))

    # ---- W4b base filter: operating, itaipu=b ----
    base_b = w4b[(w4b["fleet"] == "operating") & (w4b["itaipu"] == "b")]

    def w4b_value(null_type, scenario):
        row = base_b[(base_b["null_type"] == null_type) & (base_b["scenario"] == scenario)]
        assert len(row) == 1, f"expected 1 row for {null_type}/{scenario}, got {len(row)}"
        return float(row["excess_pp_median"].iloc[0])

    block_check = {
        ("block_bootstrap_12", "ssp126"): 40.7485901973767,
        ("block_bootstrap_12", "ssp370"): 43.20410170545621,
        ("block_bootstrap_12", "ssp585"): 53.94465124912654,
        ("block_bootstrap_36", "ssp126"): 37.76650006626666,
        ("block_bootstrap_36", "ssp370"): 40.222011574346176,
        ("block_bootstrap_36", "ssp585"): 50.962561118016495,
        ("block_bootstrap_60", "ssp126"): 38.88268474409517,
        ("block_bootstrap_60", "ssp370"): 41.33819625217469,
        ("block_bootstrap_60", "ssp585"): 52.07874579584501,
    }
    for (nt, scen), expected in block_check.items():
        got = w4b_value(nt, scen)
        assert abs(got - expected) < 1e-6, (
            f"w4b value drifted for {nt}/{scen}: expected {expected}, got {got}"
        )

    for scen in scenarios:
        h = w4b_value("block_bootstrap_12", scen)
        a = w4b_value("block_bootstrap_36", scen)
        rows.append(dict(
            family="W4b_block_12_36", choice_headline="block12",
            choice_alternative="block36", metric="excess_pp_median",
            scenario=scen, headline_value=h, alternative_value=a,
            delta=a - h, delta_unit="pp", sign_changed="NA",
            flag="non_monotonic", source_table="w4b_excess_over_null.csv",
            decision_id="D102",
        ))

    for scen in scenarios:
        h = w4b_value("block_bootstrap_36", scen)
        a = w4b_value("block_bootstrap_60", scen)
        rows.append(dict(
            family="W4b_block_36_60", choice_headline="block36",
            choice_alternative="block60", metric="excess_pp_median",
            scenario=scen, headline_value=h, alternative_value=a,
            delta=a - h, delta_unit="pp", sign_changed="NA",
            flag="non_monotonic", source_table="w4b_excess_over_null.csv",
            decision_id="D102",
        ))

    out = pd.DataFrame(rows, columns=[
        "family", "choice_headline", "choice_alternative", "metric",
        "scenario", "headline_value", "alternative_value", "delta",
        "delta_unit", "sign_changed", "flag", "source_table", "decision_id",
    ])

    assert len(out) == 12, f"expected 12 rows, got {len(out)}"
    assert out["family"].nunique() == 4, "expected 4 families"

    out.to_csv(tables / "w5_sensitivity.csv", index=False)
    print(f"written: w5_sensitivity.csv ({len(out)} rows)")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()