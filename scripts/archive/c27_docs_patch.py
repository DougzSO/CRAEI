"""C27 docs patch: O23 (null sensitivity), verified prototype definitions."""
import pathlib
import sys

DOCS = pathlib.Path("docs")


def rd(p):
    raw = pathlib.Path(p).read_bytes()
    return raw.decode("utf-8-sig").replace("\r\n", "\n"), ("\r\n" if b"\r\n" in raw else "\n")


def wr(p, t, eol):
    pathlib.Path(p).write_bytes(t.replace("\n", eol).encode("utf-8"))


d, e = rd(DOCS / "DECISIONS.md")
if "| O23 |" in d:
    sys.exit("ABORT: already applied (O23 exists)")
d = d.rstrip("\n") + """

## Open items added by C27 prep (2026-09-30)

| ID | Decision | Status | Tier/Source | Date |
|---|---|---|---|---|
| O23 | Null of R_D>=2 and its documentation. Reference rate of R_D>=2 by chance: 26.12% (c23c, AR(1), phi=0.9291, 200-series sample), 18.88% (c23d, block bootstrap, BLOCK=12 months, pool of 1,110 series), 1.80% (c23d, standardized 12-month moving sum of white noise): a 14-fold range. D76 adopts the bootstrap but no written rationale for replacing AR(1) exists in the repo (c23d report section 1 is about an F_D scale bug). Hypothesis to test, not a finding: 12-month blocks break persistence beyond 12 months; if real SPEI-12 has longer memory, the bootstrap null rate is understated and the excess over null (hydro, +31 to +60 pp median) is overstated. Options: (a) keep the bootstrap and state its rationale; (b) bootstrap as reference, other two nulls reported as a sensitivity range; (c) add block-length sensitivity (12, 24, 36, 60 months) and report the range; (b) and (c) can be combined. Not chosen. Blocks the wording of Axis 2 results. | open | author | 2026-09-30 |
"""
wr(DOCS / "DECISIONS.md", d + "\n", e)

pl, ep = rd(DOCS / "CRAEI_work_plan_v2.md")
pl = pl.rstrip("\n") + """

## E. Prototype definitions verified in C27 prep (2026-09-30)

- c23d tx35_gw_pct (c23d_checks.py lines 412-430): exposed = delta TX35 >= 30 days/yr per plant and model; GW share = exposed capacity / group capacity (fuel x fleet), plants without a hazard row count as not exposed and stay in the denominator; reported value = median over the 5 GCMs. Matches D07.
- c23d fuel_group: per-plant mode over units on plants.parquet, gas and oil merged; fleet and capacity inherited from plants.parquet (D78/D79 errors). Provisional only.
- Concentration: with few large plants per group (e.g. 84 gas/oil operating plants) GW shares are discrete and dominated by a handful of plants (gas_oil operating identical in SSP126 and SSP370; coal operating 0.24% of GW vs 10% of plants in SSP126). C31 and Table 1 must report plant-count share and top-plant concentration beside GW share.
- C30 must include the null-sensitivity decision (O23) before Axis 2 numbers are quoted.
"""
wr(DOCS / "CRAEI_work_plan_v2.md", pl + "\n", ep)
print("patch applied: O23, work plan section E")