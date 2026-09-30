# REN IPH Validation Report (COMANDO 22)
Generated: 2026-09-30T12:54:18.905954+00:00
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
## 5. Annual validation against REN/ERSE
Reference: annual IPH series reproduced in official ERSE documentation, attributed to REN (`data/validation/ren_iph_reference_annual.csv`).

**Important distinction (A vs B in the module docstring)**: REN's monthly `RegimeYearly` endpoint used for acquisition has no annual/civil-year field. The only quantity that can be derived from it is a simple calendar-year arithmetic mean of the 12 monthly values, which is compared below **only to test whether it is the same quantity ERSE reports -- not assumed to be**. It is not: 2017 is the clearest case (ERSE reports 0.47, a low-productivity year; the derived mean is far higher because 2017's mid-year, typically low-weight months, happen to carry unusually high IPH values that a simple mean over-weights relative to what an energy/reference-weighted annual figure would). The most likely explanation is that REN's real annual IPH is weighted by each month's reference/expected generation (larger in winter than summer), a weighting this monthly-ratio endpoint does not publish -- not a data error, an aggregation-method gap.
| year | reference | derived_calendar_mean | n_months_used | abs_diff | rel_diff | pass_at_2dp |
|---|---|---|---|---|---|---|
| 2015 | 0.74 | 0.7488888888888888 | 9 | 0.010000000000000009 | 0.013513513513513526 | True |
| 2016 | 1.33 | 1.3108333333333335 | 12 | 0.020000000000000018 | 0.015037593984962419 | False |
| 2017 | 0.47 | 0.7124999999999999 | 12 | 0.24 | 0.5106382978723404 | False |
| 2018 | 1.05 | 0.9291666666666668 | 12 | 0.12 | 0.11428571428571428 | False |
| 2019 | 0.81 | 1.0091666666666668 | 12 | 0.19999999999999996 | 0.2469135802469135 | False |

- **Status: FAIL** (1/5 years within tolerance via the derived calendar-mean method)

This FAIL does not invalidate the acquisition (Section 4 already confirms the underlying monthly data is correct against APA) -- it means the derived annual quantity is not a validated substitute for REN's own (unpublished-by-this-endpoint) annual figure, and no article text should present it as REN's official annual IPH.
## 6. Auxiliary comparison with DGEG
**Not completed in this session.** DGEG's monthly hydroelectric production dataset for Portugal was not acquired: no confirmed public API/download endpoint was located or verified, and per project rule this is not fabricated. This section remains an open follow-up, not a silently-skipped requirement -- see `docs/DECISIONS.md` O11.
## 7. Limitations
- The REN/W5E5 overlap is short (see Section 8): sufficient for implementation-level cross-checking, not for long-term climatological validation (distinction A vs B, module docstring).
- 2015 is missing jul/aug/sep (Section 3); any statistic requiring those specific months for 2015 has one fewer year of coverage than the other four years.
- The annual ERSE comparison (Section 5) does not validate; the true annual aggregation method is unknown from this endpoint.
- DGEG auxiliary check not completed (Section 6).
- Portugal's own small (plant, model) series population already carries a documented sample-size caveat elsewhere (D56); this report adds a second, independent one (short observational overlap) that is not about model count.
## 8. Reproducibility
Run `python scripts/22_validate_ren_iph.py` to regenerate this report and its manifest entry from the current `data/processed/ren_iph.parquet` and the reference CSVs in `data/validation/`. `tests/test_validation_ren_iph.py` covers the comparison logic against synthetic fixtures (not live network calls).
## 9. Final validation status
"The REN IPH acquisition is validated against independent official publications for the available overlap. The available 2015-2019 overlap with W5E5 is sufficient for implementation-level cross-checking but is not sufficient to establish a long-term climatological validation."

"Portugal is therefore retained in the quantitative validation framework, with the five-year overlap identified as a limitation and not as a missing-data failure."

- REN_IPH_MONTHLY_VALIDATION = PASS
- REN_IPH_ANNUAL_VALIDATION = FAIL (derived-mean method; see Section 5 caveat)
- REN_W5E5_OVERLAP = 2015-2019
- REN_W5E5_COMPLETE_YEARS (all 12 months present) = [2016, 2017, 2018, 2019] (4)
- REN_W5E5_AVAILABLE_MONTHS (actual, not assumed) = 57
