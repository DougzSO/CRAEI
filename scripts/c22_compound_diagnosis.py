"""Methodological diagnosis of the compound LR_C metric (author-run, CLAUDE.md Rule 12).

Not a production script. Answers, report-only, no decisions:
1. Does the observed compound frequency match the product of the two marginal
   above-P90 fractions (independence check)?
2. Full table of marginal above-P90 fractions vs observed compound frequency,
   every country x scenario x model.
3/4/5. Two alternative compound-month definitions (absolute threshold, and
   absolute frequency without a ratio), same discrimination diagnostic.
6. Effect of each alternative on Figure 3 (Methods Spec Sec 4).
"""

from pathlib import Path

import pandas as pd

OUT = Path("../data/outputs")
m = pd.read_parquet(OUT / "compound_months.parquet")

future = m[m["period"] == "future"].copy()
baseline = m[m["period"] == "baseline"].copy()

# ---- Part 1 & 2: marginal above-P90 fractions vs observed compound frequency ----
future["s_above"] = future["s_hydro"] > future["s_hydro_p90"]
future["h_above"] = future["h_thermal"] > future["h_thermal_p90"]

grp = future.groupby(["country", "scenario", "model"], as_index=False).agg(
    n_future_months=("compound", "size"),
    f_s_above=("s_above", "mean"),
    f_h_above=("h_above", "mean"),
    f_compound_observed=("compound", "mean"),
)
grp["f_compound_independence"] = grp["f_s_above"] * grp["f_h_above"]
grp["ratio_obs_to_indep"] = grp["f_compound_observed"] / grp["f_compound_independence"]
grp["discriminates"] = (grp["f_s_above"] < 0.5) & (grp["f_h_above"] < 0.5)

print("=" * 100)
print("PART 1/2: marginal above-P90 fractions vs observed compound frequency (percentile method)")
print("=" * 100)
print(
    grp.sort_values(["country", "model", "scenario"]).to_string(
        index=False, float_format=lambda x: f"{x:0.4f}"
    )
)
grp.to_csv(OUT / "c22_compound_diagnosis_percentile.csv", index=False)

n_majority = ((grp["f_s_above"] > 0.5) | (grp["f_h_above"] > 0.5)).sum()
print(f"\nCases where at least one marginal series exceeds P90 in >50% of future months: "
      f"{n_majority} / {len(grp)}")

# ---- Part 3: Alternative A, absolute threshold ----
# No existing params.yaml key defines an absolute S_hydro fraction or an
# absolute H_thermal day-count for the compound definition specifically
# (CLAUDE.md Rule 9 -- diagnostic only, not adopted as production values).
# Test grid chosen to bracket the percentile-implied baseline thresholds
# actually observed in compound_months.parquet (s_hydro_p90 ~0.10-0.30,
# h_thermal_p90 ~2-6 days/month across country/model).
S_HYDRO_ABS_LEVELS = [0.10, 0.20, 0.30]
H_THERMAL_ABS_LEVELS = [2.0, 5.0, 10.0]

print("\n" + "=" * 100)
print("PART 3/5: Alternative A -- fixed absolute thresholds (diagnostic grid, not in params.yaml)")
print("=" * 100)

alt_a_rows = []
for s_lvl in S_HYDRO_ABS_LEVELS:
    for h_lvl in H_THERMAL_ABS_LEVELS:
        b = baseline.copy()
        b["compound_abs"] = (b["s_hydro"] > s_lvl) & (b["h_thermal"] > h_lvl)
        fb = b.groupby(["country", "model"], as_index=False).agg(
            f_baseline_abs=("compound_abs", "mean"), n_baseline=("compound_abs", "size")
        )

        f = future.copy()
        f["compound_abs"] = (f["s_hydro"] > s_lvl) & (f["h_thermal"] > h_lvl)
        f["s_above_abs"] = f["s_hydro"] > s_lvl
        f["h_above_abs"] = f["h_thermal"] > h_lvl
        ff = f.groupby(["country", "scenario", "model"], as_index=False).agg(
            f_future_abs=("compound_abs", "mean"),
            f_s_above_abs=("s_above_abs", "mean"),
            f_h_above_abs=("h_above_abs", "mean"),
        )
        merged = ff.merge(fb, on=["country", "model"], how="left")
        merged["lr_c_abs"] = merged["f_future_abs"] / merged["f_baseline_abs"].where(
            merged["f_baseline_abs"] > 0
        )
        merged["s_hydro_level"] = s_lvl
        merged["h_thermal_level"] = h_lvl
        merged["discriminates_abs"] = (merged["f_s_above_abs"] < 0.5) & (
            merged["f_h_above_abs"] < 0.5
        )
        alt_a_rows.append(merged)

alt_a = pd.concat(alt_a_rows, ignore_index=True)
alt_a = alt_a[
    [
        "country", "scenario", "model", "s_hydro_level", "h_thermal_level",
        "f_baseline_abs", "n_baseline", "f_future_abs", "lr_c_abs",
        "f_s_above_abs", "f_h_above_abs", "discriminates_abs",
    ]
]
alt_a.to_csv(OUT / "c22_compound_diagnosis_alt_a_absolute.csv", index=False)
print(alt_a.head(30).to_string(index=False, float_format=lambda x: f"{x:0.4f}"))
print(f"... {len(alt_a)} rows total, written to c22_compound_diagnosis_alt_a_absolute.csv")
print(
    "\nDiscrimination summary (Alt A), share of rows where BOTH marginals stay <50% of months "
    "(i.e. still discriminating extremes), by threshold pair:"
)
print(
    alt_a.groupby(["s_hydro_level", "h_thermal_level"])["discriminates_abs"]
    .mean()
    .reset_index()
    .to_string(index=False)
)

# ---- Part 4: Alternative B, absolute frequency without a ratio ----
print("\n" + "=" * 100)
print("PART 4/5: Alternative B -- absolute compound frequency, percentage points, no ratio")
print("=" * 100)
alt_b = grp[["country", "scenario", "model"]].copy()
fb_pct = baseline.groupby(["country", "model"], as_index=False)["compound"].mean()
fb_pct = fb_pct.rename(columns={"compound": "f_baseline_pct"})
alt_b = alt_b.merge(
    future.groupby(["country", "scenario", "model"], as_index=False)["compound"]
    .mean()
    .rename(columns={"compound": "f_future_pct"}),
    on=["country", "scenario", "model"],
)
alt_b = alt_b.merge(fb_pct, on=["country", "model"])
alt_b["f_baseline_pct"] *= 100
alt_b["f_future_pct"] *= 100
alt_b["diff_pp"] = alt_b["f_future_pct"] - alt_b["f_baseline_pct"]
alt_b.to_csv(OUT / "c22_compound_diagnosis_alt_b_absolute_freq.csv", index=False)
print(alt_b.sort_values(["country", "model", "scenario"]).to_string(
    index=False, float_format=lambda x: f"{x:0.2f}"
))

print("\n" + "=" * 100)
print("PART 6: effect on Figure 3 (Methods Spec Sec 4)")
print("=" * 100)
print(
    """
Current (percentile LR_C): y-axis = LR_C (dimensionless risk ratio, log scale
typically). Message: 'compound months become N times more frequent.' This
message becomes unstable/misleading wherever a marginal series exceeds its
own baseline P90 in a majority of future months (see Part 1/2 output above,
notably BRA x UKESM1-0-LL across all 3 scenarios) -- LR_C there is inflated
by a shifted mean, not a co-occurrence signal, even though the two marginals
are close to independent (ratio_obs_to_indep ~1).

Alternative A (fixed absolute threshold): y-axis could still be a ratio
(f_future_abs / f_baseline_abs) but is sensitive to the arbitrary absolute
levels chosen (not sourced in params.yaml for this purpose) -- the message
shifts from 'relative to each model's own past' to 'relative to an
author-chosen fixed severity level,' which changes what the figure claims
model agreement means and requires a new Tier-3 params.yaml entry + DECISIONS.md
line before use.

Alternative B (absolute frequency, no ratio): y-axis = percentage-point
difference (f_future_pct - f_baseline_pct). Message becomes 'compound months
occupy N more percentage points of the year' -- immune to baseline-instability
and mean-shift inflation, but loses the multiplicative-risk framing the
Methods Spec's 'risk ratio' language implies; would require a wording change
in Sec 4, not just a recompute.
"""
)
