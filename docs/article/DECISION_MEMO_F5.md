# Decision memo, Phase 5: framing and final list of artifacts

Status: proposal for the author. No analysis changed. Decisions are requested for items (a), (c) and (e);
(b) follows the pre-specified criterion (D144, D145). Journal: Climate Risk Management (D142).
Numbers come from the CSVs named in each row (outputs_tables_dir); thermal values use the plant-level
population of D151 (618 plants, 39.1015 GW).

## 0. Journal limits (plan item 1)

Source: <https://www.sciencedirect.com/journal/climate-risk-management/publish/guide-for-authors>
(Elsevier guide for authors). The page returned HTTP 403 to the fetch tool (also under
elsevier.com/journals/climate-risk-management/2212-0963/guide-for-authors), so only what a search
result quoted from it is used:

| Item | Value |
|---|---|
| Original research article, length | up to 8,000 words, including main text, table and figure captions, excluding references; longer accepted occasionally if the topic demands it |
| Highlights, graphical abstract | listed among the submission requirements; counts and sizes TO BE DEFINED |
| Abstract length and format | TO BE DEFINED |
| Maximum number of figures and tables | TO BE DEFINED |
| Figure width, dpi | TO BE DEFINED |
| Supplementary material rules | TO BE DEFINED |
| Data / code availability statement | TO BE DEFINED |

No Elsevier-wide default is assumed. O52 asks the author to read the guide in a browser and fill the
TO BE DEFINED cells; item (c) below is written so that it holds for any figure limit.

## (a) Figure E1: two designs (description only)

Content required in either design: D observed against the GCM range (pair SPI x SPI and a heat pair),
P(H and T) baseline against future with the marginal / dependence decomposition, and co-location by
macro_region.

Numbers the figure carries: observed D 4.83, block-12 CI [1.70, 6.32], GCM baseline median 5.00
[3.61, 8.61] (SPI x SPI); heat pair observed 1.14 [0.28, 2.48] against GCM 2.78 [1.67, 3.33];
P(H and T) control pair 0.050 -> 0.112 / 0.072 / 0.172 (SSP1-2.6 / 3-7.0 / 5-8.5), of which marginal
0.022 / 0.008 / 0.065 and dependence 0.012 / 0.001 / 0.030; macro_region D observed SE 3.69, CO 3.41,
NE 1.14, N 2.25, S 2.27 (thermal GW 19.75, 5.37, 7.78, 1.05, 5.15).

**Design A, three panels in one row.**
(1) Dot-and-interval: for the two pairs, observed D with its block-12 CI and the five GCM baseline D
values as small markers (range bar), reference line D = 1.
(2) Decomposition: for SPI x SPI, per scenario a stacked bar of the median dP(HT) split into marginal and
dependence, with the five GCM totals as dots (shows the SSP3-7.0 dispersion, k = 3/5).
(3) Region bars: D observed with CI by macro_region (SE, CO, NE, N; S shown with 2 signal months
flagged), thermal GW written under each label, GCM baseline median as a tick.
Pro: one idea per panel, fits one page width. Con: the heat pair appears only in panel 1.

**Design B, two rows.**
Top row, three panels, one per pair (SPI x SPI, SPEI x SPEI as upper bound, SPI x heat): baseline and
future P(H and T) as paired points per GCM for the three scenarios, with the marginal / dependence
decomposition of the median written as a number above the future points. Bottom row: left, observed
against GCM baseline D for all eight pairs (lollipop, CI on observed); right, the macro_region bars of
Design A. Pro: shows that heat pairs rise through marginals (dP up in 5/5 GCMs) while dD is up in at
most 3/5, and the circularity control (SPEI against SPI) in the same figure. Con: denser, probably needs
a full page.

Recommendation: Design A as the main figure; the all-pairs lollipop and SPEI x SPEI of Design B go to
supplementary.

## (b) E3 destination

The pre-specified criterion of D144 was met (D145): E3 goes to the main text. It does not fit in the E1
figure without crowding it (E1 already has three panels with different units). Proposal: its own
two-panel figure, (1) Spearman rho of SPEI-12 against standardized ENA by lag 0-6 with block-12 CI for
SE/CO, S, NE and N, (2) lift of P(ENA <= P20 | SPEI <= -1.5) with CI by region, signal months in the
label (S not reportable, 2 months). Wording fixed in D146: "moderate and significant association", not
"validation".

## (c) Final list of figures and tables

Generator = script in scripts/article/ (D134) unless marked NEW; Phase 9 column lists the planned visual
changes only.

| Item | Content | Generator | Source CSV | Changes in Phase 9 |
|---|---|---|---|---|
| Fig 1 | Heat class map, thermal plants (745), SSP5-8.5 | fig1_heat_class_map.py | w3g_heat_cell_class.csv, plants.parquet | no |
| Fig 2 | Exposure curves by TX35 threshold | fig2_threshold_curves.py | w3_curves_plot.csv | no |
| Fig 3 | Drought exposure map (R_D >= 2, 339 / 433 / 770 plants) | fig3_drought_exposure_map.py | w4g_fd_unit_values.csv | no |
| Fig 4 | Excess over the stationary resampling null | fig4_excess_over_null.py | w4c_spi_vs_spei.csv | yes: title and note (O46), "Hydro, SPI" row (O51) |
| Fig 5a | Hydropower regional compound context by state | fig5a_state_coexposure_hydro.py | w3h_state_coexposure.csv, table3_coexposure_gcm_mean.csv | yes: colorbar overlap and cap (O45), note on GCM inflation (O47) |
| Fig 5b | Water-dependent thermal co-located exposure by state | fig5b_state_coexposure_thermal.py | w3h_state_coexposure.csv | yes: O45, O47 |
| Fig 6 | Thermal heat exposure by fuel | fig6_thermal_heat_by_fuel.py | w3_table1.csv | no |
| Fig 7 (new) | E1 hedge failure (design of item a) | NEW scripts/article/fig7_e1_hedge.py | e1_hedge_{metrics,delta,summary,observed}.csv, e1_colocation.csv | design |
| Fig 8 (new) | E3 ENA association and hit rate | NEW scripts/article/fig8_e3_ena.py | e3_spearman.csv, e3_hit_rate.csv | design |
| Table 1 | Fleet and capacity (inventory, units) | table1_fleet_capacity.py | plant_units.parquet | no |
| Table 2 | Leave-one-out, 5 largest hydro plants | table2_leave_one_out.py | w4d_leave_one_out.csv | no |
| Table 3 | Heat x drought co-exposure 4x4 (mean across 5 GCMs) | table3_crosstab.py, table3_coexposure_crosstab.py | table3_coexposure_gcm_mean.csv | note on GCM inflation (O47) |
| Table 0 | Parameters | table0_parameters.py | config/params.yaml, plant_units.parquet | no |

Because the figure/table limit is TO BE DEFINED, two nested lists:
- **Full list (13 items):** Fig 1-8 and Tables 1-3 in the main text, Table 0 and the supplementary
  Table 3 blocks in the supplementary. Fig 1 and Fig 3 stay separate (decided).
- **Compact list (8 figures reduced to 6, 3 tables to 2):** main = Fig 1, Fig 3, Fig 4, Fig 7, Fig 8 and
  Fig 5a or 5b merged into one state figure, Tables 1 and 3; supplementary = Fig 2, Fig 5 second panel,
  Fig 6, Table 2, Table 0. Fig 6 and Fig 2 carry the heat headline (Table 1 of W3), so moving them
  weakens the thermal-heat claim R5; the choice depends on the limit of O52.

## (d) Claims register

Type: **G** = depends on GCMs only; **O** = anchored in W5E5 observations. k = GCMs (of 5) sharing the
sign of the median (D114). Scenarios in the order SSP1-2.6 / SSP3-7.0 / SSP5-8.5.

| # | Claim | Value | CI or range | k/5 | 3-GCM subset (D148) | Source CSV | D | Type |
|---|---|---|---|---|---|---|---|---|
| R1 | Hydro drought exposure above the null, SPEI-12 (R_D >= 2, 102.667 GW, 194 plants) | +40.75 / +43.20 / +53.94 pp | min-max +3.18..+59.81, +1.42..+61.32, +25.70..+66.92 | 5/5/5 | 40.75 / 43.20 / 53.94 | w4c_spi_vs_spei.csv, w4b_excess_over_null.csv | D102, D148 | G |
| R2 | Same, SPI-12 (explicit lower band) | +17.40 / +3.03 / +38.60 pp | -12.93..+35.38, -12.67..+25.71, -19.48..+60.89 | 3/3/3 | 18.14 / 3.77 / 39.34 (null of 3 GCMs) | w4c_spi_vs_spei.csv | D125, D148 | G |
| R3 | Thermal (618 plants, 39.1015 GW) drought exposure above the null, SPEI-12 | +20.63 / +28.50 / +48.06 pp | -6.40..+39.46, -15.21..+50.21, +6.33..+70.31 | 4/4/5 | 8.34 / 18.74 / 34.53 | w4c_spi_vs_spei.csv | D125, D148 | G |
| R4 | Same, SPI-12 | -1.08 / +5.44 / +27.50 pp | -16.72..+9.72, -17.08..+22.89, -10.55..+40.52 | 3/3/4 | -4.80 / -7.48 / 27.50 | w4c_spi_vs_spei.csv | D125, D148 | G |
| R5 | Thermal fleet exposed to >= 30 days of TX35 per year (47.7 GW, 665 plants) | 28.4 / 36.3 / 49.1 % (median) | 19.1-49.3, 31.4-77.0, 42.3-92.2 | k1 49.3 / 77.0 / 92.2 %, k5 14.4 / 31.2 / 36.3 % of GW | 22.1 / 34.1 / 43.2 % (W3f-6) | w3_table1.csv, w3_gcm_exclusion.csv | W3 (headline definition scripts/w3_table1.py:35; D id TO BE DEFINED) | G |
| R6 | Hydro, extreme heat (plant cell) and extreme drought co-located (regional context, not a hydro heat hazard) | 36.9 / 35.2 / 54.2 GW = 35.9 / 34.3 / 52.8 % (mean) | min-max 11.3..60.3, 1.2..76.5, 4.0..84.6 GW | not sign-bearing; min-max given | 34.2 / 31.1 / 44.1 GW | table3_coexposure_gcm_mean.csv | D137, D139, D148 | G |
| R7 | Share of the extreme-drought capacity that is also extreme heat, hydro | 81 / 84 / 87 % (ratio of means) | n/a | n/a | 86 / 90 / 79 % (mean of GCM ratios) | table3_coexposure_gcm_mean.csv | D139, D148 | G |
| R8 | Thermal, extreme heat and extreme drought co-located | 4.23 / 6.52 / 12.02 GW = 10.8 / 16.7 / 30.7 % (mean) | min-max 1.79..10.69, 0.33..17.76, 5.39..26.46 GW | min-max given | 2.82 / 3.60 / 7.72 GW | table3_coexposure_gcm_mean.csv | D137, D151, D152 | G |
| R9 | E1, control pair (SPI x SPI): P(H and T) rises | 0.050 -> 0.112 / 0.072 / 0.172; dP 0.034 / 0.012 / 0.095 (marginal 0.022 / 0.008 / 0.065, dependence 0.012 / 0.001 / 0.030) | per GCM in e1_hedge_delta.csv | 4/3/5 | dP 0.000 / -0.006 / 0.095, up in 2/1/3 of 3 | e1_hedge_summary.csv, w6_subset_e1.csv | D140-D143, D148 | G |
| R10 | E1, coupling D in variant B: change from baseline | dD +0.18 / +0.40 / +0.11 (baseline D median 5.00) | dD CI lower bound above 0 in none of the 5 GCMs (SSP3-7.0 and SSP5-8.5, blocks 12/24/36) | 3/3/3 (criterion 4/5 not met) | -> 0.18 / -4.09 / -2.36 | e1_hedge_delta.csv | D142 | G |
| R11 | E1, heat pair (SPI x heat): P(H and T) rises, through marginals | dP 0.087 / 0.079 / 0.214 (marginal 0.072 / 0.083 / 0.191) | dP CI above 0 in 3/5 (SSP3-7.0) and 5/5 (SSP5-8.5) | 5/5/5; dD up 3/0/1 | up in 3/3 | e1_hedge_summary.csv | D141, D143 | G |
| R12 | Observed (W5E5 1986-2014) thermal-hydro drought dependence, SPI x SPI | D = 4.83; P(T given H) 0.486 against P(T) 0.101 | block-12 [1.70, 6.32]; block 24 [1.42, 5.97]; block 36 [1.24, 5.68]; circular shift p < 0.001 | n/a | n/a | e1_hedge_observed.csv | D141, D143 | O |
| R13 | GCM baseline D, same definition (variant B, SPI x SPI) | median 5.00 | range 3.61-8.61 | n/a | median 7.78 (3 GCMs) | e1_hedge_observed.csv | D143 | G |
| R14 | Observed heat x drought pair shows no dependence; GCMs show it | observed D = 1.14, p = 0.43; GCM baseline median 2.78 | observed [0.28, 2.48]; GCM 1.67-3.33 | n/a | n/a | e1_hedge_observed.csv | D143, O47 | O and G |
| R15 | Co-location by macro_region (D, observed SPI x SPI, thermal restricted to the region, hydro national) | SE 3.69, CO 3.41, NE 1.14, N 2.25, S 2.27 (all 4.83) | SE [1.17, 5.60], CO [0.88, 5.97], NE [0.57, 4.09], N [0.29, 5.15], S [0.00, 3.80] | n/a | n/a | e1_colocation.csv | D143 | O |
| R16 | E3, association of SPEI-12 and ENA, SE/CO | Spearman rho 0.370, n = 240, lag 0 | [0.174, 0.570]; lags 1-3 include 0; SPI 0.397 [0.197, 0.576] | n/a | n/a | e3_spearman.csv | D144, D145 | O |
| R17 | E3, other regions, lag 0 | S 0.515, NE 0.745, N 0.494 | S [0.322, 0.624], NE [0.570, 0.832], N [0.319, 0.660] | n/a | n/a | e3_spearman.csv | D145 | O |
| R18 | E3, hit rate of SPEI-12 <= -1.5 for ENA <= P20 | SE/CO lift 2.5 (14 signal months), POD 0.146, HSS 0.149; NE lift 3.67, HSS 0.485; N lift 3.08, HSS 0.194; S not reportable (2 months) | SE/CO lift 0.00-5.22, HSS -0.009..0.327; NE lift 2.18-7.03; N lift 1.65-6.30 | n/a | n/a | e3_hit_rate.csv | D146, D147 | O |
| R19 | Leave-one-out: reservoir share with R_D >= 2 (raw, not excess), 66.4 GW, 135 plants | 55.54 / 55.10 / 74.03 % | per GCM in w6_nonmono_gcm.csv | n/a | n/a | w4d_leave_one_out.csv | D135, D148 | G |
| R20 | SSP3-7.0 below SSP1-2.6 cases (R2 hydro SPI, R19, R6 mean, planned hydro, 6 states of Fig 5a) | see D148 per GCM and plant | one or two GCMs (mri, ipsl, mpi fall, ukesm rises) and a few large plants set the sign | n/a | n/a | w6_nonmono_gcm.csv, w6_nonmono_plants.csv | D148 | G |

## (e) Framing and limitations (3-5 sentences, each tied to the register)

1. Hydro drought exposure above a stationary resampling null is large and consistent across the five GCMs
   with SPEI-12 (R1: +41 to +54 pp, 5/5), and smaller and model-dependent with SPI-12, which is the
   explicit lower band (R2: +3 to +39 pp, 3/5).
2. Water-dependent thermal drought exposure rises clearly only under SSP5-8.5 (R3 +48 pp, R4 +28 pp,
   k = 5 and 4) and is model-dependent under SSP1-2.6 and SSP3-7.0 (k = 3 to 4; R3, R4 change sign or
   shrink without UKESM1-0-LL and IPSL-CM6A-LR).
3. In the observed climate the thermal fleet is already in drought when hydro is: D = 4.83, CI [1.70, 6.32]
   (R12), concentrated in Sudeste and Centro-Oeste (R15; 64% of the thermal capacity), so thermal capacity
   is not an independent insurance against hydro drought there.
4. Warming raises the frequency of joint stress mainly through the marginals (R9: 0.065 of 0.095 in
   SSP5-8.5; R11: 0.191 of 0.214 for heat), without a consistent increase in coupling (R10: dD up in 3/5
   GCMs, criterion of 4/5 not met).
5. The drought index is associated with observed natural inflow (R16, rho 0.37 in SE/CO), but as an
   association: the hit rate in SE/CO is not distinguishable from no skill (R18), in tension with the
   concentration of the E1 dependence in the same region, and E3 is not a validation (D146).

Declared limitations, each tied to the evidence that quantifies it:
- SPEI against SPI, Hargreaves PET temperature dependence: R1 against R2, R3 against R4 (circularity
  control of E1 uses SPI; SPEI x SPEI is the upper bound).
- GCMs inflate heat x drought dependence relative to observations: R14 (2.78 against 1.14, O47).
- Spread between GCMs: k/5 of R1-R11 and the 3-GCM subset (D148); SSP3-7.0 non-monotonicity (R20).
- Aggregation: national capacity shares for E1 (R15 shows the regional concentration); macro_region is an
  approximation of ONS submarkets in E3 (D145); state medians of 5 values on few plants in Fig 5 (R20).
- Exposure against generation: ENA is natural inflow without reservoir operation (R16-R18); no generation
  data enter the study (generation was left as a secondary target, Phase 4 plan).
- Time windows: future 2042-2070 and observed 1986-2014 in E1 because the first 11 SPEI-12 months are
  undefined (D141).
- Thermal population: plant-level cooling class (D151), 0.668 GW operating and 2.432 GW planned of
  mixed-cooling units treated as air-cooled.

## Decisions requested (PARE E PERGUNTE)

(a) Figure E1: Design A (recommended), Design B, or another variant.
(c) Final list: full list or compact list, and which items go to the main text once O52 is filled.
(e) Framing: approve, edit or replace the 5 sentences and the limitations above.

## Decisions of the author (recorded in D153)

- (a) Figure E1: Design A.
- (c) Compact list. Main figures (6): Fig 1, Fig 3, Fig 4, Fig 5 (state maps; one merged figure or 5a in
  the main text and 5b in the supplementary, decided in the Phase 9 design proposal), Fig 7 (E1, Design A),
  Fig 8 (E3). Main tables (2): Table 1, Table 3 (main block). Supplementary: Fig 2, Fig 6, Table 0,
  Table 2, Table 3 supplementary blocks (and Fig 5b if it is not in the main text).
- (e) Pending: sentence 2 contains a heat number that does not match the CSV (see D153); sentences 1, 3, 4
  and 5 match the register.
- O52 postponed; neutral dimensions until the journal is adjusted: 1 column about 90 mm, 2 columns about
  180 mm, 300 dpi, fonts legible at 100%.
- New order: Phase 9 -> Phase W (text drafts) -> Phase 7 -> Phase 8 -> Phase 10.
