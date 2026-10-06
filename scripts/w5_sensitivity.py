"""W5 sensitivity table: collects cross-analysis sensitivity findings into
a single table, scenario by scenario, sourced from already-produced CSVs
(no new hazard computation here). See docs/METHODS_SPEC.md Section 9 and
DECISIONS.md D101 (W3f7 source), D102 (W4b source), D107 (this schema),
D120 (W4b agreement source), D124 (W4f threshold-grid source), D125 (W4c
SPI-vs-SPEI source, corrected thermal null), D128 (this extension: 8 new
families from W4c/W4f/W4b-agreement, 12 families / 36 rows total).

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
    w4c = pd.read_csv(tables / "w4c_spi_vs_spei.csv")
    w4f = pd.read_csv(tables / "w4f_threshold_grid.csv")
    w4b_agr = pd.read_csv(tables / "w4b_agreement.csv")

    assert len(w3f7) == 1296, f"w3f7 row count changed: {len(w3f7)}"
    assert len(w4b) == 108, f"w4b row count changed: {len(w4b)}"
    assert len(w4c) == 324, f"w4c row count changed: {len(w4c)}"
    assert len(w4f) == 972, f"w4f row count changed: {len(w4f)}"
    assert len(w4b_agr) == 108, f"w4b_agreement row count changed: {len(w4b_agr)}"

    scenarios = ["ssp126", "ssp370", "ssp585"]
    rows = []

    # ================= ORIGINAL 4 FAMILIES (D107/C69, unchanged) =================
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

    # ================= NEW FAMILIES: W4c index choice (D125) =================
    def w4c_value(group, hazard, scenario, itaipu):
        f = w4c[(w4c["group"] == group) & (w4c["hazard"] == hazard)
                & (w4c["fleet"] == "operating") & (w4c["scenario"] == scenario)
                & (w4c["null_type"] == "block_bootstrap_12")]
        if itaipu is not None:
            f = f[f["itaipu"] == itaipu]
        assert len(f) == 1, f"expected 1 row for {group}/{hazard}/{scenario}/{itaipu}, got {len(f)}"
        return float(f["excess_pp_median"].iloc[0])

    hydro_spi_check = {"ssp126": 17.400304, "ssp370": 3.030546, "ssp585": 38.595041}
    thermal_spei_check = {"ssp126": 20.627763, "ssp370": 28.499072, "ssp585": 48.059192}
    thermal_spi_check = {"ssp126": -1.081071, "ssp370": 5.437349, "ssp585": 27.498395}

    for scen in scenarios:
        h = w4c_value("hydro", "spei", scen, "b")
        a = w4c_value("hydro", "spi", scen, "b")
        assert abs(h - block_check[("block_bootstrap_12", scen)]) < 1e-6, f"hydro spei drift {scen}"
        assert abs(a - hydro_spi_check[scen]) < 1e-4, f"hydro spi drift {scen}"
        rows.append(dict(family="W4c_index_hydro", choice_headline="spei", choice_alternative="spi",
                          metric="excess_pp_median", scenario=scen, headline_value=h, alternative_value=a,
                          delta=a - h, delta_unit="pp", sign_changed=sign_changed_flag(h, a),
                          flag="smaller_magnitude_same_sign",
                          source_table="w4c_spi_vs_spei.csv", decision_id="D125"))

    # Per-row flag: ssp126 sign-flips (SPEI +20.63 -> SPI -1.08), ssp370/585
    # keep sign with smaller magnitude under SPI.
    thermal_flags = {
        "ssp126": "sign_flip_smaller_magnitude",
        "ssp370": "smaller_magnitude_same_sign",
        "ssp585": "smaller_magnitude_same_sign",
    }
    for scen in scenarios:
        h = w4c_value("thermal_water_dependent", "spei", scen, "na")
        a = w4c_value("thermal_water_dependent", "spi", scen, "na")
        assert abs(h - thermal_spei_check[scen]) < 1e-4, f"thermal spei drift {scen}"
        assert abs(a - thermal_spi_check[scen]) < 1e-4, f"thermal spi drift {scen}"
        rows.append(dict(family="W4c_index_thermal_water_dependent", choice_headline="spei",
                          choice_alternative="spi", metric="excess_pp_median", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="pp",
                          sign_changed=sign_changed_flag(h, a), flag=thermal_flags[scen],
                          source_table="w4c_spi_vs_spei.csv", decision_id="D125"))

    # ================= NEW FAMILIES: W4f threshold grid (D124) =================
    def w4f_value(spei_t, rd_t, scenario):
        f = w4f[(w4f["spei_threshold"] == spei_t) & (w4f["rd_threshold"] == rd_t)
                & (w4f["fleet"] == "operating") & (w4f["itaipu"] == "b")
                & (w4f["scenario"] == scenario) & (w4f["null_type"] == "block_bootstrap_12")]
        assert len(f) == 1, f"expected 1 row for spei={spei_t}/rd={rd_t}/{scenario}, got {len(f)}"
        return float(f["excess_pp_median"].iloc[0])

    spei_m10_check = {"ssp126": 14.417460, "ssp370": 23.307366, "ssp585": 59.692962}
    spei_m20_check = {"ssp126": 35.866609, "ssp370": 49.629082, "ssp585": 62.990811}
    rd15_check = {"ssp126": 38.808136, "ssp370": 41.158453, "ssp585": 50.629851}
    rd30_check = {"ssp126": 20.537978, "ssp370": 29.542819, "ssp585": 48.599576}

    # Per-row flag: direction of the delta is not uniform across scenarios
    # for the SPEI-threshold families (unlike the R_D-threshold families
    # below, which are monotonic across all 3 scenarios).
    spei_10_15_flags = {
        "ssp126": "stricter_threshold_increases_excess",
        "ssp370": "stricter_threshold_increases_excess",
        "ssp585": "stricter_threshold_decreases_excess",
    }
    for scen in scenarios:
        h = w4f_value(-1.0, 2.0, scen)
        a = w4f_value(-1.5, 2.0, scen)
        assert abs(h - spei_m10_check[scen]) < 1e-4, f"w4f spei-1.0 drift {scen}"
        assert abs(a - block_check[("block_bootstrap_12", scen)]) < 1e-4, f"w4f production-cell drift {scen}"
        rows.append(dict(family="W4f_spei_threshold_-1.0_-1.5", choice_headline="spei_-1.0",
                          choice_alternative="spei_-1.5", metric="excess_pp_median", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="pp",
                          sign_changed=sign_changed_flag(h, a), flag=spei_10_15_flags[scen],
                          source_table="w4f_threshold_grid.csv", decision_id="D124"))

    spei_15_20_flags = {
        "ssp126": "stricter_threshold_decreases_excess",
        "ssp370": "stricter_threshold_increases_excess",
        "ssp585": "stricter_threshold_increases_excess",
    }
    for scen in scenarios:
        h = w4f_value(-1.5, 2.0, scen)
        a = w4f_value(-2.0, 2.0, scen)
        assert abs(a - spei_m20_check[scen]) < 1e-4, f"w4f spei-2.0 drift {scen}"
        rows.append(dict(family="W4f_spei_threshold_-1.5_-2.0", choice_headline="spei_-1.5",
                          choice_alternative="spei_-2.0", metric="excess_pp_median", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="pp",
                          sign_changed=sign_changed_flag(h, a), flag=spei_15_20_flags[scen],
                          source_table="w4f_threshold_grid.csv", decision_id="D124"))

    for scen in scenarios:
        h = w4f_value(-1.5, 1.5, scen)
        a = w4f_value(-1.5, 2.0, scen)
        assert abs(h - rd15_check[scen]) < 1e-4, f"w4f rd1.5 drift {scen}"
        rows.append(dict(family="W4f_rd_threshold_1.5_2.0", choice_headline="rd_1.5",
                          choice_alternative="rd_2.0", metric="excess_pp_median", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="pp",
                          sign_changed=sign_changed_flag(h, a), flag="larger_magnitude_same_sign",
                          source_table="w4f_threshold_grid.csv", decision_id="D124"))

    for scen in scenarios:
        h = w4f_value(-1.5, 2.0, scen)
        a = w4f_value(-1.5, 3.0, scen)
        assert abs(a - rd30_check[scen]) < 1e-4, f"w4f rd3.0 drift {scen}"
        rows.append(dict(family="W4f_rd_threshold_2.0_3.0", choice_headline="rd_2.0",
                          choice_alternative="rd_3.0", metric="excess_pp_median", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="pp",
                          sign_changed=sign_changed_flag(h, a), flag="smaller_magnitude_same_sign",
                          source_table="w4f_threshold_grid.csv", decision_id="D124"))

    # ================= NEW FAMILIES: W4b agreement (D120) =================
    def w4b_agr_value(null_type, scenario):
        f = w4b_agr[(w4b_agr["fleet"] == "operating") & (w4b_agr["itaipu"] == "b")
                    & (w4b_agr["null_type"] == null_type) & (w4b_agr["scenario"] == scenario)]
        assert len(f) == 1, f"expected 1 row for {null_type}/{scenario}, got {len(f)}"
        return int(f["k_agreement"].iloc[0])

    k_12_36_check = {"ssp126": (5, 5), "ssp370": (5, 4), "ssp585": (5, 5)}
    k_36_60_check = {"ssp126": (5, 5), "ssp370": (4, 4), "ssp585": (5, 5)}

    for scen in scenarios:
        h = w4b_agr_value("block_bootstrap_12", scen)
        a = w4b_agr_value("block_bootstrap_36", scen)
        assert (h, a) == k_12_36_check[scen], f"k_agreement 12_36 drift {scen}"
        flag = "unchanged" if h == a else "agreement_decreased"
        rows.append(dict(family="W4b_agreement_block_12_36", choice_headline="block12",
                          choice_alternative="block36", metric="k_agreement", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="k_of_5",
                          sign_changed="NA", flag=flag,
                          source_table="w4b_agreement.csv", decision_id="D120"))

    for scen in scenarios:
        h = w4b_agr_value("block_bootstrap_36", scen)
        a = w4b_agr_value("block_bootstrap_60", scen)
        assert (h, a) == k_36_60_check[scen], f"k_agreement 36_60 drift {scen}"
        flag = "unchanged" if h == a else "agreement_decreased"
        rows.append(dict(family="W4b_agreement_block_36_60", choice_headline="block36",
                          choice_alternative="block60", metric="k_agreement", scenario=scen,
                          headline_value=h, alternative_value=a, delta=a - h, delta_unit="k_of_5",
                          sign_changed="NA", flag=flag,
                          source_table="w4b_agreement.csv", decision_id="D120"))

    out = pd.DataFrame(rows, columns=[
        "family", "choice_headline", "choice_alternative", "metric",
        "scenario", "headline_value", "alternative_value", "delta",
        "delta_unit", "sign_changed", "flag", "source_table", "decision_id",
    ])

    assert len(out) == 36, f"expected 36 rows, got {len(out)}"
    assert out["family"].nunique() == 12, f"expected 12 families, got {out['family'].nunique()}"

    # ---- promotion-safety check: first 12 rows must equal the pre-existing file ----
    old_path = tables / "w5_sensitivity.csv.bak_pre12fam"
    if old_path.exists():
        # na_filter=False: the original file stores the literal string "NA"
        # for sign_changed in the W4b block families; pandas' default NA
        # list includes the exact token "NA" and would otherwise silently
        # turn it into a real NaN on re-read, producing a false drift
        # positive against the in-memory "NA" string built by this script.
        old = pd.read_csv(old_path, na_filter=False)
        assert len(old) == 12, f"pre-existing w5_sensitivity.csv row count changed: {len(old)}"
        old_cols = old.columns.tolist()
        merged_old = out.iloc[:12][old_cols].reset_index(drop=True)
        old_reset = old[old_cols].reset_index(drop=True)
        num_cols = ["headline_value", "alternative_value", "delta"]
        max_diff = (merged_old[num_cols].astype(float) - old_reset[num_cols].astype(float)).abs().max().max()
        assert max_diff < 1e-9, f"original 12 rows drifted: max_diff={max_diff}"
        non_num_cols = [c for c in old_cols if c not in num_cols]
        assert (merged_old[non_num_cols].astype(str) == old_reset[non_num_cols].astype(str)).all().all(), \
            "original 12 rows text columns drifted"
        print(f"promotion safety: first 12 rows identical to pre-existing file, max numeric diff {max_diff:.2e}")
    else:
        print("WARNING: backup file not found, promotion-safety check skipped")

    out.to_csv(tables / "w5_sensitivity.csv", index=False)
    print(f"written: w5_sensitivity.csv ({len(out)} rows, {out['family'].nunique()} families)")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()