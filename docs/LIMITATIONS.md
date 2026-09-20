| ID  | Limitation | Declared in | Mitigation |
|---|---|---|---|
| L01 | GEM has no cooling technology field | Methods §1.2 | Freshwater/coastal bounds |
| L02 | India has no validation data | Methods §1.7 | Stated as limitation |
| L03 | Hazard index is not a plant operating limit | Methods §0 | Described as exposure, not impact |
| L04 | Climate data resolution is 0.5° | Methods §1.3 | Area-weighted catchment aggregation |
| L05 | Future SPEI series start in December 2041 | Methods §3 Step 6 | Stated in Methods |
| L06 | Aqueduct is not consistent with the ISIMIP3b ensemble | Methods §1.4 (H3) | Reported separately from H1/H2 |
| L07 | Wind power is excluded from the hazard assessment | Methods §0, §1.4 | Justified in §6 Q1 |
| L08 | W5E5 ends in 2019 (2021 water crisis outside validation) | Methods §1.7 | Stated in Methods |
| L09 | Validation has no India coverage | Methods §1.7 | Stated as limitation |
| L10 | SPEI extrapolation truncated at ±3 | Methods §1.3, §1.4 (H2) | Clipping documented in Methods |
| L11 | Geothermal capacity (GEM `Type`, Portugal only) is out of the four defined technology classes | D15 | Excluded from the fleet, same treatment as wind |
| L12 | ISIMIP climate files are cropped to each country's bbox (COMANDO 11); an upstream hydro catchment that extends past that bbox (e.g. into a neighboring country) has no grid cells there to weight | D25, COMANDO 14 | Catchment weights renormalize to sum 1 over the in-bbox cells only; `n_upstream_basins` and `pct_diff_up_area` in the catchment validation report flag which plants have the largest unweighted catchment fraction |
| L13 | Aqueduct 4.0 `future_annual` water stress (`ws`) is the median of an internal 5-GCM ensemble (PCR-GLOBWB 2 forced by CMIP6), independent of and not decomposable into this project's ISIMIP3b 5-model ensemble used for H1/H2 (D01) — only the pre-aggregated median value is available, no per-model spread | D34 | Reported as a single value per scenario, no model-agreement statistic for H3 (already separate from H1/H2 per L06) |
| L14 | Portugal's study scope is continental only (D40): Azores and Madeira are excluded from the plant inventory entirely, not analyzed under any hazard (H1/H2/H3), because the Azores have no Aqueduct coverage at all (every row is the -9999 no-match sentinel) and Madeira has only 1 real Aqueduct basin nationwide (`pfaf_id` 152000) -- found while investigating a join bug (D37) that had silently snapped these plants to a mainland basin 9-17 degrees away. 9 GEM plants (18 units, including all 4 water-dependent thermal ones) are excluded from `plants.parquet`, reason `non_mainland_excluded` | D37, D40 | Excluded at the inventory stage (COMANDO 13), not imputed or silently misjoined; all PRT results in this project are mainland-only by construction |
