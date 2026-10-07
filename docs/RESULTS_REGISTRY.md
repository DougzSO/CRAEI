> **Document role:** Registry of every number citable in the article text (was METHODS_SPEC Appendix D).
> **Contains:** result handlers (HC, HL, DR, W4f, CO, ST, SE, VA, PE, TH1 families), one row per handler id.
> **Does NOT contain:** decision rationale -> docs/DECISIONS.md; methods narrative -> docs/METHODS_SPEC.md; figure/table layout status -> docs/FIGURES_TABLES_MAP.md.
> **Status:** living; update as results close.

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


