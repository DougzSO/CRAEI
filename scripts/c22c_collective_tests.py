"""COMANDO 22-C Part 1: collective (not cell-by-cell) dependence tests.

Cell-by-cell CI-excludes-1 readout understates the evidence: what actually
decides whether real dependence exists is the detection rate against chance
and the consistency of direction, not whether any single cell's CI happens
to clear 1.0.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RNG = np.random.default_rng(20260930)
DIAG = Path("../data/outputs/diagnostics")


def block_bootstrap_median_ci(
    values: np.ndarray, n_boot: int = 10_000
) -> tuple[float, float, float]:
    n = len(values)
    boots = RNG.choice(values, size=(n_boot, n), replace=True)
    medians = np.median(boots, axis=1)
    lo, hi = np.percentile(medians, [2.5, 97.5])
    return float(np.median(values)), float(lo), float(hi)


def main() -> None:
    nat = pd.read_csv(DIAG / "c22b_dependence_uncertainty.csv")
    disc = pd.read_csv(DIAG / "c22_compound_diagnosis_percentile.csv")
    nat = nat.merge(disc[["country", "scenario", "model", "discriminates"]], how="left")
    reg = pd.read_csv(DIAG / "c22b_regional_dependence_uncertainty.csv")

    print("=" * 100)
    print("ACTION 1: detection rate vs. expected under the null (alpha=5%)")
    print("=" * 100)
    nat_disc = nat[nat["discriminates"]]
    n_nat = len(nat_disc)
    obs_nat = int(nat_disc["reportable_block_excludes_1"].sum())
    exp_nat = 0.05 * n_nat
    print(
        f"National (32 discriminating cells): observed={obs_nat}, expected={exp_nat:.2f}, "
        f"ratio={obs_nat / exp_nat:.2f}x"
    )

    n_reg = len(reg)
    obs_reg = int(reg["reportable_block_excludes_1"].sum())
    exp_reg = 0.05 * n_reg
    print(
        f"Regional (615 cells): observed={obs_reg}, expected={exp_reg:.2f}, "
        f"ratio={obs_reg / exp_reg:.2f}x"
    )

    print("\n" + "=" * 100)
    print("ACTION 2: sign test on direction (ratio > 1.0)")
    print("=" * 100)
    nat_nondeg = nat[~(nat["k_future_observed"] == 0)]
    n_nat_nd = len(nat_nondeg)
    n_above_nat = int((nat_nondeg["dependence_ratio"] > 1.0).sum())
    p_nat = stats.binomtest(n_above_nat, n_nat_nd, 0.5).pvalue
    print(
        f"National non-degenerate cells: {n_nat_nd} (45 total, "
        f"{45 - n_nat_nd} degenerate k=0 excluded)"
    )
    print(f"  {n_above_nat}/{n_nat_nd} above 1.0, binomial p={p_nat:.6f}")

    reg_nondeg = reg[reg["k_future_observed"] > 0]
    n_reg_nd = len(reg_nondeg)
    n_above_reg = int((reg_nondeg["dependence_ratio"] > 1.0).sum())
    p_reg = stats.binomtest(n_above_reg, n_reg_nd, 0.5).pvalue
    print(
        f"\nRegional non-degenerate cells: {n_reg_nd} (615 total, "
        f"{615 - n_reg_nd} degenerate k=0 excluded)"
    )
    print(f"  {n_above_reg}/{n_reg_nd} above 1.0, binomial p={p_reg:.3e}")

    print("\n" + "=" * 100)
    print("ACTION 3: sign test collapsed to country x model (15 units, median of 3 scenarios)")
    print("=" * 100)
    nat_nondeg_grp = nat_nondeg.groupby(["country", "model"])["dependence_ratio"].median()
    n_units = len(nat_nondeg_grp)
    n_above_units = int((nat_nondeg_grp > 1.0).sum())
    p_units = stats.binomtest(n_above_units, n_units, 0.5).pvalue
    print(
        f"{n_above_units}/{n_units} country x model units have median ratio > 1.0, "
        f"p={p_units:.4f}"
    )
    print(nat_nondeg_grp.reset_index().to_string(index=False))

    print("\n" + "=" * 100)
    print("ACTION 4: collective effect size -- median ratio + block bootstrap CI, by country")
    print("=" * 100)
    for country in ["BRA", "IND", "PRT"]:
        vals = nat_nondeg.loc[
            nat_nondeg["country"] == country, "dependence_ratio"
        ].dropna().to_numpy()
        if len(vals) == 0:
            continue
        med, lo, hi = block_bootstrap_median_ci(vals)
        print(f"National {country}: n={len(vals)}, median={med:.3f}, 95% CI=[{lo:.3f}, {hi:.3f}]")

    for country in ["BRA", "IND", "PRT"]:
        vals = reg_nondeg.loc[
            reg_nondeg["country_national"] == country, "dependence_ratio"
        ].dropna().to_numpy()
        if len(vals) == 0:
            continue
        med, lo, hi = block_bootstrap_median_ci(vals)
        print(f"Regional {country}: n={len(vals)}, median={med:.3f}, 95% CI=[{lo:.3f}, {hi:.3f}]")


if __name__ == "__main__":
    main()
