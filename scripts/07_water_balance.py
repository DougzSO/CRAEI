"""COMANDO 16: PET (Hargreaves-Samani) and monthly water balance (Spec §1.4 H2, §3 Step 5).

For each country x model x scenario, loads the cropped tasmax/tasmin/pr files
at every cell a plant uses directly (COMANDO 14 `plant_cell.parquet`) or
through a hydro catchment (`catchment_weights.parquet`) -- the catchment set
is a superset of the nearest-cell set, since an upstream basin can span many
cells beyond the plant's own. Computes daily PET, then monthly P/PET/D at
cell scale (`water_balance_cell.parquet`, used directly by water-dependent
thermal plants' cell-scale SPEI) and catchment scale for hydro plants
(`water_balance_catchment.parquet`, weight-averaged with COMANDO 14's
weights). Historical loads from 1984 (not the Spec §1.3 baseline's 1985),
so a future 12-month SPEI accumulation (Spec §3 Step 6) has the history it
needs to reach January 1985.

Processes one country/model/scenario at a time with explicit `del` +
`gc.collect()`, same discipline as COMANDO 15 (`docs/DECISIONS.md` D41):
this machine has ~6 GB RAM. The one country/model/scenario chunk (at most
a few thousand cells x ~31 years of days) is already small enough that the
catchment weighting for that chunk's ~200-400 hydro plants runs as a single
merge+groupby, not a further per-plant loop -- looping in Python over each
catchment would only add overhead without a memory benefit at this size.
"""

import gc
from pathlib import Path

import pandas as pd

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_datasets, load_paths
from craei.hazards import pet
from craei.hazards.loading import cells_with_catchments_by_country, download_years_span, pr_daily, tasmax_daily, tasmin_daily

TX_BELOW_TN_STOP_FRACTION = 0.001  # Spec-instructed COMANDO 16 stop threshold (0.1% of days)


def report_fao56_example() -> None:
    """Action 2: report the calculated vs. the published Ra, not just assert a match."""
    calculated = pet.extraterrestrial_radiation(lat_deg=-20.0, day_of_year=246)
    published = 32.2  # docs/refs/fao56_example8.md: FAO-56 Example 8, 3 September at 20S
    print(
        f"FAO-56 Example 8 check: calculated Ra={calculated:.4f} MJ m-2 d-1, "
        f"published Ra={published} MJ m-2 d-1 (lat=-20.0, day_of_year=246); "
        f"source docs/refs/fao56_example8.md"
    )


def build_daily(country: str, model: str, scenario: str, cells, climate_dir: Path, datasets_cfg: dict):
    period = "baseline" if scenario == "historical" else "future"
    start_year, end_year = download_years_span(scenario, datasets_cfg)

    tasmax_path = climate_dir / model / scenario / "tasmax" / f"{model}_{scenario}_tasmax_{country}.nc"
    tasmin_path = climate_dir / model / scenario / "tasmin" / f"{model}_{scenario}_tasmin_{country}.nc"
    pr_path = climate_dir / model / scenario / "pr" / f"{model}_{scenario}_pr_{country}.nc"

    tasmax = tasmax_daily(tasmax_path, cells, start_year, end_year)
    tasmin = tasmin_daily(tasmin_path, cells, start_year, end_year)
    temps = tasmax.merge(tasmin, on=["date", "cell_lat", "cell_lon"])
    del tasmax, tasmin

    tx_tn_counts = pet.count_tx_below_tn(temps)
    n_days = int(tx_tn_counts["n_days"].sum())
    n_bad = int(tx_tn_counts["n_tx_below_tn"].sum())
    fraction = n_bad / n_days if n_days else 0.0
    print(f"{country}/{model}/{scenario}: TX<TN on {n_bad}/{n_days} days ({fraction:.4%}), before treatment")
    if fraction > TX_BELOW_TN_STOP_FRACTION:
        raise RuntimeError(
            f"{country}/{model}/{scenario}: TX<TN fraction {fraction:.4%} exceeds the "
            f"{TX_BELOW_TN_STOP_FRACTION:.1%} stop threshold (Spec COMANDO 16, Action 3)"
        )

    pet_df = pet.daily_pet(temps)
    n_truncated = int(pet_df["pet_truncated"].sum())
    del temps
    gc.collect()

    pr = pr_daily(pr_path, cells, start_year, end_year)
    daily = pet_df[["date", "cell_lat", "cell_lon", "pet_mm"]].merge(
        pr[["date", "cell_lat", "cell_lon", "pr_mm"]], on=["date", "cell_lat", "cell_lon"]
    )
    daily = daily.rename(columns={"pr_mm": "p_mm"})
    daily["model"], daily["scenario"], daily["period"] = model, scenario, period
    del pet_df, pr
    gc.collect()

    return daily, n_truncated, len(cells)


def main() -> None:
    report_fao56_example()

    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])
    climate_dir = raw_dir / "climate" / "isimip3b"

    cells_by_country = cells_with_catchments_by_country(processed_dir)
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country"])
    weights = pd.read_parquet(processed_dir / "catchment_weights.parquet")

    cell_frames = []
    catchment_frames = []
    truncated_by_country: dict[str, int] = {}

    for country in STUDY_COUNTRIES:
        cells = cells_by_country[country]
        print(f"\n{country}: {len(cells)} cells (plant nearest-cell + hydro catchment union)")
        weights_country = weights.merge(plants[plants["country"] == country][["plant_uid"]], on="plant_uid")

        truncated_by_country[country] = 0
        for model in datasets_cfg["models"]:
            for scenario in datasets_cfg["scenarios"]:
                daily, n_truncated, _ = build_daily(country, model, scenario, cells, climate_dir, datasets_cfg)
                truncated_by_country[country] += n_truncated

                cell_balance = pet.monthly_water_balance(daily)
                del daily
                gc.collect()

                catchment_balance = pet.catchment_water_balance(
                    cell_balance[["cell_lat", "cell_lon", "model", "scenario", "period", "month", "P", "PET"]],
                    weights_country,
                )

                cell_frames.append(cell_balance)
                catchment_frames.append(catchment_balance)
                print(f"{country}/{model}/{scenario}: {n_truncated} days with PET truncated to zero")

        print(f"{country}: total PET-truncated days across all models/scenarios: {truncated_by_country[country]}")

        # Action 6: weights still sum to 1 per plant after the join to this country's cell set.
        available_cells = cell_frames[-1][["cell_lat", "cell_lon"]].drop_duplicates()
        joined = weights_country.merge(available_cells, on=["cell_lat", "cell_lon"])
        sums = joined.groupby("plant_uid")["weight"].sum()
        bad = (sums.sub(1.0).abs() > 1e-6).sum()
        print(f"{country}: catchment weights sum to 1 for {len(sums) - bad}/{len(sums)} hydro plants")

    water_balance_cell = pd.concat(cell_frames, ignore_index=True)
    water_balance_catchment = pd.concat(catchment_frames, ignore_index=True)

    cell_out = processed_dir / "water_balance_cell.parquet"
    catchment_out = processed_dir / "water_balance_catchment.parquet"
    water_balance_cell.to_parquet(cell_out, index=False)
    water_balance_catchment.to_parquet(catchment_out, index=False)
    print(f"\nwrote {cell_out}: {len(water_balance_cell)} rows")
    print(f"wrote {catchment_out}: {len(water_balance_catchment)} rows")

    # Action 5: first/last balance date per period.
    for period, g in water_balance_cell.groupby("period"):
        print(f"period={period}: first month={g['month'].min()}, last month={g['month'].max()}")

    # Zero NaN outside ocean cells: every cell here is already land-restricted (COMANDO 14 GADM mask).
    n_nan = int(water_balance_cell[["P", "PET", "D"]].isna().sum().sum())
    print(f"NaN in water_balance_cell P/PET/D: {n_nan}")
    n_nan_catchment = int(water_balance_catchment[["P", "PET", "D"]].isna().sum().sum())
    print(f"NaN in water_balance_catchment P/PET/D: {n_nan_catchment}")


if __name__ == "__main__":
    main()
