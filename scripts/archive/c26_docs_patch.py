"""C26 docs patch: O22, D79, D56 status, D76 fix, L31, work plan addendum."""
import pathlib
import re
import sys

DOCS = pathlib.Path("docs")


def rd(p):
    raw = pathlib.Path(p).read_bytes()
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), ("\r\n" if b"\r\n" in raw else "\n")


def wr(p, t, eol):
    pathlib.Path(p).write_bytes(t.replace("\n", eol).encode("utf-8"))


def sub1(t, old, new, label):
    if t.count(old) != 1:
        sys.exit(f"ABORT: anchor not unique/found for {label} (count={t.count(old)})")
    return t.replace(old, new)


d, e = rd(DOCS / "DECISIONS.md")
if "| D79 |" in d:
    sys.exit("ABORT: patch already applied (D79 exists)")

d = sub1(d, "| D56 | TO CONFIRM | not classified by rule; review |",
         "| D56 | OUT-OF-SCOPE-v2 | Portugal sample-size note on D55; D55 method itself stays ACTIVE-method |",
         "D56 index")
d = sub1(d,
         "Basis: c23d_report.md title and sections 2-3; the written rationale for the correction "
         "must be quoted from c23d section 1 in command C30.",
         "Basis: numbers from c23d_report.md sections 2-3. NOTE (C26 correction): c23d_report.md "
         "section 1 does not justify the replacement of the c23c AR(1) null; it diagnoses an F_D "
         "scale bug (percent vs fraction), already fixed. The reason for preferring the block "
         "bootstrap over AR(1) was not found in the repo; to be recovered or restated by the "
         "author in command C30 before the article text quotes it.",
         "D76 text")

d = d.rstrip("\n") + """

## Decisions and open items added by C26 (2026-09-30)

| ID | Decision | Status | Tier/Source | Date |
|---|---|---|---|---|
| D79 | Complement to D78: a second aggregation error in inventory/plants.py (lines 141-145). Six Brazilian thermal plants (22 units, 7.63 GW) mix GEM Types (e.g. Porto do Pecem: coal 1.09 + oil/gas 2.02 GW; Jorge Lacerda: coal 0.86 + oil/gas 0.45; Lins: bioenergy 0.016 + oil/gas 2.05; Itaqui, Guarani, Laranjeiras). tech_class is the mode over units and capacity_mw is the sum over all units, so each plant's whole capacity goes to one tech_class. Hazards (H1/H2) are unaffected (same location). Fuel and technology capacity tables must come from plant_units.parquet (per unit). plants.parquet stays unchanged (regression gate). | closed | author delegated to assistant, C26 | 2026-09-30 |
| O22 | Binational hydro: GEM gives Itaipu 7,000 MW Brazil + 7,000 MW Paraguay; plants.parquet counts 14,000 MW as Brazilian (hydro operating 109.67 GW includes 7 GW Paraguayan). Panambi (576 MW, 288 per country) is filed under Argentina so its 288 MW Brazilian share is absent (small). Options: (a) asset level, whole plant (it serves the Brazilian grid; keeps GW as is); (b) Brazilian share only (Itaipu 7,000 MW; hydro operating 102.67 GW); (c) report both. Leave-one-out shows Itaipu is the most sensitive plant (delta +9 to +12 pp in SSP126/370, -5.5 pp in SSP585). Not chosen. | open | author | 2026-09-30 |
"""
wr(DOCS / "DECISIONS.md", d + "\n", e)

lm, el = rd(DOCS / "LIMITATIONS.md")
lm = lm.rstrip("\n") + """
| L31 | PROPOSED. Plants.parquet assigns one tech_class and one fleet per plant (mode over units) and sums all unit capacities, so plant-level capacity by fleet/technology is wrong for 5 to 6 mixed plants (D78/D79). Article capacity tables use plant_units. | D78, D79 | plant_units.parquet (C28) |
"""
wr(DOCS / "LIMITATIONS.md", lm + "\n", el)

pl, ep = rd(DOCS / "CRAEI_work_plan_v2.md")
pl = pl.rstrip("\n") + """

## D. Revision after C26 (2026-09-30): W3-W5 are promotions of existing prototypes

Prototype outputs live in data/outputs/audit/c23/c23d/ (script scripts/c23d_checks.py). They are provisional: fuel_group there is the per-plant mode over plants.parquet (gas and oil merged), so it inherits D78/D79 errors (e.g. bioenergy operating 20.57 GW vs 17.43 GW per unit; coal 5.14 vs 3.00).

| Prototype (c23d item) | Provisional finding | Promoted by | Change vs prototype |
|---|---|---|---|
| 2-3 null and excess over null | null R_D>=2: 18.88% (block bootstrap), 1.80% (white noise) | C30 | rationale for null to be restated (D76) |
| 4 SPI-12 vs SPEI-12 | hydro_reservoir SPEI 53.0/49.8/76.5%, SPI 41.4/22.1/50.8% (SSP126/370/585) | C35 | resolve fit-scheme confound (O18) |
| 5 sign agreement | hydro 1-3 of 5 GCMs; thermal water-dependent 4-5 of 5 | C36 | add O21 uncertainty |
| 6 fuel x fleet TX35 | planned >= operating (bioenergy 41 to 62% SSP126) | C31 | use plant_units, split gas/oil (D77), verify definition of tx35_gw_pct |
| 7 leave-one-out | removing Itaipu: 53.0 to 62.1 / 49.8 to 61.6 / 76.5 to 71.0% | C37 | prototype removed the largest per bucket (3 reservoir + 2 run-of-river), not the 5 largest overall (O19); Itaipu treatment per O22 |

Open items now tracked: O16-O22. Commands C27 (fuel x tech x fleet per unit) and C28 (plant_units) come first; C29-C37 start only after C28 passes pytest and the regression gate.
"""
wr(DOCS / "CRAEI_work_plan_v2.md", pl + "\n", ep)

dd = (DOCS / "DECISIONS.md").read_text(encoding="utf-8-sig")
for k in ("D79", "O22"):
    assert f"| {k} |" in dd
assert "\u00c2\u00a7" not in dd
print("patch applied: D56 index, D76 fixed, D79, O22, L31, work plan section D")