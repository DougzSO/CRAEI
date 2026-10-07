> **Document role:** Tracker of open methodological items not yet decided by the author (was METHODS_SPEC Appendix E).
> **Contains:** O-id, one-line description, status.
> **Does NOT contain:** full rationale of a resolved item -> docs/DECISIONS.md (search the O-id or its closing D-id).
> **Status:** living; one cross-reference fixed at split time (O20, Fig 5->Fig 4).

---

## Appendix E. Open items

O16 (harvest window, no source); O18 (SPI x SPEI scheme, W4c); O19 (leave-one-
out of Axis 2, W4d); O20 (water x air thermal in Fig 4, renumbered D131 from the original Fig 5); O21 (hydro cell
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

O44 (CLOSED, D136: nuclear restored as a real 0% bar, footnote corrected; was: Fig 6 footnote says nuclear has "no planned capacity" and oil is excluded from the planned fleet, but Table 1 lists planned nuclear, 1 unit 1.405 GW, with 0% exposure in w3_table1.csv; footnote wording to be reviewed by the author).
CLOSED C107: Fig 5a/5b use a one-line legend below the maps; no colorbar (D155). O45 (Fig 5a/5b horizontal colorbar overlaps the middle panel and its scale bar; reproduced as in C87, layout fix deferred to the visual-adjustment phase).

DONE C107: Fig 4 title, axis label and null text applied (axis label short, title and pools in the caption, results.md). O46 (apply in Phase 9 the Fig 4 title, x-axis label and note drafted in docs/article/text_snippets.md, section A3: stationary resampling null, pools named; Fig 4 is unchanged until then).

DONE C107: heat x drought statement is in the Fig 5a caption and in the Table 3 notes (results.md). O47 (Phase 9 / article text: in W5E5 observations the heat x drought pair shows no dependence (D = 1.14, block-12 CI 0.28-2.48 includes 1, D143), while the GCMs give a baseline D of about 2.8 (median 2.78, range 1.67-3.33). The notes of Fig 5a/5b and Table 3 must state that GCM heat x drought co-exposure is probably inflated relative to observations, citing these numbers).

O48 CLOSED (D151): option A, plant-level cooling class everywhere; Table 3 and w3h aligned to 618 plants / 39.1015 GW.

O49 CLOSED (D149): w3h_state_coexposure.csv denominator corrected, percentages were 5x too low in Fig 5a/5b since C63/C87; GW correct; figures rebuilt, check_headlines extended.

O50 (claims register, Phase 5 input): (a) hydro exposure claim rests on SPEI (k = 5/5 in every scenario); SPI (k = 3/5) is stated as the explicit lower band (hydro SPI excess 17.40/3.03/38.60 pp vs SPEI 40.75/43.20/53.94). (b) Thermal drought exposure is robust only in SSP5-8.5 (SPEI k = 5/5, SPI k = 4/5 with 27.50 pp) and model-dependent in SSP1-2.6 and SSP3-7.0 (k = 4/5 SPEI, 3/5 SPI; drops without UKESM1-0-LL and IPSL-CM6A-LR: SPEI 8.34/18.74/34.53, SPI -4.80/-7.48/27.50, D148). (c) E3: significant rho in SE/CO (0.37, n = 240) but hit rate without significance (HSS CI includes 0, 14 signal months; NE and N have lift > 1, D147); this is stated together with the tension against the concentration of the E1 dependence in SE/CO and Centro-Oeste (D143).

DONE C107: Fig 4 has the Hydro, SPI row. O51 (Phase 9): Fig 4 must include a 'Hydro, SPI' row, for symmetry with the thermal SPEI and SPI rows (values in w4c_spi_vs_spei.csv, hydro, spi).

O52 (Phase 5: the Climate Risk Management guide for authors, https://www.sciencedirect.com/journal/climate-risk-management/publish/guide-for-authors, could not be fetched (HTTP 403); author to read it and fill in the DECISION_MEMO_F5.md section 0 cells marked TO BE DEFINED: abstract format, highlights, number of figures and tables, figure width and dpi, supplementary rules, data availability statement).

Author-level open items, outside the pipeline: O20, O33 pending
assignment; India and Portugal analysis deferred until Brazil closes;
external copy/backup of the raw data directory deferred.
O42 (docs/STATUS_LOG.md has a gap for C70-C87; backfill pending, low priority,
does not block the article-script phase).

---

O53 (Phase 8): GADM 4.1 (state and country shapes used for the article maps) does not allow redistribution. data/external/geo/gadm_brazil.gpkg and the GADM source files stay out of the Zenodo deposit; the README must tell users how to obtain GADM 4.1 (gadm.org) and set gadm_bra_dir in config/paths.local.yaml, then run scripts/geo_base.py (D155).
