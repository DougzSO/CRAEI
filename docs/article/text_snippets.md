> **Document role:** Draft article text (English) awaiting author approval.
> **Contains:** proposed wording for the null model (A3) and the hydropower compound-context reframing (A1).
> **Does NOT contain:** methods or results (-> docs/METHODS_SPEC.md, docs/RESULTS_REGISTRY.md).
> **Status:** DRAFT v2, not approved. No figure has been changed from these texts (Fig 4 text is applied in Phase 9, O46).

---

## A3. Null model (Fig 4)

### Which null hypothesis the block bootstrap tests

The block bootstrap draws baseline and future as two independent resamples of randomly chosen
series of the pool (all catchments or cells x 5 GCMs, baseline 1985-2014), not as a resample of
the same plant's own series: each member of a pair is `pool[rng.integers(0, len(pool))]`
resampled in contiguous 12-month blocks (`src/craei/hazards/null_model.py:34-40`), and the
baseline and the future of one simulation are two separate such draws
(`null_model.py:49-57`). The null is therefore stationary (no trend) with random location and no
pairing of baseline and future within the same plant and GCM, which METHODS_SPEC.md (section 6,
item 1) states explicitly. "No-Climate-Change" is therefore not exact (the null also removes the
within-plant pairing), and the title and text below use "stationary resampling null".

### Null types in w4b_excess_over_null.csv / w4c_spi_vs_spei.csv

Six `null_type` values; headline = `block_bootstrap_12` (D83/D102, production point
SPEI <= -1.5, R_D >= 2.0).

| null_type | What it is | Role |
|---|---|---|
| block_bootstrap_12 | random pool member, 12-month blocks, 360-month series | headline |
| block_bootstrap_24 / _36 / _60 | same, longer blocks | block-length sensitivity (non-monotonic, D102) |
| white_noise_ms12 | standardized 12-month moving sum of white noise | lower reference (1.80% hydro, 2.10% thermal) |
| ar1 | stationary AR(1), phi estimated from the pool | upper reference |

### (a) Methods paragraph (under 150 words)

> **Null model of internal variability.** Observed exposure is compared with a stationary null
> with no trend and no pairing between baseline and future. We draw 2,000 pairs of synthetic
> 360-month SPEI-12 series: each member of a pair is one series picked at random from the pool
> (all catchments for hydropower, all cells for water-dependent thermal plants, times five GCMs,
> 1985-2014) and resampled in contiguous 12-month blocks. Baseline and future are thus
> independent draws from random locations and GCMs, whereas the observed data pair both periods
> within the same plant and GCM. A pair is "exposed" when the frequency of months with
> SPEI <= -1.5 at least doubles (R_D >= 2). The pools hold 1,110 (hydropower) and 1,705
> (thermal) series; the null rates are 18.88% and 17.74%. Excess exposure is the observed share
> of operating capacity with R_D >= 2 minus the null rate, in percentage points.

### (b) Fig 4 title and axis label (replaces "Climate Exposure Exceeds Chance ...")

> Title: **Drought Exposure Relative to a Stationary Resampling Null, Brazil's Operating Fleet**
>
> X axis: **Excess over the stationary resampling null (percentage points of operating capacity)**

(The title states what is tested and does not claim an exceedance: thermal SPI at SSP1-2.6 is -1.1 pp.)

### (c) Fig 4 note (names the pools)

> Point = median, line = range across 5 GCMs. Null: baseline and future drawn independently at
> random from the pool (12-month blocks, 2,000 draws, no trend); excess = share of operating
> capacity with R_D >= 2.0 minus the null rate. Pools differ by scale: hydropower, 1,110
> catchment-scale series (null rates 18.88% SPEI, 20.47% SPI); thermal, 1,705 cell-scale series
> (17.74% SPEI, 17.84% SPI).

Source checks: w4_null.py:17-18 (seed 23, n_sim 2,000, 360 months, block 12), w4_null.py:35-36
(pool 1,110), w4c_null_thermal.py:32 and :57-61 (cell-scale pool), null_model.py:94-117 (R_D >= threshold
rate, undefined baseline excluded), w4b_excess_over_null.py:98-101 (excess = observed - null).

### Pool size 1,705 vs 1,710 (resolved, D138)

Two thermal cell pools exist. W4g/W4r (and the co-exposure of Table 3) use the unit-level population
of plant_units: 699 plants, 342 cells, 1,710 series. The W4c null behind Fig 4
(`w4c_null_thermal.py:38-55`) selects plants by the plant-level class (plants.parquet and bucket
in plant_hazards): 694 plants, 341 cells, 1,705 series. The difference is 5 plants (Guarani,
Atlantico, Termopecem, Azulao, Termo Norte) whose plant-level class is air-only although some of
their units are water-dependent; they add one cell. `truncated_pet_cells.parquet` is not the cause:
it lists 51 Indian cells and no Brazilian one. Fig 4 uses 1,705.

---

## A1. Hydropower regional compound climate context (Fig 5a, Table 3 hydropower block)

Approved: title and structure. PENDING: the ratios in the note, because the V3 ratios differ from V1 by
more than 3 pp in two scenarios (table below). Nothing has been applied to Fig 5a or Table 3.

### Co-extreme / extreme-drought ratios, hydropower, operating (national, canonical pool)

| | V1 median (previous text) | V3 mean (Table 3 main since D137) |
|---|---|---|
| SSP1-2.6 | 36.5 / 43.8 = 83% | 35.9 / 44.2 = 81% |
| SSP3-7.0 | 37.4 / 42.3 = 88% | 34.3 / 40.6 = 84% |
| SSP5-8.5 | 55.9 / 60.7 = 92% | 52.8 / 60.4 = 87% |

### 1. Fig 5a title, colorbar and Table 3 block heading

> Suptitle: **Regional Compound Climate Context by State -- Hydropower: Extreme Basin Drought and
> Extreme Plant-Cell Heat** / (Baseline 1985-2014, Future 2041-2070, Itaipu Brazil share)
>
> Colorbar: **Median share of capacity with extreme basin drought and extreme cell heat (%)**
>
> Table 3 hydropower block heading: **Hydropower, Regional Compound Climate Context (Itaipu Brazil share)**

### 2. Footnote (Fig 5a) and note (Table 3, hydropower block), with V3 ratios

> Heat is shown as regional climatic context at the plant cell (TX35 class), not as a heat hazard
> to hydropower, which is outside H1. Compound = extreme drought class (catchment) and extreme heat
> class (plant cell), same GCM. For the operating fleet, the compound share is 81%, 84% and 87% of
> the extreme-drought share alone (SSP1-2.6 / SSP3-7.0 / SSP5-8.5; mean across 5 GCMs: 35.9 of
> 44.2%, 34.3 of 40.6%, 52.8 of 60.4%). This overlap is attributed in part to the temperature
> dependence of SPEI-Hargreaves; the circularity control of the E1 analysis (SPI-based) will test
> it when available.

Note: Fig 5a maps state-level medians (w3h_state_coexposure.csv), while the ratios come from the
national Table 3 (mean across 5 GCMs); the footnote says "national" to avoid mixing the two.

### 3. Sentence for D88

> Reframing (D139): hydropower remains outside H1 (D88 unchanged); the plant-cell TX35 class is kept
> only as regional climatic context and is now labelled as such wherever it appears (Fig 5a,
> Table 3 hydropower block).

## O48. Thermal population (Methods)

> Water-dependent thermal plants are identified by the plant-level cooling class. Five plants whose
> plant-level class is air-cooled but that hold some water-dependent units (three operating: Guarani,
> Atlântico, Termo Norte; two planned: Termopecém, Azulão) are treated as air-cooled, which gives an
> analytical operating water-dependent population of 618 plants and 39.10 GW (39.77 GW at unit level)
> and a planned population of 41.15 GW (43.58 GW at unit level) (D151).
