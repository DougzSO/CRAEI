# Methods (draft)

Status: draft for the author (Phase W). Sources: docs/METHODS_SPEC.md (section numbers in brackets), docs/article/E1_spec.md,
docs/article/text_snippets.md (null model A3, thermal population O48), docs/DECISIONS.md (D-ids in brackets). Method
parameters (thresholds, windows, pool sizes, draws) are specification values and cite their source; population counts
and every result number are register rows [R..] of docs/article/DECISION_MEMO_F5.md. Reference slots are
[CIT-NEEDED: topic]; names after "suggest" come from docs/ and must be verified by the author.

---

## 2.1 Design

We assess two climate hazards at the plant locations of the Brazilian power fleet: extreme heat for thermal plants and
drought for hydropower and water-dependent thermal plants. Each hazard is reported on its own; no composite index is
built [METHODS_SPEC 4, 11]. We then ask where the two hazards coincide in space, whether drought in the hydropower
catchments coincides in time with drought or heat at the thermal plants (analysis E1), and whether the drought index
tracks observed natural inflow (analysis E3). The study covers Brazil only. [AUTHOR: one sentence on why Brazil and why
a hydro-thermal system is the right test case.]

## 2.2 Power plant inventory and populations

Plants come from the Global Energy Monitor Global Integrated Power Tracker, snapshot of 9 August 2026 [METHODS_SPEC 2]
[CIT-NEEDED: Global Energy Monitor, Global Integrated Power Tracker]. Units are grouped into plants by a stable identifier
(hash of name, latitude and longitude) and capacity is summed from the unit table [D77, D78]. The operating fleet
contains the units in operation; the planned fleet contains the units under construction, in pre-construction and
announced. Shelved, cancelled, mothballed and retired units are excluded. Thermal plants are classified by fuel (coal,
gas, oil, multi-fuel, nuclear, bioenergy) and by cooling dependence. Water-dependent plants are steam, combined-cycle,
nuclear and bioenergy plants; open-cycle turbines and engines are treated as air-cooled and receive the heat hazard only.
GEM has no cooling field, so the classification rests on technology and is an upper bound for water dependence
[METHODS_SPEC 2]. A plant belongs to the water-dependent population when its plant-level class is water-dependent; five
plants with some water-dependent units but an air-cooled plant-level class are treated as air-cooled [D151, O48].
Hydropower is counted with Itaipu at its Brazilian share of 7,000 MW (version b) in every headline result; the binational
14,000 MW asset (version a) is a sensitivity [D82, D102]. The populations are 194 operating hydropower plants and 618
operating water-dependent thermal plants; Table 1 gives capacity and counts by technology and fuel [R27]. [AUTHOR: justification of the cooling classification and its limits.]

## 2.3 Climate data

Daily maximum and minimum temperature and precipitation come from the ISIMIP3b bias-adjusted input data at 0.5 degrees
for five GCMs (GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL) [METHODS_SPEC 3] [CIT-NEEDED: ISIMIP3b
protocol; suggest Frieler et al. 2021, verify]. ISIMIP bias-adjusted the models against W5E5 v2.0 with ISIMIP3BASD
[CIT-NEEDED: ISIMIP3BASD; suggest Lange 2019, verify] [CIT-NEEDED: W5E5; suggest Cucchi et al. 2020 and Lange et al.
2021, verify]. The baseline is each model's historical run, 1985-2014; the future is 2041-2070 under SSP1-2.6, SSP3-7.0 and
SSP5-8.5. Baseline statistics (thresholds, distribution parameters) are estimated on the baseline of each model and applied
unchanged to its future; no statistic is fitted on the series it classifies. Each plant is assigned to the nearest 0.5-degree
land cell. For hydropower, the upstream catchment is built from HydroBASINS level 6 and climate is area-weighted over its
cells [CIT-NEEDED: HydroBASINS; suggest Lehner and Grill 2013, verify]. Observed forcing for E1 and E3 is W5E5 v2.0
over 1985-2014 (E1) and 1984-2019 (E3). [AUTHOR: whether the claim that the five GCMs span the CMIP6 sensitivity range is
kept; it is not verified in this project, O33.] [CIT-NEEDED: CMIP6 climate sensitivity of the five GCMs]

## 2.4 Heat hazard (H1)

H1 is defined for thermal plants. For each plant cell we count the days per year with maximum temperature at or above
35 degC (TX35), averaged over 30 years. The change is the difference between future and baseline, because baselines are zero
in many cells [METHODS_SPEC 4.1]. The headline change class is an increase of at least 30 days per year, tested on a grid
of 10 to 100 days [D87]. We also classify the future TX35 level as low (< 10 days), medium (10 to < 30), high (30 to < 60)
and extreme (>= 60) [METHODS_SPEC 5]. TX35 is an indicator of cooling-relevant heat, not an operating limit
[METHODS_SPEC 4.1]. Hydropower is outside H1 by design [D88]; its plant-cell TX35 appears only as regional climatic
context in the co-exposure analysis. [AUTHOR: motivation for 35 degC; link to thermal efficiency and cooling derating.]
[CIT-NEEDED: heat effects on thermal plant output and cooling]

## 2.5 Drought hazard (H2) and exposure

Drought is the 12-month Standardized Precipitation Evapotranspiration Index (SPEI-12) [CIT-NEEDED: SPEI; suggest
Vicente-Serrano et al. 2010, verify]. Potential evapotranspiration follows Hargreaves and Samani from daily temperature
[CIT-NEEDED: Hargreaves and Samani 1985, verify] with FAO-56 extraterrestrial radiation [CIT-NEEDED: FAO-56]. The monthly
water balance is accumulated over 12 months and fitted with a three-parameter log-logistic distribution by probability
weighted moments on the 1985-2014 baseline of each series, with a Pearson type III fallback where the fit does not
converge [METHODS_SPEC 4.2, Appendix B]. Values are clipped to [-3, 3]. Hydropower is evaluated at the catchment, water-
dependent thermal plants at the plant cell. Severe drought frequency F_D is the fraction of months with SPEI-12 <= -1.5.
The change metric is R_D = F_D(future) / F_D(baseline), and a plant is exposed when R_D >= 2, tested at 1.5 and 3. The
exposure of a fleet is the share of its operating capacity that is exposed, with the median and range over the five GCMs.
We repeat the analysis with the 12-month Standardized Precipitation Index (SPI-12), which ignores evaporative demand, to
separate the precipitation signal from the Hargreaves temperature term [METHODS_SPEC 4.2]. Because the Hargreaves
formulation depends on temperature, SPEI results are read with the SPI comparison next to them. [AUTHOR: PET-based
indices and warming-driven drying; literature.] [CIT-NEEDED: PET-based drought indices overstate drying; suggest Milly and
Dunne 2016, verify]

## 2.6 Stationary resampling null

Observed exposure is compared with a stationary null with no trend and no pairing between baseline and future. We draw
2,000 pairs of synthetic 360-month SPEI-12 series: each member of a pair is one series picked at random from the pool (all
catchments for hydropower, all cells for water-dependent thermal plants, times five GCMs, baseline 1985-2014) and resampled
in contiguous 12-month blocks. Baseline and future are therefore independent draws from random locations and GCMs, whereas
the observed data pair both periods within the same plant and GCM. A pair is exposed when the frequency of months with
SPEI <= -1.5 at least doubles (R_D >= 2). The pools hold 1,110 (hydropower) and 1,705 (thermal) series; the null rates are
18.88% and 17.74% for SPEI-12 and 20.47% and 17.84% for SPI-12. Excess exposure is the observed share of operating capacity
with R_D >= 2 minus the null rate, in percentage points [D83, D102, D125, D138; text_snippets.md A3]. Block lengths of 24,
36 and 60 months are sensitivities; the null rate is not monotonic in block length [D102]. [CIT-NEEDED: moving-block
bootstrap] [AUTHOR: why a stationary resampling null rather than the baseline itself, in one or two sentences; the baseline
is calibrated to the same fixed drought frequency by construction, METHODS_SPEC 4.2.]

## 2.7 Co-located heat and drought exposure

We classify each plant by the future TX35 level (above) and by the future F_D against the percentiles of the null (low <=
p50, medium p50 to p90, high p90 to p99, extreme > p99) and cross-tabulate the two classes in GW, per GCM and scenario, with
the same GCM supplying both hazards [METHODS_SPEC 5, 7]. The headline cell is extreme heat and extreme drought. The
analysis shows spatial coincidence at the plant, not simultaneity in time. For hydropower, heat is regional climatic
context at the plant cell and not a hazard to the plant (H1 stays thermal) [D88, D139]. For water-dependent thermal plants
the drought classes use the cut points of the W4g reference pool (1,710 series, unit-level population) applied to the
plant-level population [D151]. State results assign plants to administrative states by spatial join (nearest polygon
when a point falls outside) and report, for each state, the share of the state's own operating capacity and the GW in the
headline cell [D100, D149]. Cross-tab means over the five GCMs add up to the fleet total, whereas medians do not [D137].

## 2.8 Hydrothermal hedge failure (E1)

E1 asks whether water-dependent thermal capacity is under stress more often than expected under independence in months of
hydropower drought, and whether this rises from the baseline to the future [E1_spec.md]. The criterion below was fixed
before any E1 result [D140].

*Series.* For each GCM, H is the capacity share of operating hydropower with SPI-12 <= -1.5 each month. T is the capacity
share of operating water-dependent thermal plants in one of three states: SPI-12 <= -1.5 at the plant cell (control
channel), N35 above the local baseline P90 of monthly hot days (heat channel), or SPEI-12 <= -1.5 (upper bound, because it
shares the temperature term with the heat channel). The control pair is H and T both defined with SPI-12.

*Events and metrics.* An event is a month in which the series exceeds a threshold q. Variant A uses q = P90 of the baseline
series and applies it to baseline and future; variant B uses the P90 of each period. With P(H), P(T) and P(H and T) the
event frequencies, D = P(H and T) / (P(H) P(T)) is the dependence and 1 means independence. Variant A gives the change in
P(H and T), dP; it is split exactly into a marginal part, the change in P(H) P(T), and a dependence part, the change in
P(H and T) - P(H) P(T). Variant B gives the change in D (dD). Future series use 2042-2070 because the first 11 SPEI-12
months are undefined; the observed series use 1986-2014 for the same reason [D141].

*Observed check.* We compute the same metrics from W5E5 with the thermal cell and hydropower catchment series of the
fleet, using the series' own P90, and show them beside the five GCM baselines. Intervals are 95% percentile intervals of a
moving-block bootstrap (12 months; 24 and 36 as sensitivities; 2,000 draws; fixed seed). The test of D > 1 shifts one series
circularly against the other by a random lag [D141].

*Co-location.* We repeat the control-pair D with the thermal capacity restricted to one macro-region against national
hydropower; macro-regions are the five IBGE regions [D143].

*Pre-specified criterion.* The primary signal criterion is met when P(H and T) in the control pair under variant A rises from
baseline to future in at least four of five GCMs under both SSP3-7.0 and SSP5-8.5. Reinforcing evidence, not a condition, is
dD > 0 in at least four of five GCMs and an observed D > 1 with a bootstrap interval that excludes 1 [D140, D142].

## 2.9 Association with natural inflow (E3)

E3 compares the hydropower-weighted W5E5 SPEI-12 of each region with the monthly natural inflow energy (ENA bruta) of the
National Electric System Operator (ONS), 2000-2019 (240 months) [D144] [CIT-NEEDED: ONS ENA data]. The inflow is
standardized by calendar month. Regions are the macro-regions, which approximate the ONS submarkets (Southeast plus
Center-West for the ONS SE/CO subsystem, South, Northeast, North). We report Spearman correlation for lags of 0 to 6 months
(SPEI at t - L, ENA at t) with a 12-month moving-block bootstrap interval, all lags, none selected afterwards. The criterion
fixed before the computation sends E3 to the main text if the SE/CO correlation has an interval that excludes zero for at
least one lag from 0 to 3 [D144]. The hit-rate analysis, also pre-specified [D146], takes an ENA drought month as an anomaly
at or below the 20th percentile of its calendar month and a signal as SPEI-12 <= -1.5. We report the lift of
P(event | signal) over the 20% base rate, the probability of detection and the Heidke skill score, with bootstrap intervals;
regions with fewer than ten signal months are not reportable [CIT-NEEDED: Heidke skill score]. [AUTHOR: why ENA is the
closest observed counterpart available and what it omits (reservoir operation).]

## 2.10 Agreement, sensitivities and robustness

Results are medians over the five GCMs with the full range; the range is the spread of five deterministic runs, not a
confidence interval [METHODS_SPEC 9, D85]. Agreement k/5 is the number of GCMs whose sign equals the sign of the median
[D114]. Sensitivities are: a subset of three GCMs (GFDL-ESM4, MPI-ESM1-2-HR, MRI-ESM2-0) [D148]; Itaipu at 14,000 MW (version a);
SPI against SPEI; block length of the null; and leave-one-out of the five largest hydropower plants, reported as the change in
the raw capacity share with R_D >= 2 (not the excess) [D113, D135]. Cases in which SSP3-7.0 gives a smaller exposure than
SSP1-2.6 are decomposed by GCM and by plant [D148]. The methods that the article does not use are in Appendix F of the
specification. All code is run through one pipeline with fixed seeds [D156]; code and data availability statements follow the
journal's requirements. [AUTHOR: data and code availability wording once the journal guide is read, O52.]
