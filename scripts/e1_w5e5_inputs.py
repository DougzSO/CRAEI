"""E1 observed inputs from W5E5 (D140, docs/article/E1_spec.md section 4).

Raw W5E5 v2.0 files (tasmax, tasmin, pr; Brazil box; 1984-2019) are already in raw_dir. For the cells of
the water-dependent thermal plants (operating + planned) derive, with the same PET (Hargreaves), water
balance and single baseline fit (1985-2014) as scripts/24_w5e5_spei_validation.py and scripts/08_spei.py:
monthly SPEI-12, SPI-12 and N35 (days with TX >= 35 C). For the hydro catchments derive SPI-12 from the
existing water_balance_catchment_w5e5.parquet (spei_w5e5.parquet only carries SPEI-12).

Writes data/processed/w5e5_thermal_cells_monthly.parquet (id, month, SPEI_12, SPI_12, N35) and
data/processed/w5e5_hydro_spi12.parquet (id, month, SPI_12). New files; nothing else is touched.
"""

import gc
import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e1_populations as pops  # noqa: E402

from craei.config import load_datasets, load_params, load_paths  # noqa: E402
from craei.hazards import heat, pet, spei  # noqa: E402
from craei.hazards.pet import KELVIN_OFFSET_C  # noqa: E402

w5 = importlib.import_module("24_w5e5_spei_validation")
HEAT_C = 35.0
PR_TO_MM = w5.PR_FLUX_TO_MM_PER_DAY


def label_period(df):
    in_base = df["month"].dt.year.between(spei.BASELINE_START_YEAR, spei.BASELINE_END_YEAR)
    return df.assign(period=in_base.map({True: "baseline", False: "observed"}))


def index_12(balance, value_col, out_col, fit_fn, clip):
    """12-month standardized index per (id, model), single baseline fit (as scripts/24 and 08)."""
    group_cols = ["id", "model"]
    d = label_period(balance)
    src = d.rename(columns={value_col: "x"})[[*group_cols, "scenario", "period", "month", "x"]]
    acc = spei.accumulate(src, window=12, value_col="x")
    base = acc[(acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")]
    fitted = spei.fit_baseline_single(base, "x_acc12", group_cols, fit_fn)
    out = spei.standardize(acc, "x_acc12", fitted, group_cols, clip_bound=clip, out_col=out_col)
    fail = spei.fit_failure_summary(fitted, group_cols)
    print(f"{out_col}: fit failures in {(fail['n_months_failed'] > 0).sum()}/{len(fail)} series")
    return out[["id", "month", out_col]]


def thermal_cells_monthly(paths, datasets_cfg, cells, clip):
    raw_dir = Path(paths["raw_dir"])
    bbox = datasets_cfg["bboxes"]["BRA"]
    start, end = int(datasets_cfg["w5e5"]["years"]["start"]), int(datasets_cfg["w5e5"]["years"]["end"])
    tx = w5.load_cell_series_multi(w5.find_files(raw_dir, "tasmax", bbox), cells, "tasmax_c", start, end)
    tx["tasmax_c"] -= KELVIN_OFFSET_C
    n35 = heat.monthly_hot_day_counts(tx, HEAT_C).rename(columns={"value": "N35"})
    tn = w5.load_cell_series_multi(w5.find_files(raw_dir, "tasmin", bbox), cells, "tasmin_c", start, end)
    tn["tasmin_c"] -= KELVIN_OFFSET_C
    temps = tx.merge(tn, on=["date", "cell_lat", "cell_lon"])
    del tx, tn
    gc.collect()
    n_bad = int(pet.count_tx_below_tn(temps)["n_tx_below_tn"].sum())
    pet_df = pet.daily_pet(temps)
    print(f"TX<TN days {n_bad}; PET-truncated days {int(pet_df['pet_truncated'].sum())}")
    del temps
    pr = w5.load_cell_series_multi(w5.find_files(raw_dir, "pr", bbox), cells, "pr_mm", start, end)
    pr["pr_mm"] *= PR_TO_MM
    daily = pet_df[["date", "cell_lat", "cell_lon", "pet_mm"]].merge(
        pr.rename(columns={"pr_mm": "p_mm"}), on=["date", "cell_lat", "cell_lon"])
    daily["model"], daily["scenario"], daily["period"] = "w5e5", "w5e5", "baseline"
    del pet_df, pr
    gc.collect()
    bal = pet.monthly_water_balance(daily)
    bal["id"] = bal["cell_lat"].astype(str) + "_" + bal["cell_lon"].astype(str)
    spei12 = index_12(bal, "D", "SPEI_12", spei.fit_spei_distribution, clip)
    spi12 = index_12(bal, "P", "SPI_12", spei.gamma_fit_fn, clip)
    n35["id"] = n35["cell_lat"].astype(str) + "_" + n35["cell_lon"].astype(str)
    out = spei12.merge(spi12, on=["id", "month"], how="outer").merge(
        n35[["id", "month", "N35"]], on=["id", "month"], how="left")
    return out


def hydro_spi(proc, hydro_ids, clip):
    wb = pd.read_parquet(proc / "water_balance_catchment_w5e5.parquet")
    wb = wb[wb["id"].isin(set(hydro_ids))]
    assert wb["id"].nunique() == len(set(hydro_ids)), (wb["id"].nunique(), len(set(hydro_ids)))
    return index_12(wb, "P", "SPI_12", spei.gamma_fit_fn, clip)


def main():
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    clip = float(load_params()["spei_clip_bound"]["value"])
    p = pops.load_populations(proc)
    cells = (p["operating_plus_planned"][["cell_lat", "cell_lon"]].drop_duplicates()
             .reset_index(drop=True))
    print(f"thermal cells: {len(cells)}; hydro plants: {len(p['hydro'])}")
    t = thermal_cells_monthly(paths, load_datasets(), cells, clip)
    assert t["N35"].notna().all() and t["id"].nunique() == len(cells)
    t.to_parquet(proc / "w5e5_thermal_cells_monthly.parquet", index=False)
    print("written w5e5_thermal_cells_monthly.parquet", t.shape,
          "SPEI NaN", int(t["SPEI_12"].isna().sum()), "SPI NaN", int(t["SPI_12"].isna().sum()))
    h = hydro_spi(proc, p["hydro"]["plant_uid"], clip)
    h.to_parquet(proc / "w5e5_hydro_spi12.parquet", index=False)
    print("written w5e5_hydro_spi12.parquet", h.shape, "SPI NaN", int(h["SPI_12"].isna().sum()))
    print("month range:", t["month"].min(), t["month"].max(), "| np:", np.__version__)


if __name__ == "__main__":
    main()
