# FAO-56 Example 8: Extraterrestrial Radiation (Ra)

Source: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop
evapotranspiration - Guidelines for computing crop water requirements*. FAO
Irrigation and Drainage Paper 56. Chapter 3, Example 8.
<https://www.fao.org/4/x0490e/x0490e07.htm> (fetched 2026-09-28).

Used by `tests/test_hazards_pet.py::test_extraterrestrial_radiation_matches_fao56_example`
to verify `craei.hazards.pet.extraterrestrial_radiation` against the
published worked example, per Spec §1.4 H2 / `pet.py`'s docstring.

## Problem statement

"Determine the extraterrestrial radiation (Ra) for 3 September at 20°S."

## Worked calculation, as printed

- Eq. 22 (latitude to radians): 20°S -> φ = (π/180)(-20) = **-0.35 rad**
- Day of year (Table 2.5): J = **246**
- Eq. 23 (inverse relative distance Earth-Sun): dr = 1 + 0.033 cos(2π(246)/365) = **0.985**
- Eq. 24 (solar declination): δ = 0.409 sin(2π(246)/365 - 1.39) = **0.120 rad**
- Eq. 25 (sunset hour angle): ωs = arccos[-tan(-0.35)tan(0.120)] = **1.527 rad**
- Intermediate terms: sin(φ)sin(δ) = -0.041; cos(φ)cos(δ) = 0.933
- Eq. 21 (Ra): Ra = (24(60)/π)(0.0820)(0.985)[1.527(-0.041) + 0.933 sin(1.527)]
  = **32.2 MJ m⁻² d⁻¹**

## Verdict (COMANDO 16)

`craei.hazards.pet.extraterrestrial_radiation(lat_deg=-20.0, day_of_year=246)`
is compared against this published 32.2 MJ m⁻² d⁻¹ figure in the test above;
see `PROGRESS.json` C16 for the calculated value from this run.
