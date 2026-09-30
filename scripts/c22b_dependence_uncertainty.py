"""COMANDO 22-B Part 1: uncertainty of the compound dependence_ratio (author-run,
CLAUDE.md Rule 12 -- methodological decision, not delegated).

For each of the 45 country x scenario x model cells:
- absolute observed/expected/baseline compound-month counts
- a moving-block-bootstrap 95% CI for dependence_ratio (block=12 months, 10,000
  resamples) -- not a naive binomial CI, because SPEI-12 is a 12-month
  accumulation and consecutive months are strongly autocorrelated
- the naive binomial (Wilson) CI for comparison, to show why it understates
  uncertainty
- the effective sample size implied by the lag-1..24 autocorrelation of the
  binary compound series
- a reportable flag: block-bootstrap CI excludes 1.0
"""

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(20260930)
BLOCK = 12
N_BOOT = 10_000
OUT = Path("../data/outputs")


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def moving_block_bootstrap_ratio(
    compound: np.ndarray, s_above: np.ndarray, h_above: np.ndarray, block: int, n_boot: int
) -> np.ndarray:
    n = len(compound)
    n_blocks = int(np.ceil(n / block))
    starts_max = n - block  # last valid block start (0-indexed)
    ratios = np.empty(n_boot)
    for b in range(n_boot):
        starts = RNG.integers(0, starts_max + 1, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:n]
        c_r = compound[idx].mean()
        s_r = s_above[idx].mean()
        h_r = h_above[idx].mean()
        denom = s_r * h_r
        ratios[b] = c_r / denom if denom > 0 else np.nan
    return ratios


def effective_n(binary_series: np.ndarray, max_lag: int = 24) -> float:
    n = len(binary_series)
    x = binary_series.astype(float) - binary_series.mean()
    var = (x**2).sum()
    if var == 0:
        return float(n)
    acf = []
    for k in range(1, max_lag + 1):
        num = (x[: n - k] * x[k:]).sum()
        acf.append(num / var)
    denom = 1 + 2 * sum(acf)
    return float(n / denom) if denom > 0 else float(n)


def main() -> None:
    m = pd.read_parquet(OUT / "compound_months.parquet")
    rows = []
    for (country, model, scenario), fut in m[m["period"] == "future"].groupby(
        ["country", "model", "scenario"]
    ):
        fut = fut.sort_values("month")
        base = m[
            (m["period"] == "baseline") & (m["country"] == country) & (m["model"] == model)
        ].sort_values("month")

        compound = fut["compound"].to_numpy(dtype=bool)
        s_above = (fut["s_hydro"] > fut["s_hydro_p90"]).to_numpy()
        h_above = (fut["h_thermal"] > fut["h_thermal_p90"]).to_numpy()

        n_future = len(fut)
        n_baseline = len(base)
        k_future_obs = int(compound.sum())
        k_baseline_obs = int(base["compound"].sum())
        f_s = s_above.mean()
        f_h = h_above.mean()
        k_future_expected = n_future * f_s * f_h
        dependence_ratio = (k_future_obs / n_future) / (f_s * f_h) if f_s * f_h > 0 else np.nan

        boot = moving_block_bootstrap_ratio(
            compound.astype(float), s_above.astype(float), h_above.astype(float), BLOCK, N_BOOT
        )
        boot_valid = boot[~np.isnan(boot)]
        if len(boot_valid) > 0:
            ci_block_lo, ci_block_hi = np.percentile(boot_valid, [2.5, 97.5])
        else:
            ci_block_lo, ci_block_hi = (np.nan, np.nan)

        wilson_lo, wilson_hi = wilson_ci(k_future_obs, n_future)
        denom_fixed = f_s * f_h
        ci_naive_lo = wilson_lo / denom_fixed if denom_fixed > 0 else np.nan
        ci_naive_hi = wilson_hi / denom_fixed if denom_fixed > 0 else np.nan

        n_eff = effective_n(compound, max_lag=24)

        has_ci = not np.isnan(ci_block_lo) and not np.isnan(ci_block_hi)
        reportable = bool(has_ci and (ci_block_lo > 1.0 or ci_block_hi < 1.0))

        rows.append(
            {
                "country": country,
                "scenario": scenario,
                "model": model,
                "n_future_months": n_future,
                "n_baseline_months": n_baseline,
                "k_future_observed": k_future_obs,
                "k_future_expected_indep": round(k_future_expected, 2),
                "k_baseline_observed": k_baseline_obs,
                "dependence_ratio": dependence_ratio,
                "ci_block_lo": ci_block_lo,
                "ci_block_hi": ci_block_hi,
                "ci_naive_binomial_lo": ci_naive_lo,
                "ci_naive_binomial_hi": ci_naive_hi,
                "n_eff_acf": round(n_eff, 1),
                "reportable_block_excludes_1": reportable,
            }
        )

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "diagnostics" / "c22b_dependence_uncertainty.csv", index=False)

    print(out.to_string(index=False, float_format=lambda x: f"{x:0.3f}"))

    n_reportable_45 = out["reportable_block_excludes_1"].sum()
    print(f"\nReportable (block CI excludes 1.0) among all 45 cells: {n_reportable_45} / 45")

    # Discriminating = both marginals < 50% future months above P90 (from prior diagnosis).
    discr = pd.read_csv(OUT / "c22_compound_diagnosis_percentile.csv")
    merged = out.merge(discr[["country", "scenario", "model", "discriminates"]], how="left")
    n_disc = merged["discriminates"].sum()
    n_reportable_disc = merged.loc[merged["discriminates"], "reportable_block_excludes_1"].sum()
    print(
        f"Reportable among the {int(n_disc)} discriminating cells: "
        f"{int(n_reportable_disc)} / {int(n_disc)}"
    )

    # Count vs CI-width relationship, for the author's minimum-count floor decision (O12).
    out["ci_block_width"] = out["ci_block_hi"] - out["ci_block_lo"]
    rel = out[
        [
            "country",
            "scenario",
            "model",
            "k_future_observed",
            "ci_block_width",
            "reportable_block_excludes_1",
        ]
    ]
    rel = rel.sort_values("k_future_observed")
    rel.to_csv(OUT / "diagnostics" / "c22b_count_vs_ci_width.csv", index=False)
    print("\nCount (k_future_observed) vs block-bootstrap CI width, sorted ascending:")
    print(rel.to_string(index=False, float_format=lambda x: f"{x:0.3f}"))


if __name__ == "__main__":
    OUT_DIAG = OUT / "diagnostics"
    OUT_DIAG.mkdir(parents=True, exist_ok=True)
    main()
