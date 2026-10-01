# Design v2: Heat and drought exposure of the Brazilian power fleet

Scope v2 (D71): Brazil only; Axis 1 heat exposure of the thermal fleet by fuel (operating vs planned); Axis 2 hydro drought against an internal-variability null. Replaces the three-country design archived at docs/archive/METHODS_SPEC_v1_pre_rework.md. Blocks marked "verbatim" are copied unchanged from v1. Anything not yet defined is marked "to be defined" with its open item (O-id).

---

## 1. Methods

### 1.1 Study domain and scope (v2)

Brazil only (D71). The pipeline still produces India and Portugal results; they are not analysed here and the Brazil filter is applied at table level, not by deleting code. See Appendix A for components outside the article.

### 1.2 Infrastructure data

Plant locations, capacities, technologies and statuses come from the Global Energy Monitor (GEM) Global Integrated Power Tracker (snapshot 9 August 2026). Units are aggregated to plants using a stable identifier (hash of name, latitude and longitude). Two fleets are analysed: the operating fleet (status "operating") and the planned fleet, split into advanced (construction, pre-construction) and early stage (announced). Shelved, cancelled, mothballed and retired units are excluded.

Technology classes:

- **Hydro**: conventional reservoir, run-of-river and pumped storage, as recorded by GEM. Where the type field is missing, the plant is treated as reservoir.
- **Thermal, water-dependent**: coal, oil and gas steam cycles, combined-cycle gas, nuclear, and bioenergy steam plants.
- **Thermal, air-only**: open-cycle gas turbines and reciprocating engines, where identifiable. These receive heat hazards only.
- **Solar PV**: Supplementary Information only.

GEM contains no cooling-technology field. Freshwater hazards for water-dependent thermal plants are therefore computed under two bounds. The upper bound assumes all plants withdraw freshwater. The lower bound treats plants within 5 km of the coastline (Natural Earth 1:10m) as seawater-cooled and removes them from freshwater hazards while keeping them for heat. The 5 km distance is an author assumption (evidence tier 3) and is tested at 2 and 10 km.

### 1.3 Climate data and baseline

Daily maximum temperature (tasmax), minimum temperature (tasmin) and precipitation (pr) are taken from the ISIMIP3b bias-adjusted atmospheric climate input data (0.5°), for the five ISIMIP3b primary GCMs: GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0 and UKESM1-0-LL. The baseline is the historical simulation of each model for 1985-2014; projections cover 2041-2070 under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Data were bias-adjusted by the ISIMIP team against W5E5 v2.0 with ISIMIP3BASD v2.5.0 (Lange, 2019; Frieler et al., 2021).

Justification: (i) every model has a historical baseline, which removes the self-referential calibration of the previous framework; (ii) bias adjustment to a common observational reference makes absolute thresholds (e.g. 35 °C) meaningful across models without in-house downscaling; (iii) all three variables are available for every model and scenario, which allows a temperature-range PET formulation; (iv) the five models were selected by ISIMIP to cover a range of climate sensitivity, unlike the previous pair, which sat at the low end of CMIP6 sensitivity.

All indices are computed in two stages: baseline statistics (thresholds, distribution parameters) are estimated on 1985-2014 of each model, then applied unchanged to 2041-2070 of the same model. No percentile or distribution is ever fitted on the series being classified.

Tasmax/tasmin consistency (TX >= TN) has been verified across the full ensemble: 707,545,940 cell-days tested (all 5 models x 4 scenarios x 3 countries, every plant-catchment cell), 0 inversions (TX < TN) and 0 exact or near-equal (tolerance 1e-6) coincidences found.

Plants are assigned to the nearest 0.5° land cell. For hydro plants, the upstream catchment is built from HydroBASINS level 6 by recursively following the `NEXT_DOWN` topology from the sub-basin containing the plant; climate variables are area-weighted over all grid cells intersecting the catchment before computing indices.

### 1.4 Hazard definitions

**H1. Extreme heat (thermal plants; solar in SI).** Annual count of days with daily maximum temperature at or above 35 °C and 40 °C:

TX35 = (1/30) Σ_y Σ_d 1[TX_{y,d} ≥ 35 °C], and analogously TX40.

The change metric is ΔTX35 = TX35_future − TX35_baseline (days yr⁻¹). A difference is used instead of a ratio because baselines are zero in many cells. TX35 and TX40 are indices published in the IPCC AR6 Interactive Atlas; they are used as indicators of cooling-relevant heat, not as operating limits. The headline exposure class is ΔTX35 ≥ 30 days yr⁻¹ (about one additional month of such days; tier 3, tested at 15 and 60).

**H2. Drought (hydro at catchment scale; water-dependent thermal at cell scale).** Standardized Precipitation Evapotranspiration Index at 12-month accumulation (SPEI-12), with potential evapotranspiration from Hargreaves-Samani:

PET_d = 0.0023 × 0.408 × Ra_d × (T̄_d + 17.8) × (TX_d − TN_d)^0.5,  T̄_d = (TX_d + TN_d)/2

where Ra is extraterrestrial radiation (MJ m⁻² d⁻¹; FAO-56, Eq. 21) and 0.408 converts to mm d⁻¹. The monthly water balance D_m = P_m − PET_m is accumulated over 12 months for SPEI-12 (3 months for SPEI-3). The three-parameter log-logistic distribution (probability-weighted moments, Vicente-Serrano et al. 2010) is fit per plant or cell and per GCM on that series' own 1985-2014 baseline, never mixed with other plants/cells/models, so standardization always measures a deviation from that series' own local climatology. SPEI-12 is fit once per series on all 360 baseline months together, without separating by calendar month: a 12-month accumulation already removes essentially all seasonal signal from the accumulated series (verified directly: mean standardized SPEI-12 by calendar month is within ±0.01 of zero in every month). SPEI-3 retains a calendar-month fit but widens each month's sample with its two immediate neighboring calendar months across all 30 years (a 3-month moving window in calendar-month space, not in the accumulation window itself), since a 3-month accumulation keeps more seasonal structure than SPEI-12 does. Where the closed-form estimator does not converge, a Pearson Type III maximum-likelihood fit is used instead (Bobee and Robitaille 1977, about 26% of series for SPEI-12); the two estimators' baseline severe-drought frequency differs by a median at or near zero for two of the three study countries and up to about 0.8 percentage points for the third at this sample size, so the choice between them does not materially affect results. Values are clipped to [−3, 3]. Severe drought frequency is

F_D = fraction of months with SPEI-12 ≤ −1.5,

which is close to 6.7% in the baseline by construction (standard normal probability below −1.5). The change metric is the ratio R_D = F_D,future / F_D,baseline. The headline exposure class is R_D ≥ 2 (severe drought at least twice as frequent; tier 3, tested at 1.5 and 3). For run-of-river plants SPEI-3 is also reported. Hargreaves was chosen over Thornthwaite because Thornthwaite is known to overstate drying under warming, and over Penman-Monteith for simplicity; SPI-12 (precipitation only) is reported as the lower bound that ignores atmospheric demand.

### 1.5 Exposure assessment

Hazards are never combined into a single score. For country c, technology t, hazard h, scenario s and model k, capacity exposure is

E_{c,t,h,s,k} = Σ_{i∈(c,t)} Cap_i × 1[Δ_{i,h,s,k} ≥ τ_h] / Σ_{i∈(c,t)} Cap_i,

reported both as a share and in GW. Model agreement is defined as at least four of five GCMs projecting a change of the same sign (ΔTX35 > 0; R_D > 1). Ensemble results are the median across models with the full model range.

### 1.6 Fleet and fuel classification (v2; D77, D78)

Capacity by fleet and fuel is computed from GEM unit-level rows (table plant_units.parquet, command C28), not from plants.parquet, because plants.parquet assigns one fleet per plant by the mode of unit status (D78). Hazards are joined on plant_uid (location is shared by all units of a plant).

Fuel classes (D77): Type first (coal, nuclear, bioenergy); oil/gas split by GEM Fuel classification into gas (Gas, LNG only), oil, multi_fuel; bioenergy subtypes agricultural_waste (bagasse proxy), paper_mill_waste, wood_biomass, other_bioenergy. Brazil operating reference totals (GW): gas 19.32, bioenergy 17.43, oil 4.60, coal 3.00, nuclear 1.99, multi_fuel 1.33; total 47.67.

### 1.7 Heat axis (v2)

H1 and the exposure formula of 1.5 apply, with a fuel dimension added: E over (fuel, fleet, scenario, model). Outputs: share and GW above the headline class (dTX35 >= 30 days/yr), ensemble median, model range, agreement (at least 4 of 5 GCMs).

- Threshold curves (GW fraction vs dTX35): TO BE DEFINED, see O17 (curve grid).
- Operating vs planned comparison: TO BE DEFINED, see O17 (metric and uncertainty).
- Harvest-season variant for bioenergy: TO BE DEFINED, see O16.

### 1.8 Drought axis (v2)

H2 and the fitting method of 1.4 apply unchanged (D54/D55).

- Internal-variability null (D76): block bootstrap, pool of 1,110 (id, model) series of 360 baseline months, N_SIM=2000, seed 23; preliminary reference values from c23d_report.md: 18.88% of series reach R_D>=2 at SPEI<=-1.5 (1,991 of 2,000 with R_D defined); white-noise lower reference 1.80%. Excess over null = observed capacity share minus the null rate, by bucket, scenario, GCM; descriptive, not a significance test (L26). Production script to be written (C30), acceptance = reproduce these numbers.
- SPI vs SPEI comparison: TO BE DEFINED, see O18.
- Uncertainty of the excess (GCM range, agreement, clustering): TO BE DEFINED, see O21.
- Leave-one-out of the 5 largest hydro plants: TO BE DEFINED, see O19.
- Thermal water-dependent bucket in Fig 5: TO BE DEFINED, see O20.

### 1.9 Validation (v2)

National ONS validation (D70, rho=0.361, CI 0.027-0.811, n=20) is supplementary (D73). Details in Appendix A (v1 section 1.7).

---

## 3. Technical pipeline (inherited; verbatim)

Execution machine, measured (COMANDO 15 follow-up, O06/O07 audit): AMD Ryzen 3 PRO 2200G, 4 cores / 4 logical processors, 6.4 GB RAM total. Project data (`data_root`, country-cropped climate files, `plants.parquet`, etc.) lives on the internal SSD (Samsung MZNLN128HAHQ, 128 GB); the raw global ISIMIP cache lives on an external USB HDD (Seagate Basic, 4 TB, D27'/D28). This is well below the 8+ cores / 32 GB this section originally assumed — see D41 (memory-constrained, per-country/model/scenario processing) and the per-step times below, which are measured where a COMANDO on this machine recorded one, and explicitly marked "not measured" otherwise (most are still the original rough pre-implementation estimates).

**Step 1. Plant inventory**
Input: GEM tracker CSV; Natural Earth 10m coastline.
Processing: filter countries and statuses; aggregate units to plants; assign technology class and water dependence; compute distance to coast (projected CRS per country); flag coastal plants at 2/5/10 km.
Output: `plants.parquet` (plant_uid, country, fleet [operating/planned_adv/planned_early], tech_class, water_dependent [bool], hydro_type, capacity_mw, lat, lon, dist_coast_km).
Time: not measured with wall-clock precision (COMANDO 13 ran in an earlier session with no stopwatch log). The 2026-09-20 D40 rerun's output timestamp (`plants.parquet` 18:05) is a few minutes before Step 3's outputs (below), consistent with well under the original 0.5 h estimate, but the run's start time was not logged, so this is not a measurement.

**Step 2. Climate data acquisition**
Input: ISIMIP repository.
Processing: download bounding-box cutouts for 5 GCMs × {historical, ssp126, ssp370, ssp585} × {tasmax, tasmin, pr}, keeping files overlapping 1984-2014 and 2041-2070; W5E5 observations 1984-2019 for the same variables.
Output: `data/isimip/{model}/{scenario}/{var}_{country}_{decade}.nc`; `data/w5e5/{var}_{country}_{decade}.nc`; checksum manifest.
Time: not a single measured duration by design (server-queue-dependent, D23); observed throughput and elapsed time for the actual COMANDO 11/12 run are in `docs/DECISIONS.md`.

**Step 3. Spatial mapping**
Input: `plants.parquet`; HydroBASINS level 6; one ISIMIP grid template.
Processing: nearest land cell per plant; for hydro, sub-basin containing the plant and upstream set via `NEXT_DOWN` traversal; area weights of grid cells intersecting each catchment.
Output: `plant_cell.parquet` (plant_uid, cell_lat, cell_lon, dist_to_cell_km); `catchment_weights.parquet` (plant_uid, cell_lat, cell_lon, weight).
Time: not measured with wall-clock precision, same caveat as Step 1. The 2026-09-20 D40 rerun's output timestamps (`plant_cell.parquet` 18:09, `catchment_weights.parquet` 18:10) span about 5 minutes together with Step 1's `plants.parquet` (18:05), well under the original 1-2 h estimate, but again not a logged measurement.

**Step 4. Daily temperature and precipitation indices**
Input: ISIMIP cutouts; unique cells from Step 3.
Processing: for each model and period, per cell: annual TX35, TX40; monthly N35; wet-day P95 (baseline) and exceedance counts in both periods; annual Rx5day.
Output: `indices_daily.parquet` (cell_lat, cell_lon, model, scenario, period, index, year, month [nullable], value).
Time: measured, COMANDO 15, this machine: **72 min** end to end for all 60 model/scenario/country jobs (`indices_daily.parquet` written 18:57, script launched ~17:45), under the machine's real memory constraints (D41) and with the system near its RAM ceiling (~89% used) for part of the run. Faster than the original 2-4 h estimate despite the weaker hardware (D41): Step 4 only ever touches the cells a plant actually uses (a few hundred to ~1,000 per country, not the full country grid), which apparently dominates over the RAM constraint's cost.

**Step 5. PET and water balance**
Input: ISIMIP tasmax, tasmin, pr; W5E5 for validation.
Processing: daily Ra from latitude and day of year; Hargreaves PET; monthly P, PET, D; catchment-averaged D for hydro plants using weights from Step 3.
Output: `water_balance_cell.parquet`, `water_balance_catchment.parquet` (id, model, scenario, month, P, PET, D).
Time: completed successfully (COMANDO 16, this machine) but without a logged start timestamp this run, so no reliable elapsed time — the original 1-2 h estimate is neither confirmed nor measured. Input cell count is larger than Step 4's (union of nearest-cell and hydro-catchment cells, e.g. 1,993 for Brazil vs. Step 4's 967), so Step 4's 72 min measurement is not a safe proxy either.

**Step 6. SPEI and SPI**
Input: Step 5 outputs.
Processing: 12-month and 3-month accumulation; SPEI-12 is fit once per (id, model) series on its own 360 baseline values (no calendar-month split); SPEI-3 is fit per calendar month with a +/-1 adjacent-month window (n=90); both via PWM log-logistic with a Pearson III MLE fallback where PWM does not converge (docs/DECISIONS.md D54/D55; see the Step 6 note below for the full comparison against alternatives, including a regional pooling approach that was tried and reverted); apply the same per-series parameters to 2041-2070; clip to [−3, 3]; SPI with gamma distribution, per (id, model) per calendar month, n=30 (unaffected by the SPEI estimator choice). Future series start in December 2041 because 2031-2040 is not downloaded; state this in Methods.
Output: `spei.parquet` (id, model, scenario, month, spei12, spei3, spi12, distribution).
Time: measured (this machine, fit+standardize loop only, D54's per-series temporal method): **581.5s (~9.7 min)** -- faster than the earlier per-calendar-month hybrid's 3,649s (~61 min, D45/17-F) because SPEI-12's single per-series fit needs one fit attempt per series instead of twelve, cutting the number of (slower) Pearson III MLE calls by roughly the same factor.


> Editorial note (C24): the next block documents the COMANDO 17-F per-calendar-month hybrid fit, superseded in production by D54/D55 (see 1.4 H2 and Step 6 above). Kept verbatim as the method-comparison record.

**Step 6 note: PWM log-logistic fit failures and hybrid fallback (COMANDO 17-C/17-D/17-E/17-F; `docs/DECISIONS.md` D45, closed)**

The three-parameter log-logistic distribution in Step 6 is fit by unbiased
probability-weighted moments (PWMs), the closed-form estimator of
Vicente-Serrano et al. (2010): from a calendar month's 30 baseline values
(1985-2014), sample PWMs b0, b1, b2 give a shape parameter beta =
(2b1-b0)/(6b1-b0-6b2), then scale alpha and location gamma from beta. The
production implementation (`craei.hazards.spei._fit_loglogistic_pwm`)
rejects a fit whenever beta is non-positive or non-finite, any Gamma-function
evaluation in the alpha step is non-finite or zero, or the fitted gamma
(location) exceeds the sample minimum (a log-logistic's support is
[gamma, infinity), so gamma above the smallest observed value is a support
violation, fixed in COMANDO 17-D). On this project's real water-balance
deficit D = P - PET, roughly 30% of (plant/cell, model, calendar-month)
baseline fits are rejected this way (COMANDO 17-B: 32.4% hydro catchment
SPEI-12, 14.4% run-of-river SPEI-3, 29.1% thermal-cell SPEI-12, all with the
full 30-sample baseline and zero missing months -- COMANDO 17-C ruled out
sample size and data gaps as causes). Every rejected fit is left as `NaN` in
`spei.parquet` and counted, never silently replaced by a default value.

*Why PWM fails for the 3-parameter log-logistic under high skewness.* The
PWM estimator inverts three sample moments (b0, b1, b2) into three
distribution parameters through the closed-form relation above. That
relation is only defined, and only gives a physically meaningful beta > 0,
for a restricted region of the (b0, b1, b2) space consistent with a
log-logistic shape; a 30-observation empirical sample of a distribution that
is more sharply skewed, more symmetric, or otherwise differently shaped than
a log-logistic (as D = P - PET can be, month to month and cell to cell, in
this project's real data) can and does land the PWM triplet outside that
region, most commonly flipping the sign of the numerator/denominator ratio
that defines beta. COMANDO 17-C measured this directly: 100% of the failures
are the beta <= 0 branch, with beta ranging from -2.96 to -21,878 -- not
values near zero, but sign-flipped and often large in magnitude, consistent
with the sample's L-moments falling well outside the PWM formula's valid
domain for this distribution family rather than marginally missing it.
COMANDO 17-C also found no support for two alternative explanations tested
directly: the failures are not concentrated in any particular season (16-50%
across every calendar month in all three countries, with Brazil's rate
higher than India's dry-season rate if anything), and failing vs. passing
groups show no consistent difference in coefficient of variation. This
matches a known small-sample weakness of the L-moment/PWM estimator for the
three-parameter log-logistic reported in the hydrological literature, not a
defect specific to this implementation.

*Why taking the absolute value of beta is mathematically and physically
invalid.* The sign of beta determines which tail of the log-logistic
distribution is heavier: a positive beta gives the standard right-skewed
log-logistic form used for SPEI (Vicente-Serrano et al. 2010); replacing a
computed beta < 0 with |beta| does not recover a valid alternative fit to
the same data -- it substitutes the parameters of a different distribution
shape than the one the sample's moments actually support, with the tail
direction inverted. Because SPEI's standardization step
(`norm.ppf(cdf(D_acc, *params))`) maps quantiles of the fitted distribution
onto the standard normal, inverting the tail inverts which end of the
distribution reads as extreme: a real wet anomaly could be reported as an
extreme dry SPEI value, and vice versa, silently corrupting both the
severe-drought frequency F_D (Sec. 1.4 H2) and any classification built on
it. `|beta|` was considered and rejected on exactly this basis, not adopted.

*Alternative estimators measured, not adopted (COMANDO 17-E).* A
stratified-sample benchmark (`scripts/benchmark_spei_fitters.py`, fixed
seed) compared the production PWM estimator against a moment-seeded
3-parameter log-logistic MLE, a Generalized Extreme Value fit (MLE), and a
Pearson Type III fit (MLE). Fitting every alternative on the full ~247,000
baseline combos was measured as computationally infeasible in this session
(a 200-combo pilot: ~60-100ms per MLE call vs. PWM's closed-form
microseconds), so each bucket's evaluation is a fixed-seed random sample of
up to 800 PWM-failing and 800 PWM-passing combos (not the full population;
treat every percentage below as approximate, not exact):

| Bucket | Method | Failure rate | Recovery on PWM failures | F_D | Relative time |
|---|---|---|---|---|---|
| Hydro catchment SPEI-12 | PWM (production) | 50.0%\* | 0.0% | 5.90% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.71% | 396x |
| | GEV (MLE) | 0.0% | 100.0% | 7.94% | 580x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.46% | 219x |
| Run-of-river SPEI-3 | PWM (production) | 50.0%\* | 0.0% | 5.35% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.86% | 449x |
| | GEV (MLE) | 0.0% | 100.0% | 8.13% | 735x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.26% | 288x |
| Thermal cell SPEI-12 | PWM (production) | 50.0%\* | 0.0% | 5.70% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.74% | 262x |
| | GEV (MLE) | 0.0% | 100.0% | 8.72% | 480x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.37% | 154x |

\*PWM's 50.0% sample failure rate is the stratified sample design (800
failing + 800 passing drawn on purpose to measure recovery), not the real
population rate (32.4% / 14.4% / 29.1%, COMANDO 17-B); its F_D is computed
only from the sample's passing half, consistent with the real production
run's 5.9-6.6% (COMANDO 17-D).

All three alternatives recovered every one of the 2,400 sampled PWM
failures (100%) with zero failures of their own, at 150-735x PWM's
wall-clock cost. All three land somewhat above the ~6.7% expectation (PWM's
own passing-only F_D lands somewhat below it); Pearson III is closest to
6.7% and cheapest among the three alternatives, GEV furthest and most
expensive. Following this benchmark, COMANDO 17-F adopted the hybrid
strategy below.

**Fitting strategy (hybrid PWM + MLE fallback, COMANDO 17-F, closes
`docs/DECISIONS.md` D45):**

We fit the log-logistic distribution via closed-form probability-weighted
moments (PWM; Vicente-Serrano et al. 2010) when the estimator yields valid
parameters (shape beta > 0, and location gamma <= min(sample), the
log-logistic support restriction, COMANDO 17-D). In practice 29.6% of
(plant/cell, model, calendar-month) baseline combinations across the 3
SPEI series (hydro catchment SPEI-12, run-of-river SPEI-3, thermal-cell
SPEI-12; `spei.parquet`'s `distribution` column) need the fallback -- close
to, if a little below, the ~30% COMANDO 17-B/17-C measured for PWM's own
failure rate, since the fallback only fires on PWM's actual rejects, not a
fixed quota. The PWM estimator produces beta <= 0 for these because of high
skewness in the water balance D = P - PET over a 30-sample baseline
(COMANDO 17-C: a shape-parameter sign flip, beta ranging -2.96 to -21,878,
not a near-zero edge case, and not concentrated in any particular season --
see the "Why PWM fails" note above). For these cases we fall back to
fitting the Pearson Type III distribution via maximum likelihood estimation
(`scipy.stats.pearson3.fit`), which is numerically stable under high
skewness and used in hydrological drought analysis (Bobee and Robitaille
1977). The hybrid recovers 100% of PWM's fitting failures on this
project's real data (0/3,275 hydro catchment, 0/1,305 run-of-river, 0/16,010
thermal-cell (group, calendar-month) combinations left unfit; the 3.03%
`NaN` rate remaining in `spei.parquet`'s `SPEI_12` column is the
already-documented, structural lead-in `NaN` from `accumulate()`'s
`min_periods=window` behavior -- the first 11 months of each of the
baseline and 3 future scenario blocks per group, Spec L05 -- not a fitting
failure). Baseline F_D (SPEI-12 <= -1.5), hydro and thermal combined, mean
over (id, model) groups: 6.21%, close to the ~6.7% standard-normal
expectation. Computational overhead: measured directly, both sides of the
same comparison, on the real full ~247,000 baseline (plant/cell, model,
calendar-month) combinations -- 3,649s (~61 min) for the hybrid
fit+standardize loop vs. 189s (~3.2 min) for an otherwise-identical
PWM-only pass (`fit_spei_distribution` swapped for `loglogistic_fit_fn`,
same data, same machine), a **~19.3x overhead**. This is higher than a
draft estimate of ~15x and far higher than an earlier, pre-measurement
draft's "minimal (~1.2-1.4x)" framing, which is not supported by
measurement and is corrected here; ~19.3x is acceptable for this project's
batch, offline scientific processing (a single Step 6 run, not a
latency-sensitive path). The final SPEI values are
distribution-agnostic (standardized via inverse normal CDF regardless of
which distribution produced them), preserving comparability with the SPEI
literature for the majority (70.4%) of baseline combinations still fit by
the standard log-logistic estimator.

**Step 7. Plant-level hazard table**
Input: Steps 3-6.
Processing (`craei.hazards.consolidate`, COMANDO 18): plants are assigned one bucket each (hydro_reservoir incl. pumped storage, hydro_run_of_river, thermal_water_dependent, thermal_air_only, solar); ΔTX35/ΔTX40 (cell-scale) for the two thermal buckets, F_D/R_D of catchment-scale SPEI-12 for hydro (plus catchment-scale SPEI-3, additional not substitute, for run-of-river) and cell-scale SPEI-12 for water-dependent thermal (SPEI, not SPI -- SPI-12 is COMANDO 22's sensitivity test), and H4 (Supplementary Information: p95 exceedance-frequency ratio, Rx5day percentage change) for every bucket with a linked cell. R_D is left `NaN`, not computed, when the baseline F_D is exactly zero (rare by construction, F_D's baseline expectation is ~6.2%, D45); this is counted, not silently substituted.
Output: `plant_hazards.parquet` (plant_uid, bucket, model, scenario, hazard, baseline_value, future_value, delta, ratio).
Time: measured, COMANDO 18, this machine: **68s** (script wall time, includes Step 8). 446,700 rows (5,910 hydro_reservoir F_D-SPEI12 + 2 H4 hazards x 394 plants x 5 models x 3 scenarios; 3,915 hydro_run_of_river F_D-SPEI12 + F_D-SPEI3 x 262 x 5 x 3, plus H4; 19,200 x 4 hazards thermal_water_dependent (1,280 plants); 795 x 4 hazards thermal_air_only (53 plants); 157,050 x 2 H4-only hazards solar (10,470 plants)). R_D-baseline-zero rate (Action 2, stop threshold 1%): 0.000% hydro_reservoir, 0.000% hydro_run_of_river (both SPEI series), 0.016% thermal_water_dependent (3/19,200) -- did not trigger the stop condition. See docs/DECISIONS.md D47 for the full breakdown.

**Step 8. Aqueduct water stress**
Input: Aqueduct 4.0 `future_annual` `ws` (2050, 3 scenarios, `pfaf_id`-keyed) and `baseline_annual` `bws` (acquired and deduplicated to (country, pfaf_id), D32/D38).
Processing: water-dependent thermal plants joined to their containing HydroBASINS polygon's `pfaf_id` (D37's distance-guarded nearest match); Aqueduct categories applied as published (D33/D36); two cooling bounds reported per L01 (D47) -- "upper" (all water-dependent thermal plants) and "lower" (same set excluding plants within `coastal_buffer_km`=5 km of the coast).
Output: `plant_aqueduct.parquet` (plant_uid, scenario, cooling_bound, ws_value, ws_category, bws_value, bws_category).
Time: measured, COMANDO 18, this machine: included in Step 7's 68s (single script run). 7,311 rows = 1,280 water-dependent thermal plants x 3 scenarios x 2 cooling bounds (7,680) minus 369 rows (123 plants x 3 scenarios) excluded from "lower" as coastal. 0 plants in category -1 ("arid_low_water_use") or "no_data" (no Aqueduct match) in this run, in any country or cooling bound (see D47 for a discrepancy this raises against an earlier ad-hoc session note, not reconciled).

**Step 9. Exposure aggregation and agreement**
Input: Steps 1, 7, 8.
Processing: capacity shares and GW above headline classes per country × technology × fleet × scenario × model; ensemble median and range; model agreement flags per plant.
Output: `exposure_summary.csv` (country, tech_class, fleet, hazard, scenario, cooling_bound, median_share, min_share, max_share, median_gw, agreement_share).
Time: 0.5 h (not measured).

Total compute: roughly 11-18 h (not measured as a single run; see O07 in docs/DECISIONS.md for the projection from Steps 1-4's actual measured/observed times and the open question this raises about the 24 h criterion).


## 4. Results map (figure/table -> source -> producing script -> blocking item)

| Item | Source table | Producing script | Blocking |
|---|---|---|---|
| Fig 1 fleet and capacity by technology and fuel | plant_units.parquet | to be written (C29) | D77, D78 (C28) |
| Fig 2 TX35 exposure maps per thermal plant by fuel | plant_hazards.parquet (h1) + plants coords + plant_units | to be written (C31, C41) | C28 |
| Fig 3 heat-threshold curves, operating vs planned | plant_hazards + plant_units | to be written (C32, C34) | O17 |
| Fig 4 drought maps SPEI and SPI per hydro plant | plant_hazards (SPEI); SPI only in spei.parquet | to be written (C35) | O18 |
| Fig 5 excess over null by bucket and scenario, GCM range | null table + plant_hazards | to be written (C30, C36) | O20, O21 |
| Table 1 GW fraction exposed by technology, fuel, scenario | plant_units + plant_hazards | to be written (C38) | O16, O17 |
| Table 2 leave-one-out, 5 largest hydro | c23d_7_leave_one_out.csv (audit) | to be promoted (C37) | O19, L30 |
| Supplementary ONS validation | validation.csv | exists (scripts/25_validation_stats.py) | none |

---


---

## Appendix A. Pipeline components outside v2 article scope (verbatim from v1; v1 numbering)


> Editorial note (C24): ONS national validation is supplementary (D73); subsystem validation and Portugal REN/DGEG are outside v2.

### 1.6 Compound hydro-drought and thermal-heat metric

For each country, model and period, two monthly national series are built:

S_hydro(m) = Σ_{i∈hydro} Cap_i × 1[SPEI-12_i(m) ≤ −1.5] / Σ Cap_i (share of hydro capacity in severe drought)

H_thermal(m) = Σ_{j∈thermal} Cap_j × N35_j(m) / Σ Cap_j (capacity-weighted number of TX35 days in the month)

A compound month occurs when both series exceed their own 90th percentile estimated on 1985-2014 of the same model (if the S_hydro percentile is zero, any value above zero qualifies). Under independence the baseline frequency is about 1%. The national aggregation is justified by interconnection in Brazil (SIN) and India (national grid) and by Iberian market coupling for Portugal.

**Metric closure (D63, COMANDO 22, current state, supersedes the LR_C design below this paragraph)**: the future-to-baseline likelihood ratio LR_C = F_C,future / F_C,baseline, as originally specified, is not used as the headline quantity. A direct diagnostic found that in 13 of 45 country x scenario x model cells, at least one of S_hydro or H_thermal exceeds its own baseline P90 in a majority of future months (worst case: Brazil x UKESM1-0-LL, 64-92% of future months across the two series and three scenarios). In those cells the ratio `f_compound_observed / (f_s_above * f_h_above)` -- the observed compound frequency divided by what independence of the two marginals would predict -- is close to 1.0, meaning LR_C's large values there come from each series' own baseline-relative drift (a mean shift), not from extra co-occurrence; the P90 threshold has stopped discriminating extremes in those cases. The metric is reported instead as two separate quantities, both computed directly from the already-aggregated monthly series, no new climate data processed:

- `diff_pp` = 100 x (F_C,future - F_C,baseline): the change in compound-month frequency in percentage points. A difference, not a ratio, so it stays well-defined and interpretable even where a marginal's baseline P90 is exceeded most of the time in the future.
- `dependence_ratio` = F_C,future / (f_s_above,future x f_h_above,future), where `f_s_above,future` and `f_h_above,future` are each series' own share of future months above its baseline P90: observed future co-occurrence over the co-occurrence independence would predict, from the future marginals only. Values near 1.0 mean the two series are behaving independently above their respective thresholds in the future period (no extra coupling to report); values further from 1.0 indicate measurable dependence.

Restricting to the 32 of 45 cells where the percentile threshold still discriminates (both marginals under 50% of future months), `dependence_ratio` is not uniformly 1.0: median 1.23, 5th/95th percentile 0.78/2.69, and 20/32 cells (62.5%) deviate from 1.0 by more than 20%, mostly upward and most pronounced for India. This is reported as a real, moderate finding of positive dependence in a majority of the cells where the question is answerable, not explained away as pure independence -- see §2.3.

### 1.7 Validation

Validation targets the one sector with open observed response data. SPEI-12 is computed from W5E5 observations (1985-2019) with the same procedure and aggregated to hydro-capacity-weighted series for the four Brazilian subsystems and for Portugal. These are compared with annual natural energy inflow (ENA) from the Brazilian system operator (ONS) and with the hydro productivity index (IPH) published by the Portuguese transmission operator (REN). Statistics: Spearman correlation with 3-year block bootstrap confidence intervals, and the odds ratio of a bottom-tercile inflow year given December SPEI-12 ≤ −1. Short records produce wide intervals, which are reported as such. W5E5 is derived from ERA5, so a comparison of hazard climatology against ERA5 would not be independent and is not used as validation. EM-DAT is used only descriptively in Supplementary Information. India is not validated, which is stated as a limitation.

**Subsystem validation status**: A desagregação por subsistema ONS (N/NE/S/SE) está suspensa para v0.1.0 por ausência de fonte oficial de mapeamento planta→subsistema (ver D62). A validação de Portugal (REN IPH × SPEI-12, n=57 meses) e a correlação nacional Brasil permanecem.

**Portugal / REN IPH (D59-D61, O10-O11, COMANDO 21-23)**: primary validation variable is REN's monthly Hydro Productivity Index (IPH), acquired directly from REN DataHub's `RegimeYearly` endpoint (`craei.acquire.ren`).

- REN data coverage: 2015-01 to 2026-09.
- Climate-model overlap: 2015-01 to 2019-12.
- Usable complete calendar years: 2016-2019 (4 years; 2015 is a partial year, missing jul/aug/sep, see D60).
- Available overlap months: 57 (not the nominally assumed 60).
- Monthly validation: implementation-level / observational cross-validation against APA 2018 Tabela 7 -- matches to within 2-decimal rounding for all 33 overlapping months (`reports/ren_iph_validation.md` §4). This confirms the acquisition and date semantics are correct, not that five years of overlap gives long-term climatological power.
- Annual validation: **resolved as a methodological limitation, not a failure** (D61). Every raw REN response inspected directly exposes no annual/weighting field -- only the 12 monthly values -- and no public REN/ERSE/DGEG documentation of the exact annual aggregation formula was found. A derived calendar-year mean does not reproduce ERSE's published annual figure in general (2017 is the clearest case); this is recorded as a gap in what can be independently checked at the annual resolution, and is not used to support or undermine the monthly-resolution statistics the study actually reports.
- Auxiliary validation: DGEG gross monthly hydroelectric generation (GWh), used only as a consistency check (O11, D61) -- never treated as equivalent to IPH. Annual correlation with IPH is strong (Pearson/Spearman ≈ 0.90 over 2015-2019); monthly correlation is weaker, as expected, since generation additionally depends on afluência timing, reservoir operation, dispatch, capacity and pumping.

**Limitation**: the five-year overlap prevents robust long-term climatological inference from the Portugal correlation/odds-ratio statistics; report accordingly, parallel to L08/L09's existing short-record notes for Brazil/India.

### 1.8 Uncertainty

Uncertainty is reported through (i) scenario spread, (ii) inter-model range and agreement, and (iii) one-at-a-time tests of each discrete choice: heat class (15/30/60 days), drought class (R_D 1.5/2/3), SPEI threshold (−1.0/−1.5/−2.0), PET formulation (SPEI Hargreaves vs SPI), coastal cooling distance (2/5/10 km), and exclusion of UKESM1-0-LL (highest climate sensitivity in the ensemble). A global variance-based analysis (Sobol) is not used because the design has few discrete choices whose individual effects are more informative when shown directly.

**H3. Chronic water stress (water-dependent thermal, freshwater bound only).** WRI Aqueduct 4.0, keyed by HydroBASINS `pfaf_id`, for the baseline and for 2050 under the optimistic, business-as-usual and pessimistic scenarios, mapped to SSP1-2.6, SSP3-7.0 and SSP5-8.5. Aqueduct 4.0 splits the indicator across two collections with different field names: the baseline collection (`baseline_annual`) exposes `bws` (baseline water stress); the 2050 projections (`future_annual`) expose `ws` (water stress) under each `{bau|opt|pes}{30|50|80}` scenario/horizon code. Both are the same underlying stress ratio (withdrawal over available supply) on the same 0-5 category scale; the field renaming between collections is WRI's own convention, not a methodological difference. Aqueduct categories are used as published: low (<10%), low-medium (10-20%), medium-high (20-40%), high (40-80%), extremely high (>80%). Exposure is capacity in high or extremely high stress. H3 is reported separately from H1 and H2 because Aqueduct uses its own climate and socioeconomic forcing and is not consistent with the ISIMIP3b ensemble. Aqueduct's future-annual values are themselves the median of an internal 5-GCM ensemble distinct from this project's ISIMIP3b ensemble, with no per-model breakdown available (L13).

**H4. Extreme precipitation (Supplementary Information, all fleets).** Wet-day 95th percentile (days ≥1 mm) estimated on the baseline per cell and model; change metric is the ratio of exceedance frequency (baseline 5% of wet days by construction) and the percentage change in mean annual Rx5day. Reported as a change in flood-forcing precipitation, not as flood risk.

**Solar PV (Supplementary Information).** Peak-hour temperature loss L = γ × max(0, TX + 31.25 − 25), with γ = 0.4% °C⁻¹ (typical crystalline silicon; verify against datasheet range) and 31.25 °C the cell-to-air difference from NOCT = 45 °C at 1000 W m⁻². Because L is linear in TX above the threshold, ΔL mainly reflects warming; it is included to document that heat-driven PV losses are small compared with thermal and hydro hazards, not as a finding in itself.

**Excluded hazards.** Extreme wind is excluded for three reasons: 10 m gusts are not comparable with IEC 61400-1 design winds (50-year 10-minute reference speeds of 50, 42.5 and 37.5 m s⁻¹ at hub height for classes I-III), which are rarely approached outside tropical cyclone tracks; confidence in projected extreme wind change is low in IPCC AR6; and GCM resolution does not capture the relevant extremes. Riverine and coastal flooding, sea-level rise and wildfire are outside the scope.


> SUPERSEDED (D63/D72): the LR_C metric below was replaced by diff_pp and dependence_ratio, and the whole compound metric is outside v2 scope. 11_compound.py is archived.

**Step 10. Compound metric**
Input: `spei.parquet`, monthly N35, plants.
Processing: national monthly S_hydro and H_thermal; baseline P90 per model; compound months; LR_C per country, scenario, model.
Output: `compound.csv` (country, scenario, model, f_baseline, f_future, lr_c); `compound_months.parquet` for seasonal inset.
Time: 0.5 h (not measured).

**Step 11. Validation**
Input: W5E5 SPEI (Step 6 applied to observations); ONS ENA; REN productivity index; plants.
Processing: hydro-capacity-weighted annual SPEI-12 per subsystem and Portugal; Spearman ρ with block bootstrap; odds ratio for low-inflow years.
Output: `validation.csv` (region, n_years, rho, rho_ci_low, rho_ci_high, odds_ratio, or_ci_low, or_ci_high).
Time: 1 h (not measured).

**Step 12. Sensitivity and figures**
Input: all previous outputs.
Processing: rerun Steps 9-10 under each alternative; generate figures.
Output: `sensitivity.csv` (test, parameter_value, result_id, value); figure files.
Time: 2-3 h (not measured).

## 5. Additional downloads

| Dataset | Source | Approx. size | Purpose |
|---|---|---|---|
| ISIMIP3b bias-adjusted daily tasmax, tasmin, pr; 5 GCMs; historical + 3 SSPs | ISIMIP repository (files API cutouts) | ~35 GB uncompressed for three country boxes; compressed size lower (estimate from grid size, verify after first model) | All hazard indices |
| W5E5 v2.0 daily tasmax, tasmin, pr, 1984-2019 | ISIMIP repository (ISIMIP3a obsclim) | ~5 GB uncompressed (estimate) | Validation |
| HydroBASINS level 6, South America, Asia, Europe | HydroSHEDS | Tens to a few hundred MB (verify) | Hydro catchments |
| Natural Earth 1:10m coastline | naturalearthdata.com | <10 MB | Cooling bound |
| ONS natural energy inflow (ENA) by subsystem | ONS open data portal | <10 MB | Validation, Brazil (verify record length) |
| REN hydro productivity index | REN statistical data | <1 MB | Validation, Portugal |
| Aqueduct 4.0 baseline bws | Existing GEE asset | <100 MB | Only if baseline not yet exported |

Example (ISIMIP cutouts; check function names and filters against the current `isimip-client` README before running):

```python
from pathlib import Path
from isimip_client.client import ISIMIPClient

client = ISIMIPClient()

MODELS = ["gfdl-esm4", "ipsl-cm6a-lr", "mpi-esm1-2-hr", "mri-esm2-0", "ukesm1-0-ll"]
SCENARIOS = ["historical", "ssp126", "ssp370", "ssp585"]
VARIABLES = ["tasmax", "tasmin", "pr"]
BBOX = {  # west, east, south, north
    "BRA": (-74.5, -34.0, -34.5, 6.0),
    "IND": (68.0, 98.0, 6.0, 37.5),
    "PRT": (-31.5, -6.0, 32.5, 42.5),  # includes Azores and Madeira
}

def years_needed(path, scenario):
    y0, y1 = (int(x) for x in Path(path).stem.split("_")[-2:])
    lo, hi = (1984, 2014) if scenario == "historical" else (2041, 2070)
    return y1 >= lo and y0 <= hi

for model in MODELS:
    for scenario in SCENARIOS:
        for var in VARIABLES:
            resp = client.datasets(
                simulation_round="ISIMIP3b",
                product="InputData",
                climate_forcing=model,
                climate_scenario=scenario,
                climate_variable=var,
                time_step="daily",
            )
            paths = [
                f["path"]
                for ds in resp["results"]
                for f in ds["files"]
                if "bias-adjusted" in f["path"] and years_needed(f["path"], scenario)
            ]
            for country, (w, e, s, n) in BBOX.items():
                job = client.cutout_bbox(paths, w, e, s, n, poll=30)
                out = Path(f"data/isimip/{model}/{scenario}/{var}/{country}")
                out.mkdir(parents=True, exist_ok=True)
                client.download(job["file_url"], path=out, validate=False, extract=True)
```

Implementation notes: submit jobs in small batches to respect server limits; record each file checksum in the existing manifest; check each file's calendar attribute before computing annual counts.

---

---

## Key references to verify and cite

- van Vliet, M.T.H. et al. (2016). Power-generation system vulnerability and adaptation to changes in climate and water resources. *Nature Climate Change*.
- Frieler, K. et al. (2021, protocol). ISIMIP3b scenario and forcing protocol.
- Lange, S. (2019). Trend-preserving bias adjustment and statistical downscaling with ISIMIP3BASD. *Geoscientific Model Development*.
- Cucchi, M. et al. (2020) and Lange, S. et al. (2021). W5E5 / WFDE5.
- Vicente-Serrano, S.M. et al. (2010). A multiscalar drought index sensitive to global warming: SPEI. *Journal of Climate*.
- Hargreaves, G.H. & Samani, Z.A. (1985). Reference crop evapotranspiration from temperature. *Applied Engineering in Agriculture*.
- Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.
- Kuzma, S. et al. (2023). Aqueduct 4.0 technical note. World Resources Institute.
- Lehner, B. & Grill, G. (2013). HydroSHEDS / HydroBASINS. *Hydrological Processes*.
- IEC 61400-1 (Wind energy generation systems, design requirements).
- IPCC AR6 WGI, Chapter 11 and Atlas.


---

## v2.1 addendum (C44, D88): level lens, classes, co-located exposure, result handlers

This addendum is appended; the sections above are not edited. Where they conflict, v2.1 governs. Stale or superseded items above:
- 1.4 H1 "tested at 15 and 60 days": the heat grid is 10/20/30/40/50/60/80/100 d (O17); 30 d stays the change-lens headline.
- 1.5, 1.7 "agreement = at least 4 of 5 GCMs": tables report k = 1, 3, 5 of 5 GCMs exposed (O31).
- 1.7, 1.8 "TO BE DEFINED, see O17/O18/O19/O21": O17 is closed (D87); the null script is delivered (W4a, DECISIONS C42); the others are in the plan (G addendum 3).
- 1.8 "N_SIM=2000 ... script to be written (C30)": delivered as W4a (block 12, 24, 36, 60, AR(1), white noise).
- 1.3 and Appendix 1.8 statements on the climate sensitivity of the GCMs: not verified in the repository (O33).
- Section 4 (results map): replaced by the table at the end of this addendum.

### A. Two lenses
- Change lens (headline, Axis 1): dTX35 >= 30 d/yr; R_D >= 2. Question: how much does it worsen against the baseline?
- Level lens (new): TX35 future (days/yr) and F_D future (% of months with SPEI-12 <= -1.5). Question: how severe is the climate at the plant in 2041-2070?
- Reason: a delta ignores the level. Both lenses are reported; neither replaces the other.

### B. Heat level classes (O28)
- Exclusive bins of TX35 future, days/yr: low < 10; medium 10 to < 30; high 30 to < 90; extreme >= 90. Labels are conventions with no physical basis (tier 3). Cuts are fixed by calendar anchors (30 d about one month, 90 d about one quarter) and the O17 grid, never tuned on the future result.
- Baseline classes use the same cuts and are reported next to the future classes (class shift).
- Per (unit, GCM, scenario) the class comes from that GCM's value; GW per class is computed per GCM; then min, median, max across the 5 GCMs and k of 5. Map: class of the median over GCMs per cell, with the number of GCMs in that class.
- Units: thermal (water-dependent and air-only; air-only only inside all_thermal) and hydro. Hydro uses TX35 at the plant cell; reading: climatic context, not a cooling hazard.
- Change classes (secondary): exclusive bins of dTX35 (< 10, 10 to < 20, 20 to < 30, >= 30), derived per GCM from the existing grid.
- TX40: sensitivity on its own grid (O27).

### C. Drought level classes (O29)
- F_D future against the null of no climate change: low <= p50; medium p50 to p90; high p90 to p99; extreme > p99 of the null distribution of F_D future (SPEI <= -1.5).
- Null: block bootstrap, 12-month blocks (canonical); AR(1) as sensitivity; percentile sensitivity p75/p90/p95. Percentiles use 20,000 simulations in their own stream default_rng([23, 99]); the W4a stream is untouched.
- "Extreme" means natural variability alone rarely produces that F_D. It is not a probability of impact. Units are compared one by one with the marginal null and are spatially correlated, so the GW share above a percentile is not binomial.
- Hydro: pool of catchment series. Water-dependent thermal (cell-scale SPEI-12): pool TO BE DEFINED (O29).
- Change lens: R_D classes < 1.5, 1.5 to < 2, 2 to < 3, >= 3, each shown with its null rate from W4a. R_D undefined (baseline F_D = 0) is its own category.

### D. Co-located exposure (D88)
- Spatial coincidence at the plant location, not simultaneity in time. Calling it "co-located exposure", never "compound event".
- Units with both hazards: water-dependent thermal (cell scale) and hydro (catchment SPEI-12; TX35 at the plant cell). Air-only thermal and solar are not included. Cooling bound for thermal: O32.
- Per GCM and scenario: 4 x 4 cross-tab (heat level class x drought level class) in GW; headline = extreme in both; sensitivity = high or extreme in both. The same GCM is used for both hazards. Reported with min, median, max and k of 5.
- No index, no weights, no ranking. Individual hazards are presented first.
- Temporal coincidence (years with both): optional, O30.

### E. Aggregation rules
- Capacity from plant_units. Hydro: Itaipu counted as 7,000 MW (b) in the headline, 14,000 MW (a) as sensitivity (D82). Leave-one-out beside every headline.
- Ranges are structural, not confidence intervals. Bootstrap limits only with >= 10 cells and nan_frac = 0 (O25); otherwise descriptive.
- State and macro-region: Natural Earth admin1 (fields name, postal, region); nearest polygon for points outside, with the count reported.
- New modules take a country parameter; older scripts filter Brazil explicitly.

### F. Not claimed
Impact, vulnerability, generation loss, probabilities, ICs from the GCM range, harvest-window effects, a composite index, solar, wind, H4, results outside Brazil, simultaneity in time.

### G. Open items
O16 (harvest window, no source); O18 (SPI x SPEI scheme); O19 (leave-one-out of Axis 2); O20 (water x air in Fig 5); O21 (hydro cell bootstrap); O28 (heat cuts, proposal); O29 (null pool for thermal cells, percentiles); O30 (temporal coincidence); O31 (agreement definition); O32 (cooling bound in co-exposure); O33 (claims to verify). Pending without id: re-run W3d and W3f-3 at n_boot = 5,000.

### H. Result handlers
Every number in the text comes from one handler. A value is filled only from pasted output. Table names marked (planned) do not exist yet.

| Id | Statement slot | Table | Filter | Column | Value |
|---|---|---|---|---|---|
| F1 | Operating thermal GW (BRA) | plant_units | country, fleet, tech_class | sum capacity_mw | TO BE DEFINED |
| F2 | Planned thermal GW (adv, early, all) | plant_units | fleet | sum capacity_mw | TO BE DEFINED |
| F3 | Hydro GW operating (b headline, a sensitivity), planned hydro GW | plant_units | tech_class = hydro | sum capacity_mw | TO BE DEFINED |
| HC1 | Share of operating thermal GW with dTX35 >= 30 d, median [min-max], 3 scenarios | w3_table1 | group = all_thermal, fleet = operating, threshold = 30 | pct_median, pct_min, pct_max | TO BE DEFINED |
| HC2 | Same, in GW | w3_table1 | same | gw_median | TO BE DEFINED |
| HC3 | Agreement k = 3 and k = 5 | w3_table1 | same | pct_gw_k3, pct_gw_k5 | TO BE DEFINED |
| HC4 | By fuel (bioenergy, gas) | w3_table1 | group = fuel | pct_median, pct_min, pct_max | TO BE DEFINED |
| HC5 | Planned minus operating, paired, with cell bootstrap | w3_heat_bootstrap_paired | planned_fleet = planned_all, threshold = 30 | obs_median_diff, boot_p025, boot_p975 | TO BE DEFINED |
| HC6 | Scenario contrast | w3_heat_scenario_contrast | pair, threshold = 30 | obs_median_diff, n_gcm_pos, boot_p025_pp, boot_p975_pp | TO BE DEFINED |
| HC7 | Cell bootstrap of the share | w3_heat_bootstrap_shares | threshold = 30 | obs_median, boot_p025, boot_p975 | TO BE DEFINED |
| HC8 | Leave-one-cell-out range | w3_table1 | threshold = 30 | loo_min, loo_max | TO BE DEFINED |
| HL1 | GW and share per heat level class, thermal, by fleet and scenario | w3g_heat_level_classes (planned) | group, fleet, scenario, class | gw_median, pct_median, pct_min, pct_max | TO BE DEFINED |
| HL2 | Same, hydro | w3g_heat_level_classes (planned) | group = hydro | same | TO BE DEFINED |
| HL3 | Baseline to future class shift | w3g_heat_class_shift (planned) | fleet, scenario | gw_median | TO BE DEFINED |
| HL4 | Change classes (exclusive delta bins) | w3g_heat_change_classes (planned) | group, fleet, scenario | pct_median | TO BE DEFINED |
| HL5 | Map class per cell and GCM agreement | w3g_heat_cell_class (planned) | scenario | class_median, n_gcm_same | TO BE DEFINED |
| DR1 | Null percentiles of F_D future (20,000 simulations) | w4g_null_percentiles (planned) | null, spei_threshold = -1.5 | p50, p90, p99 | TO BE DEFINED |
| DR2 | Hydro GW per drought level class, by scenario | w4g_drought_classes (planned) | group = hydro, class | gw_median, pct_min, pct_max | TO BE DEFINED |
| DR3 | Share above null p99 and share expected by chance | w4g_drought_classes (planned) | class = extreme | pct_median | TO BE DEFINED |
| DR4 | Share with R_D >= 2 and null rate by block | w4a: w4_null_rates | is_production_point | pct_rd_ge | TO BE DEFINED |
| DR5 | Excess over the null, Itaipu b headline, a sensitivity | W4b table (planned) | scenario | excess_pp | TO BE DEFINED |
| DR6 | SPI x SPEI with the same fitting scheme | W4c table (planned) | scenario | pct_exposed | TO BE DEFINED |
| DR7 | Leave-one-out of the 5 largest hydro plants | W4d table (planned) | plant, scenario | pct_exposed | TO BE DEFINED |
| DR8 | GCM range and agreement of the hydro result | W4e table (planned) | scenario | pct_min, pct_median, pct_max, k | TO BE DEFINED |
| CO1 | 4 x 4 cross-tab, GW | w4h_coexposure (planned) | group, scenario | gw_median | TO BE DEFINED |
| CO2 | GW and share extreme in both, range | w4h_coexposure (planned) | heat = extreme, drought = extreme | gw_median, gw_min, gw_max | TO BE DEFINED |
| CO3 | High or extreme in both (sensitivity) | w4h_coexposure (planned) | heat, drought >= high | gw_median | TO BE DEFINED |
| ST1 | GW in extreme heat by state and macro-region | w3h_state_summary (planned) | class = extreme | gw_median | TO BE DEFINED |
| ST2 | Co-exposure by state; units assigned by nearest polygon | w3h_state_summary (planned) | state | gw_median, n_nearest | TO BE DEFINED |
| SE1 | GCM exclusion (drop one, drop UKESM+IPSL) | w3_gcm_exclusion, w3_gcm_exclusion_contrast, w3_gcm_exclusion_rank | exclusion | pct_median, diff_median, sign_changed, order | TO BE DEFINED |
| SE2 | Threshold, weight, TX40 | w3_heat_sensitivity, w3_tx40_curves | choice | diff_median_pp, pct_median | TO BE DEFINED |
| SE3 | Null type and block size | w4_null_rates | null, block_months | pct_rd_ge | TO BE DEFINED |
| SE4 | Cuts of the classes, percentiles | w5_sensitivity (planned) | family | delta_pp | TO BE DEFINED |
| VA1 | ONS national validation | validation | region = Brazil | rho, rho_ci_low, rho_ci_high, n_years | TO BE DEFINED |

### I. Results map (v2.1)
| Item | Content | Source | Blocking |
|---|---|---|---|
| Fig 1 | Fleet and capacity by technology and fuel | plant_units | none |
| Fig 2 | Heat level class map (cells, plants sized by GW) | w3g_heat_cell_class | W3g |
| Fig 3 | Threshold curves, operating vs planned | w3_curves_plot | none |
| Fig 4 | Drought level class map, SPEI and SPI | w4g tables | W4g, O18 |
| Fig 5 | Excess over the null by scenario, GCM range | W4b table | W4b, O20, O21 |
| Fig 6 | Co-located exposure map and cross-tab | w4h_coexposure | W4h, O32 |
| Table 1 | GW exposed by technology, fuel, scenario | w3_table1 | none |
| Table 2 | Leave-one-out, 5 largest hydro | W4d table | W4d, O19 |
| Table 3 | 4 x 4 cross-tab, GW | w4h_coexposure | W4h |
| Supplementary | ONS validation | validation | none |