"""COMANDO 18-F: temporal (same-series) alternatives to regional (cross-series)
pooling for raising SPEI's fitted sample size, per docs/DECISIONS.md D51's
reversion.

D52's regional pool (country, bucket, calendar month) mixed different
plants/cells/models into one shared reference, standardizing each series
against a regional peer average instead of its own climatology -- breaking
SPEI's basic definition and leaving per-plant R_D undefined for 24-64% of
series (O09). This script measures two temporal alternatives that never mix
different (id, model) series, only widen the time window within each
series' own 30-year record:

(a) calendar-month window: fit calendar month m using D values from m and
    its k adjacent calendar months (circular), all 30 years -- k=1 gives
    n=90, k=2 gives n=150. Applies to SPEI-12 and SPEI-3.
(b) single per-series fit: fit once per (id, model) on all 360 baseline
    values, no calendar-month stratification -- only for SPEI-12, where a
    12-month accumulation already removes most seasonality (Action 5 checks
    this directly rather than assuming it).

Compared against the original per-series, single-calendar-month fit (n=30,
PWM only, no Pearson III fallback -- kept constant across every variant so
only the sample size changes, not the estimator) and, for reference, the
already-measured D52 regional-pool numbers (not recomputed here). Read-only:
writes nothing to spei.parquet.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_params, load_paths
from craei.hazards import spei
from craei.hazards.consolidate import BUCKET_THERMAL_WATER, _assign_bucket

H2_EXCLUDED_PLANT_IDS = {"5131763b8e53f91a7783faeea1fb15095453fd967630297cac52261097daf54c"}
GROUP_COLS = ["id", "model"]


def _fit_with_key(tagged: pd.DataFrame, acc_col: str, group_cols: list[str], key_col: str) -> pd.DataFrame:
    d = tagged.dropna(subset=[acc_col])
    rows = []
    for keys, g in d.groupby(group_cols + [key_col], sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        params, distribution = spei.loglogistic_fit_fn(g[acc_col].to_numpy(dtype=float))
        row = dict(zip(group_cols + [key_col], keys))
        row["fit_ok"] = params is not None
        row["fit_params"] = params
        row["distribution"] = distribution
        rows.append(row)
    return pd.DataFrame(rows).rename(columns={key_col: "cal_month"})


def _window_frame(baseline_acc: pd.DataFrame, acc_col: str, k: int) -> pd.DataFrame:
    d = baseline_acc.dropna(subset=[acc_col]).copy()
    d["true_month"] = d["month"].dt.month
    parts = []
    for offset in range(-k, k + 1):
        tmp = d.copy()
        tmp["target_month"] = ((tmp["true_month"] - 1 + offset) % 12) + 1
        parts.append(tmp)
    return pd.concat(parts, ignore_index=True)


def fit_variant_a(acc: pd.DataFrame, baseline_acc: pd.DataFrame, acc_col: str, k: int, clip_bound: float, out_col: str):
    expanded = _window_frame(baseline_acc, acc_col, k)
    fitted = _fit_with_key(expanded, acc_col, GROUP_COLS, "target_month")
    out = spei.standardize(acc, acc_col, fitted, GROUP_COLS, clip_bound, out_col)
    return out, fitted


def fit_variant_b(acc: pd.DataFrame, baseline_acc: pd.DataFrame, acc_col: str, clip_bound: float, out_col: str):
    d = baseline_acc.dropna(subset=[acc_col])
    rows = []
    for keys, g in d.groupby(GROUP_COLS, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        params, distribution = spei.loglogistic_fit_fn(g[acc_col].to_numpy(dtype=float))
        rows.append({**dict(zip(GROUP_COLS, keys)), "fit_ok": params is not None, "fit_params": params, "distribution": distribution})
    single = pd.DataFrame(rows)
    months = pd.DataFrame({"cal_month": range(1, 13)})
    fitted = single.merge(months, how="cross")
    out = spei.standardize(acc, acc_col, fitted, GROUP_COLS, clip_bound, out_col)
    return out, single


def fit_original(acc: pd.DataFrame, baseline_acc: pd.DataFrame, acc_col: str, clip_bound: float, out_col: str):
    fitted = spei.fit_baseline(baseline_acc, acc_col, GROUP_COLS, spei.loglogistic_fit_fn)
    out = spei.standardize(acc, acc_col, fitted, GROUP_COLS, clip_bound, out_col)
    return out, fitted


def main() -> None:
    paths = load_paths()
    params = load_params()
    processed_dir = Path(paths["processed_dir"])
    clip_bound = float(params["spei_clip_bound"]["value"])
    threshold = float(params["drought_spei_threshold"]["value"])

    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=["plant_uid", "country", "tech_class", "hydro_type"])
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    hydro_plants = hydro_plants[~hydro_plants["plant_uid"].isin(H2_EXCLUDED_PLANT_IDS)].copy()
    hydro_plants["bucket"] = _assign_bucket(hydro_plants)
    id_country = dict(zip(hydro_plants["plant_uid"], hydro_plants["country"]))
    id_bucket = dict(zip(hydro_plants["plant_uid"], hydro_plants["bucket"]))
    run_of_river_ids = set(hydro_plants.loc[hydro_plants["hydro_type"] == "run-of-river", "plant_uid"])

    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet", columns=["plant_uid", "cell_lat", "cell_lon"])
    thermal_water = plants[plants["tech_class"] == "thermal_water_dependent"]
    tw_cell = thermal_water.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"]).copy()
    tw_cell["id"] = tw_cell["cell_lat"].astype(str) + "_" + tw_cell["cell_lon"].astype(str)
    tw_u = tw_cell.drop_duplicates(subset="id")
    cell_country = dict(zip(tw_u["id"], tw_u["country"]))

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())

    variants = ["original_n30", "window_k1_n90", "window_k2_n150", "single_n360"]
    fd_rows = []  # per (variant, hazard, id, model) F_D
    fail_rows = []  # per (variant, hazard) fit failure counts
    seasonal_rows = []  # variant b seasonal residual check

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

                for label, fn in [
                    ("original_n30", lambda a, b: fit_original(a, b, "D_acc12", clip_bound, "SPEI_X")),
                    ("window_k1_n90", lambda a, b: fit_variant_a(a, b, "D_acc12", 1, clip_bound, "SPEI_X")),
                    ("window_k2_n150", lambda a, b: fit_variant_a(a, b, "D_acc12", 2, clip_bound, "SPEI_X")),
                    ("single_n360", lambda a, b: fit_variant_b(a, b, "D_acc12", clip_bound, "SPEI_X")),
                ]:
                    out, fitted = fn(acc12, baseline12)
                    base_out = out[out["period"] == "baseline"].dropna(subset=["SPEI_X"])
                    fd = spei.severe_drought_frequency(base_out, "SPEI_X", threshold, GROUP_COLS)
                    fd["hazard"] = "SPEI_12"
                    fd["variant"] = label
                    fd_rows.append(fd)
                    n_ok = int(fitted["fit_ok"].sum())
                    fail_rows.append({"variant": label, "hazard": "SPEI_12", "model": model, "country": country, "n_fit_attempts": len(fitted), "n_fit_ok": n_ok})
                    if label == "single_n360":
                        m = out[out["period"] == "baseline"].dropna(subset=["SPEI_X"]).copy()
                        m["cal_month"] = m["month"].dt.month
                        seasonal_rows.append(m.groupby("cal_month")["SPEI_X"].mean().rename(f"{model}_{country}"))
                    del out, fitted, base_out
                    gc.collect()

                ror = chunk.loc[chunk["id"].isin(run_of_river_ids), d_cols]
                if len(ror):
                    acc3 = spei.accumulate(ror, window=3, value_col="D")
                    baseline3 = acc3[(acc3["period"] == "baseline") & (acc3["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
                    for label, fn in [
                        ("original_n30", lambda a, b: fit_original(a, b, "D_acc3", clip_bound, "SPEI_X3")),
                        ("window_k1_n90", lambda a, b: fit_variant_a(a, b, "D_acc3", 1, clip_bound, "SPEI_X3")),
                        ("window_k2_n150", lambda a, b: fit_variant_a(a, b, "D_acc3", 2, clip_bound, "SPEI_X3")),
                    ]:
                        out, fitted = fn(acc3, baseline3)
                        base_out = out[out["period"] == "baseline"].dropna(subset=["SPEI_X3"])
                        fd = spei.severe_drought_frequency(base_out, "SPEI_X3", threshold, GROUP_COLS)
                        fd["hazard"] = "SPEI_3"
                        fd["variant"] = label
                        fd_rows.append(fd)
                        n_ok = int(fitted["fit_ok"].sum())
                        fail_rows.append({"variant": label, "hazard": "SPEI_3", "model": model, "country": country, "n_fit_attempts": len(fitted), "n_fit_ok": n_ok})
                        del out, fitted, base_out
                        gc.collect()
                del acc12, baseline12
            del chunk

            country_cell_ids = {cid for cid, c in cell_country.items() if c == country}
            cchunk = cell_model.copy()
            cchunk["id"] = cchunk["cell_lat"].astype(str) + "_" + cchunk["cell_lon"].astype(str)
            cchunk = cchunk[cchunk["id"].isin(country_cell_ids)]
            if len(cchunk):
                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(cchunk[d_cols], window=12, value_col="D")
                baseline12 = acc12[(acc12["period"] == "baseline") & (acc12["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
                for label, fn in [
                    ("original_n30", lambda a, b: fit_original(a, b, "D_acc12", clip_bound, "SPEI_X")),
                    ("window_k1_n90", lambda a, b: fit_variant_a(a, b, "D_acc12", 1, clip_bound, "SPEI_X")),
                    ("window_k2_n150", lambda a, b: fit_variant_a(a, b, "D_acc12", 2, clip_bound, "SPEI_X")),
                    ("single_n360", lambda a, b: fit_variant_b(a, b, "D_acc12", clip_bound, "SPEI_X")),
                ]:
                    out, fitted = fn(acc12, baseline12)
                    base_out = out[out["period"] == "baseline"].dropna(subset=["SPEI_X"])
                    fd = spei.severe_drought_frequency(base_out, "SPEI_X", threshold, GROUP_COLS)
                    fd["hazard"] = "SPEI_12_thermal"
                    fd["variant"] = label
                    fd_rows.append(fd)
                    n_ok = int(fitted["fit_ok"].sum())
                    fail_rows.append({"variant": label, "hazard": "SPEI_12_thermal", "model": model, "country": country, "n_fit_attempts": len(fitted), "n_fit_ok": n_ok})
                    if label == "single_n360":
                        m = out[out["period"] == "baseline"].dropna(subset=["SPEI_X"]).copy()
                        m["cal_month"] = m["month"].dt.month
                        seasonal_rows.append(m.groupby("cal_month")["SPEI_X"].mean().rename(f"thermal_{model}_{country}"))
                    del out, fitted, base_out
                    gc.collect()
                del acc12, baseline12
            del cchunk
            gc.collect()
        del catchment_model, cell_model
        gc.collect()
        print(f"model {model}: done")

    fd_all = pd.concat(fd_rows, ignore_index=True)
    fail_all = pd.DataFrame(fail_rows)
    fd_all.to_csv(processed_dir / "temporal_pooling_fd_variants.csv", index=False)

    id_country_all = {**id_country, **cell_country}
    id_bucket_all = {**id_bucket, **{c: BUCKET_THERMAL_WATER for c in cell_country}}
    fd_all["country"] = fd_all["id"].map(id_country_all)
    fd_all["bucket"] = fd_all["id"].map(id_bucket_all)

    print("\n=== Action 2/3: F_D baseline by variant, country, bucket -- mean/median/P5/P95/median-mean-ratio ===")
    for (variant, hazard), g in fd_all.groupby(["variant", "hazard"]):
        print(f"\n--- {variant} / {hazard} ---")
        stats_tbl = g.groupby(["country", "bucket"])["F_D"].agg(["mean", "median", lambda s: s.quantile(0.05), lambda s: s.quantile(0.95), "count"])
        stats_tbl.columns = ["mean", "median", "P5", "P95", "count"]
        stats_tbl["median_over_mean"] = stats_tbl["median"] / stats_tbl["mean"]
        print(stats_tbl)

    print("\n=== Fit failure rate by variant/hazard ===")
    fail_summary = fail_all.groupby(["variant", "hazard"]).agg(n_attempts=("n_fit_attempts", "sum"), n_ok=("n_fit_ok", "sum"))
    fail_summary["failure_rate"] = 1 - fail_summary["n_ok"] / fail_summary["n_attempts"]
    print(fail_summary)

    print("\n=== Action 5: variant (b) seasonal residual (mean SPEI by calendar month) ===")
    seasonal_df = pd.concat(seasonal_rows, axis=1)
    print(seasonal_df.mean(axis=1).rename("mean_SPEI_by_cal_month"))
    seasonal_df.to_csv(processed_dir / "temporal_pooling_variant_b_seasonal.csv")


if __name__ == "__main__":
    main()
