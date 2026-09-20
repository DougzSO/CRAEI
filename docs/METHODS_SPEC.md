# Design: Water and Heat Hazards to Hydro and Thermal Power Fleets in Brazil, India and Portugal

Working title: *Compounding drought and heat threaten the backup logic of hydro-thermal power systems*

Target: Nature Climate Change (Article). Fallback venues if desk-rejected: Nature Communications, Environmental Research Letters.

---

## 0. Design position and reviewer risks (read first)

**Core position.** The study becomes an asset-level assessment of how climate change alters the frequency of drought and extreme heat at hydro and thermal power plants, with two system-level findings as the headline: (i) the change in the joint occurrence of hydro drought and thermal heat stress in the same month, which is when thermal backup is most needed and least reliable, and (ii) how much of the planned pipeline is being sited into worsening conditions. Per-hazard exposure maps support these findings; they are not the headline.

**Main reviewer risks, in order of severity.**

1. *Novelty against published NCC work.* van Vliet et al. (2016, NCC) already assessed hydro and thermal vulnerability globally with physically based hydrological and water temperature models. An index-based design is methodologically simpler than that precedent in the same journal. Novelty must come from asset resolution (thousands of plants, three contrasting systems), the compound hydro-drought/thermal-heat metric, the planned-pipeline lock-in analysis, and an out-of-sample check against observed hydro inflow. Without the compound and pipeline results, this is an ERL-level paper.
2. *Weak causal link from index to operational impact.* Thresholds such as TX35 are climatological indices, not plant operating limits. The text must describe hazard exposure and its change, never "generation loss", unless validated.
3. *Cooling technology unknown.* Handled with two explicit bounds (Section 1.2), declared as a limitation.
4. *Small ensemble with two high-sensitivity models.* Handled with median, full range and a hot-model exclusion test.
5. *Validation only possible for hydro in Brazil and Portugal.* India remains unvalidated; this is stated, not hidden.

**Decisions that break with the previous framework.**

- The existing 9.3 GB of processed rasters are not used. They carry the self-referential baseline and a 1 km resampling of ~100 km model output that implies resolution the data does not have.
- The raw CMIP6 GFDL-ESM4/MIROC6 files are superseded by ISIMIP3b bias-adjusted data, which includes the historical period, tasmin for every model-scenario pair, and five GCMs in one consistent product. A new download was unavoidable in any case, because fixing the baseline requires historical simulations.
- Wind power is excluded from the hazard assessment; solar PV moves to Supplementary Information (justification in Section 6, Q1).
- No composite score, no weights, no normalization to 0-1.
- ERA5 gusts and IBTrACS are not used. Note: 127,245 IBTrACS records attributed to Portugal is not physically plausible for a country with almost no tropical cyclone landfalls; the country filter probably used a bounding box capturing North Atlantic tracks.

---

## 1. Methods

### 1.1 Study domain

Brazil, India and Portugal represent three power-system archetypes under contrasting climates: a hydro-dominated interconnected system with thermal backup (Brazil, tropical), a coal-dominated thermal system under monsoon variability (India), and a high renewable-share Mediterranean system balanced by hydro and gas (Portugal). This framing gives the country selection a mechanistic rationale beyond climatic contrast, since the compound metric (Section 1.6) tests the hydro-thermal complementarity each system relies on to a different degree.

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

Plants are assigned to the nearest 0.5° land cell. For hydro plants, the upstream catchment is built from HydroBASINS level 6 by recursively following the `NEXT_DOWN` topology from the sub-basin containing the plant; climate variables are area-weighted over all grid cells intersecting the catchment before computing indices.

### 1.4 Hazard definitions

**H1. Extreme heat (thermal plants; solar in SI).** Annual count of days with daily maximum temperature at or above 35 °C and 40 °C:

TX35 = (1/30) Σ_y Σ_d 1[TX_{y,d} ≥ 35 °C], and analogously TX40.

The change metric is ΔTX35 = TX35_future − TX35_baseline (days yr⁻¹). A difference is used instead of a ratio because baselines are zero in many cells. TX35 and TX40 are indices published in the IPCC AR6 Interactive Atlas; they are used as indicators of cooling-relevant heat, not as operating limits. The headline exposure class is ΔTX35 ≥ 30 days yr⁻¹ (about one additional month of such days; tier 3, tested at 15 and 60).

**H2. Drought (hydro at catchment scale; water-dependent thermal at cell scale).** Standardized Precipitation Evapotranspiration Index at 12-month accumulation (SPEI-12), with potential evapotranspiration from Hargreaves-Samani:

PET_d = 0.0023 × 0.408 × Ra_d × (T̄_d + 17.8) × (TX_d − TN_d)^0.5,  T̄_d = (TX_d + TN_d)/2

where Ra is extraterrestrial radiation (MJ m⁻² d⁻¹; FAO-56, Eq. 21) and 0.408 converts to mm d⁻¹. The monthly water balance D_m = P_m − PET_m is accumulated over 12 months and fitted per calendar month with a three-parameter log-logistic distribution on 1985-2014; the fitted parameters transform both periods. Values are clipped to [−3, 3]. Severe drought frequency is

F_D = fraction of months with SPEI-12 ≤ −1.5,

which is close to 6.7% in the baseline by construction (standard normal probability below −1.5). The change metric is the ratio R_D = F_D,future / F_D,baseline. The headline exposure class is R_D ≥ 2 (severe drought at least twice as frequent; tier 3, tested at 1.5 and 3). For run-of-river plants SPEI-3 is also reported. Hargreaves was chosen over Thornthwaite because Thornthwaite is known to overstate drying under warming, and over Penman-Monteith for simplicity; SPI-12 (precipitation only) is reported as the lower bound that ignores atmospheric demand.

**H3. Chronic water stress (water-dependent thermal, freshwater bound only).** WRI Aqueduct 4.0, keyed by HydroBASINS `pfaf_id`, for the baseline and for 2050 under the optimistic, business-as-usual and pessimistic scenarios, mapped to SSP1-2.6, SSP3-7.0 and SSP5-8.5. Aqueduct 4.0 splits the indicator across two collections with different field names: the baseline collection (`baseline_annual`) exposes `bws` (baseline water stress); the 2050 projections (`future_annual`) expose `ws` (water stress) under each `{bau|opt|pes}{30|50|80}` scenario/horizon code. Both are the same underlying stress ratio (withdrawal over available supply) on the same 0-5 category scale; the field renaming between collections is WRI's own convention, not a methodological difference. Aqueduct categories are used as published: low (<10%), low-medium (10-20%), medium-high (20-40%), high (40-80%), extremely high (>80%). Exposure is capacity in high or extremely high stress. H3 is reported separately from H1 and H2 because Aqueduct uses its own climate and socioeconomic forcing and is not consistent with the ISIMIP3b ensemble. Aqueduct's future-annual values are themselves the median of an internal 5-GCM ensemble distinct from this project's ISIMIP3b ensemble, with no per-model breakdown available (L13).

**H4. Extreme precipitation (Supplementary Information, all fleets).** Wet-day 95th percentile (days ≥1 mm) estimated on the baseline per cell and model; change metric is the ratio of exceedance frequency (baseline 5% of wet days by construction) and the percentage change in mean annual Rx5day. Reported as a change in flood-forcing precipitation, not as flood risk.

**Solar PV (Supplementary Information).** Peak-hour temperature loss L = γ × max(0, TX + 31.25 − 25), with γ = 0.4% °C⁻¹ (typical crystalline silicon; verify against datasheet range) and 31.25 °C the cell-to-air difference from NOCT = 45 °C at 1000 W m⁻². Because L is linear in TX above the threshold, ΔL mainly reflects warming; it is included to document that heat-driven PV losses are small compared with thermal and hydro hazards, not as a finding in itself.

**Excluded hazards.** Extreme wind is excluded for three reasons: 10 m gusts are not comparable with IEC 61400-1 design winds (50-year 10-minute reference speeds of 50, 42.5 and 37.5 m s⁻¹ at hub height for classes I-III), which are rarely approached outside tropical cyclone tracks; confidence in projected extreme wind change is low in IPCC AR6; and GCM resolution does not capture the relevant extremes. Riverine and coastal flooding, sea-level rise and wildfire are outside the scope.

### 1.5 Exposure assessment

Hazards are never combined into a single score. For country c, technology t, hazard h, scenario s and model k, capacity exposure is

E_{c,t,h,s,k} = Σ_{i∈(c,t)} Cap_i × 1[Δ_{i,h,s,k} ≥ τ_h] / Σ_{i∈(c,t)} Cap_i,

reported both as a share and in GW. Model agreement is defined as at least four of five GCMs projecting a change of the same sign (ΔTX35 > 0; R_D > 1). Ensemble results are the median across models with the full model range.

### 1.6 Compound hydro-drought and thermal-heat metric

For each country, model and period, two monthly national series are built:

S_hydro(m) = Σ_{i∈hydro} Cap_i × 1[SPEI-12_i(m) ≤ −1.5] / Σ Cap_i (share of hydro capacity in severe drought)

H_thermal(m) = Σ_{j∈thermal} Cap_j × N35_j(m) / Σ Cap_j (capacity-weighted number of TX35 days in the month)

A compound month occurs when both series exceed their own 90th percentile estimated on 1985-2014 of the same model (if the S_hydro percentile is zero, any value above zero qualifies). Under independence the baseline frequency is about 1%; the metric is the future-to-baseline likelihood ratio LR_C = F_C,future / F_C,baseline. The national aggregation is justified by interconnection in Brazil (SIN) and India (national grid) and by Iberian market coupling for Portugal.

### 1.7 Validation

Validation targets the one sector with open observed response data. SPEI-12 is computed from W5E5 observations (1985-2019) with the same procedure and aggregated to hydro-capacity-weighted series for the four Brazilian subsystems and for Portugal. These are compared with annual natural energy inflow (ENA) from the Brazilian system operator (ONS) and with the hydro productivity index published by the Portuguese transmission operator (REN). Statistics: Spearman correlation with 3-year block bootstrap confidence intervals, and the odds ratio of a bottom-tercile inflow year given December SPEI-12 ≤ −1. Short records produce wide intervals, which are reported as such. W5E5 is derived from ERA5, so a comparison of hazard climatology against ERA5 would not be independent and is not used as validation. EM-DAT is used only descriptively in Supplementary Information. India is not validated, which is stated as a limitation.

### 1.8 Uncertainty

Uncertainty is reported through (i) scenario spread, (ii) inter-model range and agreement, and (iii) one-at-a-time tests of each discrete choice: heat class (15/30/60 days), drought class (R_D 1.5/2/3), SPEI threshold (−1.0/−1.5/−2.0), PET formulation (SPEI Hargreaves vs SPI), coastal cooling distance (2/5/10 km), and exclusion of UKESM1-0-LL (highest climate sensitivity in the ensemble). A global variance-based analysis (Sobol) is not used because the design has few discrete choices whose individual effects are more informative when shown directly.

---

## 2. Results

Numbers in brackets are placeholders to be filled from the pipeline. No value below is a prediction. Where a baseline value follows from construction, it is stated.

### 2.1 Overview

The operating fleet comprises [N_hydro] hydro plants ([X] GW) and [N_thermal] thermal plants ([Y] GW) across Brazil, India and Portugal, of which [Z] GW are water-dependent thermal and [W]% of that capacity lies within 5 km of the coast. The planned fleet adds [P_adv] GW in advanced stages and [P_early] GW in early stages for hydro and thermal.

Interpretation to write: the three systems differ in how much of their firm capacity depends on water (hydro plus freshwater-cooled thermal), which sets up the compound analysis.

### 2.2 Result 1: Heat and drought exposure of the operating fleet

`[FIGURE 1: Plant-level maps of ΔTX35 at thermal plants and R_D at hydro plants, SSP3-7.0, ensemble median; hollow markers where fewer than 4 of 5 GCMs agree; three country panels]`

`[FIGURE 2: Share of capacity in the headline exposure classes by country, technology and SSP; bars = ensemble median, whiskers = model range]`

Expected content: [A]% of thermal capacity ([A_GW] GW) crosses ΔTX35 ≥ 30 days yr⁻¹ under SSP3-7.0 (range [a1-a2]%), and [B]% of hydro capacity faces at least a doubling of severe drought frequency (R_D ≥ 2). Baseline severe drought frequency is ~6.7% of months by construction, so R_D = 2 means ~13% of months.

Hypotheses to test, with what would falsify them:

- Warming-driven heat exposure grows consistently across models for the Indian thermal fleet. Falsified if model agreement is below 4/5 over most Indian thermal capacity.
- Drought signal at hydro catchments is less consistent across models than heat, especially where precipitation projections diverge (e.g. parts of Brazil). If agreement is low, the finding becomes "drought exposure is uncertain in sign" and is still reportable, since that uncertainty matters for hydro-dependent planning.
- Portugal shows high drought ratios under all scenarios, consistent with Mediterranean drying. Falsified if R_D < 1.5 across most models.
- SSP differences at mid-century are smaller than model spread. This is the likely outcome for 2041-2070 and should be reported directly rather than framed as a scenario result.

For water stress (H3), report [C] GW of water-dependent thermal capacity in high or extremely high bws in 2050 under the upper bound and [C_low] GW under the coastal lower bound. The gap between the two bounds is itself a result: it quantifies how much the unknown cooling technology matters.

### 2.3 Result 2: More frequent coincidence of hydro drought and thermal heat

`[FIGURE 3: Likelihood ratio of compound months (LR_C) by country and SSP, with individual model points; inset: seasonal distribution of compound months, baseline vs future]`

Expected content: baseline compound frequency ~1% of months under independence (to be compared with the empirical baseline, which may be higher if drought and heat co-vary). Future LR_C of [D] in Brazil, [E] in India, [F] in Portugal under SSP3-7.0.

Interpretation to write: an LR_C well above 1 means that the months with the largest share of hydro capacity in drought increasingly coincide with the months of highest heat stress on thermal plants, weakening the assumption that thermal backup compensates for low hydro output. If LR_C is near 1 in a country, the implication is that hydro-thermal complementarity is preserved there, which is also a useful result. The Brazil case can be connected qualitatively to the 2021 water crisis, without claiming attribution.

### 2.4 Result 3: The planned pipeline and future hazard

`[FIGURE 4: For each country, share of operating vs planned (advanced, early) hydro and thermal capacity in the headline exposure classes, SSP3-7.0; model range as whiskers]`

Expected content: [G]% of advanced-stage planned thermal capacity and [H]% of planned hydro capacity lie in locations meeting the headline classes, compared with [G0]% and [H0]% of the operating fleet.

Interpretation to write: if the planned share exceeds the operating share, new investment is being directed toward worsening conditions, locking in exposure for plant lifetimes that extend well past 2050. If the shares are similar or lower, siting is neutral or favourable to adaptation. Either outcome answers a question relevant to planners.

### 2.5 Validation

`[FIGURE 5: Observed hydro-capacity-weighted SPEI-12 (W5E5) vs annual inflow indicators: Brazil subsystems (ONS ENA) and Portugal (REN hydro productivity index); time series and scatter with Spearman ρ and 95% CI]`

Expected content: Spearman ρ of [ρ_BR_SE] (Southeast/Centre-West), [ρ_BR_S], [ρ_BR_NE], [ρ_BR_N], [ρ_PT], with odds ratios for low-inflow years. A moderate to strong positive correlation supports SPEI-12 as a proxy for hydro water availability. Weak correlation in regulated or cascade-dominated subsystems should be reported and discussed as a limit of a climate-only index.

### 2.6 Sensitivity

`[EXTENDED DATA FIGURE: Headline numbers (Results 1-3) under each one-at-a-time alternative]`

Report whether the ranking of countries and technologies changes under any alternative. The key statement for the main text is whether the direction of the compound and pipeline findings survives all tests, including exclusion of UKESM1-0-LL and replacement of SPEI by SPI.

---

## 3. Technical pipeline

Compute estimates assume a recent laptop or workstation (8+ cores, 32 GB RAM), excluding download time. They are rough estimates.

**Step 1. Plant inventory**
Input: GEM tracker CSV; Natural Earth 10m coastline.
Processing: filter countries and statuses; aggregate units to plants; assign technology class and water dependence; compute distance to coast (projected CRS per country); flag coastal plants at 2/5/10 km.
Output: `plants.parquet` (plant_uid, country, fleet [operating/planned_adv/planned_early], tech_class, water_dependent [bool], hydro_type, capacity_mw, lat, lon, dist_coast_km).
Time: 0.5 h.

**Step 2. Climate data acquisition**
Input: ISIMIP repository.
Processing: download bounding-box cutouts for 5 GCMs × {historical, ssp126, ssp370, ssp585} × {tasmax, tasmin, pr}, keeping files overlapping 1984-2014 and 2041-2070; W5E5 observations 1984-2019 for the same variables.
Output: `data/isimip/{model}/{scenario}/{var}_{country}_{decade}.nc`; `data/w5e5/{var}_{country}_{decade}.nc`; checksum manifest.
Time: compute negligible; download depends on server queue (hours to days).

**Step 3. Spatial mapping**
Input: `plants.parquet`; HydroBASINS level 6; one ISIMIP grid template.
Processing: nearest land cell per plant; for hydro, sub-basin containing the plant and upstream set via `NEXT_DOWN` traversal; area weights of grid cells intersecting each catchment.
Output: `plant_cell.parquet` (plant_uid, cell_lat, cell_lon, dist_to_cell_km); `catchment_weights.parquet` (plant_uid, cell_lat, cell_lon, weight).
Time: 1-2 h.

**Step 4. Daily temperature and precipitation indices**
Input: ISIMIP cutouts; unique cells from Step 3.
Processing: for each model and period, per cell: annual TX35, TX40; monthly N35; wet-day P95 (baseline) and exceedance counts in both periods; annual Rx5day.
Output: `indices_daily.parquet` (cell_lat, cell_lon, model, scenario, period, index, year, month [nullable], value).
Time: 2-4 h.

**Step 5. PET and water balance**
Input: ISIMIP tasmax, tasmin, pr; W5E5 for validation.
Processing: daily Ra from latitude and day of year; Hargreaves PET; monthly P, PET, D; catchment-averaged D for hydro plants using weights from Step 3.
Output: `water_balance_cell.parquet`, `water_balance_catchment.parquet` (id, model, scenario, month, P, PET, D).
Time: 1-2 h.

**Step 6. SPEI and SPI**
Input: Step 5 outputs.
Processing: 12-month and 3-month accumulation; log-logistic fit per calendar month on 1985-2014 per model (xclim standardized index functions with a calibration period, or explicit fit with scipy); apply the same parameters to 2041-2070; clip to [−3, 3]; SPI with gamma distribution. Future series start in December 2041 because 2031-2040 is not downloaded; state this in Methods.
Output: `spei.parquet` (id, model, scenario, month, spei12, spei3, spi12).
Time: 1-2 h.

**Step 7. Plant-level hazard table**
Input: Steps 3-6.
Processing: join indices to plants; compute ΔTX35, ΔTX40, F_D, R_D, R95 ratio, ΔRx5day per plant, model, scenario.
Output: `plant_hazards.parquet` (plant_uid, model, scenario, hazard, baseline_value, future_value, delta, ratio).
Time: 0.5 h.

**Step 8. Aqueduct water stress**
Input: Aqueduct 4.0 `future_annual` `ws` (2050, 3 scenarios; local export present, `pfaf_id`-keyed) and `baseline_annual` `bws` (not yet exported — see DECISIONS.md D32).
Processing: join to water-dependent thermal plants by catchment `pfaf_id`; categories.
Output: `plant_aqueduct.parquet` (plant_uid, scenario, ws_value, ws_category) for the join skeleton; baseline columns added once D32 is resolved.
Time: 0.5 h.

**Step 9. Exposure aggregation and agreement**
Input: Steps 1, 7, 8.
Processing: capacity shares and GW above headline classes per country × technology × fleet × scenario × model; ensemble median and range; model agreement flags per plant.
Output: `exposure_summary.csv` (country, tech_class, fleet, hazard, scenario, cooling_bound, median_share, min_share, max_share, median_gw, agreement_share).
Time: 0.5 h.

**Step 10. Compound metric**
Input: `spei.parquet`, monthly N35, plants.
Processing: national monthly S_hydro and H_thermal; baseline P90 per model; compound months; LR_C per country, scenario, model.
Output: `compound.csv` (country, scenario, model, f_baseline, f_future, lr_c); `compound_months.parquet` for seasonal inset.
Time: 0.5 h.

**Step 11. Validation**
Input: W5E5 SPEI (Step 6 applied to observations); ONS ENA; REN productivity index; plants.
Processing: hydro-capacity-weighted annual SPEI-12 per subsystem and Portugal; Spearman ρ with block bootstrap; odds ratio for low-inflow years.
Output: `validation.csv` (region, n_years, rho, rho_ci_low, rho_ci_high, odds_ratio, or_ci_low, or_ci_high).
Time: 1 h.

**Step 12. Sensitivity and figures**
Input: all previous outputs.
Processing: rerun Steps 9-10 under each alternative; generate figures.
Output: `sensitivity.csv` (test, parameter_value, result_id, value); figure files.
Time: 2-3 h.

Total compute: roughly 11-18 h, within the 24 h constraint.

---

## 4. Main figures

**Figure 1. Where heat and drought exposure increases.**
Type: plant-level maps, three country panels, two layers (thermal ΔTX35, hydro R_D), SSP3-7.0 median, hollow markers for low agreement.
Data: Steps 7 and 9.
Message: the spatial pattern of exposure change across the operating fleet and where models agree.

**Figure 2. Which fleets carry the exposure.**
Type: grouped bars with model-range whiskers, by country × technology × SSP; freshwater upper and coastal lower bound shown for thermal.
Data: Step 9.
Message: magnitude of capacity affected, differences between systems, and the size of cooling and model uncertainty relative to scenario differences.

**Figure 3. Hydro drought and thermal heat increasingly coincide.**
Type: dot plot of LR_C per model with median, by country and SSP; seasonal inset.
Data: Step 10.
Message: the central system-level finding on the reliability of thermal backup.

**Figure 4. New capacity is sited into [worsening/similar] conditions.**
Type: paired bars, operating vs planned (advanced, early), by country and technology.
Data: Step 9 (planned fleet).
Message: lock-in of exposure through current investment decisions.

**Figure 5. Observed drought index tracks hydro inflow.**
Type: time series and scatter panels for Brazilian subsystems and Portugal.
Data: Step 11.
Message: SPEI-12 at catchment scale is a meaningful proxy for the hydro hazard.

Extended Data (not main): sensitivity summary (Step 12), extreme precipitation (H4), solar PV temperature loss, EM-DAT descriptive overlay.

---

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

## 6. Design decisions

**Q1. Which hazards?**
Main text: extreme heat (H1), drought (H2), chronic water stress (H3). Supplementary: extreme precipitation (H4), solar PV temperature loss. Excluded: extreme wind, cyclones, flooding, sea-level rise, wildfire.
Why: these three hazards have established physical mechanisms for hydro and thermal generation (water availability and cooling efficiency) and can be computed consistently from the same bias-adjusted ensemble (H1, H2). Wind power is removed because its main climate sensitivities (resource change and acute storms) cannot be assessed with standard indices from GCM output with acceptable confidence, and assigning it heat as a proxy mechanism would not survive review. Keeping wind in the headline with an inappropriate hazard would weaken the paper more than excluding it with a stated reason. Solar goes to SI because its heat sensitivity is small and would dilute the main message.

**Q2. Baseline?**
Model historical simulations (1985-2014) from ISIMIP3b, not ERA5. ERA5 alone cannot fix the problem: comparing a raw GCM future with a reanalysis baseline mixes model bias with climate signal. Using each model's own historical run removes the self-referential calibration; using the bias-adjusted product makes absolute thresholds comparable across models. W5E5 observations are used only for validation.

**Q3. Ensemble?**
Five GCMs (ISIMIP3b primary set). Two models are not enough for NCC, and the previous pair covered only the low end of climate sensitivity. There is no defensible way to project SSP-specific hazard change without GCM output. The rework problem came from processing raw CMIP6 files model by model; a pre-processed, bias-adjusted ensemble with a single access API removes most of that. Because two of the five models have high climate sensitivity, results are reported as median and full range, with a test excluding UKESM1-0-LL.

**Q4. Risk index?**
Option A (per-hazard exposure), with the compound metric as the only multi-hazard construct. A weighted composite score (B) requires weights with no empirical basis and invites the first reviewer objection; a multidimensional classification (C) adds complexity without a clear interpretation. The compound metric is a better multi-hazard result because it has a physical meaning at system level.

**Q5. Validation?**
Option B, limited to hydro in Brazil and Portugal, against observed inflow indicators. EM-DAT and IBTrACS correlations (A) do not validate plant-level hazard: EM-DAT records human impacts at coarse locations and has no power-sector outcome. A predictive model (C) is beyond scope and would need plant-level generation data unavailable for India.

**Q6. Priority of analyses for the main text.**
1. Technology analysis combined with geographic hotspots (Figures 1-2).
2. Compound hydro-drought/thermal-heat metric (Figure 3), which is not in the original list but is the strongest candidate for NCC novelty.
3. Planned pipeline exposure (Figure 4), also new.
4. GCM spread and agreement, integrated into every figure rather than shown separately.
5. SSP comparison, integrated into Figures 2-4; at 2041-2070 scenario differences are expected to be smaller than model spread, so it cannot be the headline.
6. Parametric sensitivity as one-at-a-time tests in Extended Data; Sobol/Monte Carlo is not used.
7. Additional horizons (2030, 2070): dropped. They multiply downloads and figures without changing the argument.

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
