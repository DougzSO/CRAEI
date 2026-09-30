"""COMANDO 18-G Action 2: PWM vs. Pearson III F_D gap under n=360 (SPEI-12
single per-series fit, no calendar stratification, D54's chosen method),
for series where PWM converges -- must be measured before the fallback
estimator choice is fixed (Action 3).

Real data, full population (all 3 countries, all 5 models, both hydro
catchment and thermal cell buckets), not sampled: n=360 fits are cheap
enough (one fit per series, not per calendar month) to run PWM on every
series directly; Pearson III MLE is only refit on the subset where PWM
already succeeds (to isolate the estimator effect on identical data, same
logic as COMANDO 18-D/18-C). Read-only.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.consolidate import BUCKET_THERMAL_WATER, _assign_bucket

H2_EXCLUDED_PLANT_IDS = {"5131763b8e53f91a7783faeea1fb15095453fd967630297cac52261097daf54c"}


def _fit_both_single(baseline_acc: pd.DataFrame, acc_col: str, group_cols: list[str], threshold: float) -> pd.DataFrame:
    d = baseline_acc.dropna(subset=[acc_col])
    rows = []
    for keys, g in d.groupby(group_cols, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        values = g[acc_col].to_numpy(dtype=float)
        pwm_params, pwm_status = spei._fit_loglogistic_pwm(values)
        if pwm_status != "success":
            continue
        p3_params, p3_status = spei._fit_pearson3_mle(values)
        if p3_status != "success":
            continue
        cdf_pwm = sps.fisk.cdf(values, pwm_params["shape"], pwm_params["loc"], pwm_params["scale"])
        cdf_p3 = sps.pearson3.cdf(values, p3_params["shape"], p3_params["loc"], p3_params["scale"])
        z_pwm = sps.norm.ppf(np.clip(cdf_pwm, 1e-10, 1 - 1e-10))
        z_p3 = sps.norm.ppf(np.clip(cdf_p3, 1e-10, 1 - 1e-10))
        f_d_pwm = float((z_pwm <= threshold).mean())
        f_d_p3 = float((z_p3 <= threshold).mean())
        row = dict(zip(group_cols, keys))
        row["f_d_pwm"] = f_d_pwm
        row["f_d_pearson3"] = f_d_p3
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    threshold = float(params["drought_spei_threshold"]["value"])

    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class", "hydro_type"])
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    hydro_plants = hydro_plants[~hydro_plants["plant_uid"].isin(H2_EXCLUDED_PLANT_IDS)].copy()
    hydro_plants["bucket"] = _assign_bucket(hydro_plants)
    id_country = dict(zip(hydro_plants["plant_uid"], hydro_plants["country"]))
    id_bucket = dict(zip(hydro_plants["plant_uid"], hydro_plants["bucket"]))

    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"])
    thermal_water = plants[plants["tech_class"] == "thermal_water_dependent"]
    tw_cell = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"]).copy()
    tw_cell["id"] = tw_cell["cell_lat"].astype(str) + "_" + tw_cell["cell_lon"].astype(str)
    tw_u = tw_cell.drop_duplicates(subset="id")
    cell_country = dict(zip(tw_u["id"], tw_u["country"]))

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())

    results = []
    for model in models:
        catchment_model = pd.read_parquet(catchment_path, filters=[("model", "=", model)])
        cell_model = pd.read_parquet(cell_path, filters=[("model", "=", model)])

        for country in STUDY_COUNTRIES:
            country_hydro_ids = set(hydro_plants.loc[hydro_plants["country"] == country, "plant_uid"])
            chunk = catchment_model[catchment_model["id"].isin(country_hydro_ids)]
            if len(chunk):
                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(chunk[d_cols], window=12, value_col="D")
                baseline12 = acc12[(acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
                gap = _fit_both_single(baseline12, "D_acc12", ["id", "model"], threshold)
                gap["hazard"] = "SPEI_12"
                results.append(gap)
                del acc12, baseline12

            cchunk = cell_model.copy()
            cchunk["id"] = cchunk["cell_lat"].astype(str) + "_" + cchunk["cell_lon"].astype(str)
            country_cell_ids = {cid for cid, c in cell_country.items() if c == country}
            cchunk = cchunk[cchunk["id"].isin(country_cell_ids)]
            if len(cchunk):
                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(cchunk[d_cols], window=12, value_col="D")
                baseline12 = acc12[(acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
                gap = _fit_both_single(baseline12, "D_acc12", ["id", "model"], threshold)
                gap["hazard"] = "SPEI_12_thermal"
                results.append(gap)
                del acc12, baseline12
            del chunk, cchunk
        del catchment_model, cell_model
        print(f"model {model}: done")

    gap_all = pd.concat(results, ignore_index=True)
    id_country_all = {**id_country, **cell_country}
    id_bucket_all = {**id_bucket, **{c: BUCKET_THERMAL_WATER for c in cell_country}}
    gap_all["country"] = gap_all["id"].map(id_country_all)
    gap_all["bucket"] = gap_all["id"].map(id_bucket_all)
    gap_all["gap_pp"] = (gap_all["f_d_pearson3"] - gap_all["f_d_pwm"]) * 100
    gap_all.to_csv(processed_dir / "n360_pwm_vs_pearson3_gap.csv", index=False)

    print("\n=== PWM vs Pearson III F_D gap at n=360, series where both converge ===")
    for (country, bucket), g in gap_all.groupby(["country", "bucket"]):
        pos = (g["gap_pp"] > 0).sum()
        neg = (g["gap_pp"] < 0).sum()
        print(
            f"{bucket:24s} {country}: n={len(g):4d} median={g['gap_pp'].median():+.3f}pp "
            f"P5={g['gap_pp'].quantile(0.05):+.3f}pp P95={g['gap_pp'].quantile(0.95):+.3f}pp "
            f"sign: {pos} pos / {neg} neg"
        )


if __name__ == "__main__":
    main()
