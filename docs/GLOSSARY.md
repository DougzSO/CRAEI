> **Document role:** Definitions of recurring abbreviations, id prefixes, hazard/metric names and group labels used across all CRAEI docs.
> **Contains:** id prefixes (C/D/O), phase prefixes (W1-W8, w3/w4/w5 script families), hazard/metric names, classes, null types, fleet/group labels, Itaipu convention, cutset naming.
> **Does NOT contain:** decision rationale (-> DECISIONS.md), methods detail (-> METHODS_SPEC.md).
> **Status:** living; add terms as they appear.

---

## IDs

- **C-id** (C1, C2, ... C85+): one per work "command"/session-chunk, sequential, logged in docs/STATUS_LOG.md and referenced from docs/DECISIONS.md.
- **D-id** (D1, D2, ... D131+): one per author decision or closed finding, the permanent record, docs/DECISIONS.md, append-only.
- **O-id** (O1, O2, ... O41+): one per open methodological item awaiting an author decision, docs/OPEN_ITEMS.md; closed once a D-id settles it.
- **L-id** (L01-L31, legacy): limitation ids used before C66; superseded by **B1-B7** in METHODS_SPEC.md Appendix F. Only appear in docs/archive/LIMITATIONS_pre_C66.md now.
- **HA-id** (HA1-HA7): untested hypotheses listed in the archived SCOPE.md; never formally closed under their own id, but their substance is covered by later closed results (see docs/archive/SCOPE_pre_C66.md and docs/RESULTS_REGISTRY.md).

## Phases / script-family prefixes

- **W1-W8**: work-plan phases (docs/CRAEI_work_plan_v2.md): W1 read-only verifications, W2 pipeline additions, W3 heat/null and excess (Axis 1), W4 heat by fuel / drought (Axis 2), W5 sensitivity register, W6 tables/figures, W7 reproducibility, W8 operations/backlog.
- **w3_*, w4_*, w5_*** (scripts/): script families implementing W3/W4/W5; a letter suffix (w3a, w3g, w4b, w4c, w4f, w4h...) marks a sub-step, not a strict order.
- **S0-S13**: pipeline execution stages (docs/archive/PIPELINE_MAP_pre_C66.md); superseded by METHODS_SPEC.md Appendix A's Step 1-12 numbering, the current reference.

## Hazard and metric names

- **TX35 / TX40**: annual count of days with daily max temperature >= 35 / 40 degC.
- **dTX35**: TX35_future - TX35_baseline (days/yr), the heat change metric.
- **SPEI-12 / SPEI-3**: Standardized Precipitation-Evapotranspiration Index, 12-/3-month accumulation, Hargreaves-Samani PET.
- **SPI-12**: Standardized Precipitation Index (precipitation only), 12-month accumulation, gamma fit.
- **F_D**: fraction of months with SPEI <= -1.5; computed for a baseline and a future window.
- **R_D**: F_D_future / F_D_baseline; undefined (NaN) when F_D_baseline = 0; production "exposed" threshold is R_D >= 2.
- **H1-H4**: the four hazard definitions, METHODS_SPEC.md Section 4 (H1 heat, H2 drought, H3 chronic water stress/Aqueduct -- out of v2 scope, H4 extreme precipitation -- SI only).

## Classes and agreement

- **Heat/drought level classes**: discretized exposure levels (low/medium/high/extreme), cuts fixed by O28/O29 (closed); never a continuous gradient.
- **k of 5 (agreement)**: number of the 5 GCMs sharing the same sign in a contrast; reported as k=1,3,5 (O31, closed) -- NOT the unused params.yaml model_agreement_fraction.
- **Cutset (e.g. p50_p90_p99)**: which percentiles are retained/displayed together; canonical display cutset for Table 3 / Fig 5 is p50_p90_p99 (D90).

## Null model (internal variability)

- **block12/24/36/60**: block-bootstrap null, block length in months; block12 is production/canonical.
- **year / anystart / free**: emulated-null variants (craei.hazards.null_emulator); "free" is the baseline block-bootstrap family, "year" resamples whole calendar years, "anystart" resamples 12-month windows starting at any month.
- **AR1 / white noise**: structural sensitivity bounds, never the headline (white noise = lower reference, since SPEI-12 is serially correlated by construction).
- **n_sim = 2,000**: production count for all null-model scripts; a one-off n_sim=5,000 check exists only for W3d/W3f-3 CI tables (C80/D126); a planned n_sim=20,000 run (DR1) has NOT been executed.

## Fleet / group labels

- **fleet**: operating, planned_adv, planned_early, planned_all (= planned_adv + planned_early).
- **group** (hazard tables): all_thermal, or individual fuel/tech groups; hydro appears as its own group only in drought (H2) and co-exposure tables, by design -- H1 (heat) has no hydro generation-limiting mechanism in this framework.
- **tech_class**: solar_pv, hydro, thermal_water_dependent, thermal_air_only.
- **fuel_class**: solar, hydro, bioenergy, gas, oil, coal, nuclear, multi_fuel (D77).

## Itaipu convention

- **Itaipu b** (headline): Brazilian share only, 7,000 MW -- every headline result.
- **Itaipu a** (sensitivity): whole binational asset, 14,000 MW (D82, D85).

## Pool / scope scale

- **catchment-scale**: hydro hazard values area-weighted over each plant's upstream catchment (HydroBASINS).
- **cell-scale**: water-dependent thermal hazard values use the single ISIMIP grid cell containing the plant.
- **pool**: the set of (id, model) series a null distribution draws from; hydro and thermal_water_dependent each have their OWN pool -- never mix one group's null with another group's observed values (the error caught and fixed in D125/O18).
