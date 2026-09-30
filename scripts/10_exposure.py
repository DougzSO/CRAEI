"""COMANDO 19: exposure aggregation and agreement (Spec §1.5, §3 Step 9).

Produces `exposure_summary.csv` (main text: H1/H2, operating + planned
fleets), `exposure_aqueduct.csv` (H3, own table, both cooling bounds) and
`exposure_si.csv` (Supplementary Information: H4). Output directory comes
from `config.py`'s `load_paths()["outputs_tables_dir"]` (COMANDO 22-B Part 3:
`outputs_dir` itself is never written to directly), never a hardcoded path.
"""

from pathlib import Path

from craei.config import load_paths
from craei.exposure import aggregate as agg
from craei.hazards.consolidate import _assign_bucket


def main() -> None:
    paths = load_paths()
    inputs = agg.load_exposure_inputs()
    plants = inputs["plants"].copy()
    plants["bucket"] = _assign_bucket(plants)

    summary = agg.build_exposure_summary(plants, inputs["plant_hazards"])
    aqueduct = agg.build_exposure_aqueduct(plants, inputs["plant_aqueduct"])
    si = agg.build_exposure_si(plants, inputs["plant_hazards"])

    outputs_dir = Path(paths["outputs_tables_dir"])
    summary.to_csv(outputs_dir / "exposure_summary.csv", index=False)
    aqueduct.to_csv(outputs_dir / "exposure_aqueduct.csv", index=False)
    si.to_csv(outputs_dir / "exposure_si.csv", index=False)

    print("=== Step 9: exposure aggregation ===")
    print(f"exposure_summary.csv: {len(summary)} rows -> {outputs_dir / 'exposure_summary.csv'}")
    print(f"exposure_aqueduct.csv: {len(aqueduct)} rows -> {outputs_dir / 'exposure_aqueduct.csv'}")
    print(f"exposure_si.csv: {len(si)} rows -> {outputs_dir / 'exposure_si.csv'}")

    print("\nFleets present in exposure_summary.csv:", sorted(summary["fleet"].unique()))
    print("Buckets present in exposure_summary.csv:", sorted(summary["tech_class"].unique()))

    print("\n=== Validation: capacity accounting ===")
    total_by_country_bucket_fleet = plants.groupby(["country", "bucket", "fleet"])[
        "capacity_mw"
    ].sum()
    print("Total MW by country x bucket x fleet (from plants.parquet):")
    print(total_by_country_bucket_fleet.to_string())
    print(
        "\nCompletion criterion: this total must match the denominator implied by "
        "exposure_summary.csv's median_share/median_gw for each group -- verified in "
        "tests/test_exposure_aggregate.py, not recomputed here (large-table cost)."
    )


if __name__ == "__main__":
    main()
