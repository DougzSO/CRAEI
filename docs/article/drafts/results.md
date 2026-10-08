# Results (draft)

Status: draft for the author (Phase W). Captions are those of Phase 9 (D155) and are unchanged; each block is followed by its results paragraph. Every number cites a register row [R..] (docs/article/DECISION_MEMO_F5.md, rows R1-R28; R1 = [R01]). Order follows the five framing sentences; the figure numbers are those of the files (see outline.md for the text order). Scenarios: SSP1-2.6 / SSP3-7.0 / SSP5-8.5. Baseline 1985-2014, future 2041-2070 unless stated (E1: future 2042-2070, observed W5E5 1986-2014).

---

## 3.1 Hydropower drought exposure exceeds the null

**Figure 3.** Drought exposure rises with scenario severity: 339, 433 and 770 of 921 plants have a median
future-to-baseline frequency ratio of SPEI-12 at or below -1.5 (R_D) of at least 2. Projected drought exposure of
hydropower and thermal plants in Brazil. A plant is exposed when the median over 5 GCMs of R_D, the ratio of the
future to the baseline frequency of SPEI-12 <= -1.5, is at least 2.0 (red); otherwise it is not exposed (blue).
Marker shape = technology (circle, hydropower; diamond, water-dependent thermal; triangle, air-cooled thermal);
marker size proportional to capacity (MW). Panel titles give the number of exposed plants out of 921. Source: w4g_fd_unit_values.csv, plants.parquet.

Under SSP1-2.6, SSP3-7.0 and SSP5-8.5, 339, 433 and 770 of 921 plants have a median R_D of at least 2 [R23]. Among the 222 hydropower plants 118, 93 and 176 are exposed, and among the 694 water-dependent thermal plants 219, 338 and 590 [R23]. The count of exposed hydropower plants is lower under SSP3-7.0 than under SSP1-2.6; one or two GCMs and a few large plants set that sign (Section 3.6) [R20]. [AUTHOR: spatial pattern of exposed and unexposed plants by region, read from the map.]

---

**Figure 4.** Drought exposure relative to a stationary resampling null, Brazil's operating fleet. Excess of the
share of operating capacity with R_D >= 2.0 over the null rate, in percentage points, for hydropower (Itaipu at
the Brazilian share, 102.7 GW, 194 plants) and water-dependent thermal capacity (39.1 GW, 618 plants), with SPEI-12
and with SPI-12. Point = median, line = range across 5 GCMs; labels give the median and, in parentheses, the
number of GCMs with the sign of the median (k of 5). Null: baseline and future drawn independently at random from
the pool (12-month blocks, 2,000 draws, no trend); excess = observed share minus the null rate. Pools differ by
scale: hydropower, 1,110 catchment-scale series (null rates 18.88% SPEI, 20.47% SPI); thermal, 1,705 cell-scale
series (17.74% SPEI, 17.84% SPI). Source: w4c_spi_vs_spei.csv, w6_agreement_k.csv [R01]-[R04].

Under SPEI-12, the share of operating hydropower capacity with R_D of at least 2 exceeds the null rate by +40.75, +43.20 and +53.94 pp (SSP1-2.6, SSP3-7.0, SSP5-8.5), and all five GCMs share the sign of the median in each scenario [R01]. The ranges across GCMs are +3.18 to +59.81, +1.42 to +61.32 and +25.70 to +66.92 pp [R01]. The excess is weaker under precipitation-only SPI-12: +17.40, +3.03 and +38.60 pp, with three GCMs sharing the sign in each scenario and ranges that include zero (-12.93 to +35.38, -12.67 to +25.71, -19.48 to +60.89 pp) [R02]. We take the SPEI result as the claim and the SPI result as its lower band; the difference indicates that part of the projected drying comes from evaporative demand. The result for the three-GCM subset is the same as for five GCMs under SPEI (+40.75, +43.20, +53.94 pp) and close under SPI (+18.14, +3.77, +39.34 pp, with the null re-simulated for the subset) [R01, R02]. [AUTHOR: interpretation of the SPEI-SPI gap and the literature on PET-based indices.] [CIT-NEEDED: PET-based drought indices overstate drying, Milly and Dunne 2016]

---

**Table 2.** Leave-one-out sensitivity of the hydropower drought exposure to the five largest plants. Share of the
operating hydro capacity of each bucket (reservoir, run-of-river) with R_D >= 2.0 (future-to-baseline frequency
ratio of SPEI-12 <= -1.5), capacity-weighted, median across 5 GCMs, for the full fleet and with each plant removed;
delta = share with the plant removed minus share with the full fleet. This is the raw capacity share, not the
excess over the null, and is not comparable with the headline excess of Figure 4. Itaipu at the Brazilian share
(7,000 MW); the whole binational asset (14,000 MW) is in the sensitivity table. Reservoir bucket: 66.4 GW, 135
plants; run-of-river: 36.2 GW, 59 plants. Source: w4d_leave_one_out.csv [R19].

Removing one of the five largest plants changes the reservoir-bucket share by less than 10 pp in every scenario [R26]. The full-fleet shares are 55.54, 55.10 and 74.03% [R19]. Without Itaipu the share changes by +6.54, +6.49 and -3.06 pp; without Belo Monte by +2.28, -9.14 and +5.49 pp; without Tucurui by -0.41, -6.62 and -3.83 pp [R26]. In the run-of-river bucket (67.14, 72.01 and 79.27%), removing Jirau or Santo Antonio lowers the share by 2.26 to 3.79 pp [R26]. The sign of the SSP3-7.0 change depends on a few large plants [R20]. [AUTHOR: reading of the leave-one-out for the headline claim.]

---

**Figure 5a.** Under extreme heat and extreme drought combined, 8, 5 and 11 of 19 states with hydropower have more
than half of their hydropower capacity exposed under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Hydropower (Itaipu at the
Brazilian share): share of each state's own operating capacity under extreme heat (TX35 class) and extreme
drought (F_D class against the block12 null), same GCM, median across 5 GCMs (colour, five classes), and capacity
under both extremes (hollow circles, area proportional to GW, median across GCMs). Gray hatched states have no
hydropower capacity; dotted states have three or fewer plants, so the median over five GCMs rests on few units.
The share is a state share, not a national share. Heat is shown as regional climatic context at the plant cell
(TX35 class), not as a heat hazard to hydropower, which is outside H1. Compound = extreme drought class (catchment)
and extreme heat class (plant cell), same GCM. For the national operating fleet, the compound share is 81%, 84%
and 87% of the extreme-drought share alone (SSP1-2.6 / SSP3-7.0 / SSP5-8.5; mean across 5 GCMs: 35.9 of 44.2%,
34.3 of 40.6%, 52.8 of 60.4%). Under precipitation-only SPI, hydro drought exposure agrees in only 3/5 GCMs
(Figure 4), and observed heat x drought dependence is absent (D = 1.14 [0.28, 2.48]; GCMs ~2.8), so the co-extreme
share is partly an artefact of the temperature dependence of SPEI-Hargreaves. Source: w3h_state_coexposure.csv,
table3_coexposure_gcm_mean.csv [R06], [R07], [R14].

In 8, 5 and 11 of the 19 states with hydropower, more than half of the state's hydropower capacity is under extreme heat and extreme drought (SSP1-2.6, SSP3-7.0, SSP5-8.5) [R24]. Nationally, 36.9, 35.2 and 54.2 GW (mean over GCMs) are in that cell, 35.9, 34.3 and 52.8% of the fleet, with ranges of 11.3 to 60.3, 1.2 to 76.5 and 4.0 to 84.6 GW across GCMs [R06]. The cell holds 81, 84 and 87% of the capacity in extreme drought alone [R07]. Under SSP5-8.5 Para has the largest co-extreme capacity, 22.35 GW [R24]. In W5E5 observations the heat and drought pair shows no dependence (D = 1.14, interval 0.28 to 2.48), whereas the GCMs give a baseline D of about 2.8 [R14], and SPI-12 exposure agrees in only three of five GCMs [R02]. The co-extreme share is therefore probably inflated by the temperature term of SPEI-Hargreaves and by the GCM dependence. The three-GCM subset gives 34.2, 31.1 and 44.1 GW and 86, 90 and 79% [R06, R07]. [AUTHOR: regional reading of the map (North, Center-West, Northeast, Southeast, South).]

---

## 3.2 Thermal backup: heat in all GCMs, drought mainly under SSP5-8.5

**Figure 1.** Heat exposure of the thermal fleet rises with scenario severity: 205, 291 and 340 of 745 thermal
plants sit in extreme-heat cells under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Projected TX35 heat exposure
classification of the 0.5 degree cells of Brazil (low, medium, high, extreme; median across 5 GCMs; background)
and of the thermal plants (markers coloured by the class of their cell, with the same colours as the
background). Marker shape = technology (diamond, water-dependent thermal; triangle, air-cooled thermal); marker
size proportional to capacity (MW). Hydropower is excluded by design (H1, D88): the heat hazard is defined for
thermal plants only. Panel titles give the number of plants in extreme-heat cells out of 745. Scale bar: 0, 500 and 1000 km.
Source: w3g_heat_cell_class.csv, plants.parquet [R05].

The number of the 745 thermal plants in cells of extreme TX35 class rises from 205 under SSP1-2.6 to 291 under SSP3-7.0 and 340 under SSP5-8.5 [R22]. [AUTHOR: spatial pattern: where the extreme cells are and which plants stay in low or medium cells.]

---

**Figure 2.** Heat exposure of the thermal fleet increases with scenario severity at every threshold. Share of
thermal fleet capacity (median across 5 GCMs, %) with at least the threshold number of days per year above 35 C
(TX35), for thresholds of 10 to 100 days, for the operating fleet (solid; 47.7 GW, 774 units) and the planned fleet
(dashed; 48.3 GW, 108 units). Shaded bands: minimum to maximum across the 5 GCMs for the operating fleet at every
threshold. SSP5-8.5 emphasized. Supplementary figure. Source: w3_curves_plot.csv [R05].

The share of operating thermal capacity with at least 30 days per year of TX35 is 28.4, 36.3 and 49.1% (median over GCMs; 47.7 GW) [R05]. The range across GCMs is 19.1 to 49.3, 31.4 to 77.0 and 42.3 to 92.2% [R05]. In at least one GCM 49.3, 77.0 and 92.2% of the capacity is exposed, and in all five GCMs 14.4, 31.2 and 36.3% [R05]. The three-GCM subset gives 22.1, 34.1 and 43.2% [R05]. For the planned fleet (48.35 GW) the shares are 15.9, 39.0 and 61.6%, with ranges of 6.3 to 61.7, 20.6 to 76.9 and 43.1 to 94.4% [R28]. The share is a function of the threshold: the curves fall as the threshold rises from 10 to 100 days, and the ordering of the scenarios holds at every threshold. [AUTHOR: reading of the threshold dependence.]

---

**Figure 6.** Heat exposure by fuel type varies widely: nuclear capacity shows none, and multi-fuel capacity is
insensitive to the scenario. Share of fuel-class capacity with at least 30 days per year of TX35 exceedance
(median across 5 GCMs, %) for the operating and planned thermal fleets; capacity (GW) and number of units (n)
under each label. Nuclear is shown at 0% in all scenarios (operating and planned); oil has no planned capacity
("n/a" = no capacity of that fuel class). Gas includes water-dependent and air-cooled units (see Table 1 for the
split). Supplementary figure. Source: w3_table1.csv at threshold 30 [R05].

Nuclear capacity (1.99 GW) has no exposure in any scenario, and multi-fuel capacity (1.33 GW) is at 62.8% in all three scenarios [R25]. Coal (3.00 GW) rises from 0.0% to 12.0% and 48.2%, bioenergy (17.43 GW) from 41.7% to 61.2% and 68.2%, gas (19.32 GW) from 22.4% to 22.4% and 40.4%, and oil (4.60 GW) from 24.1% to 24.1% and 34.7% [R25]. The planned gas capacity (44.12 GW) is at 14.4, 39.1 and 62.1% [R28]. [AUTHOR: reading by fuel; what explains the flat gas and oil values between SSP1-2.6 and SSP3-7.0.]

---

For water-dependent thermal capacity (Figure 4), the SPEI-12 excess over the null is +20.63, +28.50 and +48.06 pp, with four, four and five GCMs sharing the sign [R03]. The range across GCMs includes zero under SSP1-2.6 (-6.40 to +39.46 pp) and SSP3-7.0 (-15.21 to +50.21 pp) and excludes it under SSP5-8.5 (+6.33 to +70.31 pp) [R03]. Under SPI-12 the excess is -1.08, +5.44 and +27.50 pp, with agreement in three, three and four GCMs and ranges that include zero in all scenarios [R04]. Thermal drought exposure is therefore clear only under SSP5-8.5 and depends on the GCM in the lower scenarios. In the three-GCM subset the SPEI excess falls to +8.34, +18.74 and +34.53 pp and the SPI excess to -4.80, -7.48 and +27.50 pp, so the SPI excess loses its sign under SSP3-7.0 [R03, R04]. Heat is more robust than drought: the share of water-dependent thermal capacity under monthly heat stress (N35 above the baseline P90) rises from 6.5% to 23.2, 29.8 and 35.2% in all five GCMs in every scenario [R21].

---

**Figure 5b.** For water-dependent thermal capacity, 1, 7 and 10 of 26 states have more than half of their
capacity under extreme heat and extreme drought combined under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Same design as
Figure 5a for the operating water-dependent thermal fleet (618 plants, 39.1 GW; classified by plant-level cooling
class, D151); the circle scale is larger than in Figure 5a (legend). Supplementary figure. Source:
w3h_state_coexposure.csv, table3_coexposure_gcm_mean.csv [R08].

Among the 26 states with water-dependent thermal capacity, 1, 7 and 10 have more than half of their capacity under extreme heat and extreme drought (SSP1-2.6, SSP3-7.0, SSP5-8.5) [R24]. Nationally, 4.23, 6.52 and 12.02 GW (10.8, 16.7 and 30.7% of the fleet) are in that cell [R08]. Under SSP5-8.5 Sao Paulo (2.67 GW) and Mato Grosso do Sul (2.56 GW) hold the largest capacity [R24]. [AUTHOR: reading of the thermal state pattern.]

---

## 3.3 The hedge is already correlated in the observed climate

**Figure 7.** Thermal backup is already correlated with hydro drought, and warming raises joint stress mainly
through the marginals. (a) Dependence D = P(H and T) / (P(H) P(T)) between hydro drought (H, share of hydro
capacity with SPI-12 <= -1.5) and thermal stress (T) for the control pair (T = share of thermal capacity with
SPI-12 <= -1.5) and the heat pair (T = share of thermal capacity above its local baseline P90 of monthly hot days);
events are exceedances of the P90 of each series. Black: observed in W5E5 1986-2014 with the 95% moving-block
bootstrap interval (12 months, 2,000 draws); grey: the five GCMs at baseline 1985-2014 (diamonds) and their
median. Dashed line: independence (D = 1). (b) Change in P(H and T) from baseline to future (2042-2070) for the
control pair, with the baseline P90 applied to the future: median marginal and dependence components (stacked), the
median of the total (black bar) and the five GCM totals (dots); the components are medians over the GCMs and need
not add up to the median of the total (SSP3-7.0: 0.009 against 0.012). (c) D by macro-region for the control pair,
thermal capacity restricted to the region against national hydro: observed (black, 95% CI) and GCM baseline
(grey, median and range); dotted line: national observed D (4.83); region labels give thermal GW and number of
plants. Operating thermal fleet, 39.1 GW, 618 plants. Source: e1_hedge_observed.csv, e1_hedge_metrics.csv,
e1_hedge_delta.csv, e1_hedge_summary.csv, e1_colocation.csv [R09]-[R15].

In W5E5 over 1986-2014, hydropower drought and thermal drought co-occur 4.83 times as often as under independence (95% interval 1.70 to 6.32); the probability that thermal capacity is under drought is 0.486 in hydropower-drought months (P(T given H)) against 0.101 in all months (P(T)) [R12]. The intervals for blocks of 24 and 36 months are 1.42 to 5.97 and 1.24 to 5.68, and a circular-shift test gives p < 0.001 [R12]. The GCMs reproduce the dependence at baseline (median D = 5.00, range 3.61 to 8.61) [R13]. D is 3.69 in the Southeast (interval 1.17 to 5.60), 3.41 in the Center-West (0.88 to 5.97), 2.25 in the North (0.29 to 5.15), 2.27 in the South (0.00 to 3.80) and 1.14 in the Northeast (0.57 to 4.09) [R15]; only the Southeast interval excludes 1. The Southeast and Center-West hold 64% of the operating thermal capacity [R15]. The heat pair does not show the dependence in observations (D = 1.14, interval 0.28 to 2.48, p = 0.43), whereas the GCM baseline median is 2.78 (range 1.67 to 3.33) [R14]. [AUTHOR: interpretation of the regional pattern and of the observed-model difference; literature on hydro-thermal complementarity in Brazil.] [CIT-NEEDED: hydrothermal complementarity in the Brazilian system]

---

## 3.4 Warming raises joint stress through the marginals

Under variant A, P(H and T) in the control pair rises from 0.050 at baseline to 0.112, 0.072 and 0.172 (Figure 7b), a change of +0.034, +0.012 and +0.095 [R09]. The medians of the marginal part are 0.022, 0.008 and 0.065 and of the dependence part 0.012, 0.001 and 0.030; the parts are medians over the GCMs and need not add up to the median of the total [R09]. The change is positive in four, three and five of the five GCMs [R09]. The pre-specified primary criterion required at least four of five GCMs under both SSP3-7.0 and SSP5-8.5; it is not met, because SSP3-7.0 has three [R09]. In the three-GCM subset the change is 0.000, -0.006 and +0.095, positive in two, one and three of three GCMs [R09]. The coupling does not strengthen consistently. Under variant B, D changes by +0.18, +0.40 and +0.11 from a baseline median of 5.00; three of five GCMs share the sign in each scenario, and the lower bound of the dD interval is above zero in none of the GCMs under SSP3-7.0 and SSP5-8.5 [R10]. For the heat pair the change in P(H and T) is +0.087, +0.079 and +0.214, almost all of it marginal (+0.072, +0.083, +0.191) [R11]; the interval of the change lies above zero in three of five GCMs under SSP3-7.0 and in five of five under SSP5-8.5 [R11]. Warming therefore raises the joint stress mainly by making each side fail more often, and the evidence for stronger coupling is weak. [AUTHOR: interpretation of the marginal and dependence split.]

---

## 3.5 Evidence quality: drought index and inflow, co-exposure

**Figure 8.** The drought index tracks observed natural inflow moderately, and least in the Southeast/Center-West.
(a) Spearman correlation between the hydro-capacity-weighted W5E5 SPEI-12 of each region and the standardized
monthly anomaly of the natural inflow energy (ENA bruta, ONS), 2000-2019 (240 months), for lags of 0 to 6 months
(SPEI-12 at t-L, ENA at t), with the 95% moving-block bootstrap interval (12 months, 2,000 draws); the shaded band
marks the lags (0-3) of the pre-specified criterion for SE/CO. (b) Lift of the probability of a drought month in
ENA (anomaly at or below the 20th percentile of its calendar month) given a drought signal (SPEI-12 <= -1.5) over
the 20% base rate, lag 0, with the 95% moving-block bootstrap interval; labels give the number of signal months and
the Heidke skill score; regions with fewer than 10 signal months are not reportable. Regions approximate the ONS
submarkets by macro-region (SE/CO = Southeast + Center-West); capacity (GW) and number of plants in the legend.
Source: e3_spearman.csv, e3_hit_rate.csv [R16]-[R18].

SPEI-12 and standardized natural inflow are positively correlated in the Southeast and Center-West at lag 0 (Spearman rho = 0.370, 95% interval 0.174 to 0.570, n = 240 months); the intervals for lags 1 to 3 include zero [R16]. SPI-12 gives 0.397 (0.197 to 0.576) [R16]. The correlation is higher in the Northeast (0.745), the South (0.515) and the North (0.494) [R17]. The pre-specified criterion is met, and we describe the result as a moderate and significant association, not a validation [D146]. The hit-rate analysis is weaker. In the Southeast and Center-West the signal (SPEI-12 <= -1.5) occurs in 14 months; the lift over the 20% base rate is 2.5 (interval 0.00 to 5.22), the probability of detection 0.146 and the Heidke skill score 0.149 (-0.009 to 0.327), so the interval does not exclude no skill [R18]. The lift is 3.67 in the Northeast (interval 2.18 to 7.03; skill score 0.485) and 3.08 in the North (1.65 to 6.30; 0.194); the South has two signal months and is not reportable [R18]. The index tracks inflow least in the region where the E1 dependence concentrates [R15, R16]. [AUTHOR: the South in 2014-2015, wet in both the index and the inflow (D146), as evidence of regional discrimination; ENA as natural inflow without reservoir operation.]

---

**Table 3.** Heat x drought co-exposure cross-tab (4 x 4), mean across 5 GCMs. Rows = heat class (TX35, future),
columns = drought class (F_D future against the block12 null, cuts p50/p90/p99), both from the same GCM; each cell
gives % of fleet capacity (mean GW) [min-max across GCMs, GW]. The 16 means of each table add up to the fleet total
(hydropower 102.7 GW, 194 plants; water-dependent thermal 39.1 GW, 618 plants), unlike the headline results, which
use the median. Hydropower (Itaipu at the Brazilian share): heat is regional climatic context at the plant cell,
not a hydro hazard (H1); the compound share is 81%, 84% and 87% of the extreme-drought share alone (SSP1-2.6 /
SSP3-7.0 / SSP5-8.5). Water-dependent thermal: the drought classes use the cut points of the W4g reference pool
(1,710 series, unit-level population) applied to the 618-plant population classified by plant-level cooling class
(D151). In W5E5 observations the heat x drought pair shows no dependence (D = 1.14, 95% CI 0.28-2.48 includes 1),
whereas the GCMs give a baseline D of about 2.8; GCM heat x drought co-exposure is therefore probably inflated
relative to observations. The per-cell median version (not additive; gap column) is the reference table in the
supplementary material. Source: table3_coexposure_gcm_mean.csv [R06]-[R08].

Hydropower: extreme heat and extreme drought co-locate in 36.9, 35.2 and 54.2 GW (mean over GCMs), equal to 81, 84 and 87% of the capacity in extreme drought [R06, R07]. Water-dependent thermal capacity: 4.23, 6.52 and 12.02 GW, or 10.8, 16.7 and 30.7% of the fleet, with ranges of 1.79 to 10.69, 0.33 to 17.76 and 5.39 to 26.46 GW [R08]. For the three-GCM subset the thermal values are 2.82, 3.60 and 7.72 GW [R08]. The cross-tab means add up to the fleet total, which the medians do not. Because the observed heat and drought pair shows no dependence and the GCMs do [R14], we read the GCM co-exposure as an upper estimate. [AUTHOR: other cells of the 4 x 4 table and the supplementary medians.]

---

## 3.6 Results that do not support a stronger reading

Several results do not support the stronger reading and are part of the findings. (i) The primary E1 criterion is not met: the control-pair P(H and T) rises in three of five GCMs under SSP3-7.0 [R09]. (ii) The change in coupling, dD, is not consistently positive (three of five GCMs) and its interval excludes zero in no GCM [R10]. (iii) Hydropower SPI-12 exposure agrees in three of five GCMs, and the SSP3-7.0 excess is +3.03 pp with a range from -12.67 to +25.71 pp [R02]. (iv) Thermal drought exposure is clear only under SSP5-8.5, and the SPI excess loses its sign under SSP3-7.0 in the three-GCM subset [R03, R04]. (v) The hit-rate skill score for the Southeast and Center-West has an interval that includes zero (14 signal months) [R18], and the index tracks inflow least where the E1 dependence concentrates [R15, R16]. (vi) The observed heat and drought dependence is absent (D = 1.14), so GCM co-exposure is probably inflated [R14]. (vii) Cases with SSP3-7.0 below SSP1-2.6 depend on one or two GCMs and a few large plants [R20].
