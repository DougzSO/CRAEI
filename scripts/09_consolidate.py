"""COMANDO 18: plant-level hazard table and Aqueduct water stress (Spec §3 Steps 7-8).

Step 7: `hazards.consolidate.plant_hazards` joins H1 (heat), H2 (drought)
and H4 (Supplementary Information) onto every plant, one row per
(plant, model, scenario, bucket, hazard). Step 8: `hazards.aqueduct` joins
water-dependent thermal plants to Aqueduct 4.0 by HydroBASINS `pfaf_id`,
reporting both L01 cooling bounds.

Both steps only read already-built parquet files (`plants.parquet`,
`indices_daily.parquet`, `spei.parquet`, `plant_cell.parquet`); no
`groupby(...).transform/apply/rolling` over the full tables (CLAUDE.md
Rule 11) -- `consolidate.py`'s aggregation is `.agg()`/`.mean()` reductions
only.
"""

from pathlib import Path

import pandas as pd

from craei.acquire.auxiliary import HYDROBASINS_REGIONS
from craei.config import load_paths
from craei.hazards import aqueduct as aq
from craei.hazards import consolidate
from craei.spatial import catchments as cat


def run_step7(processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    inputs = consolidate.load_plant_hazard_inputs(processed_dir)
    hazards, r_d_zeros = consolidate.plant_hazards(
        inputs["plants"], inputs["indices_daily"], inputs["spei"], inputs["plant_cell"]
    )
    hazards.to_parquet(processed_dir / "plant_hazards.parquet", index=False)
    r_d_zeros.to_csv(processed_dir / "plant_hazards_r_d_baseline_zero.csv", index=False)

    plants = inputs["plants"].copy()
    plants["bucket"] = consolidate._assign_bucket(plants)
    print("=== Step 7: plant_hazards.parquet ===")
    print(f"Total rows: {len(hazards)}")
    print("\nRows by bucket x hazard:")
    print(hazards.groupby(["bucket", "hazard"], dropna=False).size().to_string())
    print("\nExpected plant counts by bucket:")
    print(plants["bucket"].value_counts().to_string())

    print("\nNaN counts by hazard (baseline_value/future_value/ratio):")
    nan_report = hazards.groupby("hazard")[["baseline_value", "future_value", "ratio"]].apply(
        lambda d: d.isna().sum()
    )
    print(nan_report.to_string())

    print("\nR_D baseline-zero rate by bucket/country/model/scenario (Action 2):")
    if len(r_d_zeros):
        merged = r_d_zeros.merge(plants[["plant_uid", "country"]], on="plant_uid", how="left")
        counts = merged.groupby(["bucket", "hazard"]).size()
        totals = hazards[hazards["hazard"].str.startswith("f_d_")].groupby(
            ["bucket", "hazard"]
        ).size()
        counts = counts.reindex(totals.index, fill_value=0)
        rate = (counts / totals * 100).round(3)
        print(rate.to_string())
        if (rate > 1.0).any():
            print(
                "\n*** STOP CONDITION (Action 2): R_D baseline-zero rate exceeds 1% in at "
                "least one bucket -- see printed rates above. This needs an author decision "
                "before R_D is used downstream for the affected bucket(s); documented as an "
                "open decision, not resolved here. ***"
            )
    else:
        print("0 rows -- R_D baseline-zero never occurs in this run.")

    return hazards, r_d_zeros


def run_step8(processed_dir: Path, raw_dir: Path, aqueduct_dir: Path) -> pd.DataFrame:
    plants = pd.read_parquet(processed_dir / "plants.parquet")
    water_dep = plants[plants["tech_class"] == "thermal_water_dependent"].copy()

    hydrobasins_dir = raw_dir / "boundaries" / "hydrobasins"
    basins_by_region = {
        region: cat.load_hydrobasins(hydrobasins_dir / f"hybas_{region}_lev06_v1c.zip")
        for region in set(HYDROBASINS_REGIONS.values())
    }
    plant_pfaf = aq.join_plants_to_pfaf(water_dep, basins_by_region, HYDROBASINS_REGIONS)

    future = aq.load_aqueduct_future(aqueduct_dir)
    baseline_path = raw_dir / "aqueduct" / "baseline_annual" / "aqueduct_baseline_annual_3countries.csv"
    baseline = aq.load_aqueduct_baseline(baseline_path)

    coastal_flag = water_dep[["plant_uid", "coastal_5km"]]
    out = aq.plant_aqueduct_exposure(plant_pfaf, future, baseline, coastal_flag=coastal_flag)
    out.to_parquet(processed_dir / "plant_aqueduct.parquet", index=False)

    print("\n=== Step 8: plant_aqueduct.parquet ===")
    n_water_dep = len(water_dep)
    # baseline is folded into ws/bws columns, not extra rows here
    print(f"Water-dependent thermal plants: {n_water_dep}")
    print(f"Rows: {len(out)} (expected water_dep x 3 scenarios x 2 cooling bounds = {n_water_dep * 3 * 2})")
    print("(baseline bws is a column per row, not a 4th 'scenario' row -- see note below)")

    print("\nCategory -1 (arid_low_water_use) and no_data counts by country, per cooling bound:")
    with_country = out.merge(plants[["plant_uid", "country"]], on="plant_uid", how="left")
    for cat_name in ("arid_low_water_use", "no_data"):
        counts = with_country[with_country["ws_category"] == cat_name].groupby(
            ["cooling_bound", "country"]
        ).size()
        print(f"\n{cat_name}:")
        print(counts.to_string() if len(counts) else "  none")

    return out


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])
    raw_dir = Path(paths["raw_dir"])
    aqueduct_dir = Path(paths["aqueduct_dir"])

    hazards, r_d_zeros = run_step7(processed_dir)
    aqueduct_out = run_step8(processed_dir, raw_dir, aqueduct_dir)

    print("\n=== Validation (Action 4) ===")
    plants = pd.read_parquet(processed_dir / "plants.parquet")
    plants["bucket"] = consolidate._assign_bucket(plants)
    non_hydro_with_basin_hazard = hazards[
        hazards["hazard"].isin(["f_d_spei12", "f_d_spei3"])
        & hazards["bucket"].isin(
            [consolidate.BUCKET_THERMAL_AIR, consolidate.BUCKET_SOLAR, consolidate.BUCKET_OTHER]
        )
    ]
    print(
        f"Non-hydro/non-water-thermal plants with a SPEI hazard row: {len(non_hydro_with_basin_hazard)} "
        "(must be 0)"
    )
    assert len(non_hydro_with_basin_hazard) == 0

    coastal_lower = aqueduct_out[aqueduct_out["cooling_bound"] == "lower"]
    coastal_plants = set(
        plants[plants["coastal_5km"]]["plant_uid"]
    ) & set(plants[plants["tech_class"] == "thermal_water_dependent"]["plant_uid"])
    leaked = set(coastal_lower["plant_uid"]) & coastal_plants
    print(
        f"Coastal water-dependent plants leaking into the 'lower' cooling bound: {len(leaked)} (must be 0)"
    )
    assert len(leaked) == 0

    print("\nDone.")


if __name__ == "__main__":
    main()
