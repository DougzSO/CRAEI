"""COMANDO 22-D: SPEI-12 (W5E5) x ONS ENA (Brazil, national) and x REN IPH
(Portugal, monthly) validation statistics -- Spec Sec1.7/Fig.5, Step 11.

Brazil: hydro-capacity-weighted SPEI-12 (December value per year, W5E5,
`spei_w5e5.parquet`) vs national ENA (sum of the four subsystems' MWmed,
annual mean of daily values). Spearman with 3-year block bootstrap
(10,000 resamples); odds ratio of bottom-tercile ENA year given December
SPEI-12 <= -1. n_years = the 2000-2019 W5E5/ONS-ENA intersection (20).

Portugal: hydro-capacity-weighted SPEI-12 (monthly, W5E5) vs REN IPH
(monthly), 57-month overlap (D60). Spearman with 12-month block bootstrap
(SPEI-12 is a 12-month accumulation; consecutive months are strongly
autocorrelated, so a 3-month or no-block bootstrap would understate the CI
-- Methods Spec Sec1.7). n_eff = n_obs / block_size (~4.75), reported
alongside the raw n_obs=57 so the two are never conflated.

Writes `<outputs_tables_dir>/validation.csv`.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_paths

RNG_SEED = 20260930  # fixed for reproducibility, not a methodological parameter
N_BOOT = 10_000
BRA_BLOCK_YEARS = 3
PRT_BLOCK_MONTHS = 12
DEC_SPEI_THRESHOLD = -1.0  # Spec Sec1.7: "December SPEI-12 <= -1" (distinct from H2's -1.5)


def moving_block_bootstrap_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """One resample of length `n` (or the largest multiple of `block` <= n)
    built from contiguous blocks of `block` consecutive original indices,
    drawn with replacement (standard moving-block bootstrap)."""
    n_blocks = max(n // block, 1)
    if n > block:
        starts = rng.integers(0, n - block + 1, size=n_blocks)
    else:
        starts = np.zeros(n_blocks, dtype=int)
    idx = np.concatenate([np.arange(s, s + block) for s in starts])
    return idx[:n]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    from scipy.stats import spearmanr

    rho, _ = spearmanr(x, y)
    return rho


def block_bootstrap_spearman_ci(
    x: np.ndarray, y: np.ndarray, block: int, n_boot: int, rng: np.random.Generator
):
    n = len(x)
    boot_rhos = np.empty(n_boot)
    for i in range(n_boot):
        idx = moving_block_bootstrap_indices(n, block, rng)
        boot_rhos[i] = spearman(x[idx], y[idx])
    boot_rhos = boot_rhos[np.isfinite(boot_rhos)]
    return np.nanpercentile(boot_rhos, 2.5), np.nanpercentile(boot_rhos, 97.5)


def odds_ratio(spei_dec_leq: np.ndarray, ena_bottom_tercile: np.ndarray) -> float:
    a = int(np.sum(spei_dec_leq & ena_bottom_tercile))
    b = int(np.sum(spei_dec_leq & ~ena_bottom_tercile))
    c = int(np.sum(~spei_dec_leq & ena_bottom_tercile))
    d = int(np.sum(~spei_dec_leq & ~ena_bottom_tercile))
    if min(a, b, c, d) == 0:  # Haldane-Anscombe correction for zero cells
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    return (a * d) / (b * c)


def block_bootstrap_or_ci(
    spei_dec_leq: np.ndarray,
    ena_bottom_tercile: np.ndarray,
    block: int,
    n_boot: int,
    rng: np.random.Generator,
):
    n = len(spei_dec_leq)
    boot_or = np.empty(n_boot)
    for i in range(n_boot):
        idx = moving_block_bootstrap_indices(n, block, rng)
        boot_or[i] = odds_ratio(spei_dec_leq[idx], ena_bottom_tercile[idx])
    boot_or = boot_or[np.isfinite(boot_or)]
    return np.nanpercentile(boot_or, 2.5), np.nanpercentile(boot_or, 97.5)


def load_ena_national_annual(raw_dir: Path) -> pd.DataFrame:
    ena_dir = raw_dir / "validation" / "ons_ena"
    frames = []
    for f in sorted(ena_dir.glob("ENA_Diario_por_Subsistema-*.csv")):
        df = pd.read_csv(f, sep=";", decimal=".", parse_dates=["ena_data"])
        frames.append(df[["id_subsistema", "ena_data", "ena_bruta_regiao_mwmed"]])
    all_ena = pd.concat(frames, ignore_index=True)
    national_daily = all_ena.groupby("ena_data", as_index=False)["ena_bruta_regiao_mwmed"].sum()
    national_daily["year"] = national_daily["ena_data"].dt.year
    # Annual value = calendar-year mean of the daily national MWmed total
    # (MWmed is already an absolute average-power unit; summing the 4
    # subsystems is valid -- see COMANDO 22-D report Action 2. Annual mean,
    # not annual sum, keeps the MWmed unit meaningful at annual resolution).
    annual = national_daily.groupby("year", as_index=False)["ena_bruta_regiao_mwmed"].mean()
    annual = annual.rename(columns={"ena_bruta_regiao_mwmed": "ena_mwmed_annual"})
    return annual


def capacity_weighted_spei(
    spei_w5e5: pd.DataFrame, plants: pd.DataFrame, country: str
) -> pd.DataFrame:
    hydro = plants[(plants["country"] == country) & (plants["tech_class"] == "hydro")][
        ["plant_uid", "capacity_mw"]
    ].rename(columns={"plant_uid": "id"})
    d = spei_w5e5[spei_w5e5["country"] == country].merge(hydro, on="id")
    d = d.dropna(subset=["SPEI_12"])
    out = (
        d.assign(w=d["SPEI_12"] * d["capacity_mw"])
        .groupby("month", as_index=False)
        .agg(w_sum=("w", "sum"), cap_sum=("capacity_mw", "sum"))
    )
    out["spei12_cw"] = out["w_sum"] / out["cap_sum"]
    return out[["month", "spei12_cw"]]


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])
    raw_dir = Path(paths["raw_dir"])
    outputs_tables_dir = Path(paths["outputs_tables_dir"])
    rng = np.random.default_rng(RNG_SEED)

    spei_w5e5 = pd.read_parquet(processed_dir / "spei_w5e5.parquet")
    plant_cols = ["plant_uid", "country", "tech_class", "capacity_mw"]
    plants = pd.read_parquet(processed_dir / "plants.parquet", columns=plant_cols)

    rows = []

    # ---------------- Brazil: national, annual (December SPEI-12) ----------------
    bra_spei_monthly = capacity_weighted_spei(spei_w5e5, plants, "BRA")
    bra_spei_dec = bra_spei_monthly[bra_spei_monthly["month"].dt.month == 12].copy()
    bra_spei_dec["year"] = bra_spei_dec["month"].dt.year

    ena_annual = load_ena_national_annual(raw_dir)

    bra = bra_spei_dec.merge(ena_annual, on="year").sort_values("year").reset_index(drop=True)
    # W5E5(<=2019) x ONS-ENA(>=2000) intersection
    bra = bra[(bra["year"] >= 2000) & (bra["year"] <= 2019)]
    n_years = len(bra)
    print(f"Brazil: n_years (2000-2019 intersection) = {n_years}")

    x = bra["spei12_cw"].to_numpy()
    y = bra["ena_mwmed_annual"].to_numpy()
    rho = spearman(x, y)
    rho_lo, rho_hi = block_bootstrap_spearman_ci(x, y, BRA_BLOCK_YEARS, N_BOOT, rng)

    tercile_cut = np.quantile(y, 1 / 3)
    ena_bottom = y <= tercile_cut
    spei_leq = x <= DEC_SPEI_THRESHOLD
    or_point = odds_ratio(spei_leq, ena_bottom)
    or_lo, or_hi = block_bootstrap_or_ci(spei_leq, ena_bottom, BRA_BLOCK_YEARS, N_BOOT, rng)

    print(
        f"Brazil: rho={rho:.3f} [{rho_lo:.3f}, {rho_hi:.3f}], "
        f"OR={or_point:.3f} [{or_lo:.3f}, {or_hi:.3f}]"
    )

    rows.append(
        dict(
            region="BRA_national",
            resolution="annual",
            n_obs=n_years,
            n_eff=n_years,
            rho=rho,
            rho_ci_low=rho_lo,
            rho_ci_high=rho_hi,
            odds_ratio=or_point,
            or_ci_low=or_lo,
            or_ci_high=or_hi,
            bootstrap_block=f"{BRA_BLOCK_YEARS}-year",
        )
    )

    # ---------------- Portugal: monthly ----------------
    prt_spei_monthly = capacity_weighted_spei(spei_w5e5, plants, "PRT")
    ren_iph = pd.read_parquet(processed_dir / "ren_iph.parquet")[["date", "iph"]]
    ren_iph = ren_iph.rename(columns={"date": "month"})

    prt = prt_spei_monthly.merge(ren_iph, on="month").sort_values("month").reset_index(drop=True)
    n_obs = len(prt)
    print(f"Portugal: n_obs (monthly overlap) = {n_obs}")

    xp = prt["spei12_cw"].to_numpy()
    yp = prt["iph"].to_numpy()
    rho_p = spearman(xp, yp)
    rho_p_lo, rho_p_hi = block_bootstrap_spearman_ci(xp, yp, PRT_BLOCK_MONTHS, N_BOOT, rng)
    n_eff_p = n_obs / PRT_BLOCK_MONTHS

    print(f"Portugal: rho={rho_p:.3f} [{rho_p_lo:.3f}, {rho_p_hi:.3f}], n_eff~{n_eff_p:.2f}")

    rows.append(
        dict(
            region="PRT",
            resolution="monthly",
            n_obs=n_obs,
            n_eff=round(n_eff_p, 2),
            rho=rho_p,
            rho_ci_low=rho_p_lo,
            rho_ci_high=rho_p_hi,
            odds_ratio=np.nan,
            or_ci_low=np.nan,
            or_ci_high=np.nan,
            bootstrap_block=f"{PRT_BLOCK_MONTHS}-month",
        )
    )

    out = pd.DataFrame(rows)
    out_path = outputs_tables_dir / "validation.csv"
    out.to_csv(out_path, index=False)
    print(f"\nwrote {out_path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
