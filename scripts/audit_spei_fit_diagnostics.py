"""COMANDO 17-B: SPEI fit-failure diagnostics (Spec §1.4 H2, §3 Step 6;
`docs/LIMITATIONS.md` L16).

Diagnoses why COMANDO 17's baseline log-logistic/gamma fits fail -- sample
size per (group, calendar-month), failure cause, accumulate/cut order, and
calendar-month gaps in the water-balance series -- and reports hydro plants
dominated by PET-truncated cells (COMANDO 16). Report only (Action 7): does
not decide `MIN_FIT_SAMPLES` or an acceptable failure rate; that is the
author's call once these numbers exist.

Chunked by (model, country) and processed with explicit `gc.collect()`, same
discipline as `scripts/08_spei.py` (`docs/DECISIONS.md` D44, CLAUDE.md Rule
11) -- only small per-chunk diagnostic tables (counts, not raw series) are
kept across chunks, so this stays well inside this machine's ~6 GB.
"""

import gc
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from craei.acquire.isimip import STUDY_COUNTRIES
from craei.config import load_paths
from craei.hazards import spei
from craei.hazards.loading import cells_with_catchments_by_country

MIN_SAMPLE_FOR_REPORT = 25  # Action 1: series with fewer valid values than this are flagged


def _classify_loglogistic(values: np.ndarray) -> str:
    """Action 2 cause for one (group, calendar-month) log-logistic (SPEI) fit."""
    values = values[np.isfinite(values)]
    if len(values) < spei.MIN_FIT_SAMPLES:
        return "few_valid_values"
    if np.ptp(values) < 1e-9:
        return "degenerate_scale"
    try:
        params = spei._fit_loglogistic_pwm(values)
    except Exception:
        return "other"
    return "ok" if params is not None else "not_converged"


def _classify_gamma(values: np.ndarray) -> str:
    """Action 2 cause for one (group, calendar-month) gamma (SPI) fit."""
    values = values[np.isfinite(values)]
    if len(values) < spei.MIN_FIT_SAMPLES:
        return "few_valid_values"
    if np.ptp(values) < 1e-9:
        return "degenerate_scale"
    try:
        params = stats.gamma.fit(values, floc=0.0)
    except Exception:
        return "other"
    if not all(np.isfinite(p) for p in params) or params[-1] <= 0:
        return "not_converged"
    return "ok"


def diagnose_baseline_fits(
    acc: pd.DataFrame, acc_col: str, group_cols: list[str], classify_fn
) -> pd.DataFrame:
    """Actions 1+2: one row per (group, calendar-month) with its sample size and failure cause.

    Mirrors `spei.fit_baseline`'s own restriction and grouping exactly (same
    `period == "baseline"` + `month >= BASELINE_START_YEAR` cut, same
    `dropna(subset=[acc_col])`, same `group_cols + ["cal_month"]` groupby) so
    these numbers describe the real production fit, not an approximation of it.
    """
    baseline_acc = acc[
        (acc["period"] == "baseline") & (acc["month"] >= f"{spei.BASELINE_START_YEAR}-01-01")
    ]
    d = baseline_acc.dropna(subset=[acc_col]).copy()
    d["cal_month"] = d["month"].dt.month
    rows = []
    for keys, g in d.groupby(group_cols + ["cal_month"], sort=False):
        values = g[acc_col].to_numpy(dtype=float)
        rows.append({"n_valid": len(values), "cause": classify_fn(values)})
    return pd.DataFrame(rows, columns=["n_valid", "cause"])


def count_month_gaps(chunk: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """Action 4: per-group count of missing calendar months between its first and last month."""
    d = chunk[[*group_cols, "month"]].copy()
    d["_midx"] = d["month"].dt.year * 12 + d["month"].dt.month
    g = d.groupby(group_cols)["_midx"].agg(n="size", mn="min", mx="max")
    g["expected"] = g["mx"] - g["mn"] + 1
    g["gaps"] = g["expected"] - g["n"]
    return g[["gaps"]].reset_index(drop=True)


def _report_sample_sizes(label: str, diag_parts: list[pd.DataFrame]) -> None:
    empty = pd.DataFrame(columns=["n_valid", "cause"])
    diag = pd.concat(diag_parts, ignore_index=True) if diag_parts else empty
    n = diag["n_valid"]
    print(f"\n--- {label}: sample size per (group, calendar-month), n={len(diag)} ---")
    print(f"median={n.median():.1f}, P5={n.quantile(0.05):.1f}, min={n.min()}")
    print(f"(group, calendar-month) combinations with < {MIN_SAMPLE_FOR_REPORT} valid values: "
          f"{(n < MIN_SAMPLE_FOR_REPORT).sum()}/{len(diag)}")
    print("failure cause counts (excluding 'ok'):")
    print(diag.loc[diag["cause"] != "ok", "cause"].value_counts().to_string())


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])

    plants = pd.read_parquet(
        processed_dir / "plants.parquet",
        columns=["plant_uid", "country", "tech_class", "hydro_type", "basin_id", "capacity_mw"],
    )
    hydro_plants = plants[plants["tech_class"] == "hydro"]
    is_ror = hydro_plants["hydro_type"] == "run-of-river"
    run_of_river_ids = set(hydro_plants.loc[is_ror, "plant_uid"])
    hydro_ids_by_country = {
        country: set(hydro_plants.loc[hydro_plants["country"] == country, "plant_uid"])
        for country in STUDY_COUNTRIES
    }
    cells_by_country = {
        country: set(zip(cells["cell_lat"], cells["cell_lon"]))
        for country, cells in cells_with_catchments_by_country(processed_dir).items()
    }

    catchment_path = processed_dir / "water_balance_catchment.parquet"
    cell_path = processed_dir / "water_balance_cell.parquet"
    models = sorted(pd.read_parquet(catchment_path, columns=["model"])["model"].unique())

    hydro12_parts, hydro3_parts, thermal12_parts = [], [], []
    gaps_catchment_parts, gaps_cell_parts = [], []

    for model in models:
        catchment_model = pd.read_parquet(catchment_path, filters=[("model", "=", model)])
        cell_model = pd.read_parquet(cell_path, filters=[("model", "=", model)])

        for country in STUDY_COUNTRIES:
            country_ids = hydro_ids_by_country[country]
            group_cols3 = ["id", "model", "scenario"]
            catchment_chunk = catchment_model[catchment_model["id"].isin(country_ids)]
            if len(catchment_chunk):
                gaps_catchment_parts.append(count_month_gaps(catchment_chunk, group_cols3))

                d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12 = spei.accumulate(catchment_chunk[d_cols], window=12, value_col="D")
                hydro12_parts.append(
                    diagnose_baseline_fits(acc12, "D_acc12", ["id", "model"], _classify_loglogistic)
                )

                ror = catchment_chunk.loc[catchment_chunk["id"].isin(run_of_river_ids), d_cols]
                if len(ror):
                    acc3 = spei.accumulate(ror, window=3, value_col="D")
                    hydro3_parts.append(
                        diagnose_baseline_fits(
                            acc3, "D_acc3", ["id", "model"], _classify_loglogistic
                        )
                    )
                del acc12, ror
            del catchment_chunk

            cell_mask = pd.Series(
                list(zip(cell_model["cell_lat"], cell_model["cell_lon"])), index=cell_model.index
            ).isin(cells_by_country[country])
            cell_chunk = cell_model[cell_mask].copy()
            if len(cell_chunk):
                cell_chunk["id"] = (
                    cell_chunk["cell_lat"].astype(str) + "_" + cell_chunk["cell_lon"].astype(str)
                )
                gaps_cell_parts.append(count_month_gaps(cell_chunk, group_cols3))

                cell_d_cols = ["id", "model", "scenario", "period", "month", "D"]
                acc12_cell = spei.accumulate(cell_chunk[cell_d_cols], window=12, value_col="D")
                thermal12_parts.append(
                    diagnose_baseline_fits(
                        acc12_cell, "D_acc12", ["id", "model"], _classify_loglogistic
                    )
                )
                del acc12_cell
            del cell_chunk

            print(f"{model}/{country}: done")

        del catchment_model, cell_model
        gc.collect()

    # Action 3: order of accumulation vs. baseline-window cut.
    print("\n=== Action 3: accumulate-then-cut order ===")
    print(
        "scripts/08_spei.py's process_hydro/process_thermal_cell call spei.accumulate() on the\n"
        "full water_balance_{catchment,cell} chunk (1984 lead-in month through 2070, all\n"
        "scenarios) BEFORE _fit_and_standardize restricts to period=='baseline' and\n"
        "month>=1985-01-01 -- accumulate first, cut second. The only NaN this order itself\n"
        "introduces are the 11 (window=12) / 2 (window=3) lead-in months of 1984, which never\n"
        "enter the 1985-2014 baseline sample. This audit's diagnose_baseline_fits() applies the\n"
        "same order. Had the cut come first, every calendar month's baseline sample would be\n"
        "short by however many of its 30 years fall in the first (window-1) months after the\n"
        "cut point -- the per-calendar-month sample-size numbers below would show that pattern."
    )

    # Actions 1+2.
    _report_sample_sizes("SPEI-12 hydro catchment", hydro12_parts)
    _report_sample_sizes("SPEI-3 run-of-river", hydro3_parts)
    _report_sample_sizes("SPEI-12 thermal cell", thermal12_parts)

    # Action 4.
    print("\n=== Action 4: calendar-month gaps in water-balance series (after COMANDO 16 join) ===")
    for label, parts in (
        ("water_balance_catchment (hydro)", gaps_catchment_parts),
        ("water_balance_cell (thermal)", gaps_cell_parts),
    ):
        gaps = pd.concat(parts, ignore_index=True)["gaps"] if parts else pd.Series(dtype=int)
        print(f"{label}: {len(gaps)} (id, model, scenario) series; max gaps in any one series: "
              f"{gaps.max() if len(gaps) else 'n/a'}; series with >=1 gap: {(gaps > 0).sum()}")

    # Action 5: hydro plants dominated by PET-truncated cells (COMANDO 16's 51 India cells).
    print("\n=== Action 5: hydro plants by truncated-PET-cell catchment weight ===")
    weights = pd.read_parquet(processed_dir / "catchment_weights.parquet")
    truncated_cells_path = processed_dir / "truncated_pet_cells.parquet"
    if not truncated_cells_path.exists():
        print(f"{truncated_cells_path} not found -- rerun the PET-truncation audit script first")
    else:
        truncated_cells = pd.read_parquet(truncated_cells_path)
        trunc_cells = truncated_cells[["cell_lat", "cell_lon"]].drop_duplicates()
        hit = weights.merge(trunc_cells, on=["cell_lat", "cell_lon"])
        per_plant = hit.groupby("plant_uid", as_index=False)["weight"].sum()
        per_plant = per_plant.merge(
            plants[["plant_uid", "country", "basin_id", "capacity_mw"]], on="plant_uid"
        )
        for threshold in (0.5, 0.8):
            n = (per_plant["weight"] > threshold).sum()
            print(f"hydro plants with truncated-cell weight sum > {threshold}: {n}")
        at_one = per_plant[per_plant["weight"] >= 1.0 - 1e-9]
        print(f"hydro plants with truncated-cell weight sum == 1.0: {len(at_one)}")
        cols = ["plant_uid", "country", "basin_id", "capacity_mw", "weight"]
        print(at_one[cols].to_string(index=False))


if __name__ == "__main__":
    main()
