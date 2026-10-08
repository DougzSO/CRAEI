# Discussion (draft)

Status: draft for the author (Phase W). Every number cites a register row [R..] of docs/article/DECISION_MEMO_F5.md; limitations in
Section 4.4 are tied to the row that quantifies them. Reference slots are [CIT-NEEDED: topic]; [AUTHOR] marks context,
interpretation or literature the author adds.

---

## 4.1 The thermal backup sits in the same hydroclimatic regime as the hydropower

In observations, the probability that the water-dependent thermal fleet is under drought is 0.486 in months of hydropower drought, against
0.101 in all months, a dependence of 4.83 times the independence expectation [R12]. The five GCMs reproduce it at baseline (median 5.00)
[R13]. The dependence concentrates in the Southeast and Center-West, where D is 3.69 and 3.41 and which hold 64% of the operating
thermal capacity; the interval excludes independence only in the Southeast [R15]. The same two regions hold the largest
co-extreme thermal capacity at the state level under SSP5-8.5 (Sao Paulo 2.67 GW, Mato Grosso do Sul 2.56 GW) [R24]. A fleet
designed to cover hydropower shortfalls therefore draws on the same sky: when the catchments are dry, the cells that host the
thermal plants are more often dry as well. [AUTHOR: link to the Brazilian dispatch logic, where thermal plants cover low
reservoir periods, and to the 2014-2015 Southeast drought.] [CIT-NEEDED: hydrothermal coordination and thermal dispatch in the
Brazilian system] [CIT-NEEDED: the 2014-2015 Southeast Brazil drought and its power-system effects]

## 4.2 Warming raises joint stress through the marginals, not through stronger coupling

Under SSP5-8.5 the joint frequency of hydropower drought and thermal drought rises by 0.095, of which 0.065 comes from each side
failing more often and 0.030 from a change in dependence [R09]. Under SSP3-7.0 the rise is 0.012 and the dependence part is 0.001
[R09]. The coupling itself does not change consistently: dD is positive in three of five GCMs and its interval excludes zero in none
[R10]. The primary criterion of the analysis is not met, because the change in P(H and T) is positive in three of five GCMs under
SSP3-7.0 [R09]. For heat, the picture is clearer and the mechanism is the same: the joint stress of hydropower drought and thermal
heat rises in all five GCMs in every scenario, with an interval above zero in three of five GCMs under SSP3-7.0 and in five of five under SSP5-8.5, almost entirely through the marginals [R11], and the
share of thermal capacity under monthly heat stress grows from 6.5% to 23.2, 29.8 and 35.2% [R21]. The weakening of the hedge in this
study is a result of both sides becoming more stressed, not of a tighter link between them. [AUTHOR: whether this reading changes
how adaptation is framed.]

## 4.3 Implications for the planned water-dependent gas expansion

The planned thermal fleet is 48.35 GW, of which 41.15 GW is water-dependent at plant level and gas is 44.12 GW, with 39.35 GW of it
water-dependent [R27]. Under SSP3-7.0 and SSP5-8.5, 39.0 and 61.6% of the planned thermal capacity, and 39.1 and 62.1% of the planned
gas capacity, would face at least 30 days per year of TX35 [R28]; the operating fleet is at 36.3 and 49.1% [R05]. Planned capacity is
therefore at least as exposed to heat as the existing capacity in the higher scenarios. We have not computed the drought exposure of
the planned fleet, and the region in which the planned plants will sit is not in the inventory at a resolution that tests the
Southeast and Center-West concentration [AUTHOR: whether planned plant locations are available]. If the plants follow the existing
pattern, the evidence of Section 4.1 suggests that they add backup capacity in the regime where it is most correlated with hydropower
drought. [AUTHOR: planning context for the expansion.] [CIT-NEEDED: Brazilian ten-year energy expansion plan, thermal and gas
expansion]

## 4.4 Limitations

*Drought index.* SPEI uses a temperature-dependent evaporative term. The hydropower excess is +40.75, +43.20 and +53.94 pp under SPEI
and +17.40, +3.03 and +38.60 pp under SPI [R01, R02]; the thermal excess is +20.63, +28.50 and +48.06 pp under SPEI and -1.08, +5.44 and
+27.50 pp under SPI [R03, R04]. We use SPEI as the claim and SPI as the lower band; E1 uses SPI as the circularity control.

*GCM dependence between heat and drought.* In observations the heat and drought pair shows no dependence (D = 1.14), whereas the GCMs
give about 2.8 [R14]. GCM co-exposure (Figures 5a and 5b, Table 3) is probably inflated. ISIMIP3BASD adjusts variables mostly
univariately, so the precipitation-temperature dependence of the GCMs may be distorted [CIT-NEEDED: ISIMIP3BASD and multivariate
dependence].

*Spread between GCMs.* The range across five deterministic runs is not a confidence interval. The agreement k/5 ranges from three to
five across the headline rows [R01-R11], the three-GCM subset changes the thermal excess to +8.34, +18.74 and +34.53 pp [R03], and the
exposure under SSP3-7.0 falls below SSP1-2.6 in several rows because one or two GCMs and a few large plants set the sign [R20].

*Few plants dominate.* Removing Itaipu, Belo Monte or Tucurui moves the reservoir-bucket share by up to 9.14 pp [R26], and state
medians rest on three or fewer plants in several states (dotted states in Figures 5a and 5b).

*Aggregation.* E1 uses national capacity shares, which mix climatically distinct regions; the regional D ranges from 1.14 to 3.69
[R15]. In E3 the macro-regions approximate the ONS submarkets, and the Northeast and North do not coincide exactly with the ONS
subsystems [R16-R18].

*Exposure is not generation.* The inflow used for the E3 comparison is natural inflow without reservoir operation [R16-R18], and no
generation data enter the study. The SPEI-ENA association is moderate (rho = 0.370 in the Southeast and Center-West) and the
skill score has an interval that includes zero [R16, R18]; the index is weakest in the region where the E1 dependence is largest.

*Time windows and population.* The E1 future covers 2042-2070 and the observed series 1986-2014, because the first 11 months of
SPEI-12 are undefined [D141]. Thermal plants are classified by the plant-level cooling class; mixed-cooling plants treated as
air-cooled reduce the operating water-dependent population from 39.77 to 39.1015 GW [R27]. The TX35 threshold is an indicator of
heat, not an operating limit [AUTHOR: link to plant derating data].

## 4.5 What the study does not answer

The study measures climatic exposure at plant locations. It does not estimate generation losses, dispatch or reliability: no
generation or operating data enter the analysis, and the drought index is not a model of reservoir operation or of thermal
dispatch. It does not assess wind or solar capacity, transmission, demand or the cost of adaptation. It reports spatial coincidence
and the monthly co-occurrence of national and regional series, not the simultaneity of hazards at one plant, and it does not assign
probabilities to impacts [METHODS_SPEC 11]. The drought exposure of the planned fleet and the cooling technology of individual
plants are outside the headline results. [AUTHOR: next steps, for example generation data and dispatch models.]
