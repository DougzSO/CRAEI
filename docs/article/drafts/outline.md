# Article outline (draft)

Status: draft for the author (Phase W). Target journal: Climate Risk Management (D142). Length limit found: 8,000 words for an
original research article, including main text, tables and figure captions, excluding references; other limits (abstract,
highlights, number of figures, dpi, availability statements) are TO BE DEFINED (O52). Word counts below are measured on the
drafts (`wc -w`, including the status lines) or planned for sections not yet written.

## Working title (author to choose)

[AUTHOR: title. The framing is: hydropower drought exposure, the thermal backup in the same hydroclimatic regime, and warming
that raises joint stress through the marginals.]

## Sections

| Section | Content | Figures and tables | Words (drafted / planned) |
|---|---|---|---|
| Abstract | problem, data, five findings, limitation; format TO BE DEFINED (O52) | none | planned 200 |
| 1 Introduction | see 1.1 | none | planned 600 |
| 2 Methods | 2.1 Design (105); 2.2 Inventory and populations (230); 2.3 Climate data (195); 2.4 Heat H1 (155); 2.5 Drought H2 (230); 2.6 Null (215); 2.7 Co-exposure (190); 2.8 E1 (420); 2.9 E3 (210); 2.10 Sensitivities (165) | Table 1 (2.2) | drafted 2,200 |
| 3 Results | 3.1 Hydropower drought exposure; 3.2 Thermal backup; 3.3 Hedge correlated in observations; 3.4 Marginals; 3.5 Evidence quality; 3.6 Results that do not support a stronger reading | Figures 3, 4, 5a, 1, 7, 8; Tables 2, 3 (main or supplementary, see below) | drafted 3,800, of which captions about 1,900 |
| 4 Discussion | 4.1 Same hydroclimatic regime (185); 4.2 Marginals, not coupling (210); 4.3 Planned gas expansion (185); 4.4 Limitations (400); 4.5 What is not answered (120) | none | drafted 1,160 |
| 5 Conclusions | five findings and the two limits that matter most | none | planned 150 |
| Availability | data and code statements; format TO BE DEFINED (O52) | none | planned 80 |

Estimated total (abstract excluded): about 8,000 words with the full list in the main text, which is at the limit, and about 7,200
with the compact list below.

### 1.1 Introduction (to write, five paragraphs)

1. Power-system dependence on water and temperature; thermal cooling and hydropower [CIT-NEEDED: power generation vulnerability to
   climate and water; suggest van Vliet et al. 2016, verify]. [AUTHOR]
2. The Brazilian system: hydropower share, thermal backup role, planned water-dependent gas expansion [CIT-NEEDED: Brazilian
   power system structure and expansion plan]. [AUTHOR]
3. Gap: hazards are assessed one at a time and without a null for internal variability; the correlation of the backup with the
   asset it covers is rarely tested [CIT-NEEDED: compound hazards and power systems]. [AUTHOR]
4. This study: five GCMs, three scenarios, plant-level exposure for heat and drought, stationary null, E1 and E3 analyses.
5. Findings in one sentence each (the five framing sentences) and article structure.

## Figures and tables in text order

The figure numbers below are those of the files in `data/outputs/article/` (D134). The text order differs from the numbering
because Section 3 follows the five framing sentences. [AUTHOR: decide whether to renumber at submission; the map of new to
current numbers is in the last column.]

| Text order | Item | Section | Placement (compact list, D153) | Current ID | Caption + paragraph words |
|---|---|---|---|---|---|
| 1 | Table 1 fleet and capacity | 2.2 | main | Table 1 | caption not drafted |
| 2 | Drought exposure map, all plants | 3.1 | main | Fig 3 | 110 + 86 |
| 3 | Excess over the null (forest plot) | 3.1 | main | Fig 4 | 135 + 182 |
| 4 | Leave-one-out, five largest plants | 3.1 | supplementary | Table 2 | 118 + 102 |
| 5 | Hydropower co-exposure by state | 3.1 | main | Fig 5a | 238 + 178 |
| 6 | Heat class map, thermal plants | 3.2 | main | Fig 1 | 126 + 44 |
| 7 | Heat exposure curves by threshold | 3.2 | supplementary | Fig 2 | 87 + 138 |
| 8 | Heat exposure by fuel | 3.2 | supplementary | Fig 6 | 101 + 91 |
| 9 | Thermal co-exposure by state | 3.2 | supplementary | Fig 5b | 69 + 72 |
| 10 | E1 hedge failure | 3.3, 3.4 | main | Fig 7 | 240 + 204 (+ 259 in 3.4) |
| 11 | E3 inflow association | 3.5 | main | Fig 8 | 167 + 212 |
| 12 | Heat x drought cross-tab | 3.5 | main (main block), supplementary (medians) | Table 3 | 208 + 126 |
| s | Parameters | supplementary | supplementary | Table 0 | not drafted |

Moving Table 2, Fig 2, Fig 6 and Fig 5b to the supplementary material removes about 780 words from the main count. Fig 2 and
Fig 6 carry the thermal heat claim [R05, R25]; if they leave the main text, the heat claim of Section 3.2 relies on Fig 1 and
the text only.

## Register coverage

Rows R1-R21 (docs/article/DECISION_MEMO_F5.md section d) plus R22-R28 added in Phase W (counts, fuel shares, leave-one-out
changes, inventory and planned-fleet heat). Every results paragraph and every number of the discussion cites a row.
Methods numbers are specification parameters cited to METHODS_SPEC, E1_spec or D-ids.

## Placeholders

[AUTHOR] marks: Methods 8, Results 12, Discussion 7. [CIT-NEEDED] marks: Methods 15, Results 2, Discussion 5, plus the
Introduction slots above (counts of the drafts at the time of writing; the author's list is in the Phase W report).
