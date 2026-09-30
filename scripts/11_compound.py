"""COMANDO 20: compound hydro-drought / thermal-heat metric (Spec §1.6, §3 Step 10).

Action 1: before anything else, confirm `indices_daily.parquet` carries a
real monthly `n35` series (not just the annual `tx35` total) -- Spec §1.6's
H_thermal needs it. `compound.assert_n35_monthly` raises and stops the run
if it does not.

Output directory comes from `config.py`'s `load_paths()["outputs_tables_dir"]`
(COMANDO 22-B Part 3: `outputs_dir` itself is never written to directly),
never a hardcoded path.
"""

from pathlib import Path

from craei.config import load_params, load_paths
from craei.exposure import compound


def main() -> None:
    paths = load_paths()
    inputs = compound.load_compound_inputs()

    print("=== Step 10 Action 1: confirming monthly N35 ===")
    compound.assert_n35_monthly(inputs["indices_daily"])
    print("OK: 'n35' present in indices_daily.parquet with non-null 'month'.")

    params = load_params()
    spei_threshold = params["drought_spei_threshold"]["value"]
    percentile = params["compound_baseline_percentile"]["value"]

    series = compound.build_compound_series(
        inputs["plants"],
        inputs["spei"],
        inputs["indices_daily"],
        inputs["plant_cell"],
        spei_threshold,
    )
    thresholds = compound.baseline_thresholds(series, percentile)
    flagged = compound.flag_compound_months(series, thresholds)
    summary = compound.compound_summary(flagged)

    outputs_dir = Path(paths["outputs_tables_dir"])
    summary.to_csv(outputs_dir / "compound.csv", index=False)
    flagged.to_parquet(outputs_dir / "compound_months.parquet", index=False)

    print("\n=== Step 10: compound.csv / compound_months.parquet ===")
    print(f"compound.csv: {len(summary)} rows (expected 3 countries x 3 scenarios x 5 models = 45)")
    print(f"-> {outputs_dir / 'compound.csv'}")
    print(
        f"compound_months.parquet: {len(flagged)} rows -> {outputs_dir / 'compound_months.parquet'}"
    )

    print("\nBaseline compound frequency by country and model (Action 3 -- not assumed ~1%):")
    print(
        flagged[flagged["period"] == "baseline"]
        .groupby(["country", "model"])["compound"]
        .mean()
        .to_string()
    )

    print("\nP90 = 0 fallback count by country and model (Action 4):")
    fallback_counts = thresholds.groupby("country")["s_hydro_p90_is_zero"].sum()
    print(fallback_counts.to_string())
    n_fallback = int(thresholds["s_hydro_p90_is_zero"].sum())
    print(f"Total (country, model) groups with S_hydro P90 = 0: {n_fallback} / {len(thresholds)}")

    print("\nlr_c = NaN count (legacy column, baseline frequency exactly zero):")
    nan_lr_c = summary["lr_c"].isna().sum()
    print(f"{nan_lr_c} / {len(summary)} rows")

    print(
        "\ndiff_pp (closed headline metric, D63) and dependence_ratio "
        "(observed future compound frequency over independence-implied), by country/scenario/model:"
    )
    print(
        summary[
            ["country", "scenario", "model", "diff_pp", "dependence_ratio"]
        ].to_string(index=False)
    )
    nan_dep = summary["dependence_ratio"].isna().sum()
    print(
        f"\ndependence_ratio = NaN (independence product exactly zero): "
        f"{nan_dep} / {len(summary)} rows"
    )

    if len(summary) != 45:
        print(
            f"\n*** Row count is {len(summary)}, not the expected 45 (3 countries x 3 scenarios x "
            "5 models) -- check country/model/scenario coverage in spei.parquet/"
            "indices_daily.parquet before treating compound.csv as complete. ***"
        )
    print("\nDone.")


if __name__ == "__main__":
    main()
