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
O45 (Fig 5a/5b horizontal colorbar overlaps the middle panel and its scale bar; reproduced as in C87, layout fix deferred to the visual-adjustment phase).

Author-level open items, outside the pipeline: O20, O33 pending
assignment; India and Portugal analysis deferred until Brazil closes;
external copy/backup of the raw data directory deferred.
O42 (docs/STATUS_LOG.md has a gap for C70-C87; backfill pending, low priority,
does not block the article-script phase).

---


