"""COMANDO 18-E Action 5 (sensitivity): pool by (country, calendar month) only,
merging hydro_reservoir + hydro_run_of_river + thermal_water_dependent into one
country-wide pool, instead of production's (country, bucket, calendar month).
Reports whether the country F_D ranking changes vs. the bucket-level pool.
Read-only, does not touch spei.parquet.
"""

import gc
from pathlib import Path

import pandas as pd

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.consolidate import BUCKET_THERMAL_WATER, _assign_bucket

H2_EXCLUDED_PLANT_IDS = {"5131763b8e53f91a7783faeea1fb15095453fd967630297cac52261097daf54c"}
POOL_COLS = ["country"]  # bucket dropped, unlike production


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    clip_bound = float(params["spei_clip_bound"]["value"])
    severe_threshold = float(params["drought_spei_threshold"]["value"])

    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class", "hydro_type"])
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    hydro_plants = hydro_plants[~hydro_plants["plant_uid"].isin(H2_EXCLUDED_PLANT_IDS)].copy()
    id_country = dict(zip(hydro_plants["plant_uid"], hydro_plants["country"]))

    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"])
    thermal_water = plants[plants["tech_class"] == "thermal_water_dependent"]
    tw_cell = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"]).copy()
    tw_cell["id"] = tw_cell["cell_lat"].astype(str) + "_" + tw_cell["cell_lon"].astype(str)
    cell_country = dict(zip(tw_cell.drop_duplicates(subset="id")["id"], tw_cell.drop_duplicates(subset="id")["country"]))

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())
    catchment_all = pd.read_parquet(catchment_path)

    fd_parts = []
    for country in STUDY_COUNTRIES:
        country_hydro_ids = set(hydro_plants.loc[hydro_plants["country"] == country, "plant_uid"])
        chunk = catchment_all[catchment_all["id"].isin(country_hydro_ids)][
            ["id", "model", "scenario", "period", "month", "D"]
        ].copy()
        chunk["country"] = country
        if len(chunk):
            acc12 = spei.accumulate(chunk, window=12, value_col="D")
            baseline_acc = acc12[(acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
            fitted = spei.fit_baseline(baseline_acc, "D_acc12", POOL_COLS, spei.loglogistic_fit_fn)
            spei12 = spei.standardize(acc12, "D_acc12", fitted, POOL_COLS, clip_bound, "SPEI_12")
            spei12 = spei12[spei12["period"] == "baseline"].dropna(subset=["SPEI_12"])
            fd = spei.severe_drought_frequency(spei12, "SPEI_12", severe_threshold, ["id", "model"])
            fd["country"] = country
            fd_parts.append(fd)
        del chunk
        gc.collect()

        country_cell_ids = {cid for cid, c in cell_country.items() if c == country}
        if country_cell_ids:
            parts = []
            for model in models:
                cchunk = pd.read_parquet(cell_path, filters=[("model", "=", model)])
                cchunk = cchunk.copy()
                cchunk["id"] = cchunk["cell_lat"].astype(str) + "_" + cchunk["cell_lon"].astype(str)
                cchunk = cchunk[cchunk["id"].isin(country_cell_ids)]
                cchunk["country"] = country
                if len(cchunk):
                    acc12 = spei.accumulate(
                        cchunk[["id", "model", "scenario", "period", "month", "D", "country"]], window=12, value_col="D"
                    )
                    baseline = acc12[(acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
                    parts.append(baseline.dropna(subset=["D_acc12"])[POOL_COLS + ["month", "D_acc12"]])
                del cchunk
                gc.collect()
            if parts:
                pooled_baseline = pd.concat(parts, ignore_index=True)
                fitted12 = spei.fit_baseline(pooled_baseline, "D_acc12", POOL_COLS, spei.loglogistic_fit_fn)
                del pooled_baseline
                for model in models:
                    cchunk = pd.read_parquet(cell_path, filters=[("model", "=", model)])
                    cchunk = cchunk.copy()
                    cchunk["id"] = cchunk["cell_lat"].astype(str) + "_" + cchunk["cell_lon"].astype(str)
                    cchunk = cchunk[cchunk["id"].isin(country_cell_ids)]
                    cchunk["country"] = country
                    if len(cchunk):
                        acc12 = spei.accumulate(
                            cchunk[["id", "model", "scenario", "period", "month", "D", "country"]], window=12, value_col="D"
                        )
                        spei12 = spei.standardize(acc12, "D_acc12", fitted12, POOL_COLS, clip_bound, "SPEI_12")
                        spei12 = spei12[spei12["period"] == "baseline"].dropna(subset=["SPEI_12"])
                        fd = spei.severe_drought_frequency(spei12, "SPEI_12", severe_threshold, ["id", "model"])
                        fd["country"] = country
                        fd_parts.append(fd)
                    del cchunk
                    gc.collect()
        print(f"{country}: done")

    del catchment_all
    fd_all = pd.concat(fd_parts, ignore_index=True)
    print("\n=== (country, month)-only pool: mean F_D per country ===")
    print(fd_all.groupby("country")["F_D"].agg(["mean", "median", "count"]))
    spread = fd_all.groupby("country")["F_D"].mean()
    print(f"\nranking: {spread.sort_values(ascending=False).index.tolist()}")
    print(f"spread: {(spread.max() - spread.min())*100:.3f}pp")


if __name__ == "__main__":
    main()
