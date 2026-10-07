"""
Table 3 extraction (article): hydro (Itaipu b) + thermal_water_dependent,
fleet operating + planned_all, 3 scenarios, canonical pool/null/cutset
(catchment|cell, block12, p50_p90_p99), full 4x4 heat x drought cross-tab.

Read-only over w4h_coexposure.csv (D97/C59, canonical==True rows only).
No recomputation of hazard or null values. Reports the known median-is-not-
additive gap (gw_total vs sum of 16 cell gw_median) explicitly per combo,
per D80/D96/D97/D99/D106 precedent -- not hidden, not treated as an error.

Scope decided by the author in chat (Group E, Table 3): Option A
(hydro+thermal x operating+planned_all x 3 scenarios x itaipu=b for hydro)
with planned_all included for robustness.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from craei.config import load_paths  # noqa: E402

paths = load_paths()
tables_dir = Path(paths["outputs_tables_dir"])

src_path = tables_dir / "w4h_coexposure.csv"
out_path = tables_dir / "table3_coexposure.csv"

df = pd.read_csv(src_path)

# --- Check A: canonical subset is well-formed before any filtering ---
canon = df[df["canonical"] == True].copy()
assert len(canon) == 576, f"expected 576 canonical rows, got {len(canon)}"
n_combos = canon.groupby(["group", "fleet", "itaipu", "scenario"]).ngroups
assert n_combos == 36, f"expected 36 combos, got {n_combos}"
assert len(canon) == n_combos * 16, "canonical rows must be combos x 16 cells"

# --- Filter to the article's Table 3 scope (Option A + planned_all) ---
mask = (
    canon["group"].isin(["hydro", "thermal_water_dependent"])
    & canon["fleet"].isin(["operating", "planned_all"])
    & canon["itaipu"].isin(["b", "na"])
    & canon["scenario"].isin(["ssp126", "ssp370", "ssp585"])
)
table3 = canon[mask].copy()

n_combos_t3 = table3.groupby(["group", "fleet", "scenario"]).ngroups
assert n_combos_t3 == 12, f"expected 12 combos, got {n_combos_t3}"
assert len(table3) == 192, f"expected 192 rows, got {len(table3)}"

# --- Check B: regression against D102 headline (hydro operating itaipu b) ---
hyd_op_b = table3[
    (table3["group"] == "hydro") & (table3["fleet"] == "operating")
]["gw_total"].unique()
assert len(hyd_op_b) == 1, "gw_total must be constant within hydro/operating"
assert abs(hyd_op_b[0] - 102.667) < 0.001, (
    f"hydro operating itaipu b gw_total {hyd_op_b[0]} != 102.667 (D102 regression)"
)

# --- Check C: subset reproduces source rows exactly, no silent drift ---
# Full key including pool/null/cutset/canonical, since the source table
# carries multiple pool/null/cutset variants per group/fleet/itaipu/
# scenario/heat_class/drought_class combination (an incomplete key here
# would duplicate-match across variants and give a false failure).
merge_cols = [
    "group", "fleet", "itaipu", "scenario", "heat_class", "drought_class",
    "pool", "null", "cutset", "canonical",
]
check = table3.merge(
    df, on=merge_cols, how="left", suffixes=("", "_src"), validate="one_to_one"
)
assert len(check) == len(table3), "check C merge changed row count, key not unique"
num_cols = ["gw_total", "gw_min", "gw_median", "gw_max", "pct_min", "pct_median", "pct_max"]
max_diff = 0.0
for c in num_cols:
    d = (check[c] - check[f"{c}_src"]).abs().max()
    max_diff = max(max_diff, d)
assert max_diff < 1e-9, f"check C failed, max diff {max_diff:.2e}"

# --- Compute the known median-is-not-additive gap, per combo, documented ---
gap_rows = []
for (g, f, s), grp in table3.groupby(["group", "fleet", "scenario"]):
    sum_median = grp["gw_median"].sum()
    gw_total = grp["gw_total"].iloc[0]
    gap_rows.append(
        {
            "group": g,
            "fleet": f,
            "scenario": s,
            "gw_total": gw_total,
            "sum_gw_median_16cells": sum_median,
            "gap_gw": gw_total - sum_median,
        }
    )
gap_df = pd.DataFrame(gap_rows)
table3 = table3.merge(gap_df[["group", "fleet", "scenario", "gap_gw"]],
                       on=["group", "fleet", "scenario"], how="left")

print("Checks A/B/C: PASS")
print(f"rows: {len(table3)}, combos: {n_combos_t3}")
print("gap_gw summary (median not additive, documented not hidden):")
print(gap_df.to_string(index=False))

table3.to_csv(out_path, index=False)
print(f"wrote {out_path} ({len(table3)} rows)")