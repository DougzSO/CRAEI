> **Document role:** Status of every figure and table planned for the article (was METHODS_SPEC Appendix C).
> **Contains:** one row per Fig/Table, source CSV(s), DONE/PLANNED status, scope notes.
> **Does NOT contain:** underlying numeric values -> docs/RESULTS_REGISTRY.md; decision rationale -> docs/DECISIONS.md.
> **Status:** living; D131 renumbering applied C86/D132.

---

## Appendix C. Results map (figures and tables)

| Item | Content | Source table(s) | Status / blocking |
|---|---|---|---|
| Table 0 | Framework parameters (GCMs, baseline/future periods, scenarios, thresholds, Itaipu convention, null n_sim) | config/params.yaml, METHODS_SPEC Sections 1-3 | PLANNED (new, D131/D132) |
| Fig 1 | Heat level class map (cells, plants sized by GW) | w3g_heat_cell_class.csv | DONE (data, C46/W3g, 1,404 rows, cell_lat/cell_lon/class_median); figure PLANNED (was Fig 2, renumbered D131) |
| Fig 2 | Threshold curves, operating vs planned | w3_curves_plot | DONE (data), figure PLANNED (was Fig 3, renumbered D131) |
| Fig 3 | Drought level class map, SPEI and SPI | w4g_fd_unit_values.csv joined to plants.parquet (plant_uid, lat/lon) | DONE (data, O18 closed D123/D125); no dedicated per-cell table exists, point map via join; figure PLANNED (was Fig 4, renumbered D131) |
| Fig 4 | Excess over the null by scenario, GCM range | w4b_excess_over_null.csv | DONE (C64, D102); figure PLANNED (was Fig 5, renumbered D131) |
| Fig 5 | Co-located exposure map and cross-tab | w4h_coexposure.csv, w3h_state_coexposure.csv | DONE (data, C59/C63); figure PLANNED (was Fig 6, renumbered D131) |
| Fig 6 | GW exposed by technology (fuel class), fleet and scenario, TX35>=30 d/yr (heatmap/tile, operating vs planned_all facets, 3 scenarios) | w3_table1.csv | DONE (data); figure PLANNED (new, D131: replaces the original tabular "Table 1" design -- 243 rows judged too large for a table, condensed into a heatmap instead) |
| Table 1 | Fleet and capacity by technology and fuel, operating vs planned | plant_units.parquet (BRA only) | DONE (data); table PLANNED (new content, D131: replaces the original standalone Fig 1, judged redundant once Fig 5's map carries the exposure-class layer) |
| Table 2 | Leave-one-out, 5 largest hydro | w4d_leave_one_out.csv (copy of c23d_7_leave_one_out.csv, audit/c23/c23d) | DONE (D113, O19 closed); table PLANNED |
| Table 3 | 4x4 cross-tab, GW | w4h_coexposure.csv, table3_coexposure.csv | DONE (C59/D97 data; scope fixed C85/D130): group in {hydro, thermal_water_dependent} x fleet in {operating, planned_all} x itaipu=b (hydro) / na (thermal) x scenario in {ssp126,370,585}, canonical pool/null/cutset (catchment|cell, block12, p50_p90_p99), full 4x4 heat x drought cross-tab, 192 rows. gw_total vs sum of 16 cell gw_median gap reported per combo (median not additive, D80/D96/D97/D99/D106), range 0.39-23.53 GW. Regression check vs D102 (hydro operating itaipu b = 102.667 GW) PASS. Table formatting for publication pending (Group E/H). |
| Supplementary | ONS validation | validation.csv | DONE (D73) |

---


