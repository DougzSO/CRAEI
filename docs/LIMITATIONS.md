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
