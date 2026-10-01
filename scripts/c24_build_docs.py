"""C24 build A: non-destructive v2 docs (DECISIONS, LIMITATIONS, METHODS_SPEC)."""
import pathlib
import re
import sys

DOCS = pathlib.Path("docs")
ARCH = DOCS / "archive"


def load(p):
    raw = p.read_bytes()
    eol = "\r\n" if b"\r\n" in raw else "\n"
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), eol


def save(p, text, eol):
    p.write_bytes(text.replace("\n", eol).encode("utf-8"))


# ---------------------------------------------------------------- status map
A, AM, SUP, OUT, SUPS, HIST = ("ACTIVE", "ACTIVE-method", "SUPPLEMENTARY",
                               "OUT-OF-SCOPE-v2", "SUPERSEDED", "HISTORICAL")
S = {}


def mark(ids, st, note=""):
    for i in ids.split():
        S[i] = (st, note)


mark("D01 D02 D04 D05 D11 D12 D13 D15 D17", A)
mark("D03", A, "article uses H1 and H2 only; H3/H4/solar in appendix (D74)")
mark("D07 D08", A, "class thresholds kept for Table 1; v2 adds threshold curves and the null (D76)")
mark("D16", A, "see D78: unit-level fleet capacity fixes mixed-status plants")
mark("D06", OUT, "coastal bound only matters for H3 freshwater")
mark("D09 D58 D63 D64 D65 D66 D67 O12 O13", OUT, "compound metric outside article (D72)")
mark("D10", SUP, "ONS/REN validation: national ONS supplementary (D73), REN out")
mark("D18 D59 D60 D61 O10 O11", OUT, "Portugal REN/DGEG validation")
mark("D62 D68 D69", OUT, "ONS subsystem / regional assignment")
mark("D70 O14", SUP, "national ONS validation kept as supplementary (D73)")
mark("O15", OUT, "EM-DAT descriptive")
mark("O01 D14 D27 D45 D51 D52", SUPS, "see superseding decision in the row text")
mark("D19 D20 D21 D22 D23 D24 D25 D26 D27' D28 D29 D30 O02 D41 D43 D44 D46 D47 D57", A,
     "pipeline record")
mark("O06 O07", HIST, "closed by D42 / D43")
mark("D31 D32 D33 D34 D35 D36 D37 D38 D39", OUT, "Aqueduct (H3) outside article (D74)")
mark("D40", A, "pipeline fact; Portugal outside article")
mark("D42", OUT, "H4 wet-day threshold; H4 outside article")
mark("D48", OUT, "solar PV metric not implemented")
mark("D49 D50 D53 O08 O09", HIST, "diagnostic chain leading to D54/D55")
mark("D54 D55", AM, "adopted SPEI fitting method")
# limitations
mark("L01", A, "applies to water-dependent/air-only class and the thermal drought bucket")
mark("L03 L04 L05 L07 L10 L12 L19", A)
mark("L08", SUP, "supports the supplementary ONS validation")
mark("L02 L06 L09 L11 L13 L14 L15 L16 L18 L20 L21 L22", OUT, "India/Portugal/H3/H4/compound/subsystem")
mark("L17", SUPS, "withdrawn 2026-09-30")


def ids_in(text):
    seen, out = set(), []
    for m in re.finditer(r"^\| (D\d+'?|O\d+|L\d+) \|", text, re.M):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append(m.group(1))
    return out


def maxn(ids, p):
    return max(int(re.sub(r"\D", "", i)) for i in ids if i[0] == p)


def index_block(title, ids):
    rows = []
    for i in ids:
        st, note = S.get(i, ("TO CONFIRM", "not classified by rule; review"))
        rows.append(f"| {i} | {st} | {note} |")
    return (f"## {title}\n\nAdded by C24 (2026-09-30). Statuses: ACTIVE, ACTIVE-method, "
            "SUPPLEMENTARY, OUT-OF-SCOPE-v2 (kept as record), SUPERSEDED, HISTORICAL, "
            "TO CONFIRM. No existing row below was edited.\n\n"
            "| ID | Scope v2 status | Note |\n|---|---|---|\n" + "\n".join(rows) + "\n")


def insert_before_table(text, block):
    m = re.search(r"^\| ID ", text, re.M)
    if not m:
        sys.exit("ABORT: table header row not found")
    return text[:m.start()] + block + "\n\n" + text[m.start():]


# ------------------------------------------------------------- new content
D_NEW = """

## Decisions and open items added by C24 (Scope v2, 2026-09-30)

| ID | Decision | Status | Tier/Source | Date |
|---|---|---|---|---|
| D71 | Scope v2: one article, Brazil only, two axes. Axis 1 (main): heat exposure of the Brazilian thermal fleet broken down by fuel, operating vs planned. Axis 2 (secondary): hydro drought exposure reported against an internal-variability null, with GCM spread, SPI/SPEI comparison and leave-one-out. Out: India, Portugal, flooding, solar, wind, composite score. IND/PRT code and outputs stay in the pipeline for a second article or data descriptor (no code deleted; Brazil filter applied at table level). | closed | author, C24 | 2026-09-30 |
| D72 | Compound hydro-drought/thermal-heat metric removed from the article. Artifacts (compound.csv, compound_months.parquet) stay in tables/ until C25; 11_compound.py stays archived; readers (c23_scope_audit.py, 22_audit.py, src/craei/audit) are removed in C25. | closed | author, C24 | 2026-09-30 |
| D73 | ONS national validation (D70: rho=0.361, CI 0.027-0.811, n=20) kept as supplementary material and as a stated limitation, not a main figure. Moves to the main text only if a reviewer requests it. Subsystem validation stays suspended (D62/L20). | closed | author delegated to assistant, C24 | 2026-09-30 |
| D74 | H3 (Aqueduct) and H4 (extreme precipitation) and solar rows are outside the article; kept as pipeline artifacts for article 2. Reason: Aqueduct is not consistent with the ISIMIP3b ensemble (L06/L13) and none of the three serves the two axes. | closed | author delegated to assistant, C24 | 2026-09-30 |
| D75 | Target journals: Climate Risk Management, Renewable Energy, Applied Energy; Earth's Future if the planning component is strong. | closed | author, C24 | 2026-09-30 |
| D76 | Internal-variability null: the canonical null is the block bootstrap of c23d (pool of real (id, model) baseline SPEI-12 series, 360-month windows, N_SIM=2000, seed 23): R_D>=2 occurs by chance in 18.88% of series at SPEI<=-1.5. The white-noise reference (1.80%) is reported only as a lower reference (SPEI-12 is serially correlated by construction). The c23c AR(1) null (26.12%) is superseded. Basis: c23d_report.md title and sections 2-3; the written rationale for the correction must be quoted from c23d section 1 in command C30. Excess over null is descriptive (observed minus null rate), not a significance test. | closed | author delegated to assistant, C24 | 2026-09-30 |
| D77 | Fuel classes come from GEM unit-level fields, never from plants.parquet. Rule: Type first (coal, nuclear, bioenergy); for oil/gas use Fuel classification (oil/gas only): gas (Gas plus LNG only), oil, multi_fuel. Bioenergy subtype from Fuel (combustion only): agricultural_waste (solids only; proxy for bagasse, GEM does not name bagasse), paper_mill_waste, wood_biomass (wood and other biomass), other_bioenergy (everything else, incl. agricultural biogas, landfill gas, wastes, biodiesel, unknown). No GW splitting across fuels. Reference totals, Brazil operating, unit level: gas 19.32, bioenergy 17.43 (agricultural 12.08, paper mill 3.81, wood about 1.06, other about 0.48), oil 4.60, multi_fuel 1.33, coal 3.00, nuclear 1.99 = 47.67 GW. Command C27/C28 must reproduce these. | closed | author delegated to assistant, C24 | 2026-09-30 |
| D78 | Fleet attribution fix without touching plants.parquet. inventory/plants.py (line about 141) assigns each plant one fleet = mode of its units' status counted by units. This mis-assigns 5 Brazilian thermal plants (22 units: 3.56 GW operating-status, 6.46 GW announced-status), giving operating +3.55 GW and planned_early -3.55 GW vs GEM unit-level totals (47.67/17.31/31.04 GW). Fix: auxiliary unit-level table plant_units.parquet (plant_uid, fleet, fuel_class, bio_subtype, capacity_mw); hazards stay joined on plant_uid (same location). plants.parquet and the regression-gate baseline stay unchanged. Article capacity-by-fleet numbers use plant_units. Old exposure_summary.csv carries the mode-based error and is not used in the article. | closed | author delegated to assistant, C24 | 2026-09-30 |
| O16 | Heat metric for bioenergy: annual TX35 vs harvest-season TX35 (monthly n35 exists in indices_daily.parquet, no climate reprocessing). Options: (a) annual only; (b) annual plus season window by region (commonly cited: roughly April-November Center-South, September-March North-Northeast; source to be cited, not verified here); (c) all-months monthly profile per fuel. Not chosen. | open | author | 2026-09-30 |
| O17 | Operating-vs-planned comparison metric and threshold-curve grid. Options: (a) difference in GW share above threshold (planned minus operating) with GCM range; (b) ratio; (c) GW-weighted median dTX35 per fleet; (d) bootstrap over plants. Curve grid for GW fraction vs dTX35: e.g. 0-60 days/yr in steps of 5. Not chosen. | open | author | 2026-09-30 |
| O18 | SPI vs SPEI divergence metric. Confound to resolve first: SPI-12 is fitted per calendar month (n=30, gamma) while SPEI-12 is fitted once per series (n=360); c23d applies the SPEI bootstrap null (18.88%) to SPI. Options: (a) refit SPI with the SPEI scheme and its own null; (b) keep SPI as is and state the confound; (c) drop SPI. Not chosen. | open | author | 2026-09-30 |
| O19 | Leave-one-out definition (Table 2): c23d item 7 already removes each of the 5 largest Brazilian hydro plants by GW. Confirm after reading c23d_7_leave_one_out.csv: metric reported (GW share R_D>=2, excess over null), and treatment of binational plants (see L30). Not chosen. | open | author | 2026-09-30 |
| O20 | Whether the thermal_water_dependent drought bucket stays in Fig 5. Default: yes (already computed, links the axes). Option: restrict Axis 2 to hydro buckets only. | open | author | 2026-09-30 |
| O21 | Uncertainty reporting for excess over null: plants in the same basin/cell and the 5 GCMs are not independent. Options: (a) GCM min-max range only (c23d); (b) add model-agreement (at least 4/5 same sign); (c) cluster bootstrap by basin. Not chosen. | open | author | 2026-09-30 |
"""

L_NEW = """

## Limitations proposed by C24 (Scope v2, 2026-09-30) - PROPOSED, need author confirmation

| ID | Limitation | Declared in | Mitigation |
|---|---|---|---|
| L23 | PROPOSED. Exposure is not vulnerability, and differences between fuels reflect where plants are sited, not the technology. | SCOPE.md | Claim language: exposure by location; never impact or loss (L03) |
| L24 | PROPOSED. GEM does not name bagasse: agricultural_waste is a proxy. Bioenergy plants operate mostly in the harvest season, so annual TX35 may not represent the operating window; feedstock supply risk is not assessed. | D77, O16 | Declared proxy; seasonal variant if O16 chooses it |
| L25 | PROPOSED. GEM fuel fields are multi-valued strings with unknown categories (e.g. bioenergy unknown 0.19 GW; technology unknown 3.21 GW operating). | D77 | Classification rule documented; unknowns kept as their own class |
| L26 | PROPOSED. One realization per GCM: internal variability is not sampled. The null is synthetic (bootstrap from the model's own baseline series); excess over null is descriptive, not a significance test. | D76 | Null reported with the white-noise lower reference |
| L27 | PROPOSED. Effective sample size: 5 GCMs share components and plants in the same basin or cell share climate, so GW shares and plant counts overstate independent information. | O21 | GCM range, agreement and (if chosen) cluster bootstrap |
| L28 | PROPOSED. Hargreaves-Samani PET is temperature-based and omits humidity, wind and radiation changes; PET sensitivity is probed only through SPI (precipitation only). | METHODS_SPEC 1.4 H2 | SPI/SPEI comparison (O18) |
| L29 | PROPOSED. Validation is weak and national: Brazil rho=0.361, CI 0.027-0.811, n=20 (D70), W5E5 rather than the GCMs; no subsystem validation (L20). | D73 | Supplementary only; stated limit of SPEI as proxy |
| L30 | PROPOSED, TO VERIFY. Binational hydro (Itaipu, 14,000 MW, L22) may be counted in full as Brazilian; GEM has per-country capacity columns for hydropower. | C26 | Verify; use the Brazilian share if confirmed |
"""

# --------------------------------------------------------------- DECISIONS
for name in ("DECISIONS", "LIMITATIONS"):
    cur, eol = load(DOCS / f"{name}.md")
    old, _ = load(ARCH / f"{name}_v1_pre_rework.md")
    if cur != old:
        sys.exit(f"ABORT: docs/{name}.md differs from its archived v1 copy")
    ids = ids_in(old)
    if name == "DECISIONS":
        got = (maxn(ids, "D"), maxn(ids, "O"))
        if got != (70, 15):
            sys.exit(f"ABORT: expected max D70/O15, found {got}; renumber D71+/O16+")
        idx = index_block("Scope v2 status index", ids)
        app = D_NEW
    else:
        if maxn(ids, "L") != 22:
            sys.exit(f"ABORT: expected max L22, found {maxn(ids, 'L')}")
        idx = index_block("Scope v2 status index (limitations)", ids)
        app = L_NEW
    new = insert_before_table(old, idx) + app
    restored = new.replace(idx + "\n\n", "", 1)
    assert restored.endswith(app)
    assert restored[:-len(app)] == old, "non-destructive check failed"
    save(DOCS / f"{name}.md", new, eol)
    tc = [i for i in ids if i not in S]
    print(f"{name}.md: {len(ids)} ids indexed; TO CONFIRM: {tc}")

# ------------------------------------------------------------ METHODS_SPEC
M, eolM = load(ARCH / "METHODS_SPEC_v1_pre_rework.md")


def block(start, end):
    ms = list(re.finditer(start, M, re.M))
    if len(ms) != 1:
        sys.exit(f"ABORT: start pattern {start!r} matched {len(ms)} times")
    me = re.compile(end, re.M).search(M, ms[0].end())
    if not me:
        sys.exit(f"ABORT: end pattern {end!r} not found")
    return M[ms[0].start():me.start()].rstrip("\n") + "\n"


def step(n):
    if n == 6:
        return block(r"^\*\*Step 6\.", r"^\*\*Step 6 note")
    if n == 12:
        return block(r"^\*\*Step 12\.", r"^Total compute")
    return block(rf"^\*\*Step {n}\.", rf"^\*\*Step {n + 1}\.")


HEADER = """# Design v2: Heat and drought exposure of the Brazilian power fleet

Scope v2 (D71): Brazil only; Axis 1 heat exposure of the thermal fleet by fuel (operating vs planned); Axis 2 hydro drought against an internal-variability null. Replaces the three-country design archived at docs/archive/METHODS_SPEC_v1_pre_rework.md. Blocks marked "verbatim" are copied unchanged from v1. Anything not yet defined is written as TO BE DEFINED with its open item.

---

## 1. Methods

### 1.1 Study domain and scope (v2)

Brazil only (D71). The pipeline still produces India and Portugal results; they are not analysed here and the Brazil filter is applied at table level, not by deleting code. See Appendix A for components outside the article.

"""

NEW_FLEET = """
### 1.6 Fleet and fuel classification (v2; D77, D78)

Capacity by fleet and fuel is computed from GEM unit-level rows (table plant_units.parquet, command C28), not from plants.parquet, because plants.parquet assigns one fleet per plant by the mode of unit status (D78). Hazards are joined on plant_uid (location is shared by all units of a plant).

Fuel classes (D77): Type first (coal, nuclear, bioenergy); oil/gas split by GEM Fuel classification into gas (Gas, LNG only), oil, multi_fuel; bioenergy subtypes agricultural_waste (bagasse proxy), paper_mill_waste, wood_biomass, other_bioenergy. Brazil operating reference totals (GW): gas 19.32, bioenergy 17.43, oil 4.60, coal 3.00, nuclear 1.99, multi_fuel 1.33; total 47.67.

### 1.7 Heat axis (v2)

H1 and the exposure formula of 1.5 apply, with a fuel dimension added: E over (fuel, fleet, scenario, model). Outputs: share and GW above the headline class (dTX35 >= 30 days/yr), ensemble median, model range, agreement (at least 4 of 5 GCMs).

- Threshold curves (GW fraction vs dTX35): TO BE DEFINED, see O17 (curve grid).
- Operating vs planned comparison: TO BE DEFINED, see O17 (metric and uncertainty).
- Harvest-season variant for bioenergy: TO BE DEFINED, see O16.

### 1.8 Drought axis (v2)

H2 and the fitting method of 1.4 apply unchanged (D54/D55).

- Internal-variability null (D76): block bootstrap, pool of 1,110 (id, model) series of 360 baseline months, N_SIM=2000, seed 23; preliminary reference values from c23d_report.md: 18.88% of series reach R_D>=2 at SPEI<=-1.5 (1,991 of 2,000 with R_D defined); white-noise lower reference 1.80%. Excess over null = observed capacity share minus the null rate, by bucket, scenario, GCM; descriptive, not a significance test (L26). Production script to be written (C30), acceptance = reproduce these numbers.
- SPI vs SPEI comparison: TO BE DEFINED, see O18.
- Uncertainty of the excess (GCM range, agreement, clustering): TO BE DEFINED, see O21.
- Leave-one-out of the 5 largest hydro plants: TO BE DEFINED, see O19.
- Thermal water-dependent bucket in Fig 5: TO BE DEFINED, see O20.

### 1.9 Validation (v2)

National ONS validation (D70, rho=0.361, CI 0.027-0.811, n=20) is supplementary (D73). Details in Appendix A (v1 section 1.7).

"""

RESULTS_MAP = """
## 4. Results map (figure/table -> source -> producing script -> blocking item)

| Item | Source table | Producing script | Blocking |
|---|---|---|---|
| Fig 1 fleet and capacity by technology and fuel | plant_units.parquet | to be written (C29) | D77, D78 (C28) |
| Fig 2 TX35 exposure maps per thermal plant by fuel | plant_hazards.parquet (h1) + plants coords + plant_units | to be written (C31, C41) | C28 |
| Fig 3 heat-threshold curves, operating vs planned | plant_hazards + plant_units | to be written (C32, C34) | O17 |
| Fig 4 drought maps SPEI and SPI per hydro plant | plant_hazards (SPEI); SPI only in spei.parquet | to be written (C35) | O18 |
| Fig 5 excess over null by bucket and scenario, GCM range | null table + plant_hazards | to be written (C30, C36) | O20, O21 |
| Table 1 GW fraction exposed by technology, fuel, scenario | plant_units + plant_hazards | to be written (C38) | O16, O17 |
| Table 2 leave-one-out, 5 largest hydro | c23d_7_leave_one_out.csv (audit) | to be promoted (C37) | O19, L30 |
| Supplementary ONS validation | validation.csv | exists (scripts/25_validation_stats.py) | none |

---

"""

APPX_HEAD = """
---

## Appendix A. Pipeline components outside v2 article scope (verbatim from v1; v1 numbering)

"""

NOTE_S6 = ("\n> Editorial note (C24): the next block documents the COMANDO 17-F per-calendar-month "
           "hybrid fit, superseded in production by D54/D55 (see 1.4 H2 and Step 6 above). Kept "
           "verbatim as the method-comparison record.\n\n")
NOTE_S10 = ("\n> SUPERSEDED (D63/D72): the LR_C metric below was replaced by diff_pp and "
            "dependence_ratio, and the whole compound metric is outside v2 scope. 11_compound.py "
            "is archived.\n\n")
NOTE_17 = ("\n> Editorial note (C24): ONS national validation is supplementary (D73); subsystem "
           "validation and Portugal REN/DGEG are outside v2.\n\n")

parts = [
    HEADER,
    block(r"^### 1\.2 Infrastructure data", r"^### 1\.3"), "\n",
    block(r"^### 1\.3 ", r"^### 1\.4"), "\n",
    block(r"^### 1\.4 Hazard definitions", r"^\*\*H3\."), "\n",
    block(r"^### 1\.5 ", r"^### 1\.6"), NEW_FLEET,
    "---\n\n## 3. Technical pipeline (inherited; verbatim)\n\n",
    block(r"^Execution machine, measured", r"^\*\*Step 1\."), "\n",
]
for n in range(1, 10):
    parts += [step(n), "\n"]
    if n == 6:
        parts += [NOTE_S6, block(r"^\*\*Step 6 note", r"^\*\*Step 7\."), "\n"]
parts += [block(r"^Total compute", r"^---$"), "\n", RESULTS_MAP, APPX_HEAD, NOTE_17,
          block(r"^### 1\.6 ", r"^### 1\.7"), "\n",
          block(r"^### 1\.7 ", r"^### 1\.8"), "\n",
          block(r"^### 1\.8 ", r"^---$"), "\n",
          block(r"^\*\*H3\.", r"^### 1\.5"), "\n",
          NOTE_S10, step(10), "\n", step(11), "\n", step(12), "\n",
          block(r"^## 5\. Additional downloads", r"^## 6\."), "\n",
          "---\n\n", block(r"^## Key references to verify and cite", r"\Z")]
out = "".join(parts)
save(DOCS / "METHODS_SPEC.md", out, eolM)
tbd = [l for l in out.splitlines() if "TO BE DEFINED" in l]
bad = [l for l in tbd if not re.search(r"O\d+", l)]
print(f"METHODS_SPEC.md written: {len(out.splitlines())} lines; TO BE DEFINED lines: {len(tbd)}; "
      f"without O-id: {len(bad)}")