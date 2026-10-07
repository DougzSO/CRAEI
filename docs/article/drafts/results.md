# Results, figure and table captions (draft)

Status: captions moved out of the figures (Phase 9, D155); the results paragraphs are [AUTHOR] slots to be
completed in Phase W. Register rows [R01]... are those of docs/article/DECISION_MEMO_F5.md section (d) (R1 = [R01],
and so on). All numbers come from the CSVs named in each block. Scenarios: SSP1-2.6 / SSP3-7.0 / SSP5-8.5.
Baseline 1985-2014, future 2041-2070 unless stated (E1: future 2042-2070, observed W5E5 1986-2014).

---

**Figure 1.** Heat exposure of the thermal fleet rises with scenario severity: 205, 291 and 340 of 745 thermal
plants sit in extreme-heat cells under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Projected TX35 heat exposure
classification of the 0.5 degree cells of Brazil (low, medium, high, extreme; median across 5 GCMs; background)
and of the thermal plants (markers coloured by the class of their cell, with the same colours as the
background). Marker shape = technology (diamond, water-dependent thermal; triangle, air-cooled thermal); marker
size proportional to capacity (MW). Hydropower is excluded by design (H1, D88): the heat hazard is defined for
thermal plants only. Panel titles give the number of plants in extreme-heat cells out of 745. Scale bar: 0, 500 and 1000 km.
Source: w3g_heat_cell_class.csv, plants.parquet [R05].

[AUTHOR] Results paragraph for Figure 1: spatial pattern of heat exposure (cells and plants), counts by scenario.

---

**Figure 2.** Heat exposure of the thermal fleet increases with scenario severity at every threshold. Share of
thermal fleet capacity (median across 5 GCMs, %) with at least the threshold number of days per year above 35 C
(TX35), for thresholds of 10 to 100 days, for the operating fleet (solid; 47.7 GW, 774 units) and the planned fleet
(dashed; 48.3 GW, 108 units). Shaded bands: minimum to maximum across the 5 GCMs for the operating fleet at every
threshold. SSP5-8.5 emphasized. Supplementary figure. Source: w3_curves_plot.csv [R05].

[AUTHOR] Results paragraph for Figure 2 (supplementary): 28.4%, 36.3% and 49.1% of operating capacity at the
30-day headline threshold.

---

**Figure 3.** Drought exposure rises with scenario severity: 339, 433 and 770 of 921 plants have a median
future-to-baseline frequency ratio of SPEI-12 at or below -1.5 (R_D) of at least 2. Projected drought exposure of
hydropower and thermal plants in Brazil. A plant is exposed when the median over 5 GCMs of R_D, the ratio of the
future to the baseline frequency of SPEI-12 <= -1.5, is at least 2.0 (red); otherwise it is not exposed (blue).
Marker shape = technology (circle, hydropower; diamond, water-dependent thermal; triangle, air-cooled thermal);
marker size proportional to capacity (MW). Panel titles give the number of exposed plants out of 921. Source: w4g_fd_unit_values.csv, plants.parquet.

[AUTHOR] Results paragraph for Figure 3: spatial pattern of drought exposure; hydropower and thermal.

---

**Figure 4.** Drought exposure relative to a stationary resampling null, Brazil's operating fleet. Excess of the
share of operating capacity with R_D >= 2.0 over the null rate, in percentage points, for hydropower (Itaipu at
the Brazilian share, 102.7 GW, 194 plants) and water-dependent thermal capacity (39.1 GW, 618 plants), with SPEI-12
and with SPI-12. Point = median, line = range across 5 GCMs; labels give the median and, in parentheses, the
number of GCMs with the sign of the median (k of 5). Null: baseline and future drawn independently at random from
the pool (12-month blocks, 2,000 draws, no trend); excess = observed share minus the null rate. Pools differ by
scale: hydropower, 1,110 catchment-scale series (null rates 18.88% SPEI, 20.47% SPI); thermal, 1,705 cell-scale
series (17.74% SPEI, 17.84% SPI). Source: w4c_spi_vs_spei.csv, w6_agreement_k.csv [R01]-[R04].

[AUTHOR] Results paragraph for Figure 4: hydro SPEI +41, +43 and +54 pp (5/5 GCMs); SPI as the lower band (3/5);
thermal clear only under SSP5-8.5 (+48 pp SPEI, +27.5 pp SPI) and model-dependent otherwise; 3-GCM subset (D148).

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

[AUTHOR] Results paragraph for Figure 5a: states and regions, national co-extreme (36.9, 35.2 and 54.2 GW), role
of a few large plants and of the GCM spread (D148).

---

**Figure 5b.** For water-dependent thermal capacity, 1, 7 and 10 of 26 states have more than half of their
capacity under extreme heat and extreme drought combined under SSP1-2.6, SSP3-7.0 and SSP5-8.5. Same design as
Figure 5a for the operating water-dependent thermal fleet (618 plants, 39.1 GW; classified by plant-level cooling
class, D151); the circle scale is larger than in Figure 5a (legend). Supplementary figure. Source:
w3h_state_coexposure.csv, table3_coexposure_gcm_mean.csv [R08].

[AUTHOR] Results paragraph for Figure 5b (supplementary): thermal co-exposure by state (4.2, 6.5 and 12.0 GW, mean).

---

**Figure 6.** Heat exposure by fuel type varies widely: nuclear capacity shows none, and multi-fuel capacity is
insensitive to the scenario. Share of fuel-class capacity with at least 30 days per year of TX35 exceedance
(median across 5 GCMs, %) for the operating and planned thermal fleets; capacity (GW) and number of units (n)
under each label. Nuclear is shown at 0% in all scenarios (operating and planned); oil has no planned capacity
("n/a" = no capacity of that fuel class). Gas includes water-dependent and air-cooled units (see Table 1 for the
split). Supplementary figure. Source: w3_table1.csv at threshold 30 [R05].

[AUTHOR] Results paragraph for Figure 6 (supplementary).

---

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

[AUTHOR] Results paragraph for Figure 7: D observed 4.83 [1.70, 6.32] against GCM median 5.00; heat pair 1.14
[0.28, 2.48] against 2.78; dP(HT) +0.095 = +0.065 + 0.030 under SSP5-8.5; dD up in 3/5 GCMs; regions.

---

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

[AUTHOR] Results paragraph for Figure 8: rho 0.370 [0.174, 0.570] in SE/CO; NE 0.745, S 0.515, N 0.494; lift and
HSS; wording "moderate and significant association", not validation (D146).

---

**Table 2.** Leave-one-out sensitivity of the hydropower drought exposure to the five largest plants. Share of the
operating hydro capacity of each bucket (reservoir, run-of-river) with R_D >= 2.0 (future-to-baseline frequency
ratio of SPEI-12 <= -1.5), capacity-weighted, median across 5 GCMs, for the full fleet and with each plant removed;
delta = share with the plant removed minus share with the full fleet. This is the raw capacity share, not the
excess over the null, and is not comparable with the headline excess of Figure 4. Itaipu at the Brazilian share
(7,000 MW); the whole binational asset (14,000 MW) is in the sensitivity table. Reservoir bucket: 66.4 GW, 135
plants; run-of-river: 36.2 GW, 59 plants. Source: w4d_leave_one_out.csv [R19].

[AUTHOR] Results paragraph for Table 2: influence of Itaipu, Belo Monte and Tucuruí on the reservoir share.

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

[AUTHOR] Results paragraph for Table 3: extreme x extreme cell by group and scenario; additivity; limits.
