> **Document role:** Specification of analysis E1 (hydrothermal hedge failure), Brazil.
> **Contains:** question, evidence from the removed compound metric, pre-specified decision criterion, exact definitions, formulas, inference, observed check, scripts and schemas, limitations.
> **Does NOT contain:** results (-> docs/RESULTS_REGISTRY.md once E1 runs).
> **Status:** APPROVED by the author (Phase 3, Stage 2) with the adjustments listed in D140; implementation follows.

---

# E1. Does the water-dependent thermal insurance fail when hydropower needs it?

**Question.** In months of hydropower drought, is the water-dependent thermal fleet under stress more
often than expected under independence, and does that increase from the baseline to the future?

**Scope.** Brazil, national series only (submarkets of the SIN are out of this phase). Five GCMs
(ISIMIP3b), baseline 1985-2014 and future 2041-2070 under SSP1-2.6 / SSP3-7.0 / SSP5-8.5.
Hydropower: operating fleet, Itaipu version b (7,000 MW, D102). Thermal: operating
water-dependent fleet, 618 plants (plant-level class, as in W4c and Fig 4, D138), capacity-weighted;
secondary: operating + planned water-dependent fleet ("the future insurance").

## 0. Evidence from the compound metric removed in D72 (read-only summary)

E1 reopens a metric that the article dropped. Why it was dropped, in the decision's own words:
D72 (C24, 2026-09-30) "Compound hydro-drought/thermal-heat metric removed from the article." with D71
(scope v2: "one article, Brazil only, two axes ... Out: India, Portugal, flooding, solar, wind,
composite score"); `docs/archive/SCOPE_pre_C66.md:15`: "Compound drought-heat metric | out (D72) | not
part of the two axes". It was removed for scope, not for lack of signal or for a methodological failure.

What the removed version found (Brazil national, 15 cells = 5 GCMs x 3 scenarios,
`dependence_ratio` = f_future / (f_S_above_future x f_H_above_future), baseline P90 per GCM):

| Item | Value | Decision |
|---|---|---|
| Baseline compound frequency, Brazil | up to 3.601% (gfdl-esm4), above the ~1% independence expectation in most cells | D58 |
| Mean-shift problem | in 13/45 country-scenario-model rows a marginal exceeded its baseline P90 in more than half of the future months (BRA x UKESM1-0-LL: S_hydro 64-81%, H_thermal 70-92%; ratio_obs_to_indep 1.03-1.13); LR_C dropped | D63 |
| Absolute thresholds | rejected (the absolute level would itself become the result) | D64 |
| Brazil D (dependence_ratio), 15 cells | range 0.965-1.614; 14/15 above 1; block-bootstrap CI (block 12, 10,000 resamples) excludes 1 in 7/15 | D65, archived diagnostics |
| BRA GCM x scenario detail | gfdl-esm4 1.176 / 1.144 / 1.204; ipsl-cm6a-lr 1.233 / 1.200 / 1.125; mpi-esm1-2-hr 1.614 / 1.152 / 1.160; mri-esm2-0 1.078 / 0.965 / 1.050; ukesm1-0-ll 1.125 / 1.043 / 1.032 (SSP1-2.6 / 3-7.0 / 5-8.5) | D65 |
| Collective level | national detection 7 vs 1.60 expected (4.38x); 37/44 cells above 1 (p=5.3e-6); country x model collapse 14/15 above 1, p=0.0010 (the official sign test; the 574-cell regional p is not reportable, non-independent cells); BRA national median 1.144 [1.050, 1.200] | D67 |
| Effective sample size | n_eff 22 to ~2,315 months, typically 100-300, against a nominal 360 | D65 |
| Regional (20 usable Brazilian regions) | median 1.212 [1.179, 1.256]; 183/615 cells reportable | D66, D67 |

Reading for E1: a weak but mostly positive signal existed (D around 1.03-1.6); the old ratio mixed
marginal drift with dependence. E1 corrects that (variants A/B, decomposition below); it does not
correct national dilution (D66), which stays a limitation.

Starting point for Phase 4 (D70, ONS validation, scripts/24_w5e5_spei_validation.py and 25_validation_stats.py):
national, annual, December SPEI-12 capacity-weighted over the 222 hydro plants against the calendar-year
mean of the daily national ENA (MWmed, sum of the 4 subsystems), n_years = 20 (2000-2019 = W5E5 end x
ENA start), Spearman rho = 0.361, 95% CI [0.027, 0.811] (3-year block bootstrap, 10,000 resamples); odds
ratio (December SPEI-12 <= -1 given bottom-tercile ENA) 0.917 [0.200, 19.286]. No lag was tested (zero
lag, December value against the same calendar year); no subsystem resolution (no plant-to-subsystem
mapping, D62/L20); D73 keeps it supplementary. Portugal (REN IPH, monthly, 57 months): rho = 0.246
[-0.065, 0.625], n_eff 4.75.

## 0b. Pre-specified decision criterion (written before any E1 result)

Fixed here, before E1 is run; the result is reported against it and the criterion is not changed afterwards.

- **Primary signal criterion.** In the control channel pair (H^spi, T^spi), P(H and T) under variant A
  (baseline P90 threshold applied to the future) increases from the baseline to the future in at least
  4 of the 5 GCMs, both under SSP3-7.0 and under SSP5-8.5. Both scenarios must meet it; "increases" means
  P_f(HT) > P_b(HT), per GCM, on the point estimate. The criterion is met or not met; a partial result is
  reported as not met, with the counts.
- **Reinforcing evidence (not a condition).** (i) dD (variant B) > 0 with k >= 4/5; (ii) the observed W5E5 D
  (1985-2014) is > 1 with a block-bootstrap CI that excludes 1.
- **Reference for comparison in the Stage 4 report:** the D values of the removed version listed in section 0
  (D65-D67: BRA 15-cell range 0.965-1.614, median 1.144 [1.050, 1.200], 14/15 above 1, 7/15 with CI
  excluding 1; per GCM and scenario as tabulated). They are not a target; E1's D is computed under
  different definitions (A/B variants, capacity-share series, SPI control), so the comparison is explicit
  but not like for like.
- The report states for each criterion item: met / not met, the per-GCM counts, and the CI.

## 1. Definitions (exact)

Index month t = 1..360 within a period (baseline 1985-2014 from the historical run; future 2041-2070 per
SSP). One GCM g at a time. "Drought threshold" = -1.5 (`drought_spei_threshold`, params.yaml).

**Hydropower share.** Plants: Brazilian operating hydro with catchment-scale SPEI (spei.parquet, scale
`catchment`, id = plant). Capacity c_i (Itaipu 7,000 MW).
- H_t^spei = sum_i c_i 1[SPEI12_{i,t} <= -1.5] / sum_i c_i
- H_t^spi  = sum_i c_i 1[SPI12_{i,t}  <= -1.5] / sum_i c_i

**Thermal channels.** Plants j: Brazilian operating `thermal_water_dependent` (plant-level class), at the
plant's cell, capacity c_j. Plant-month flags:
- heat: N35_{j,t} > q90_j, with N35 the monthly count of days with TX >= 35 C of the plant cell
  (`n35`, indices_daily) and q90_j the 90th percentile of the 360 baseline months of N35 of that cell and
  GCM (local, all calendar months pooled; precedent D58 uses P90 of the national series). If q90_j = 0,
  any N35 > 0 counts (rule documented).
  Sensitivity `heat_cal`: q90 per calendar month (30 values per cell and GCM; standardization compatible
  with SPEI, removes seasonal confounding).
- spei: SPEI12_{cell,t} <= -1.5 (spei.parquet, scale `cell`).
- spi: SPI12_{cell,t} <= -1.5.
- any_spei = heat OR spei; any_spi = heat OR spi (per plant-month, before aggregation).
T_t^c = sum_j c_j flag^c_{j,t} / sum_j c_j, c in {heat, heat_cal, spei, spi, any_spei, any_spi}.

**Pairs.** Main control: (H^spi, T^spi). Upper bound: (H^spei, T^spei). Also (H^spei, T^heat), (H^spi, T^heat),
(H^spei, T^any_spei), (H^spi, T^any_spi), and the heat_cal versions.

## 2. Events, metrics and formulas

For a series x_t (H or T) and a threshold q: event e_t = 1[x_t > q]. If q is zero (zero-inflated
series), the rule is the same with strict ">" (documented, counted).

**Variant A (headline).** q = P90 of the baseline x_t of the same GCM, applied unchanged to baseline and
future. **Variant B (coupling).** q = P90 of the series of the period itself (marginals fixed near 10%).

For period p with n = 360 months: P(H) = sum h_t / n, P(T) = sum u_t / n, P(H and T) = sum h_t u_t / n,
P(T|H) = P(H and T) / P(H), D = P(H and T) / (P(H) P(T)). D and P(T|H) are undefined (NaN, counted and
reported, never set to 0) if P(H) = 0 or P(T) = 0.

**Headline (variant A):** P(H and T) baseline vs future, per GCM and scenario, plus P(T|H). Decomposition,
exact (the two parts sum to the change):

  dP(HT) = P_f(HT) - P_b(HT)
         = [P_f(H) P_f(T) - P_b(H) P_b(T)]                          (marginal part)
         + [(P_f(HT) - P_f(H) P_f(T)) - (P_b(HT) - P_b(H) P_b(T))]  (dependence part)

**Coupling (variant B):** D_b, D_f and dD = D_f - D_b, per GCM and scenario.
**Agreement:** k/5 = number of the 5 GCMs whose dD (and dP(HT)) has the same sign as the median over GCMs
(O31 definition). No pooling of cells or GCMs into one p-value (D67 amended).

## 3. Inference

- **Moving-block bootstrap** of the paired monthly series (h_t, u_t jointly), block = 12 months (main),
  24 and 36 (sensitivity), n_sim = 2,000, seed documented: `np.random.default_rng([23, 3, k])`, k = running
  index over the sorted (pair, GCM, scenario, block) keys (seed 23 as in the null scripts). Precedent
  `scripts/archive/c22b_dependence_uncertainty.py:37-52` (block 12; 10,000 resamples there). 95% CI by
  percentiles for P(H and T), P(T|H), D and dD (dD: resample the baseline and future series
  independently).
- **Test of D > 1:** circular shift of u against h by a random lag in [12, n - 12] (n_sim = 2,000, same seed
  scheme), which keeps both autocorrelations and breaks the pairing; p = (1 + #{D_null >= D_obs}) /
  (1 + n_sim). Reported per GCM and period, not pooled.

## 4. Observed check (W5E5, 1985-2014)

The raw W5E5 v2.0 files (tasmax, tasmin, pr, Brazil box lon -74.5 to -34.0, lat -34.5 to 6.0, 1981-2019) are in
raw_dir (`climate/w5e5v2.0`), so no download. `scripts/e1_w5e5_inputs.py` derives, for the thermal plant cells,
the monthly SPEI-12 and SPI-12 (same PET Hargreaves, water balance and baseline fit as
`24_w5e5_spei_validation.py` and `08_spei.py`) and N35 from W5E5 tasmax, and the SPI-12 of the hydro catchments
from the existing `water_balance_catchment_w5e5.parquet`. The same E1 metrics are then computed on the single
observed series over 1985-2014 (the thresholds are the series' own P90) and shown next to the five GCM
baselines. No future for observations.

## 5. Scripts, inputs, outputs

- `src/craei/exposure/hedge.py`: pure functions (weighted fractions, thresholds, events, metrics,
  decomposition, block bootstrap, circular-shift test); `tests/test_exposure_hedge.py` with synthetic
  independent and perfectly dependent series.
- `scripts/e1_w5e5_inputs.py`: observed inputs (above); writes `data/processed/w5e5_thermal_cells_monthly.parquet`
  and `data/processed/w5e5_hydro_spi12.parquet`.
- `scripts/e1_hedge.py`: driver. Reads plants, plant_hazards (bucket), plant_cell, spei (selective columns and
  filters), indices_daily (`n35`, thermal cells only), the two W5E5 files; writes to outputs_tables_dir:
  `e1_hedge_series.csv` (monthly H_t and T_t^c per GCM, scenario, period), `e1_hedge_metrics.csv`
  (pair, variant, GCM, scenario, period, block, P_H, P_T, P_HT, P_T_given_H, D, CI columns, p_circ),
  `e1_hedge_delta.csv` (dP_HT A with marginal and dependence parts, D_b, D_f, dD B, CIs),
  `e1_hedge_summary.csv` (median over GCMs and k/5 per pair x scenario), `e1_hedge_observed.csv`.
- Memory: selective reads only (about 4 million SPEI rows, a few hundred cells of N35); no grouped
  transform/apply/rolling over the full tables (CLAUDE.md rule 11).

## 6. Limitations (to be stated with the results)

1. **Circularity.** SPEI-Hargreaves depends on temperature, so (H^spei, T^spei) and every pair with a
   temperature-based channel share forcing; (H^spei, T^spei) is an upper bound. The main control is
   (H^spi, T^spi); T^heat and T^any remain temperature-based even there.
2. **Physical coupling is the phenomenon.** Precipitation-temperature coupling (dry soils, hotter days) is
   real and is what E1 measures; it cannot be separated from a statistical artifact with these data.
3. **Bias adjustment.** ISIMIP3BASD adjusts variables mostly univariately, so the GCM pr-tas dependence may be
   distorted.
4. **National aggregation** sums climatically decoupled regions and dilutes dependence (D66); submarkets are
   out of this phase.
5. **Hydropower drought is climatic, not inflow or dispatch.** The SPEI-ENA association is weak (D70
   rho = 0.361); E1 measures climatic coincidence, not operational hedge failure.
6. **Seasonality of the heat threshold.** A P90 pooled over all months selects the hot season; stress is
   then seasonal and can align with hydropower drought through the seasonal cycle alone. The calendar-month
   P90 (`heat_cal`) is reported next to it.
7. **Statistics.** SPEI-12 and the monthly series are strongly autocorrelated (n_eff far below 360, D65);
   the prior signal was weak (D 1.03-1.6); no pooled p-value.

## 7. Implementation notes (C96, data constraints found while running; the criterion in section 0b is unchanged)

- **Future window.** SPEI-12 of the future runs has no accumulation history: the first 11 months of 2041 are
  undefined. Every future series (all channels) uses the 29 full years 2042-2070 (348 months), the same
  window for all channels and pairs. The baseline keeps 360 months (1985-2014). Probabilities are
  frequencies, so n differs between the periods (348 vs 360).
- **Observed window.** The W5E5-derived SPEI-12 starts in 1985, so its first 11 months are undefined; the
  observed series use 1986-2014 (348 months). The observed thresholds are the series' own P90.
- **Thermal fleets** use the plant_units selection of W4c (618 operating plants, 39.1015 GW; operating +
  planned: 694 plants, 80.254 GW, 341 cells); hydro 194 plants, 102.667 GW (Itaipu b).
- **Seeds.** `default_rng([23, 3, k])`, k running over pair -> fleet -> model -> period -> variant -> block
  (see `Rng` in scripts/e1_hedge.py); the observed stream starts at k = 10,000.
- Inputs derived from raw W5E5 (new processed files): `w5e5_thermal_cells_monthly.parquet` (341 cells; fits
  without failures; TX<TN days 0; PET-truncated days 0), `w5e5_hydro_spi12.parquet` (194 catchments).
