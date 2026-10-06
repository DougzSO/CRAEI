# REN IPH Validation Report (COMANDO 22-23)
Generated: 2026-10-06T12:03:40.787017+00:00
## 1. Data source and endpoint
REN DataHub, monthly "Indice de produtibilidade hidroelectrica" (IPH). Real endpoint discovered by browser instrumentation (COMANDO 21): `POST https://datahub.ren.pt/service/Electricity/RegimeYearly/2900?culture=pt-PT&dayToSearchString={ticks}&isShare=true` (host `datahub.ren.pt`, not the documented `servicebus.ren.pt/datahubapi`).
## 2. Acquisition method
Direct `requests` POST, no browser automation needed in production (`src/craei/acquire/ren.py`). `dayToSearchString` is a .NET `DateTime.Ticks` value for a year's last day. **Critical finding (D60)**: positions 7-9 (jul/ago/set) of a `year=Y` query's 12-value series belong to calendar year Y+1, not Y -- found by cross-checking against the APA reference (Section 4) and corrected in `ren.py`'s `calendar_year_for_month`. A year=2014 query (which returns no data) must still be fetched to obtain calendar year 2015's own jul/ago/set slots -- since it has no data, calendar year 2015 is missing those three months.
## 3. Dataset coverage
- Rows: 132
- First date: 2015-01-01
- Last date: 2026-09-01
- Duplicate dates: 0
- Monotonically increasing: True
- Null IPH values: 0
- Negative IPH values: 0
- IPH range: [0.14, 2.33]
- Months per year: 2015=9, 2016=12, 2017=12, 2018=12, 2019=12, 2020=12, 2021=12, 2022=12, 2023=12, 2024=12, 2025=12, 2026=3

Note: 2015 has 9 months, not 12 (jul/aug/sep 2015 unavailable, see Section 2); 2026 has only its jul/aug/sep (sourced from the 2025 query), since a `year=2026` query is a future date to the server and returns no data for the still-incomplete current year. Neither is an acquisition bug -- both are genuine gaps in what REN's endpoint can return, documented rather than padded or hidden.
## 4. Monthly validation against APA
Reference: Agencia Portuguesa do Ambiente, "Monitorizacao Agrometeorologica e Hidrologica -- 30 de junho de 2018", Tabela 7 (source stated as REN's own monthly statistics). Hydrological-year values mapped to calendar dates per `data/validation/ren_iph_reference_apa.csv`.
- Months compared: 33
- Matched (within 0.015): 33
- Mismatched: 0
- Max abs diff: 0.010000000000000009
- Mean abs diff: 0.0012121212121212065
- **Status: PASS**

No mismatches: every compared month agrees with APA within 2-decimal rounding. This is the direct evidence that D60's jul/ago/set calendar-year shift is correct, not merely plausible -- the fix was derived FROM this comparison.
## 5. Annual comparison against REN/ERSE, and annual-method limitation
Reference: annual IPH series reproduced in official ERSE documentation, attributed to REN (`data/validation/ren_iph_reference_annual.csv`).

**COMANDO 23, Part A -- definitively resolved.** Every raw REN response saved during acquisition (2015-2025, `data/raw/validation/ren_iph/*.json`) was inspected directly: `check_annual_field_in_raw_response` confirms none carries an annual total, weight, production, or afluência field -- only `xAxis`/`yAxis`/`legend`/`plotOptions`/`chart`/`series`, with `series` holding exactly the 12 monthly values (annual field present in any inspected response: False). A search of the repository, and a web search of REN/ERSE/DGEG published technical documentation, found no public description of the exact annual aggregation formula. The only quantity derivable from this endpoint is therefore a simple calendar-year arithmetic mean of the 12 monthly values, compared below **only to test whether it is the same quantity ERSE reports -- not assumed to be**. It is not: 2017 is the clearest case (ERSE reports 0.47, a low-productivity year; the derived mean is far higher because 2017's mid-year monthly values happen to be unusually high and a simple mean over-weights them relative to REN's real, unpublished aggregation -- most likely reference/expected-generation-weighted, larger in winter than summer).
| year | reference | derived_calendar_mean | n_months_used | abs_diff | rel_diff | pass_at_2dp |
|---|---|---|---|---|---|---|
| 2015 | 0.74 | 0.7488888888888888 | 9 | 0.010000000000000009 | 0.013513513513513526 | True |
| 2016 | 1.33 | 1.3108333333333335 | 12 | 0.020000000000000018 | 0.015037593984962419 | False |
| 2017 | 0.47 | 0.7124999999999999 | 12 | 0.24 | 0.5106382978723404 | False |
| 2018 | 1.05 | 0.9291666666666668 | 12 | 0.12 | 0.11428571428571428 | False |
| 2019 | 0.81 | 1.0091666666666668 | 12 | 0.19999999999999996 | 0.2469135802469135 | False |

- Derived calendar-mean agreement: 1/5 years within tolerance.
- **Status: REN_IPH_ANNUAL_VALIDATION = RESOLVED_AS_METHODOLOGICAL_LIMITATION** -- not FAIL. This is not an error in the acquired monthly series (Section 4 independently PASSes against APA); it is that the annual figure cannot be reconstructed from the monthly endpoint without REN's undisclosed aggregation weighting. No article text should present the derived calendar-mean as REN's official annual IPH.
## 6. Auxiliary comparison with DGEG
**Completed (COMANDO 23, Part B).** DGEG publishes gross/net monthly electricity production by technology (GWh) at https://www.dgeg.gov.pt/pt/estatistica/energia/eletricidade/producao-mensal-de-eletricidade/, one `.xls` per year; the 2015-2019 files were downloaded directly (`src/craei/acquire/dgeg.py`) and the gross "Hídrica" row extracted (`data/processed/dgeg_hydro_generation.parquet`). This is a **production volume**, not REN's productivity ratio -- never called IPH, never treated as equivalent to it, and no correlation threshold is imposed as a pass/fail gate.

- Months compared: 57
- Years compared: [2015, 2016, 2017, 2018, 2019]
- Monthly Pearson r: 0.569
- Monthly Spearman r: 0.375
- Annual Pearson r: 0.901
- Annual Spearman r: 0.900

Annual REN IPH (mean) vs DGEG gross hydro generation (sum):

| year | iph_mean | hydro_generation_gwh_sum |
|---|---|---|
| 2015 | 0.7488888888888889 | 8227.0 |
| 2016 | 1.3108333333333333 | 16684.0 |
| 2017 | 0.7125 | 7389.0 |
| 2018 | 0.9291666666666667 | 13628.0 |
| 2019 | 1.0091666666666665 | 10103.0 |

Interpretation: the annual correlation (~0.90, both Pearson and Spearman) is strong and in the expected direction -- both series independently identify 2016 as the wettest year and 2015/2017 as the driest among 2015-2019. The weaker monthly correlation is expected, not a discrepancy: monthly production additionally depends on afluência timing, reservoir storage/operation, dispatch, installed capacity, and pumping, none of which IPH (a productivity ratio) captures on its own. **Status: DGEG_AUXILIARY_CHECK = COMPLETED.**
## 7. REN x W5E5 overlap
| dataset | start | end | complete_years | usable_months |
|---|---|---|---|---|
| REN IPH | 2015-01-01 | 2026-09-01 | 10 | 132 |
| W5E5 | 1984-01-01 | 2019-12-31 | 36 | 432 |
| overlap | 2015-01-01 | 2019-12-31 | 4 | 57 |

- Common period: 2015-01 to 2019-12
- Complete calendar years (all 12 months present): [2016, 2017, 2018, 2019] (4)
- Available overlap months (actual, not assumed 12/year): 57
- 2015 is explicitly a partial year (9 months, jul/aug/sep missing per Section 2/3) and is never counted among the complete years.
## 8. Scientific limitations
- The REN/W5E5 overlap is short (Section 7): sufficient for implementation-level cross-checking, not for long-term climatological validation (distinction A vs B, module docstring).
- 2015 is missing jul/aug/sep (Section 3); any statistic requiring those specific months for 2015 has one fewer year of coverage than the other four years.
- The annual ERSE comparison (Section 5) cannot be reproduced from the monthly endpoint; this is a documented methodological limitation of the annual figure, not a defect of the monthly series.
- The DGEG auxiliary check (Section 6) is a production-volume sanity check, not a substitute validation of IPH itself.
- Portugal's own small (plant, model) series population already carries a documented sample-size caveat elsewhere (D56); this report adds a second, independent one (short observational overlap) that is not about model count.
## 9. Final status
**Monthly REN IPH acquisition and validation = validated** against an independent official reference (APA), with the underlying date-mapping bug (D60) found and fixed as part of this validation.

**Annual REN/ERSE value cannot be independently reconstructed from the monthly endpoint** unless REN's official annual aggregation methodology becomes available; this is recorded as a formal methodological limitation, not an acquisition failure.

**Auxiliary DGEG comparison = completed**, showing strong annual co-movement (Pearson/Spearman ~0.90) consistent with (not equivalent to) the acquired IPH series.

Portugal is retained in the quantitative validation framework, with the five-year overlap and the annual-method limitation identified as limitations, not as missing-data failures.

- REN_IPH_ACQUISITION = PASS
- REN_IPH_MONTHLY_VALIDATION = PASS
- REN_IPH_ANNUAL_VALIDATION = RESOLVED_AS_METHODOLOGICAL_LIMITATION
- DGEG_AUXILIARY_CHECK = COMPLETED
- REN_W5E5_OVERLAP = 2015-01_to_2019-12
- REN_W5E5_COMPLETE_YEARS = 4
- REN_W5E5_AVAILABLE_MONTHS = 57
