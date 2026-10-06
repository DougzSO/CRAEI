# Methods: Heat and Drought Exposure of the Brazilian Power Generation Fleet

Document status: consolidated, article-oriented (v3.0, C66/D104). Supersedes
the v2.2 consolidated Methods (C48) and all earlier section numbering; no
numeric result is new or changed by this restructuring. Decision ids (Dxx)
and open-item ids (Oxx) are preserved so every number stays traceable to
docs/DECISIONS.md. Fully superseded narrative (the pre-C48 "Section 1" v2
design, the v2.1 addendum prose, and the abandoned LR_C compound metric) is
not reproduced here; see Appendix G for archive pointers. The live tracking
apparatus (results map, result handlers, open items) is kept in Appendices
C-E, unchanged in content, only relocated.

Status labels used below: DONE (result pasted into this document or into a
result handler), PLANNED (next in the work plan, no new data needed),
DEFERRED (after the Brazil pipeline closes; needs data not yet verified),
TO BE DEFINED (placeholder, no value exists yet).

---

## 1. Scope and claims

The article measures the EXPOSURE of Brazilian power-generation assets --
thermal and hydroelectric plants -- to heat and drought hazards under
climate change, at plant level (D71). It does not measure impact,
vulnerability, generation loss, probabilities, or confidence intervals in
the formal statistical sense. Drought is PROJECTED by the climate models,
not observed; exposure to the projected hazard is compared against what
internal climate variability alone would be expected to produce (the null
model, Section 6), never against a significance threshold.

Scope is Brazil only. Pipeline modules take a country parameter and were run
for Brazil, India and Portugal under an earlier three-country design; India
and Portugal are not analysed in this article and are deferred until the
Brazil analysis is closed. Older, Brazil-only scripts filter the country
explicitly and were not audited for other countries.

Two axes of exposure are reported, plus their intersection:
- Axis 1 (heat): the thermal fleet, by fuel, operating versus planned.
- Axis 2 (drought): hydro plants, and water-dependent thermal plants,
  against the internal-variability null.
- Co-located exposure: spatial coincidence of both hazards at the same
  plant (Section 7), never called a "compound event".

---

## 2. Infrastructure data

Plant locations, capacities, technologies and statuses come from the Global
Energy Monitor (GEM) Global Integrated Power Tracker, snapshot 9 August
2026. Units are aggregated to plants using a stable identifier (hash of
name, latitude and longitude); capacity by fleet and fuel is computed from
the unit-level table (plant_units, 14,280 units), not from plants.parquet,
because the latter assigns a single fleet per plant by the mode of unit
status (D77, D78).

Four fleets are analysed: operating; planned advanced (construction,
pre-construction); planned early (announced); and planned_all, the union of
the two planned fleets. Shelved, cancelled, mothballed and retired units are
excluded.

Technology classes. Hydro plants are split into conventional reservoir,
run-of-river and pumped storage as recorded by GEM; where the type field is
missing, the plant is treated as reservoir. Thermal, water-dependent plants
are coal, oil and gas steam cycles, combined-cycle gas, nuclear, and
bioenergy steam plants. Thermal, air-only plants are open-cycle gas turbines
and reciprocating engines, where identifiable, and receive heat hazards
only. Solar PV is reported in Supplementary Information only. Technology
class and water dependence are taken from tech_class in plant_units (D80),
not from the hazard table's own bucket field, which was found to
misclassify 6 units (5 plants, 3,100.4 MW) as air-only; for these plants the
drought index was computed directly from spei.parquet rather than from the
mislabelled bucket.

Fuel classes (D77). Thermal plants are classified by Type first (coal,
nuclear, bioenergy); the remaining oil/gas plants are split by GEM's own
Fuel field into gas (Gas, LNG only), oil, and multi_fuel; bioenergy is
further split into agricultural_waste (a bagasse proxy), paper_mill_waste,
wood_biomass and other_bioenergy. Brazil's operating-fleet reference totals
are: gas 19.32 GW, bioenergy 17.43 GW, oil 4.60 GW, coal 3.00 GW, nuclear
1.99 GW, multi_fuel 1.33 GW (total 47.67 GW).

Hydro capacity convention. Itaipu is counted at its Brazilian share, 7,000
MW (version b), in every headline result, and at the whole binational
asset, 14,000 MW (version a), as a sensitivity check (D82, D85). Planned
hydro capacity is 28 units: 5,605 MW advanced, 2,019 MW early-stage.

Cooling water. GEM has no cooling-technology field. Two bounds are used
depending on the analysis. For the WRI Aqueduct water-stress indicator (H3,
Section 4), both an upper bound (all water-dependent thermal plants treated
as freshwater-cooled) and a lower bound (plants within 5 km of the
coastline, Natural Earth 1:10 m, treated as seawater-cooled and excluded)
are computed, with the 5 km cut tested at 2 and 10 km (author assumption,
evidence tier 3). For the drought (SPEI) and co-located-exposure analyses of
water-dependent thermal plants, only the upper bound is computed at present
-- all 788 water-dependent thermal units (699 plants, 342 cells, D89); the
coastal lower bound for these two analyses is not yet computed (TO BE
DEFINED, no blocking dependency beyond scheduling).

---

## 3. Climate data and baseline

Daily maximum temperature (tasmax), minimum temperature (tasmin) and
precipitation (pr) are taken from the ISIMIP3b bias-adjusted atmospheric
climate input data at 0.5 degrees, for the five ISIMIP3b primary GCMs:
GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0 and UKESM1-0-LL. The
baseline is each model's own historical simulation, 1985-2014; projections
cover 2041-2070 under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Data were
bias-adjusted by the ISIMIP team against W5E5 v2.0 with ISIMIP3BASD v2.5.0
(Lange, 2019; Frieler et al., 2021). The claim that the five models span the
CMIP6 range of climate sensitivity, and that UKESM1-0-LL sits at the high
end, is NOT independently verified in this project and should be cited or
removed before submission (O33). [NEED REFERENCE]

All indices are computed in two stages: baseline statistics (thresholds,
distribution parameters) are estimated once on 1985-2014 of a given model
and then applied unchanged to 2041-2070 of the same model. No percentile or
distribution is ever fitted on the series being classified. Tasmax/tasmin
consistency (TX >= TN) was checked on the full three-country ensemble:
707,545,940 cell-days, 0 inversions and 0 exact-or-near-equal (tolerance
1e-6) coincidences.

Plants are assigned to the nearest 0.5-degree land cell. For hydro plants,
the upstream catchment is built from HydroBASINS level 6 by recursively
following the NEXT_DOWN topology from the sub-basin containing the plant;
climate variables are area-weighted over every grid cell intersecting the
catchment before computing indices. Hydro plants also receive TX35 at their
own plant cell, read as climatic context rather than a cooling hazard
(hydro plants are not thermally cooled).

The baseline monthly accumulation used for SPEI has 372 rows (1984-01 to
2014-12); the first valid SPEI-12 value is 1984-12 (361 valid months), but
the distribution fit itself uses only the 1985-2014 window (360 values) --
December 1984 enters the baseline F_D denominator but not the fit, an effect
measured as negligible (mean -0.003 percentage points). Future series have
360 rows starting 2041-01, with the first valid SPEI-12 value in 2041-12
(349 valid months), because the 12-month accumulation restarts at the
beginning of each block.

---

## 4. Hazard definitions

Hazards are never combined into a single score; each is reported, classified
and aggregated independently (Section 5).

### 4.1 H1 -- Extreme heat (thermal plants; hydro context; solar in SI)

Annual count of days with daily maximum temperature at or above 35 degC and
40 degC:

TX35 = (1/30) sum_y sum_d 1[TX_{y,d} >= 35 degC], and analogously TX40.

The change metric is a difference, dTX35 = TX35_future - TX35_baseline
(days/yr), rather than a ratio, because baselines are zero in many cells.
TX35/TX40 are indices published in the IPCC AR6 Interactive Atlas and are
used here as indicators of cooling-relevant heat, not as operating limits
(tier 3). The headline change class is dTX35 >= 30 days/yr (about one
additional month of such days), tested on a grid of 10/20/30/40/50/60/80/100
days (O17, closed, D87). TX40 is tested on its own grid (O27, closed). A
baseline-relative heat threshold -- days above each cell's own baseline 95th
percentile of tasmax, as a robustness check that results do not depend on
the absolute 35/40 degC cuts -- is DONE at cell/GCM scope: 967 cells, 5
GCMs, baseline mean identical across GCMs (18.27 days/yr, mechanical by
construction), future diverges more under the relative cut (SSP5-8.5:
91.68-189.50 days/yr across GCMs, median threshold 34.4-34.7 degC, as low as
~25 degC in some cells) (TH1, C60, D98). This result is not GW-weighted and
not directly comparable to the H1 change-lens headline; fleet-level
aggregation of TH1 remains open (O39).

### 4.2 H2 -- Drought (hydro at catchment scale; water-dependent thermal at cell scale)

Standardized Precipitation Evapotranspiration Index at 12-month accumulation
(SPEI-12), with potential evapotranspiration from Hargreaves-Samani:

PET_d = 0.0023 x 0.408 x Ra_d x (Tbar_d + 17.8) x (TX_d - TN_d)^0.5,
Tbar_d = (TX_d + TN_d)/2

where Ra is extraterrestrial radiation (MJ m^-2 d^-1; FAO-56, Eq. 21) and
0.408 converts to mm/d. Monthly water balance D_m = P_m - PET_m is
accumulated over 12 months (3 months for SPEI-3, additional for
run-of-river plants). The three-parameter log-logistic distribution is fit
by unbiased probability-weighted moments (PWM; Vicente-Serrano et al. 2010)
on each series' own 1985-2014 baseline, never mixed across plants, cells or
models; where PWM does not converge, a Pearson Type III maximum-likelihood
fit is used instead (Bobee and Robitaille 1977; full fitting-method note in
Appendix B). SPEI-12 is fit once per (plant/cell, model) series on all 360
baseline months together, without a calendar-month split, because a
12-month accumulation already removes essentially all seasonal signal
(verified: mean standardized SPEI-12 by calendar month within +/-0.01 of
zero in every month). SPEI-3 keeps a calendar-month fit, widened with a
+/-1 adjacent-month window across the 30 baseline years (n=90), since a
3-month accumulation retains more seasonal structure. Values are clipped to
[-3, 3].

Severe drought frequency is F_D = fraction of months with SPEI-12 <= -1.5,
close to 6.7% in the baseline by construction. Because the distribution is
calibrated on each series' own baseline, the baseline F_D is nearly fixed by
design rather than a free draw of natural variability: across the
hydro-BRA catchment pool (1,110 series = 222 plants x 5 GCMs), baseline F_D
has mean 6.75%, sd 1.23, min 2.50, max 11.11 (nominal 6.68%), and the two
halves of the baseline series are strongly anti-correlated (r = -0.797).
The log-logistic fit is used for 687 of the 1,110 series (mean 6.48%, sd
1.12); the Pearson III fallback for the remaining 423 (mean 7.21%, sd 1.26).
This self-calibration property motivates the emulated null described in
Section 6.

The change metric is R_D = F_D,future / F_D,baseline; the headline change
class is R_D >= 2 (severe drought at least twice as frequent in the future
as in the baseline), tested at 1.5 and 3. R_D is left undefined, and
reported as its own category, whenever the baseline F_D is exactly zero
(rare by construction: 0 of 6,660 unit-level rows in the W4b run, Section
6).

Hydro plants are evaluated at catchment scale; water-dependent thermal
plants at cell scale (a 1,710-series cell pool feeds the thermal null).
Run-of-river plants additionally receive SPEI-3 at catchment scale. A
SPI-12 (precipitation only, ignoring atmospheric demand) comparison against
SPEI-12 under the same classes is planned (W4c, O18) to isolate the
contribution of the Hargreaves PET formulation; SPI-12 is already available
in spei.parquet. A Penman-Monteith PET formulation is deferred: it needs
wind, radiation and humidity at daily scale, and availability of these
variables in the ISIMIP3b input has not been verified.

### 4.3 H3 -- Chronic water stress (water-dependent thermal, freshwater bound only; Supplementary Information)

WRI Aqueduct 4.0, keyed by HydroBASINS pfaf_id, for the baseline and for
2050 under the optimistic, business-as-usual and pessimistic scenarios,
mapped to SSP1-2.6, SSP3-7.0 and SSP5-8.5. Aqueduct's baseline collection
exposes bws (baseline water stress) and its 2050 projections expose ws under
each {bau|opt|pes}{30|50|80} code; both are the same withdrawal-over-supply
ratio on the same 0-5 category scale, with the field renaming a WRI
convention rather than a methodological difference. Categories are used as
published: low (<10%), low-medium (10-20%), medium-high (20-40%), high
(40-80%), extremely high (>80%); exposure is capacity in high or extremely
high stress. H3 is reported separately from H1/H2 because Aqueduct uses its
own climate and socioeconomic forcing, inconsistent with the ISIMIP3b
ensemble used elsewhere, and its future values are themselves the median of
an internal 5-GCM ensemble distinct from this project's, with no per-model
breakdown available (L13). Water-dependent thermal plants are joined to
their containing HydroBASINS polygon's pfaf_id via a distance-guarded
nearest match (D37); both cooling bounds (Section 2) are reported.

### 4.4 H4 -- Extreme precipitation (Supplementary Information, all fleets)

Wet-day 95th percentile (days >= 1 mm) estimated on the baseline per cell
and model; the change metric is the ratio of exceedance frequency (baseline
5% of wet days by construction) and the percentage change in mean annual
Rx5day. Reported as a change in flood-forcing precipitation, not as flood
risk.

### 4.5 Solar PV (Supplementary Information)

Peak-hour temperature loss L = gamma x max(0, TX + 31.25 - 25), with
gamma = 0.4%/degC (typical crystalline silicon) and 31.25 degC the
cell-to-air difference implied by NOCT = 45 degC at 1000 W/m^2. Because L is
linear in TX above the threshold, delta-L mainly reflects warming; it is
included only to document that heat-driven PV losses are small relative to
thermal and hydro hazards, not as a finding in itself.

### 4.6 Excluded hazards

Extreme wind is excluded: 10 m gusts are not comparable with IEC 61400-1
design winds (50-year, 10-minute reference speeds of 50, 42.5 and 37.5 m/s
at hub height for classes I-III, rarely approached outside tropical cyclone
tracks); confidence in projected extreme wind change is low in IPCC AR6;
and GCM resolution does not capture the relevant extremes. Riverine and
coastal flooding, sea-level rise and wildfire are outside the scope of this
article.

---

## 5. Exposure metric, lenses and classes

For country c, technology t, hazard h, scenario s and model k, capacity
exposure is

E_{c,t,h,s,k} = sum_{i in (c,t)} Cap_i x 1[Delta_{i,h,s,k} >= tau_h] /
sum_{i in (c,t)} Cap_i,

reported both as a share and in GW. Ensemble results are the median across
the 5 models with the full model range; model agreement tables report k =
1, 3 and 5 of 5 GCMs exposed, replacing an earlier ">=4 of 5 same sign" rule
that was never implemented (O31, closed: agreement means k of 5
GCMs sharing the same sign in a contrast, e.g. future vs.
baseline).

Two lenses are reported for every hazard, and neither replaces the other:
- Change lens (headline): dTX35 >= 30 d/yr; R_D >= 2. Question: how much
  does it worsen relative to the baseline?
- Level lens: TX35 future (days/yr); F_D future (% months SPEI-12 <=
  -1.5). Question: how severe is the 2041-2070 climate at the plant? A
  delta alone ignores the level, so both are always shown side by side.

Heat level classes (O28, closed C45). Exclusive bins of TX35 future
(days/yr): low < 10; medium 10 to < 30; high 30 to < 60; extreme >= 60.
Baseline uses the same cuts, reported next to the future class (class
shift). Labels are conventions with no physical basis (tier 3); cuts are
fixed by calendar anchors before seeing the future result, except the upper
cut (60 d), chosen after seeing the distribution and justified only by the
anchor and the O17 grid -- flagged for the sensitivity table (Section 9).
Change classes (secondary): dTX35 < 10, 10 to < 20, 20 to < 30, >= 30. Per
(unit, GCM, scenario) the class comes from that GCM's own value; GW per
class is computed per GCM, then summarised as min/median/max across the 5
GCMs and k of 5; maps show the class of the per-cell median with the number
of GCMs agreeing.

Drought level classes (O29, closed; cell-scale null pool adopted for
thermal). F_D future against the null distribution of no climate change:
low <= p50; medium p50-p90; high p90-p99; extreme > p99 of the null (SPEI
<= -1.5). "Extreme" means natural variability alone rarely produces that
F_D; it is not a probability of impact, and because units are compared
one-by-one against a marginal null while being spatially correlated, the GW
share above a percentile is not binomially distributed. Change classes: R_D
< 1.5, 1.5 to < 2, 2 to < 3, >= 3, each reported with its own null rate
(Section 6). The baseline-to-future class migration is descriptive only,
since the baseline is conditioned on the fit and the future is not; the
canonical drought lens is F_D future against the null, not the migration.

---

## 6. The null model of internal variability (O34, D90)

Because SPEI's own-baseline calibration makes the baseline F_D nearly fixed
by construction (Section 4.2), the baseline cannot serve as a free draw of
natural variability. Drought exposure is instead always reported against an
explicit null of internal climate variability, estimated three different
ways, with NO canonical choice among them (D90):

1. Free null (W4a/W4g, DONE). Block bootstrap (12-month blocks; 24/36/60-
   month and AR(1) as sensitivities) drawing baseline and future from
   different series of the 1,110-series pool, with no refit. At the
   production point (SPEI <= -1.5, 12-month blocks, N=2,000, seed 23):
   18.88% of series reach R_D >= 2 (1,991 of 2,000 with R_D defined); a
   white-noise lower reference gives 1.80%. Block-length sensitivity (null
   pct_rd_ge2 by block length 12/24/36/60 months): 18.88 / 19.36 / 21.87 /
   20.75%, scenario-invariant by construction. The rate is not monotonic in
   block length -- block60 (20.75%) falls below block36 (21.87%) --
   consistent with only 6 blocks being drawn per 360-month series at that
   length, which may not resample meaningfully (D83; confirmed in W4b,
   D102). An AR(1) variant is treated as an informative, not abort-on-fail,
   soft check: phi estimated from the full 1,110-series pool gives 27.58%,
   different from a fixed-phi reference (phi = 0.9291, 26.12%, estimated on
   a 200-series sample in an earlier audit) -- two different phi
   estimations of the same quantity, reported side by side. This free null
   ignores the 30-year parameter-estimation error and draws baseline and
   future from different series, whereas the real data pairs them within
   the same plant and GCM.

2. Emulated null, variant "year" (craei.hazards.null_emulator, DONE). One
   series of the pool per draw; the water-balance deficit D is resampled in
   whole calendar years; a fresh 12-month accumulation and distribution
   refit is computed on the resampled 360 baseline months with the
   production estimator; baseline and future are standardized with the
   same refitted parameters, and F_D uses the same denominators as the
   real data.

3. Emulated null, variant "anystart": identical, but using 12-month blocks
   starting at any month rather than whole calendar years.

Emulator fidelity (DONE). Refitting the real D of all 1,110 series
reproduces the stored SPEI-12 exactly: 0 fit failures, identical
distribution label (log-logistic vs Pearson III) in all 1,110 series,
maximum |z - stored| = 7.77e-05 for |SPEI| < 3 (tolerance 1e-3), maximum
|dF_D| = 0.0000 pp (tolerance 0.01). A fixed-abort check script enforces
this before any emulator output is used.

Validity rule (fixed before running). The emulated baseline F_D must
reproduce the real one within |delta sd| <= 0.20 and |delta corr(halves)|
<= 0.10 (real: sd 1.23, r = -0.797). At n = 2,000 per variant: year gives sd
1.42, r = -0.723 (PASS); anystart gives sd 1.06, r = -0.732 (PASS); the real
value lies between the two. An earlier n = 150 pilot failed both (standard
error of sd ~0.09 then, ~0.02 now).

Per-GCM validation (DONE, diagnostic). Applying the same rule separately
per GCM (1,000 draws per GCM/variant against that GCM's own 222-series real
value) shows neither variant passes in every GCM:

| GCM | real (sd / corr) | year (sd / corr) | anystart (sd / corr) |
|---|---|---|---|
| GFDL-ESM4 | 1.45 / -0.651 | 1.39 / -0.745 PASS | 1.09 / -0.766 FAIL |
| IPSL-CM6A-LR | 1.32 / -0.723 | 1.47 / -0.704 PASS | 1.04 / -0.692 FAIL |
| MPI-ESM1-2-HR | 0.85 / -0.864 | 1.35 / -0.736 FAIL | 1.00 / -0.758 FAIL |
| MRI-ESM2-0 | 1.36 / -0.715 | 1.41 / -0.748 PASS | 1.10 / -0.726 FAIL |
| UKESM1-0-LL | 1.01 / -0.810 | 1.39 / -0.724 FAIL | 1.07 / -0.737 PASS |

year passes 3 of 5 GCMs, anystart 1 of 5, and MPI fails both; the pooled
PASS (real sd 1.23, between the two variants) may partly reflect mixing
GCMs with different real dispersion, which was not tested directly. Margins
are narrow in two cases (GFDL year corr gap 0.094 against the 0.10 limit;
MPI anystart corr gap 0.106, just over), and the real per-GCM sd comes from
only 222 spatially correlated plants, so its own sampling error -- not
measured -- is likely larger than nominal.

Stationarity and trend. The nulls assume a stationary climate, but the
real GCM baselines carry their own trend: F_D second-half-minus-first-half
is +4.95 (GFDL), +4.66 (IPSL), -4.55 (MPI), +2.96 (MRI), -0.27 pp (UKESM),
mean +1.55 pp, against ~0 for both emulated variants. The lag-1
autocorrelation of annual D is close to zero (0.044; 0.005 detrended), so
persistence is not what the emulators are failing to reproduce -- it is the
trend. UKESM, whose real trend is near zero, still fails the year sd check
(1.39 vs 1.01), so the trend alone does not fully explain the sd gap
(series-level trends may cancel in the pooled mean; not tested further).

Preliminary outputs (n = 2,000 per variant; final run needs 20,000,
pending). F_D future p99: year 25.5%, anystart 19.2%, free 16.11%. R_D >=
2: 17.3% / 8.6% / 18.06%. R_D >= 3: 4.2% / 1.0% / 8.10%. The three nulls
differ substantially, confirming that none is canonical.

Reporting rule. Every drought result is shown under all three nulls; a
conclusion enters the main text only if it holds under all three, otherwise
it is reported as a range. R_D is always descriptive, shown with the
null-rate range, never as a significance test. Bounds behave as expected
qualitatively: AR(1) (soft reference) gives a lower excess-over-null than
block12, since its null rate is higher (27.58%); white noise gives the
widest excess, since its null rate is lowest (1.80%) (confirmed directly in
the W4b excess table, D102).

Production excess-over-null result (W4b, DONE, D102). Hydro BRA, Itaipu b
(Brazilian share, headline) and Itaipu a (whole asset, sensitivity), at the
production point (SPEI <= -1.5, R_D >= 2.0). Headline (hydro operating,
Itaipu b, block12, median excess_pp over 5 GCMs), SSP1-2.6/3-7.0/5-8.5:
+40.75 / +43.20 / +53.94 pp (null 18.88%; observed median
59.63/62.09/72.83%). Itaipu a gives a close result (+36.94/+39.24/+55.68
pp), as expected since only the capacity weight differs between the two
Itaipu versions. R_D is undefined for 0 of 6,660 unit-level rows (194 hydro
plants per fleet x Itaipu group).

---

## 7. Co-located exposure (D88, D89)

Spatial coincidence of both hazards at the same plant location, never
simultaneity in time and never called a "compound event". Units considered
are water-dependent thermal (cell scale) and hydro (catchment-scale SPEI
plus plant-cell TX35); air-only thermal and solar are not included. Per GCM
and scenario, a 4x4 cross-tab (heat level class x drought level class) is
built in GW, with the headline being extreme-in-both and a sensitivity of
high-or-extreme-in-both; the same GCM is used for both hazards in a given
cell of the cross-tab, and results are reported as min/median/max and k of
5. Because the drought classes depend on which null is used (Section 6),
the cross-tab is produced under each of the three nulls. Marginal totals
are required to equal the independently computed heat (Section 5) and
drought class totals; the production script aborts otherwise. No index, no
weights and no ranking are built from the cross-tab; individual hazards are
always presented first. Whether ISIMIP3BASD preserves the real
heat-rainfall dependence structure of the underlying GCM has not been
verified (O30), so temporal coincidence (years with both hazards present)
is not currently reported.

National 4x4 cross-tab results (W4h, D97, C59) exist; the extreme-by-
extreme headline (CO2) was transcribed into Appendix D in C67/D105 as a
percentage GW share (not absolute GW), by null variant. The full 4x4
matrix (CO1) remains untranscribed beyond that one cell (TO BE DEFINED,
bookkeeping only -- the data exists in w4h_coexposure.csv). The
high-or-extreme-in-both sensitivity (CO3) is NOT available as a valid
number: D97's own console output for this cell summed four already-
computed medians, which D97 itself flags as invalid because the median is
not additive (D80); this was never written to a CSV, and the correct
calculation (collapsing raw per-GCM values across the four cells before
taking a single median) is pending with no id assigned. No CO3 figure
should be cited until that calculation exists.

State and macro-region breakdown (M10, W3h, DONE). Units are assigned to
Natural Earth admin1 polygons (fields name, postal, region) by spatial
join, with points outside any polygon assigned to the nearest polygon and
the fallback count reported (craei.geo.state_assignment). For the heat-only
state summary (ST1, C62, D99): 1,122 rows, 19 of 6,926 plants (0.27%) via
nearest-polygon fallback; both capacity-parity and pre-median
national-sum-parity checks passed at 0.00e+00 difference. Headline
(all_thermal, operating, SSP5-8.5, extreme class): Sao Paulo, Maranhao and
Mato Grosso do Sul lead (2.88-2.89 GW median), preliminary. For the
state-level co-exposure summary (ST2, C63, D100): 2,952 rows, 921 plants
(hydro + thermal_water_dependent), 3 nearest-polygon fallbacks; three parity
checks (capacity, pre-median state-sum, and cross-check against the national
W4h cross-tab) all passed at 0.00e+00-order differences (max 7.11e-15). ST2
reports its own high-or-extreme-in-both quantity as the median of a single
combined flag, which is NOT the same number as W4h's own sum-of-four-medians
definition of the same label (medians are not additive); this distinction
is documented, not reconciled, since both are internally consistent within
their own tables. Headline (extreme x extreme, operating, SSP5-8.5,
block12): Para leads in hydro (22.35 GW median), followed by Rondonia,
Parana, Bahia and Minas Gerais, preliminary.

---

## 8. Planned versus operating fleet

Reported as a substantive result, not a caveat.

Change lens (paired planned-minus-operating, percentage points of GW with
dTX35 >= 30 d/yr; SSP1-2.6/3-7.0/5-8.5): -7.16 / -0.12 / +1.35, with every
cell-bootstrap interval including 0.

Level lens (share of GW in the extreme heat class, median [min-max]):
operating 23.8 [17.7-33.1] / 30.6 [26.6-52.9] / 32.4 [31.2-75.9];
planned_all 14.3 [1.6-34.7] / 24.1 [20.1-61.8] / 30.0 [20.6-74.3]. Ranges
overlap in every scenario.

Taken together, no consistent difference in exposure between planned and
operating capacity is found under the change lens (GW weighting); under the
level lens, the planned share in the extreme class is lower in SSP1-2.6 and
SSP3-7.0 and similar in SSP5-8.5, again with overlapping ranges. This is not
read as evidence that fleet expansion "locks in" or "reduces" exposure.

Weighting sensitivity (W3f-7, DONE, D101) -- a finding that changes this
reading. Repeating the change-lens contrast under TX40 (instead of TX35)
and under plant-count weighting (instead of GW weighting) shows the
GW-weighted result above does NOT generalize. Under GW weight (the
reference above), the median contrast is near zero with n_planned_ge 1-2 of
5 GCMs -- "no consistent difference". Under plant-count weight, the same
hazard and threshold grid give a median contrast that is consistently
POSITIVE in all three scenarios (+12.07 / +7.98 / +9.87 pp,
SSP1-2.6/3-7.0/5-8.5; n_planned_ge 4-5 of 5 GCMs). The planned fleet is
exposed more than the operating fleet when plants are weighted equally
rather than by capacity -- i.e. the planned fleet's exposure is
concentrated in a larger number of smaller plants. This is the clearest
sign-reversal found so far across any single-choice sensitivity test and is
flagged for explicit treatment in the sensitivity table (Section 9) and in
the article text, not only archived as a technical note.

---

## 9. Aggregation, uncertainty and sensitivity

GW is computed per class per GCM, then summarised as min/median/max and k
of 5 (k = 1, 3, 5 of 5 GCMs exposed; "agreement" is defined as k
of 5 GCMs sharing the same sign in a contrast; closed under
O31). Ranges are structural (the spread across 5 deterministic GCM
runs), not confidence intervals (D85). Cell bootstrap (currently n_boot =
2,000; a final run at n_boot = 5,000 for the W3d and W3f-3 tables is
pending) reports percentiles only when a bucket has >= 10 cells and zero
NaN fraction, otherwise results stay descriptive (O25). Every hydro
headline is reported beside a leave-one-out of the 5 largest plants (Itaipu
14,000 MW whole-asset, Belo Monte 11,233, Tucurui 8,535, Jirau 3,750, Santo
Antonio 3,568, Ilha Solteira 3,444 MW; O19, pending). A 7-set GCM-exclusion
sensitivity is DONE for the heat axis; any statement framed as "GCM
sensitivity" still rests on the unverified claim in Section 3 (O33).

A single sensitivity table (W5, PLANNED) will report, for each discrete
methodological choice, the headline value, the alternative value, the delta
in percentage points, and the planned-vs-operating contrast recomputed
under that same choice, flagged for sign change, fuel-order change,
non-overlapping ranges, or a bootstrap interval crossing zero. The families
to be covered: heat threshold grid, TX40, the baseline-relative heat
threshold (TH1), planned-fleet definition, capacity vs plant-count
weighting, water-dependent vs air-only thermal, GCM exclusion, bootstrap
sample size, Itaipu a vs b, SPEI-3 vs SPEI-12, SPI vs SPEI, the SPEI drought
threshold, the R_D threshold, null type and block length (including the two
emulated variants), the heat-class cut values, and the drought-null
percentiles. Out of scope for W5: the 15-day heat grid point (removed with
O17's closure) and the coastal buffer/H3 freshwater bound.

Two findings must be surfaced as flagged rows in W5, not buried among
families with a near-zero effect:

- Weighting reverses the planned-vs-operating sign (Section 8, W3f-7,
  D101): GW weighting shows no consistent difference; plant-count weighting
  shows a consistent, positive difference in all three scenarios.
- Block length is not monotonic in the drought null (Section 6, W4b,
  D102): the null rate falls from block12 (18.88%) to block36 (21.87%) as
  D83's persistence-breaking hypothesis predicts, then partially recovers
  at block60 (20.75%), a result read as a small-sample artifact of only 6
  blocks per 360-month series rather than evidence against the hypothesis.
  W5 must report all four block lengths, not only 12 vs 36.
---

## 10. Validation

National-scale validation against the Brazilian system operator's (ONS)
natural energy inflow (ENA) is DONE: Spearman rho = 0.361, 95% CI
[0.027, 0.811], n = 20 years (supplementary, D73). The correlation is weak
and reported as such. Subsystem-level validation (North, Northeast, South,
Southeast) is suspended for the current article version: no official
plant-to-subsystem mapping source was found (D62).

Extended validation (module W8, scheduled after Section 7 closes;
underlying data availability not yet verified) is DEFERRED:
(a) a monthly-resolution ENA-vs-SPEI-12 comparison with block bootstrap
correcting for autocorrelation, giving more data points than the annual
series above, at the cost of reduced independence between points;
(b) a distributional comparison of cell-level TX35 climatology against
INMET station records -- distributional rather than year-by-year, because
GCM simulation years do not correspond to real calendar years; W5E5 is
itself derived from ERA5, so comparing the bias-adjustment reference
against ERA5 would not be an independent check;
(c) generation-based consistency checks (Appendix F, item B1).

The constraint that GCM years are not synchronized with real calendar years
applies throughout: any validation must compare either the observed-forcing
index (SPEI computed from W5E5) against observed records, or climatological
distributions against station data, never GCM output against observation
year-by-year.

Portugal (REN hydro productivity index) and India validation work was
carried out under an earlier three-country design and is not part of the
Brazil-only scope adopted in D71. The methodology (REN DataHub acquisition,
monthly cross-validation against APA 2018 Tabela 7, the unresolved annual
REN-ERSE aggregation gap, DGEG generation as an auxiliary check) and its
results (D59-D61, O10, O11) are preserved via the archive pointer in
Appendix G and are not reproduced in the current scope.

---

## 11. What is not claimed

This article does not claim: impact, vulnerability or generation loss;
probabilities of any kind; confidence intervals derived from the 5-GCM
range (which is a structural spread, not a sampling distribution);
harvest-window effects for bioenergy; a composite exposure index combining
heat and drought; findings for solar PV or wind beyond the documentation in
Sections 4.5 and 4.6; flood risk from the H4 extreme-precipitation
indicator; results for countries other than Brazil; or temporal (as
opposed to spatial) coincidence of heat and drought hazards.

---

## Key references

- van Vliet, M.T.H. et al. (2016). Power-generation system vulnerability and
  adaptation to changes in climate and water resources. Nature Climate
  Change.
- Frieler, K. et al. (2021, protocol). ISIMIP3b scenario and forcing
  protocol.
- Lange, S. (2019). Trend-preserving bias adjustment and statistical
  downscaling with ISIMIP3BASD. Geoscientific Model Development.
- Cucchi, M. et al. (2020) and Lange, S. et al. (2021). W5E5 / WFDE5.
- Vicente-Serrano, S.M. et al. (2010). A multiscalar drought index sensitive
  to global warming: SPEI. Journal of Climate.
- Hargreaves, G.H. and Samani, Z.A. (1985). Reference crop evapotranspiration
  from temperature. Applied Engineering in Agriculture.
- Allen, R.G. et al. (1998). FAO Irrigation and Drainage Paper 56.
- Kuzma, S. et al. (2023). Aqueduct 4.0 technical note. World Resources
  Institute.
- Lehner, B. and Grill, G. (2013). HydroSHEDS / HydroBASINS. Hydrological
  Processes.
- Bobee, B. and Robitaille, R. (1977). The use of the Pearson Type III
  distribution for flood frequency analysis. Water Resources Research.
- IEC 61400-1 (Wind energy generation systems, design requirements).
- IPCC AR6 WGI, Chapter 11 and Interactive Atlas.
---

## Appendix A. Technical pipeline

Execution machine, measured: AMD Ryzen 3 PRO 2200G, 4 cores / 4 logical
processors, 6.4 GB RAM total. Project data (data_root, country-cropped
climate files, plants.parquet, etc.) lives on the internal SSD (Samsung
MZNLN128HAHQ, 128 GB); the raw global ISIMIP cache lives on an external USB
HDD (Seagate Basic, 4 TB). This is well below the 8+ cores / 32 GB this
section originally assumed; per-step times below are measured where a
logged run on this machine recorded one, and explicitly marked "not
measured" otherwise.

**Step 1. Plant inventory.** Input: GEM tracker CSV; Natural Earth 10 m
coastline. Processing: filter countries and statuses; aggregate units to
plants; assign technology class and water dependence; compute distance to
coast; flag coastal plants at 2/5/10 km. Output: plants.parquet (plant_uid,
country, fleet, tech_class, water_dependent, hydro_type, capacity_mw, lat,
lon, dist_coast_km). Time: not measured with wall-clock precision.

**Step 2. Climate data acquisition.** Input: ISIMIP repository. Processing:
download bounding-box cutouts for 5 GCMs x {historical, ssp126, ssp370,
ssp585} x {tasmax, tasmin, pr}, keeping files overlapping 1984-2014 and
2041-2070; W5E5 observations 1984-2019 for the same variables. Output:
data/isimip/{model}/{scenario}/{var}_{country}_{decade}.nc;
data/w5e5/{var}_{country}_{decade}.nc; checksum manifest. Time: not a
single measured duration by design (server-queue-dependent).

**Step 3. Spatial mapping.** Input: plants.parquet; HydroBASINS level 6;
one ISIMIP grid template. Processing: nearest land cell per plant; for
hydro, sub-basin containing the plant and upstream set via NEXT_DOWN
traversal; area weights of grid cells intersecting each catchment. Output:
plant_cell.parquet; catchment_weights.parquet. Time: not measured with
wall-clock precision.

**Step 4. Daily temperature and precipitation indices.** Input: ISIMIP
cutouts; unique cells from Step 3. Processing: for each model and period,
per cell: annual TX35, TX40; monthly N35; wet-day P95 (baseline) and
exceedance counts in both periods; annual Rx5day. Output:
indices_daily.parquet. Time: measured, 72 min end to end for all 60
model/scenario/country jobs, under real memory constraints and with the
system near its RAM ceiling for part of the run. Faster than a naive
estimate because Step 4 only ever touches the cells a plant actually uses
(a few hundred to ~1,000 per country), not the full country grid.

**Step 5. PET and water balance.** Input: ISIMIP tasmax, tasmin, pr; W5E5
for validation. Processing: daily Ra from latitude and day of year;
Hargreaves PET; monthly P, PET, D; catchment-averaged D for hydro plants.
Output: water_balance_cell.parquet, water_balance_catchment.parquet. Time:
completed successfully but without a logged start timestamp, so no reliable
elapsed time is available; input cell count is larger than Step 4's (union
of nearest-cell and hydro-catchment cells, e.g. 1,993 for Brazil vs. Step
4's 967), so Step 4's measurement is not a safe proxy.

**Step 6. SPEI and SPI.** Input: Step 5 outputs. Processing: 12-month and
3-month accumulation; SPEI-12 fit once per (id, model) series on its own
360 baseline values; SPEI-3 fit per calendar month with a +/-1
adjacent-month window (n=90); both via PWM log-logistic with a Pearson III
MLE fallback where PWM does not converge (full comparison in Appendix B);
apply the same per-series parameters to 2041-2070; clip to [-3, 3]; SPI
with gamma distribution, per (id, model) per calendar month, n=30. Future
series start in December 2041 because 2031-2040 is not downloaded. Output:
spei.parquet (id, model, scenario, month, spei12, spei3, spi12,
distribution). Time: measured, fit+standardize loop only: 581.5 s
(~9.7 min), using the per-series temporal method -- faster than an earlier
per-calendar-month hybrid's 3,649 s (~61 min) because the per-series fit
needs one fit attempt per series instead of twelve.

**Step 7. Plant-level hazard table.** Input: Steps 3-6. Processing
(craei.hazards.consolidate): plants are assigned one bucket each
(hydro_reservoir incl. pumped storage, hydro_run_of_river,
thermal_water_dependent, thermal_air_only, solar); dTX35/dTX40 (cell scale)
for the two thermal buckets; F_D/R_D of catchment-scale SPEI-12 for hydro
(plus catchment-scale SPEI-3 for run-of-river) and cell-scale SPEI-12 for
water-dependent thermal; H4 for every bucket with a linked cell. R_D is
left NaN, not computed, when baseline F_D is exactly zero. Output:
plant_hazards.parquet. Time: measured, 68 s (includes Step 8). 446,700
rows. R_D-baseline-zero rate: 0.000% hydro_reservoir, 0.000%
hydro_run_of_river, 0.016% thermal_water_dependent (3/19,200).

**Step 8. Aqueduct water stress.** Input: Aqueduct 4.0 future_annual ws
(2050, 3 scenarios, pfaf_id-keyed) and baseline_annual bws. Processing:
water-dependent thermal plants joined to their containing HydroBASINS
polygon's pfaf_id; Aqueduct categories applied as published; two cooling
bounds reported (upper: all plants; lower: excluding plants within 5 km of
the coast). Output: plant_aqueduct.parquet. Time: included in Step 7's
68 s. 7,311 rows (1,280 plants x 3 scenarios x 2 bounds, minus 369 rows
excluded from the lower bound as coastal). 0 plants fell into category -1
or "no_data" in this run.

**Step 9. Exposure aggregation and agreement.** Input: Steps 1, 7, 8.
Processing: capacity shares and GW above headline classes per country x
technology x fleet x scenario x model; ensemble median and range; model
agreement flags per plant. Output: exposure_summary.csv. Time: 0.5 h (not
measured).

**Step 10. Compound metric -- SUPERSEDED.** The originally specified
future-to-baseline likelihood ratio (LR_C) for a joint hydro-drought /
thermal-heat national monthly series was replaced by two separate
quantities (diff_pp, a percentage-point change in compound-month
frequency; dependence_ratio, observed future co-occurrence over what
independent marginals would predict), after a direct diagnostic found LR_C's
large values in several country x scenario x model cells reflected each
marginal's own baseline-relative drift, not extra co-occurrence. This
compound-metric design was carried out under the earlier three-country
scope and is outside the current Brazil-only article (D63, D72); the
script (11_compound.py) is archived. Restricting to cells where the
percentile threshold still discriminated extremes, dependence_ratio showed
measurable positive dependence in a majority of answerable cells (median
1.23, 5th/95th percentile 0.78/2.69), not pure independence -- preserved
here as a methodological record, not as part of the current article's
result set.

**Step 11. Validation.** Input: W5E5 SPEI; ONS ENA; REN productivity index;
plants. Processing: hydro-capacity-weighted annual SPEI-12 per subsystem
and Portugal; Spearman rho with block bootstrap; odds ratio for low-inflow
years. Output: validation.csv. Time: 1 h (not measured). Brazil national
result: Section 10. Subsystem and Portugal results: outside current scope
(see Appendix G).

**Step 12. Sensitivity and figures.** Input: all previous outputs.
Processing: rerun Steps 9-10 under each alternative; generate figures.
Output: sensitivity.csv; figure files. Time: 2-3 h (not measured). Status:
the current sensitivity work (Section 9, W5) supersedes this step's
original design; table and figure generation for the current scope is
PLANNED.

Total compute: roughly 11-18 h, not measured as a single run.

### A.1 Additional downloads

| Dataset | Source | Approx. size | Purpose |
|---|---|---|---|
| ISIMIP3b bias-adjusted daily tasmax, tasmin, pr; 5 GCMs; historical + 3 SSPs | ISIMIP repository | ~35 GB for Brazil | All hazard indices |
| W5E5 v2.0 daily tasmax, tasmin, pr, 1984-2019 | ISIMIP repository | ~5 GB (estimate) | Validation |
| HydroBASINS level 6 | HydroSHEDS | Tens to a few hundred MB | Hydro catchments |
| Natural Earth 1:10m coastline | naturalearthdata.com | <10 MB | Cooling bound |
| ONS natural energy inflow (ENA) | ONS open data portal | <10 MB | Validation, Brazil |
| Aqueduct 4.0 baseline bws | Existing GEE asset | <100 MB | H3 |
---

## Appendix B. SPEI fitting method: PWM failures and the Pearson III fallback

The three-parameter log-logistic distribution in Step 6 is fit by unbiased
probability-weighted moments (PWM), the closed-form estimator of
Vicente-Serrano et al. (2010): from a series' baseline values, sample PWMs
b0, b1, b2 give a shape parameter beta = (2b1-b0)/(6b1-b0-6b2), then scale
alpha and location gamma from beta. The production implementation rejects a
fit whenever beta is non-positive or non-finite, any Gamma-function
evaluation in the alpha step is non-finite or zero, or the fitted location
gamma exceeds the sample minimum (a log-logistic's support is
[gamma, infinity), so gamma above the smallest observed value is a support
violation). On this project's real water-balance deficit D = P - PET,
roughly 30% of (plant/cell, model, calendar-month) baseline fits are
rejected this way (32.4% hydro catchment SPEI-12, 14.4% run-of-river
SPEI-3, 29.1% thermal-cell SPEI-12, all with the full 30-sample baseline
and zero missing months -- sample size and data gaps were ruled out as
causes). Every rejected fit is left as NaN and counted, never silently
replaced by a default value.

**Why PWM fails under high skewness.** The PWM estimator inverts three
sample moments into three distribution parameters through a relation that
is only defined, and only gives a physically meaningful beta > 0, for a
restricted region of moment-space consistent with a log-logistic shape. A
30-observation empirical sample of a distribution more sharply skewed, more
symmetric, or otherwise differently shaped than a log-logistic (as D can be,
month to month and cell to cell) can land outside that region. Measured
directly: 100% of the failures are the beta <= 0 branch, with beta ranging
from -2.96 to -21,878 -- sign-flipped and often large in magnitude, not
values near zero. No concentration by season was found (16-50% failure
rate across every calendar month in all three countries), and failing vs.
passing groups show no consistent difference in coefficient of variation.
This matches a known small-sample weakness of the PWM estimator for the
three-parameter log-logistic reported in the hydrological literature, not a
defect specific to this implementation.

**Why |beta| is not a valid substitute.** The sign of beta determines which
tail of the log-logistic is heavier; a positive beta gives the standard
right-skewed form used for SPEI. Replacing a computed beta < 0 with |beta|
does not recover a valid fit to the same data -- it substitutes a different
distribution shape with the tail direction inverted. Because SPEI's
standardization step maps quantiles of the fitted distribution onto the
standard normal, inverting the tail would invert which end reads as
extreme: a real wet anomaly could read as extreme dry SPEI, silently
corrupting F_D and any classification built on it. |beta| was considered
and rejected on this basis.

**Alternative estimators measured, not adopted.** A stratified-sample
benchmark compared the production PWM estimator against a moment-seeded
3-parameter log-logistic MLE, a Generalized Extreme Value fit (MLE), and a
Pearson Type III fit (MLE), on a fixed-seed random sample of up to 800
PWM-failing and 800 PWM-passing combinations per bucket (not the full
~247,000-combination population, since a 200-combo pilot showed ~60-100 ms
per MLE call against PWM's closed-form microseconds):

| Bucket | Method | Failure rate | Recovery on PWM failures | F_D | Relative time |
|---|---|---|---|---|---|
| Hydro catchment SPEI-12 | PWM (production) | 50.0%* | 0.0% | 5.90% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.71% | 396x |
| | GEV (MLE) | 0.0% | 100.0% | 7.94% | 580x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.46% | 219x |
| Run-of-river SPEI-3 | PWM (production) | 50.0%* | 0.0% | 5.35% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.86% | 449x |
| | GEV (MLE) | 0.0% | 100.0% | 8.13% | 735x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.26% | 288x |
| Thermal cell SPEI-12 | PWM (production) | 50.0%* | 0.0% | 5.70% | 1.0x |
| | MLE log-logistic | 0.0% | 100.0% | 7.74% | 262x |
| | GEV (MLE) | 0.0% | 100.0% | 8.72% | 480x |
| | Pearson III (MLE) | 0.0% | 100.0% | 7.37% | 154x |

*PWM's 50.0% sample failure rate reflects the stratified sample design
(800 failing + 800 passing drawn on purpose), not the real population rate
(32.4% / 14.4% / 29.1%); its F_D is computed only from the sample's passing
half, consistent with the real production run's 5.9-6.6%.

All three alternatives recovered every one of the 2,400 sampled PWM
failures (100%) with zero failures of their own, at 150-735x PWM's
wall-clock cost. All three land somewhat above the ~6.7% standard-normal
expectation; Pearson III is closest to 6.7% and cheapest among the three,
GEV furthest and most expensive.

**Adopted hybrid strategy.** The log-logistic distribution is fit via PWM
when it yields valid parameters (beta > 0, gamma <= min(sample)); where PWM
is rejected, a Pearson Type III distribution is fit via maximum likelihood
(scipy.stats.pearson3.fit), numerically stable under high skewness and
established in hydrological drought analysis (Bobee and Robitaille 1977).
In practice 29.6% of (plant/cell, model, calendar-month) baseline
combinations across the three SPEI series need the fallback. The hybrid
recovers 100% of PWM's fitting failures on this project's real data
(0/3,275 hydro catchment, 0/1,305 run-of-river, 0/16,010 thermal-cell
combinations left unfit; the remaining 3.03% NaN rate in SPEI_12 is the
already-documented structural lead-in NaN from the accumulation window's
min_periods behavior, not a fitting failure). Baseline F_D (SPEI-12 <=
-1.5), hydro and thermal combined, mean over (id, model) groups: 6.21%,
close to the ~6.7% standard-normal expectation.

Computational overhead, measured directly on the real full ~247,000
baseline combinations: 3,649 s (~61 min) for the hybrid fit+standardize
loop vs. 189 s (~3.2 min) for an otherwise-identical PWM-only pass -- a
~19.3x overhead, higher than an earlier, unmeasured draft estimate (~15x,
and a still-earlier "minimal ~1.2-1.4x" framing that is not supported by
measurement and is corrected here). ~19.3x is acceptable for this
project's batch, offline processing. The final SPEI values are
distribution-agnostic (standardized via inverse normal CDF regardless of
which distribution produced them), preserving comparability with the SPEI
literature for the 70.4% of baseline combinations still fit by the standard
log-logistic estimator.

Note: this appendix describes the per-series (D54/D55) fitting method
currently in production. An earlier per-calendar-month hybrid variant was
tested and superseded (Step 6 timing comparison in Appendix A); its
specific failure-rate breakdown is preserved in the archived decision
record (Appendix G) and not repeated here, since the per-series method is
the only one in current use.
---

## Appendix C. Results map (figures and tables)

| Item | Content | Source table(s) | Status / blocking |
|---|---|---|---|
| Fig 1 | Fleet and capacity by technology and fuel | plant_units | DONE (data), figure PLANNED |
| Fig 2 | Heat level class map (cells, plants sized by GW) | w3g_heat_cell_class | Blocked on W3g map table |
| Fig 3 | Threshold curves, operating vs planned | w3_curves_plot | DONE (data), figure PLANNED |
| Fig 4 | Drought level class map, SPEI and SPI | w4g tables | Blocked on W4g map table, O18 |
| Fig 5 | Excess over the null by scenario, GCM range | w4b_excess_over_null.csv | DONE (C64, D102); figure PLANNED |
| Fig 6 | Co-located exposure map and cross-tab | w4h_coexposure.csv, w3h_state_coexposure.csv | DONE (data, C59/C63); figure PLANNED |
| Table 1 | GW exposed by technology, fuel, scenario | w3_table1 | DONE (data), table PLANNED |
| Table 2 | Leave-one-out, 5 largest hydro | W4d table (planned) | Blocked on O19 |
| Table 3 | 4x4 cross-tab, GW | w4h_coexposure.csv | DONE (C59, D97) |
| Supplementary | ONS validation | validation.csv | DONE (D73) |

---

## Appendix D. Result handlers

Every number quoted in the article text must trace to exactly one row
below. A value is filled only from an actually-pasted script output, never
estimated or interpolated. Table names marked (planned) do not exist yet.

| Id | Statement slot | Table | Filter | Column | Value |
|---|---|---|---|---|---|
| F1 | Operating thermal GW (BRA) | plant_units | country, fleet, tech_class | sum capacity_mw | TO BE DEFINED |
| F2 | Planned thermal GW (adv, early, all) | plant_units | fleet | sum capacity_mw | TO BE DEFINED |
| F3 | Hydro GW operating (b headline, a sensitivity), planned hydro GW | plant_units | tech_class = hydro | sum capacity_mw | TO BE DEFINED |
| HC1 | Share of operating thermal GW with dTX35 >= 30 d, median [min-max], 3 scenarios | w3_table1 | group = all_thermal, fleet = operating, threshold = 30 | pct_median, pct_min, pct_max | TO BE DEFINED |
| HC2 | Same, in GW | w3_table1 | same | gw_median | TO BE DEFINED |
| HC3 | Agreement k = 3 and k = 5 | w3_table1 | same | pct_gw_k3, pct_gw_k5 | TO BE DEFINED |
| HC4 | By fuel (bioenergy, gas) | w3_table1 | group = fuel | pct_median, pct_min, pct_max | TO BE DEFINED |
| HC5 | Planned minus operating, paired, with cell bootstrap | w3_heat_bootstrap_paired | planned_fleet = planned_all, threshold = 30 | obs_median_diff, boot_p025, boot_p975 | DONE (Section 8): -7.16 / -0.12 / +1.35 pp (SSP126/370/585), all CIs include 0 |
| HC6 | Scenario contrast | w3_heat_scenario_contrast | pair, threshold = 30 | obs_median_diff, n_gcm_pos, boot_p025_pp, boot_p975_pp | TO BE DEFINED |
| HC7 | Cell bootstrap of the share | w3_heat_bootstrap_shares | threshold = 30 | obs_median, boot_p025, boot_p975 | TO BE DEFINED |
| HC8 | Leave-one-cell-out range | w3_table1 | threshold = 30 | loo_min, loo_max | TO BE DEFINED |
| HL1 | GW and share per heat level class, thermal, by fleet and scenario | w3g_heat_level_classes (planned) | group, fleet, scenario, class | gw_median, pct_median, pct_min, pct_max | DONE (Section 8, level lens): operating 23.8 [17.7-33.1] / 30.6 [26.6-52.9] / 32.4 [31.2-75.9]; planned_all 14.3 [1.6-34.7] / 24.1 [20.1-61.8] / 30.0 [20.6-74.3] (extreme class share) |
| HL2 | Same, hydro | w3g_heat_level_classes (planned) | group = hydro | same | TO BE DEFINED |
| HL3 | Baseline to future class shift | w3g_heat_class_shift (planned) | fleet, scenario | gw_median | TO BE DEFINED |
| HL4 | Change classes (exclusive delta bins) | w3g_heat_change_classes (planned) | group, fleet, scenario | pct_median | TO BE DEFINED |
| HL5 | Map class per cell and GCM agreement | w3g_heat_cell_class (planned) | scenario | class_median, n_gcm_same | TO BE DEFINED |
| DR1 | Null percentiles of F_D future (20,000 simulations) | w4g_null_percentiles (planned) | null, spei_threshold = -1.5 | p50, p90, p99 | PRELIMINARY (n=2,000 only, Section 6): year p99 25.5%, anystart p99 19.2%, free p99 16.11%; final 20,000-draw run TO BE DEFINED |
| DR2 | Hydro GW per drought level class, by scenario | w4g_drought_classes (planned) | group = hydro, class | gw_median, pct_min, pct_max | TO BE DEFINED |
| DR3 | Share above null p99 and share expected by chance | w4g_drought_classes (planned) | class = extreme | pct_median | TO BE DEFINED |
| DR4 | Share with R_D >= 2 and null rate by block | w4a: w4_null_rates | is_production_point | pct_rd_ge | DONE (Section 6): free null block12 18.88%, block24 19.36%, block36 21.87%, block60 20.75%; white noise 1.80% |
| DR5 | Excess over the null, Itaipu b headline, a sensitivity | w4b_excess_over_null.csv | scenario | excess_pp | DONE (C64, D102): hydro BRA, block12/24/36/60 + AR1/white-noise bounds, Itaipu a/b, 108 rows. Headline (operating, Itaipu b, block12), median excess pp SSP126/370/585: +40.75 / +43.20 / +53.94. Block-length sensitivity confirms D83 hypothesis in direction, not monotonic (block60 < block36). |
| DR6 | SPI x SPEI with the same fitting scheme | w4c_spi_vs_spei.csv | group, hazard, scenario, null_type | pct_exposed, excess_pp | DONE (C77/C79, D123/D125): hydro (pool 1,110 series, catchment) vs thermal_water_dependent (pool 341 cells / 1,705 series, cell-scale); v1 merge bug (join on hazard only) fixed in v2 (join on group+hazard). Production null, operating/block12: hydro SPEI 18.88% vs SPI 20.47% (diverge); thermal SPEI 17.74% vs SPI 17.84% (close). Excess over own null, operating/block12: thermal/SPEI +20.63/+28.50/+48.06 pp; thermal/SPI -1.08/+5.44/+27.50 pp (ssp126/370/585). Prior figure "thermal/ssp126 -3.72 pp" is RETRACTED/INVALID (hydro null misapplied to thermal observed); absent from any production CSV. |
| DR7 | Leave-one-out of the 5 largest hydro plants | c23d_7_leave_one_out.csv | plant, scenario | delta_pp | DONE (D113): 5 largest hydro plants x 3 SSPs = 15 rows, delta_pp column. O19 closed in D113. |
| DR8 | GCM range and agreement of the hydro result | w4b_excess_over_null.csv, w4b_agreement.csv | scenario | pct_min, pct_median, pct_max (see DR5 ranges), agreement k/5 | DONE (C74, D120, O21): w4b_agreement.csv, 108 rows; 5/5 GCM agreement in 67 rows, 4/5 in 41 rows, never below 4/5 in that cut. |
| W4f | Hydro SPEI threshold x R_D cut sensitivity grid | w4f_threshold_grid.csv | spei_threshold, rd_cut, scenario | excess_pp | DONE (C78, D124): hydro_reservoir+hydro_run_of_river, SPEI-12, SPEI in {-1.0,-1.5,-2.0} x R_D cut in {1.5,2,3}, 972 rows. Identity check at -1.5 vs production hazards: max|diff|=0; D102 regression check PASS (40.749/43.204/53.945 pp, tol 0.01). At SPEI=-1.0/R_D>=3: median excess ssp126/370 -0.51/-1.16 pp (point estimate below null at that corner; not by itself evidence of significance). Hydro-only grid; no thermal threshold sensitivity yet (see DR6 for the single-threshold thermal/hydro null comparison). |
| CO1 | 4 x 4 cross-tab, GW | w4h_coexposure.csv | group, scenario | gw_median | PARTIAL: only extreme x extreme (see CO2) transcribed; full 16-cell matrix exists in w4h_coexposure.csv (C59, D97) but not yet copied in. TO BE DEFINED for other cells. |
| CO2 | Pct GW share extreme in both, by null variant | w4h_coexposure.csv | heat = extreme, drought = extreme, fleet = operating, cutset = p50_p90_p99 | pct_median (block12/year/anystart) | DONE (C67, D105, source D97): hydro SSP126 36.5/1.3/30.5, SSP370 37.4/11.5/34.4, SSP585 55.9/35.0/50.5; thermal_water_dependent SSP126 7.2/1.4/3.2, SSP370 10.6/2.7/7.3, SSP585 26.4/16.5/18.9. Pct share, not absolute GW; GCM min/max not in source. Canonical=True only for null=block12 (D90). |
| CO3 | High or extreme in both (sensitivity) | w4h_coexposure.csv | heat, drought >= high | gw_median | PENDING, NOT DONE (corrected C67/D105): D97's only attempt was a console-printed sum of 4 already-computed medians, explicitly flagged by D97 itself as invalid (median not additive, D80); never saved to CSV. Correct calculation (raw per-GCM collapse across the 4 cells, then one median) not yet done, no id assigned. Do not cite a CO3 number from D97. |
| ST1 | GW in extreme heat by state and macro-region | w3h_state_summary.csv | class = extreme | gw_median | DONE (C62, D99): BRA, 1,122 rows, checks (a) capacity parity and (b) pre-median national-sum parity both diff 0.00e+00; 19/6,926 plants (0.27%) assigned by nearest-polygon fallback. Headline (all_thermal, operating, ssp585): SP/MA/MS lead (2.88-2.89 GW median). |
| ST2 | Co-exposure by state; units assigned by nearest polygon | w3h_state_coexposure.csv | state | gw_median, n_nearest | DONE (C63, D100): BRA, 2,952 rows, checks (a) capacity parity, (b) pre-median state-sum parity, (c) parity against w4h_coexposure.csv all 0.00e+00-order diffs (max 7.11e-15); CO2 (extreme x extreme) only. CO3 (high-or-extreme both) here is a valid single-flag median computed directly for ST2; it is NOT comparable to any W4h-level CO3 value, because D97's own attempt at that quantity (summing four already-computed medians) was explicitly flagged as invalid in that same decision record and was never adopted (median not additive, D80) -- W4h currently has no valid CO3 number to compare against. Headline (extreme x extreme, operating, ssp585, block12): PA leads in hydro (22.35 GW median), then RO, PR, BA, MG. |
| SE1 | GCM exclusion (drop one, drop UKESM+IPSL) | w3_gcm_exclusion, w3_gcm_exclusion_contrast, w3_gcm_exclusion_rank | exclusion | pct_median, diff_median, sign_changed, order | TO BE DEFINED |
| SE2 | Threshold, weight, TX40 | w3_heat_sensitivity, w3_tx40_curves | choice | diff_median_pp, pct_median | DONE (C63, D101) for weight x TX40 cell only: GW weight median contrast ~0 (n_planned_ge 1-2/5); plant-count weight +12.07/+7.98/+9.87 pp (n_planned_ge 4-5/5). Other cells of this family TO BE DEFINED |
| SE3 | Null type and block size | w4_null_rates | null, block_months | pct_rd_ge | DONE (Section 6/DR4 above); AR1/white-noise bounds DONE (C64, D102) |
| SE4 | Cuts of the classes, percentiles | w5_sensitivity (planned) | family | delta_pp | TO BE DEFINED |
| VA1 | ONS national validation | validation | region = Brazil | rho, rho_ci_low, rho_ci_high, n_years | DONE (D73): rho = 0.361, CI [0.027, 0.811], n = 20 |
| NU1 | Emulator validity (sd, corr, variant, GCM) | w4r_emulator_validation (planned) | - | - | DONE (Section 6, pasted table); formal table export TO BE DEFINED |
| NU2 | F_D future percentiles under the 3 nulls, 20,000 draws | w4r_null_percentiles (planned) | - | - | PRELIMINARY only (n=2,000); see DR1 |
| NU3 | R_D null rates under the 3 nulls | w4r_null_rd (planned) | - | - | PRELIMINARY only (n=2,000); see Section 6 |
| NU4 | Drought classes under the 3 nulls | w4r_drought_classes (planned) | - | - | TO BE DEFINED |
| PL1 | Planned - operating, level lens, paired | W3f-7 table (planned) | - | - | DONE (C63, D101); see Section 8 and SE2 |
| VA2 | Extended validation | W8 table (planned) | - | - | DEFERRED |
| PE1 | SPI vs SPEI | w4c_spi_vs_spei.csv | - | - | DONE (same as DR6, C77/C79, D123/D125); see DR6 row. |
| TH1 | Relative heat threshold | th1_relative_threshold.csv, th1_thresholds.csv, th1_baseline_exceedance.csv | - | - | DONE (C60, D98): cell/GCM scope, BRA, 967 cells, 5 GCMs. Checks PASS: (a) baseline exceedance fraction 0.0500-0.0501; (b) tx35 reproduced 580,200/580,200 rows, max diff 0.0. Baseline mean identical across GCMs (18.27 days/yr, mechanical). Future diverges more under relative cut: ssp585 91.68-189.50 days/yr across GCMs (median threshold 34.4-34.7degC, min ~25degC in some cells). Not GW-weighted, not comparable to H1 headline. Fleet aggregation open (O39). |

---

## Appendix E. Open items

O16 (harvest window, no source); O18 (SPI x SPEI scheme, W4c); O19 (leave-one-
out of Axis 2, W4d); O20 (water x air thermal in Fig 5); O21 (hydro cell
bootstrap); O25 (bootstrap percentile gating, >=10 cells and zero NaN
fraction); O27 (TX40 grid, closed); O28 (heat level cuts, closed C45:
10/30/60); O29 (drought null pool, closed for thermal: cell-scale pool
adopted); O30 (temporal coincidence of heat and drought, not verified); O31
(agreement/k-of-5 definition, closed: same sign across k of 5 GCMs in a
contrast); O32 (cooling bound in co-exposure, not yet computed for the
drought/co-exposure analyses, only for H3); O33 (GCM climate-sensitivity
ranking claim, not verified; [NEED REFERENCE], cite or remove before
submission); O35 (full design documentation of the null: independent-series
sampling in R_D, estimation error, calibrated-baseline effect); O38 (1 of 6
items remaining: constants still outside config/params.yaml; full script audit
not done); O39 (TH1 fleet/GW-level aggregation, not yet done); O40 (mojibake,
closed by mitigation, D103 -- root cause not identified, do not reuse this id
for a new claim).

Pending without an id: re-run W3d and W3f-3 bootstraps at n_boot = 5,000
(currently 2,000); reconcile the Pearson III baseline share quoted as ~26%
in an early draft against the measured 423/1,110 in the current
hydro-BRA pool (Section 4.2) -- likely different sample scopes, not
re-checked; reconcile an earlier note of "6 plants" misclassified by the
hazard-table bucket field against the 5 plants actually found (Section 2).

Author-level open items, outside the pipeline: O20, O33 pending
assignment; India and Portugal analysis deferred until Brazil closes;
external copy/backup of the raw data directory deferred.
---

## Appendix F. Known limitations and planned extensions

To be revisited after the Brazil pipeline closes.

**B1. Exposure only, no link to generation or impact.** Exposure does not
show that generation changes. The article is framed as exposure; a modelled
derating needs coefficients from the literature not yet verified, and would
move the paper toward impact. Options under consideration: (i) an empirical
association between observed monthly generation (ONS open data;
plant-level availability not verified) and observed SPEI-12 or TX in the
past, reported as an association, not an impact model; (ii) a
literature-based sensitivity with explicit, citable coefficients; (iii)
remaining exposure-only and stating this explicitly in the abstract and
discussion. Cost and risk: medium to high, since generation is confounded
by dispatch order, reservoir operation, demand and maintenance, so option
(i) can support at most a statement that exposure is relevant, not a
magnitude of effect.

**B2. Resolution (0.5 degree) and five GCMs.** Coarse for an individual
asset; a small ensemble. Current treatment: ranges across the 5 GCMs, k of
5 agreement, leave-one-GCM-out, never confidence intervals. Options: (i)
compare cell-level TX35 climatology against INMET station records near
plants (distributional, not year-by-year; station availability not
verified); (ii) a larger ensemble or finer-resolution product (e.g.
NEX-GDDP) would be a different pipeline, out of scope. Cost: (i) medium,
(ii) high.

**B3. SPEI with Hargreaves-Samani PET.** Temperature-range PET may over- or
under-state drying under warming. Hargreaves is used for data availability
(needs only tasmax and tasmin). Planned, low cost (W4c): SPI-12 vs SPEI-12
under the same classes, isolating the contribution of atmospheric demand as
computed here -- this does not validate Hargreaves against a better PET
formulation, only measures sensitivity to including it at all. Deferred,
medium/high cost: Penman-Monteith needs wind, radiation and humidity at
daily scale; availability in ISIMIP3b and download size not verified.

**B4. TX35/TX40 thresholds not tied to plant physics.** No link to actual
operating limits of cooling systems or turbines. Done: a grid of 10-100
days of TX35 change, TX40 on its own grid, both level and change lenses,
and a baseline-relative threshold (TH1) showing results are not an artifact
of the absolute 35/40 degC cut. Deferred: technology-specific thermal
limits (need a citable source) and wet-bulb temperature (needs humidity,
not available in the current data).

**B5/B8. Weak observational validation.** rho = 0.361, CI [0.027, 0.811], n
= 20 annual points at national scale; the subsystem split is suspended
(D62, no official plant-to-subsystem map). Constraint: GCM years are not
synchronized with real years, so validation must compare the observed-
forcing index (W5E5-derived SPEI) against observed inflow, or compare
climatological distributions against stations, never GCM output against
observation year-by-year. Options (data availability not verified): (a)
monthly ENA vs SPEI-12 with block bootstrap correcting for autocorrelation;
(b) ENA by hydrological basin if a defensible plant-to-basin mapping can be
built; (c) INMET station climatology vs cell TX35 (see B2); (d) generation
checks (see B1). Cost: medium; does not change the current work-plan order
if scheduled as module W8, after Section 7 (co-located exposure) closes.

**B6. Planned vs operating result near zero under GW weighting.** Already
treated as a substantive result in Section 8, with intervals, ranges, and
the plant-count-weighting reversal reported explicitly, not minimized.

**B7. Trend in the baseline.** The three null models (Section 6) assume
stationarity; the real GCM baselines carry their own trend, documented as a
limitation there. Planned, low cost: a trend-removed emulator variant as an
explicit, separately labelled sensitivity (never the headline null), to
isolate how much of the sd gap in the per-GCM validation table is driven by
trend versus some other property of each GCM's internal variability.
---

## Appendix G. Archive pointers

The following content was produced under earlier design iterations and is
not part of the current Brazil-only scope (D71). It is preserved for
traceability, not reproduced in this document:

- **docs/archive/METHODS_SPEC_v1_pre_rework.md**: the original
  three-country (Brazil, India, Portugal) design, including the compound
  hydro-heat metric's original LR_C specification (superseded by diff_pp
  and dependence_ratio, D63/D72; see Appendix A, Step 10), the national
  compound-event analysis, and the full Portugal (REN IPH, DGEG) and India
  validation methodology and results (D59-D61, O10, O11).
- **docs/archive/METHODS_SPEC_v2.2_pre_C66.md**: the immediately prior
  version of this document (the v2.2 consolidated Methods, C48 draft, with
  all edits through C65/D103), kept as the direct predecessor of the
  current restructuring (C66/D104). Every number in the current document
  traces back to this file or to docs/DECISIONS.md; nothing was
  recalculated during the C66 restructuring.
- **docs/DECISIONS.md**: the full decision log (D1 through the current
  maximum id), the single source of truth for every number cited in this
  document. Any discrepancy between this document and DECISIONS.md should
  be resolved in favor of DECISIONS.md, and reported as an error in this
  document.
- **docs/STATUS_LOG.md**: the session-by-session technical log (commands,
  checks, pass/fail outcomes), useful for understanding how a DECISIONS.md
  entry was produced, not needed to use its result.

This document (METHODS_SPEC.md) is the current, article-oriented synthesis
of the above; it is restructured periodically (as in C66) to track the
state of the analysis, but it is never the primary record of a decision --
DECISIONS.md is.