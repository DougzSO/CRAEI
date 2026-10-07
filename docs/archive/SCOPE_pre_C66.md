# SCOPE (v2)

## Research question
How does climate change alter heat and drought exposure of the Brazilian power fleet at plant level, and does current planning site new capacity in conditions that will get worse? Exposure only: never impact, loss or vulnerability (L03, L23).

## Two axes
- **Axis 1 (main).** Heat (TX35) exposure of the thermal fleet by fuel, operating vs planned, 5 GCMs, 3 SSPs. Novelty: the breakdown by fuel and the operating-vs-planned comparison.
- **Axis 2 (secondary).** Hydro drought exposure (SPEI-12 at catchment scale), reported honestly: excess over an internal-variability null, GCM spread and agreement, SPI vs SPEI, leave-one-out of the largest plants.

## In and out of scope
| Item | Status | Reason |
|---|---|---|
| Brazil | in | single-country article (D71) |
| India, Portugal | out (pipeline kept) | second article or data descriptor |
| Compound drought-heat metric | out (D72) | not part of the two axes |
| H3 Aqueduct, H4 precipitation | out (D74) | Aqueduct inconsistent with ISIMIP3b (L06, L13); neither serves the axes |
| Solar, wind | out | no metric / low confidence (D04, L18) |
| Flooding | out | no data |
| Composite score | out | D05 |
| ONS validation | supplementary (D73) | weak national result (rho 0.361, CI 0.027-0.811); strengthens honesty of Axis 2 at zero cost |

## Article structure
Introduction; Data and methods (ISIMIP3b, 5 GCMs, 3 SSPs, continuous hazards, internal-variability null); Results: Fig 1 fleet and capacity by technology and fuel; Fig 2 TX35 exposure maps per thermal plant by fuel; Fig 3 heat-threshold curves (GW fraction vs dTX35), operating vs planned; Fig 4 drought maps (SPEI and SPI side by side) per hydro plant; Fig 5 excess over null by bucket and scenario with GCM range; Table 1 GW fraction exposed by technology, fuel and scenario (operating and planned); Table 2 leave-one-out of the 5 largest hydro plants; Discussion (planning implications for gas and bioenergy; limits: Hargreaves, validation, effective n; drought as a mixed signal); Conclusion.

## Target journals
Climate Risk Management, Renewable Energy, Applied Energy; Earth's Future if the planning component is strong (D75).

## Hypotheses (all untested)
| Id | Statement | Falsified if | Data | Status |
|---|---|---|---|---|
| HA1 | Bioenergy thermal plants have higher GW-weighted dTX35 than gas plants | median difference is not positive, or is smaller than the GCM range | plant_hazards + plant_units (C31) | untested |
| HA2 | Planned thermal capacity (mostly gas) sits in cells with higher dTX35 than the operating fleet | planned GW share above the class is not above the operating share, beyond the GCM range | C31, C34 (O17) | untested |
| HA3 | Heat exposure of the thermal fleet grows consistently across GCMs | fewer than 4 of 5 GCMs agree over most thermal GW | C31 | untested |
| HA4 | Hydro drought exposure exceeds the internal-variability null in every SSP | excess is not positive in the median, or the GCM range crosses zero over most capacity | C30, C36 | partially seen (see below) |
| HA5 | GCM agreement on the sign of drought change is weak | at least 4 of 5 agree over most hydro GW | C36 | untested |
| HA6 | SPI and SPEI give materially different hydro exposure | difference within the GCM range | C35 (O18) | untested |
| HA7 | The hydro headline is sensitive to the largest plants | removal of any of the 5 changes the share by less than the GCM range | C37 (O19) | untested |

Preliminary reading of c23d_report.md (not a result): median excess over the block-bootstrap null is 31-60 points for hydro, but the GCM minimum is below the null for hydro_reservoir SSP1-2.6 (15.7% vs 18.88%) and for thermal_water_dependent SSP3-7.0 (2.3%). HA4 is therefore not yet supported at the level of every GCM.

## Claim-language rules
Use exposure, never impact, vulnerability or generation loss. Fuel differences are reported as siting-driven exposure (L23). Bagasse is a declared proxy (L24). Excess over null is descriptive (L26).

## Reviewer-risk notes
1. **Exposure vs vulnerability by fuel.** Differences between fuels come from where plants are, not from the technology.
2. **Bagasse seasonality.** Operation is concentrated in the harvest season; annual TX35 may not represent it. Monthly n35 exists in indices_daily.parquet, so a seasonal variant needs no climate reprocessing (O16).
3. **Operating vs planned.** The central claim needs this comparison in Table 1 and Fig 3 (O17).

## Pending verification
- Mixed-status plants: 5 thermal plants carry the wrong fleet in plants.parquet (net +3.55/-3.55 GW); fixed via plant_units (D78, C28).
- Binational hydro (Itaipu): full capacity counted as Brazilian? (L30, C26).
- Fuel facts: gas incl. LNG (19.32 GW) exceeds bioenergy (17.43 GW) in operating GW; bioenergy is the largest renewable-labelled thermal group. The scope text must not say bioenergy is the largest thermal fuel.
- c23d SPI and leave-one-out result CSVs not yet read (C26).
- SPI fit scheme differs from SPEI (O18).

## What stays in the pipeline for article 2
IND and PRT results, compound metric, H3 Aqueduct, H4 precipitation, solar rows, REN/DGEG validation, EM-DAT descriptive.
