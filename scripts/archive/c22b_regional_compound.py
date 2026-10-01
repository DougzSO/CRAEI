"""COMANDO 22-B Part 2, Actions 3-6: regional compound metric.

Hypothesis (declared before measuring, per the command): within a single
sub-national region, hydro-drought/thermal-heat dependence is higher than
the national aggregation shows, because national aggregation sums together
climatically decoupled regions.

Reuses `exposure/compound.py` unchanged (no duplicated logic): the module's
functions only ever group by whatever string is in the plants frame's
`country` column, so substituting each plant's national ISO code with its
`region_id` (from `c22b_regional_assignment.py`) and calling the same
`build_compound_series` / `baseline_thresholds` / `flag_compound_months` /
`compound_summary` functions computes the identical metric at regional
resolution.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths
from craei.exposure import compound

RNG = np.random.default_rng(20260930)
BLOCK = 12
N_BOOT = 10_000


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def moving_block_bootstrap_ratio(compound_s, s_above, h_above, block, n_boot):
    n = len(compound_s)
    if n < block:
        return np.full(n_boot, np.nan)
    n_blocks = int(np.ceil(n / block))
    starts_max = n - block
    ratios = np.empty(n_boot)
    for b in range(n_boot):
        starts = RNG.integers(0, starts_max + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        c_r, s_r, h_r = compound_s[idx].mean(), s_above[idx].mean(), h_above[idx].mean()
        denom = s_r * h_r
        ratios[b] = c_r / denom if denom > 0 else np.nan
    return ratios


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])
    outputs_dir = Path(paths["outputs_dir"])
    diag_dir = outputs_dir / "diagnostics"

    region_plants = pd.read_parquet(diag_dir / "c22b_plant_region.parquet")
    inv = pd.read_csv(diag_dir / "c22b_regional_fleet_inventory.csv")
    usable_regions = set(inv.loc[inv["has_both_fleets"], "region_id"])
    print(f"Regions usable for the compound metric (both fleets present): {len(usable_regions)}")

    regional_plants = region_plants[region_plants["region_id"].isin(usable_regions)].copy()
    regional_plants["country_national"] = regional_plants["country"]
    regional_plants["country"] = regional_plants["region_id"]  # reuse compound.py unchanged

    spei = pd.read_parquet(processed_dir / "spei.parquet")
    indices_daily = pd.read_parquet(processed_dir / "indices_daily.parquet")
    plant_cell = pd.read_parquet(processed_dir / "plant_cell.parquet")

    from craei.config import load_params

    params = load_params()
    spei_threshold = params["drought_spei_threshold"]["value"]
    percentile = params["compound_baseline_percentile"]["value"]

    series = compound.build_compound_series(
        regional_plants, spei, indices_daily, plant_cell, spei_threshold
    )
    thresholds = compound.baseline_thresholds(series, percentile)
    flagged = compound.flag_compound_months(series, thresholds)
    summary = compound.compound_summary(flagged)
    # summary's "country" column is actually region_id here.
    summary = summary.rename(columns={"country": "region_id"})
    region_to_country = regional_plants[["region_id", "country_national"]].drop_duplicates()
    summary = summary.merge(region_to_country, on="region_id", how="left")

    print(f"\nRegional compound.csv-equivalent: {len(summary)} rows "
          f"({summary['region_id'].nunique()} regions x up to 3 scenarios x 5 models)")

    # Uncertainty, same method as Part 1, applied per region.
    rows = []
    for (region_id, model, scenario), fut in flagged[flagged["period"] == "future"].groupby(
        ["country", "model", "scenario"]
    ):
        fut = fut.sort_values("month")
        compound_s = fut["compound"].to_numpy(dtype=float)
        s_above = (fut["s_hydro"] > fut["s_hydro_p90"]).to_numpy(dtype=float)
        h_above = (fut["h_thermal"] > fut["h_thermal_p90"]).to_numpy(dtype=float)
        n_future = len(fut)
        k_obs = int(compound_s.sum())
        f_s, f_h = s_above.mean(), h_above.mean()
        ratio = (k_obs / n_future) / (f_s * f_h) if f_s * f_h > 0 else np.nan

        boot = moving_block_bootstrap_ratio(compound_s, s_above, h_above, BLOCK, N_BOOT)
        boot_valid = boot[~np.isnan(boot)]
        ci_lo, ci_hi = (
            tuple(np.percentile(boot_valid, [2.5, 97.5])) if len(boot_valid) else (np.nan, np.nan)
        )
        reportable = bool(not np.isnan(ci_lo) and (ci_lo > 1.0 or ci_hi < 1.0))
        rows.append(
            {
                "region_id": region_id,
                "model": model,
                "scenario": scenario,
                "n_future_months": n_future,
                "k_future_observed": k_obs,
                "dependence_ratio": ratio,
                "ci_block_lo": ci_lo,
                "ci_block_hi": ci_hi,
                "reportable_block_excludes_1": reportable,
            }
        )
    reg_unc = pd.DataFrame(rows).merge(region_to_country, on="region_id", how="left")
    reg_unc.to_csv(diag_dir / "c22b_regional_dependence_uncertainty.csv", index=False)

    # Action 4: compare regional vs national.
    national_unc = pd.read_csv(diag_dir / "c22b_dependence_uncertainty.csv")
    print(
        "\nRegional dependence_ratio distribution by country "
        "(all regional cells, point estimates):"
    )
    for country in ["BRA", "IND", "PRT"]:
        sub = reg_unc[reg_unc["country_national"] == country]["dependence_ratio"].dropna()
        if len(sub) == 0:
            continue
        print(
            f"  {country}: n={len(sub)}, median={sub.median():.3f}, "
            f"P5={sub.quantile(0.05):.3f}, P95={sub.quantile(0.95):.3f}"
        )

    n_reg_reportable = reg_unc["reportable_block_excludes_1"].sum()
    print(f"\nRegional cells with block CI excluding 1.0: {n_reg_reportable} / {len(reg_unc)}")

    print("\nPer country/model: national ratio vs median regional ratio (point estimates):")
    nat_by_cm = national_unc.groupby(["country", "model"])["dependence_ratio"].mean()
    for (country, model), nat_val in nat_by_cm.items():
        reg_vals = reg_unc.loc[
            (reg_unc["country_national"] == country) & (reg_unc["model"] == model),
            "dependence_ratio",
        ].dropna()
        if len(reg_vals) == 0:
            continue
        print(
            f"  {country}/{model}: national={nat_val:.3f} vs "
            f"regional median={reg_vals.median():.3f} "
            f"(n_regions={reg_vals.shape[0]}, "
            f"regional range [{reg_vals.min():.3f}, {reg_vals.max():.3f}])"
        )

    # Hypothesis verdict.
    higher = 0
    lower_or_equal = 0
    for country in ["BRA", "IND", "PRT"]:
        nat_vals = national_unc.loc[national_unc["country"] == country, "dependence_ratio"]
        reg_vals = reg_unc.loc[reg_unc["country_national"] == country, "dependence_ratio"].dropna()
        if len(nat_vals) == 0 or len(reg_vals) == 0:
            continue
        if reg_vals.median() > nat_vals.median():
            higher += 1
        else:
            lower_or_equal += 1
    print(
        f"\nHYPOTHESIS VERDICT: regional median ratio higher than national in "
        f"{higher}/{higher + lower_or_equal} countries "
        "(report, not interpreted as error if not confirmed)."
    )

    # Action 6: sensitivity to regional fleet size.
    inv_cap = inv.set_index("region_id")[["hydro_capacity_mw", "thermal_water_capacity_mw"]]
    reg_unc["total_regional_cap_mw"] = reg_unc["region_id"].map(
        lambda r: inv_cap.loc[r, "hydro_capacity_mw"] + inv_cap.loc[r, "thermal_water_capacity_mw"]
        if r in inv_cap.index
        else np.nan
    )
    corr = reg_unc[["total_regional_cap_mw", "dependence_ratio"]].dropna().corr().iloc[0, 1]
    print(
        f"\nSensitivity to regional fleet size: Pearson correlation between "
        f"total regional capacity and dependence_ratio point estimate = {corr:.3f}"
    )
    print(
        "If |corr| is large, part of the regional signal is a small-sample artifact, not a real "
        "effect of spatial scale, and must be reported as such."
    )


if __name__ == "__main__":
    main()
