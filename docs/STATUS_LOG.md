> **Document role:** Session-by-session technical log: commands run, checks, pass/fail outcomes.
> **Contains:** one row per step/command, chronological, append-only.
> **Does NOT contain:** decision rationale -> docs/DECISIONS.md; current pipeline state -> docs/METHODS_SPEC.md.
> **Status:** append-only.

---

# STATUS LOG (append-only; plan lives in CRAEI_work_plan_v2.md)

| date | step | status | note |
|---|---|---|---|
| 2026-10-01 | C27 | done | unit-level fuel x tech x fleet table (c27_fuel_units.py); D77 reference checks 10/10 PASS; O23 and work plan section E added |
| 2026-10-01 | C27b | done | cleanup: caches removed, 4 root stdout files moved to audit/stdout_root, 20 root logs zipped to CRAEI_backup/logs and verified; pytest 141 passed 1 skipped and gate 8/8 PASS afterwards |
| 2026-10-01 | C27c | done | addendum to D79 appended to DECISIONS.md (status proposed, pending author review) |
| 2026-10-01 | C27d | done | one-shot scripts (c24, c26, c27 patches and readonly) moved to scripts/archive via git mv |
| 2026-10-01 | C28 | done | plant_units.parquet built by unit (inventory/units.py, scripts/05b_plant_units.py); 16/16 checks PASS; capacity per plant_uid == plants.parquet (12459 plants); text columns cast for parquet; ruff line-length 100->120; pytest 149 passed 1 skipped; gate 8/8 |
| 2026-10-01 | C29 | done | Brazil fleet table by tech x fuel x fleet from plant_units (inventory/fleet.py, scripts/c29_fleet_table.py), both O22 versions side by side; D81 and O24 registered; pytest 153 passed, 1 skipped; gate lines checked |
| 2026-10-01 | C29b | done | O22 resolved as D82: headline Brazilian share 7 GW, sensitivity whole asset; c23d capacity-weighted numbers to be recomputed in W5 |
| 2026-10-01 | C25-S2 | done | 3 FutureWarnings fixed in exposure/aggregate.py (eq(True) x2, concat skips empty blocks); pytest 153 passed, 1 skipped; gate checked; no numeric change |
| 2026-10-01 | C30 | done | D83-D85 appended to DECISIONS.md; ruff extend-exclude scripts/archive; pytest 153 passed, 1 skipped, 4 warnings in 7.65s |
| 2026-10-01 | C25-S1 | done | ruff extend-exclude scripts/archive; import order fixed in c27b_cleanup.py and log_step.py; pytest 153 passed, 1 skipped, 4 warnings in 7.31s |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | W3a | done | heat exposure of BRA thermal fleet by fuel per unit (exposure/heat_fuel.py, w3_heat_fuel.py, 8 tests); 21 capacity checks PASS; tables w3_heat_*.csv; pytest 151 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | W3b | done | GW exposed in >= k of 5 GCMs per plant (exposure/heat_agreement.py, w3_agreement.py, 3 tests); BRA thermal operating total 47.67 GW matches fleet table; pytest 154 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C32 | done | ruff: unused variable and empty f-string in 09_consolidate.py, unused imports in c23c/c23d_checks.py, import order in 07_water_balance.py; no logic change (py_compile OK); pytest 157 passed, 1 skipped (measured with W3c tests present); gate 8 PASS |
| 2026-10-01 | W3c | done | leave-one-cell-out influence on heat shares (exposure/heat_influence.py, w3_influence.py, 3 tests); thresholds 20/30/40; one-cell groups give NaN; pytest 157 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C33 | done | D86 (LOCO + cell bootstrap as composition sensitivity), D87 (axis 1 metrics, proposed), O16 note appended to DECISIONS.md; numbers copied from W3a/W3b/W3c outputs |
| 2026-10-01 | W3d | done | cell-cluster bootstrap (2000 draws, seed 86) of GCM-median heat shares and of the paired planned-minus-operating difference, with paired LOCO (exposure/heat_bootstrap.py, w3_bootstrap.py, 4 tests); observed statistics reproduce W3a tables; pytest 161 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | C25-S3 | done | git rm of 14 files (audit/*, exposure/compound.py, 6 one-shot scripts, 2 tests); pytest 143 passed, 1 skipped (measured before W3a files); gate 8 PASS; ruff outside archive 62 -> 18 |
| 2026-10-01 | C34 | done | D86 addendum (W3d bootstrap results) and O25 (reporting rule, open) appended to DECISIONS.md; numbers copied from the w3_bootstrap output |
| 2026-10-01 | W3e | done | monthly delta N35 profile of operating thermal groups, capacity-weighted over cells (exposure/heat_season.py, w3_season.py, 3 tests); sum of 12 months reproduces annual plant_hazards delta; no harvest window used (O16 source unknown); pytest 164 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C35 | done | work plan section G (commit map from git log, floor 164, remaining steps); O25 closed; D84 option A restored; O26 opened (base geography) |
| 2026-10-01 | W3f-1 | done | Table 1 of Axis 1 joined from W3 tables (exposure/heat_table1.py, w3_table1.py, 3 tests), O25 rule applied; geo_base.py wrote Natural Earth Brazil layers (O26); pytest 167 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C36 | done | D87 accepted, O17 closed, O26 resolved, ruff config note appended to DECISIONS |
| 2026-10-01 | W3f-3 | done | paired scenario contrast with cell bootstrap (exposure/heat_scenario.py, w3_scenario.py, 3 tests); same draws as W3d checked against w3_heat_bootstrap_shares; per-GCM differences checked against W3a curves; pytest 170 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C37 | done | D80 and D81 accepted; geography details and Table 1 agreement checks appended to DECISIONS |
| 2026-10-01 | W3f-4 | done | Axis 1 sensitivities (TX40, plant-count weight) vs W3a reference, long table plus headline table (exposure/heat_sensitivity.py, w3_sensitivity.py, 3 tests); reference reproduces w3_heat_summary; pytest 173 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C38 | done | GCM nesting in Brazil (18/18 nested in UKESM, GW-weighted) and work plan addendum appended |
| 2026-10-01 | W3f-2 | done | plotting table of threshold curves on the 8-point grid (exposure/heat_curves.py, w3_curves.py, 3 tests); 648 rows, equals Table 1 at 20/30/40 d, monotone in threshold; pytest 176 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C39 | done | W3f-4 results registered in DECISIONS, O27 (TX40 grid) opened, work plan addendum 2 |
| 2026-10-01 | C40 | done | ruff F401 fixed in heat_curves.py (committed with the error in 5ff7947); O27 TX40 distribution and grid proposal registered; lock now includes ruff; pytest 176 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | W3f-5 | done | TX40 exposure on its own grid 1,2,5,10,20,30 d (scripts/w3_tx40.py, w3_tx40_curves.csv); reproduces W3f-4 TX40 rows at 10/20/30 d; monotone; pytest 176 passed, 1 skipped; gate 8 PASS |
| 2026-10-01 | C41 | done | O27 closed (grid accepted); Axis 2 facts registered before W4a |
| 2026-10-01 | W4a | done | null rates: blocks 12/24/36/60, AR(1), white noise; c23d checks PASS; n_boot 5000 accepted |
| 2026-10-01 | C42 | done | W4a docs and n_boot decision registered |
| 2026-10-01 | W3f-6 | done | GCM exclusion: 7 sets, contrast and fuel order under exclusion; 5-GCM checks PASS |
| 2026-10-01 | C43 | done | W3f-6 docs registered |
| 2026-10-01 | C44 | done | D88 co-located exposure and lenses; O28-O33; METHODS_SPEC v2.1 addendum; plan G addendum 3 |
| 2026-10-01 | C45 | done | O28 cuts amended to 10/30/60; O29 thermal cell pool closed |
| 2026-10-01 | W3g | done | TX35 level classes 10/30/60, shift, level x delta, cell map; checks 1-3 PASS |
| 2026-10-01 | C46 | done | W3g results registered |
| 2026-10-01 | W4g | done | Drought level classes vs null (20,000 draws, pools catchment and cell), R_D classes; checks 1-4 PASS |
| 2026-10-01 | C47 | done | W4g results registered; D89 cooling upper bound (closes O32); O34 opened |
| 2026-10-02 | C48 | done | Emulated drought null module, check and per-GCM validation; D90 three nulls no canonical, D91 TH1 definition, O35 opened, O34 closed; METHODS_SPEC v2.2 + M6 update |
| 2026-10-02 | W4r | done | Emulated drought nulls, production run 20,000 draws per pool (catchment 1,110; cell 1,710), year and anystart; refit check PASS; validity 12 of 24 rows PASS, FAIL rows kept |
| 2026-10-02 | C51 | done | W4r results registered; D92 (FAIL cases kept, tolerance unchanged), O36 opened |
| 2026-10-02 | O36 | done | Param-uncertainty decomposition of the emulated future F_D, 20,000 draws per pool and variant; replay reproduces W4r draws; year mostly, anystart not interpretable |
| 2026-10-02 | C52 | done | O36 results registered; D93, O36 closed, O37 opened |
| 2026-10-02 | C53 | done | docs/PIPELINE_MAP.md created from the repository inventory (stages, scripts, modules, tables; items not seen marked TBD) |
| 2026-10-02 | C54 | done | PIPELINE_MAP checked against code literals and corrected (S1/S2/S3/S6/S12, support scripts, constants section); O38 opened |
| 2026-10-02 | C55 | done | PIPELINE_MAP corrected: S2/S3 split into S2a/S3/S2b/S2c/S2d; raw_dir locations resolved for GEM/Aqueduct/EM-DAT/GADM/validation; S4/S5/S7-S11 reads completed; {iso} standardized to {country}; O38 updated, not closed |
| 2026-10-02 | O37 | done | 12-month sum variance diagnostic (archive/o37_anystart_sums.py): anystart sd ratio ~1.15-1.16 vs real, year ~0.98; confirms O37 hypothesis (D94); closed |
| 2026-10-02 | C56 | done | O37 closed (D94); PIPELINE_MAP O38 update, 5 of 6 items resolved (emdat writer, module reads, w3_table1/w3_curves NAMES, HydroBASINS, W5E5 36 .nc); O38 stays open pending constants/config linkage |
| 2026-10-02 | C57 | done | D95: trend-removed sensitivity of emulated drought nulls (archive/o39_detrended_sensitivity.py); reading unchanged (year mostly, anystart not); linear trend negligible (r2~0.002); sensitivity only, never headline |

- C58 / D96: W4g-rev concluído (3 nulos nas classes de nível de seca e R_D); year mais baixo que block12 em todas combinações (D93); anystart com ressalva D94/O37; nenhum canônico (D90); tabelas w4grev_*.csv; piso 215 passed, 1 skipped.

- C59 / D97: W4h concluído (co-exposição calor x seca, 4x4, sob os 3 nulos); year mais restritivo, anystart com ressalva D94/O37, block12 mais permissivo; marginais checados contra W3g/W4g/W4g-rev antes da mediana (D80); w4h_coexposure.csv (3456 linhas); piso 215 passed, 1 skipped.

[C60] D98 fechado. TH1 (D91) rodado com sucesso: checks (a) e (b) PASS. Piso 220 passed/1 skipped mantido após mover script para archive. O39 aberto: agregação TH1 por frota/GW (join plant_units/plant_cell, estilo W3g) — extensão futura, fora do escopo literal do D91, critérios de validade a fixar antes de rodar.

[C62] D99 fechado. W3h/ST1 (calor por estado/macrorregião) rodado com sucesso: checks (a) e (b) PASS, diff 0,00e+00. Piso 225 passed/1 skipped (220+5 do módulo craei.geo.state_assignment). ST2 (seca por estado) ainda pendente.

[C62] D99 fechado. W3h/ST1 (calor por estado/macrorregião) rodado com sucesso: checks (a) e (b) PASS, diff 0,00e+00. Piso 225 passed/1 skipped (220+5 do módulo craei.geo.state_assignment). O41 investigado e fechado na hora (falso alarme, params.yaml já estava correto). ST2 (seca por estado) ainda pendente.

- C63 (2026-10-05): W3h/ST2 state-level co-exposure, checks (a)-(c) PASS (D100).
  W3f-7 planned-vs-operating under TX40 and plant-count weight, checks (1)-(4)
  PASS (D101); finding: plant-count weight flips the planned-operating reading
  from "no consistent difference" to "consistently higher under planned" (see
  D101). Fixed duplicate D96/D99 blocks in DECISIONS.md (1294 -> 1261 lines).
  CLAUDE.md pytest floor line updated to C62 (225 passed, 1 skipped).

- C64 (2026-10-05): W4b excess over the null, hydro BRA, Itaipu a/b, checks
  (1)-(2) PASS (D102). AR(1) treated as informative-only (not abort), per
  w4a_null_rates.py's own docstring. Block-length sensitivity (D83) confirmed
  in direction (18.88% -> 21.87%, block12->36), not monotonic (block60
  20.75% < block36). Closes METHODS_SPEC DR5 handler. Floor unchanged: 225
  passed, 1 skipped.
- C65 (2026-10-05): O40 closed by mitigation (D103) -- accepted the ASCII-only
  policy for new prose (already in use since D83) as sufficient going
  forward; root cause of the mojibake affecting D100/D101 (C63) not
  identified, not reopened under a new id this session. METHODS_SPEC M11
  gained a flagged finding for W4b's block-length non-monotonicity (D102);
  M14 status table corrected: W4h/W3h/W3f-7/W4b rows moved from PLANNED to
  DONE with their C/D ids, emulator module row moved from IN PROGRESS to
  DONE. No code changed, no test run. Floor unchanged: 225 passed, 1 skipped.
- C66 (2026-10-05): METHODS_SPEC.md rewritten to article form (D104). No
  code, no new number, floor unchanged (225 passed, 1 skipped). Prior text
  archived at docs/archive/METHODS_SPEC_v2.2_pre_C66.md. Derived 38.1%
  (423/1,110) removed before commit.
- C67 (2026-10-05): Removed stray _tmp_check.txt. Transcribed CO2 real
  values from D97 into METHODS_SPEC Appendix D (D105). Found and corrected
  a C66 transcription error: CO3 had been marked DONE as a
  "sum-of-4-medians" when D97 itself explicitly rejects that sum as invalid
  (median not additive) and never saved it -- corrected to PENDING, no
  number citable. CO1 marked PARTIAL (only extreme x extreme transcribed).
  ST2 handler row corrected: its CO3-style value is valid on its own, not
  comparable to the (invalid, unadopted) W4h CO3 attempt. Confirmed
  terminal/clipboard corruption (character substitution, "Line"->"]ine")
  is a paste-chain artifact, not a file-on-disk issue -- unrelated to O40,
  not reopening it. No code changed. Floor unchanged: 225 passed, 1
  skipped.
- C68 (2026-10-05): Investigated a reported discrepancy (external reading
  claimed W4h blocked by O32, M14 table stale, Pearson III and plant-count
  mismatches) against the current docs on disk. D106: no real contradiction
  found. O32 was opened C44, closed C47 (D89, upper bound choice) before
  W4h ran (C59, D97) -- dependency satisfied, not blocking. "M14" does not
  exist post-C66. Pearson III and "6 vs 5 plants" items were already
  disclosed in METHODS_SPEC's own pending list, not new findings; the
  plants item is stale text (body already resolves it), noted for future
  cleanup. No code changed. Floor unchanged: 225 passed, 1 skipped.
- C69 (2026-10-05): W5 sensitivity table seeded (D107). New module
  scripts/w5_sensitivity.py reads w3f7_planned_vs_operating.csv and
  w4b_excess_over_null.csv, writes w5_sensitivity.csv (12 rows, 4
  families: W3f7_weight, W3f7_metric, W4b_block_12_36, W4b_block_36_60).
  All 18 reference values drift-checked by assert before write. Caught and
  fixed one error before commit: an initial single family-level flag for
  W3f7_metric ("smaller_magnitude_same_sign") was wrong for ssp585, which
  actually sign-flips with larger magnitude -- corrected to a per-row flag
  for that family only. No code changed outside the new script. Floor
  unchanged: 225 passed, 1 skipped (w5_sensitivity.py has no pytest unit
  yet -- script-level asserts only, consistent with w3f7/w4b precedent).- C88 (2026-10-07): Phase 0 baseline and regression gate. New
  scripts/check_headlines.py verifies 10 C87 headline items (D102/W4b hydro,
  D125/W4c thermal SPEI/SPI, Table 1 capacities, table3_coexposure 192 rows,
  w4g_fd_unit_values 13,815 rows, Fig 3 339/433/770, Fig 1 745/340), all PASS.
  data/outputs/article/_ref_C87/ saved as comparison reference (outside Git).
  docs/HANDOFF_v46.md added; CLAUDE.md consolidated (permanent rules, test
  floor history). Floor measured: 225 passed, 1 skipped.
- C89 (2026-10-07): Phase 1, article artifact scripts. 12 scripts in scripts/article/ plus build_all.py regenerate all 18 files of
  data/outputs/article/ (D134). Tables: content-identical to _ref_C87. Figures: same data, cosmetic differences listed in the phase report.
  check_headlines 10/10 PASS; floor unchanged: 225 passed, 1 skipped. Open items O44, O45 (found while reproducing Fig 5/6).
- C90 (2026-10-07): Phase 2 A2, Table 2 leave-one-out corrected (D135). Metric note fixed (drought R_D >= 2.0, not TX35), Itaipu headline version b (7,000 MW),
  version a as sensitivity; new scripts/w4d_leave_one_out.py. Floor unchanged: 225 passed, 1 skipped.
- C91 (2026-10-07): Phase 2 A5/O44, Fig 6 nuclear restored as real 0% bars, GW and n under fuel labels, gas note (D136). Floor unchanged: 225 passed, 1 skipped.
- C92 (2026-10-07): Phase 2 A4, Table 3 main = mean across 5 GCMs with min-max (additive), median version kept as table3_median_reference (D137). New scripts/w5_table3_gcm_mean.py. Floor unchanged: 225 passed, 1 skipped.
- C93 (2026-10-07): Phase 2 A3 text, null hypothesis wording and Fig 4 title/note drafted in docs/article/text_snippets.md (not applied), METHODS_SPEC line 223 corrected (1,705 vs 1,710), O46 (D138). Floor unchanged: 225 passed, 1 skipped.
- C94 (2026-10-07): Phase 2 A1, hydropower heat reframed as regional compound climate context in Fig 5a and Table 3 hydropower block, V3 ratios 81/84/87% (D139). Floor unchanged: 225 passed, 1 skipped.
- C95 (2026-10-07): Phase 3 E1 specification, docs/article/E1_spec.md with the pre-specified decision criterion, D140 reopening the D72 compound metric. No code yet. Floor unchanged: 225 passed, 1 skipped.
- C96 (2026-10-07): Phase 3 E1 implemented and run (D141): hedge.py + tests, e1_populations/e1_w5e5_inputs/e1_hedge, results CSVs outside Git. Primary criterion NOT met (SSP3-7.0 3/5, SSP5-8.5 5/5); observed D 4.83. Floor 236 passed, 1 skipped.
- C97 (2026-10-07): D142, E1 primary criterion not met (SSP3-7.0 3/5); target Climate Risk Management; SSP3-7.0 non-monotonicity logged for Phase 6. Floor 236 passed, 1 skipped.
- C98 (2026-10-07): D143, E1 post-outcome verifications (baseline-fitted SPEI/SPI confirmed with file:line, observed vs GCM same variant and pair, co-location by macro region in new scripts/e1_colocation.py, block 24/36 and calendar-month sensitivities). Floor unchanged: 236 passed, 1 skipped.
- C99 (2026-10-07): Phase 4 E3, D144 pre-specification and D145 outcome (SE/CO lag 0 rho 0.37, CI excludes 0, criterion met, main text), scripts/e3_ena_validation.py; O47 registered (Phase 9 note on GCM heat x drought inflation). Floor unchanged: 236 passed, 1 skipped.
- C100 (2026-10-07): Phase 4 E3 hit rate, D146 criterion registered before computing, D147 outcome (scripts/e3_hit_rate.py). Floor unchanged: 236 passed, 1 skipped.
- C101 (2026-10-07): Phase 6, 3-GCM subset (D148), k/5 agreement, non-monotonicity decomposition, gw and n_units columns; O48 (Table 3 thermal population 621/39.77) and O49 (w3h_state_coexposure pct 5x too low, Fig 5a/5b) registered. Floor unchanged: 236 passed, 1 skipped.
- C102 (2026-10-07): O49 closed (D149): w3h_state_coexposure denominator fixed (percentages were 5x low), Fig 5a/5b rebuilt, check_headlines 12 checks; O48 investigated (D150) and left for author decision; O50, O51 registered. Floor unchanged: 236 passed, 1 skipped.
- C103 (2026-10-07): O48 closed (D151), Table 3 and w3h thermal aligned to the plant-level class (618 plants, 39.1015 GW), Table 3 outputs, Fig 5b and Table 1 note regenerated. Floor 238 passed, 1 skipped.
- C104 (2026-10-07): Phase 5 memo docs/article/DECISION_MEMO_F5.md (decisions a, c, e pending), D152 (memo and D148 thermal co-extreme correction), O52 (journal guide unavailable). Floor unchanged: 238 passed, 1 skipped.
- C105 (2026-10-07): Phase 5 decisions recorded (D153): E1 Design A, compact list, neutral dimensions, new phase order; sentence 2 of the framing held (heat share does not match the CSV). Floor unchanged: 238 passed, 1 skipped.
