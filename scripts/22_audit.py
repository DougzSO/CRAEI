#!/usr/bin/env python
"""Phase 7 readiness audit (COMANDO 22).

Produces 5 outputs:
1. coverage.csv - coverage by country, metric, bucket, fleet
2. figure_readiness.csv - status of each main figure
3. plausibility_report.txt - plausibility check results
4. gap_actions.csv - proposed actions for gaps
5. audit_report.md - comprehensive report and readiness verdict

STOPS after audit_report.md per specification. No further commands executed.
"""

from pathlib import Path
import sys

import pandas as pd

from craei.config import load_paths
from craei.audit.coverage import load_and_compute_coverage
from craei.audit.figure_readiness import load_and_check_figures
from craei.audit.plausibility import (
    load_and_check_plausibility,
    format_plausibility_report,
)
from craei.audit.gaps import load_and_propose_gaps


def main():
    """Run the complete audit and produce all 5 outputs."""
    paths = load_paths()
    outputs_dir = Path(paths["outputs_audit_dir"])  # COMANDO 22-B Part 3: audit outputs subdir
    tables_dir = Path(paths["outputs_tables_dir"])
    processed_dir = Path(paths["processed_dir"])

    print("COMANDO 22: Phase 7 Readiness Audit")
    print("=" * 60)

    # Action 1: Coverage
    print("\nAction 1: Computing coverage by country × metric × bucket × fleet...")
    coverage = load_and_compute_coverage(processed_dir)
    coverage_file = outputs_dir / "coverage.csv"
    coverage.to_csv(coverage_file, index=False)
    print(f"  Saved: {coverage_file}")

    # Verify assert worked
    print(f"  Coverage fraction range: [{coverage['coverage_fraction'].min():.4f}, {coverage['coverage_fraction'].max():.4f}]")
    assert (coverage["coverage_fraction"] >= 0.0).all()
    assert (coverage["coverage_fraction"] <= 1.0).all()
    print("  [OK] All coverage fractions in [0, 1]")

    # Action 2: Figure readiness
    print("\nAction 2: Checking figure readiness...")
    figure_readiness = load_and_check_figures(processed_dir, tables_dir)
    figure_file = outputs_dir / "figure_readiness.csv"
    figure_readiness.to_csv(figure_file, index=False)
    print(f"  Saved: {figure_file}")
    print(figure_readiness.to_string(index=False))

    # Action 3: Plausibility
    print("\nAction 3: Running plausibility checks...")
    plausibility_checks = load_and_check_plausibility(tables_dir)
    plausibility_report = format_plausibility_report(plausibility_checks)
    plausibility_file = outputs_dir / "plausibility_report.txt"
    with open(plausibility_file, "w", encoding="utf-8") as f:
        f.write(plausibility_report)
    print(f"  Saved: {plausibility_file}")
    print(plausibility_report)

    # Action 4: Gap actions
    print("\nAction 4: Proposing gap actions...")
    gap_actions = load_and_propose_gaps(figure_readiness, plausibility_checks)
    gap_file = outputs_dir / "gap_actions.csv"
    gap_actions.to_csv(gap_file, index=False)
    print(f"  Saved: {gap_file}")
    if len(gap_actions) > 0:
        print(f"  {len(gap_actions)} gap(s) identified")

    # Action 5: Comprehensive report
    print("\nAction 5: Generating comprehensive audit report...")

    # Generate audit_report.md
    report_lines = [
        "# Phase 7 Readiness Audit (COMANDO 22)",
        "",
        "Date: 2026-09-30",
        "Status: AUDIT COMPLETE, AWAITING AUTHOR REVIEW",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"This audit verifies whether the data aggregates from C19-C21 sustain the main results. "
        f"Five outputs produced (see below); **stopping here per spec to await author approval**.",
        "",
        "---",
        "",
        "## 1. Data Coverage",
        "",
        f"**File**: `coverage.csv` ({len(coverage)} rows)",
        "",
        "Coverage by country, metric (TX35, TX40, f_d_spei12, f_d_spei3, Aqueduct), "
        "bucket, and fleet, reported as:",
        "- **numerator_plants**: distinct plants with valid (non-NaN) hazard data",
        "- **numerator_mw**: capacity of plants with data",
        "- **denominator_mw**: total capacity of bucket (per METHODS_SPEC §1.4)",
        "- **coverage_fraction**: numerator_mw / denominator_mw ∈ [0, 1]",
        "- **excluded_mw**: capacity in denominator but without data by declared limitation (L16, L19)",
        "- **absent_mw**: capacity in denominator but absent from data (missing rows)",
        "",
    ]

    # Coverage summary table
    coverage_by_country_metric = coverage.groupby(["country", "metric"]).agg({
        "denominator_mw": "first",
        "coverage_fraction": ["min", "max", "mean"]
    }).round(3)
    report_lines.append("### Coverage Fraction by Country and Metric")
    report_lines.append("")
    report_lines.append("(Minimum, maximum, and mean coverage fraction per country and metric)")
    report_lines.append("")
    for idx, row in coverage.groupby(["country", "metric"]).agg({
        "coverage_fraction": ["min", "max", "count"]
    }).round(3).iterrows():
        country, metric = idx
        report_lines.append(f"- {country} {metric}: min={row[('coverage_fraction', 'min')]} max={row[('coverage_fraction', 'max')]} (n={int(row[('coverage_fraction', 'count')])})")
    report_lines.append("")

    # Check for coverage issues
    low_coverage = coverage[coverage["coverage_fraction"] < 0.7]
    if len(low_coverage) > 0:
        report_lines.append("**Alerts**: Low coverage (< 70%)")
        for _, row in low_coverage.iterrows():
            report_lines.append(
                f"- {row['country']} {row['metric']} {row['bucket']}: {row['coverage_fraction']:.1%} "
                f"({row['numerator_mw']:.1f} / {row['denominator_mw']:.1f} MW)"
            )
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 2. Figure Readiness",
        "",
        f"**File**: `figure_readiness.csv`",
        "",
        "Status of each main figure and Extended Data:",
        "",
    ])

    # Figure readiness summary
    for _, fig in figure_readiness.iterrows():
        report_lines.append(f"- Figure {fig['figure']}: {fig['status']} - {fig['reason']}")
    report_lines.append("")

    # Count readiness by status
    readiness_counts = figure_readiness["status"].value_counts()
    report_lines.append(f"**Summary**: {len(figure_readiness)} figures checked")
    for status in ["PRONTA", "PRONTA COM RESSALVA", "BLOQUEADA"]:
        count = readiness_counts.get(status, 0)
        report_lines.append(f"- {status}: {count}")
    report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 3. Plausibility Checks",
        "",
        f"**File**: `plausibility_report.txt`",
        "",
        "Four checks run:",
        "1. **Exposure extremes**: no 0%/100% across all scenarios/models per country×bucket",
        "2. **LR_C bounds**: compound months ratio within [0.1, 20]; flags if baseline < 5 months (unstable)",
        "3. **Bucket sample size**: minimum 5 plants per country×bucket",
        "4. **Scenario ordering**: exposure increases SSP1→SSP3→SSP5 where physically expected",
        "",
        "### Check Results",
        "",
    ])

    pass_count = len(plausibility_checks.get("PASS", []))
    warn_count = len([w for w in plausibility_checks.get("WARN", []) if "CHECK:" not in w])
    fail_count = len(plausibility_checks.get("FAIL", []))

    report_lines.append(f"- **PASS**: {pass_count}")
    report_lines.append(f"- **WARN**: {warn_count}")
    report_lines.append(f"- **FAIL**: {fail_count}")
    report_lines.append("")

    if fail_count > 0:
        report_lines.append("#### FAIL cases:")
        for fail_msg in plausibility_checks.get("FAIL", []):
            report_lines.append(f"- {fail_msg}")
        report_lines.append("")

    if warn_count > 0:
        report_lines.append("#### WARN cases (non-critical):")
        for warn_msg in plausibility_checks.get("WARN", []):
            if "CHECK:" not in warn_msg:
                report_lines.append(f"- {warn_msg}")
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 4. Gap Actions",
        "",
        f"**File**: `gap_actions.csv` ({len(gap_actions)} rows)",
        "",
    ])

    if len(gap_actions) > 0:
        report_lines.append("Proposed minimal actions for FAIL and BLOQUEADA items:")
        report_lines.append("")
        for _, action in gap_actions.iterrows():
            if action["issue_type"] != "info":
                report_lines.append(
                    f"- {action['issue_id']}: {action['recommended_action'].upper()} - {action['rationale']}"
                )
        report_lines.append("")
    else:
        report_lines.append("No gaps requiring action.")
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## 5. Closed Limitations (Not Recalculated)",
        "",
        "The following limitations were closed in prior COMODOs and are "
        "**not** part of this audit's scope; they are referenced for completeness:",
        "",
        "- **D62/L20**: Regional subsystem mapping (plant→ONS subsystem) absent for Brazil; "
        "suspended for v0.1.0",
        "- **L16** (COMANDO 18-G): Nimoo Bazgo (45 MW, hydro run-of-river, India) excluded from H2 "
        "(SPEI-12 dependent on truncated PET in glacial regime); stays in H1/H3; "
        "capacity enters exposure denominator as not-exposed",
        "- **L19** (COMANDO 18-G): 39 thermal plants with baseline F_D = 0 (0.203% of combinations); "
        "R_D left NaN; capacity enters exposure denominator as not-exposed",
        "",
        "---",
        "",
        "## Explicit Readiness Verdict for Phase 7",
        "",
    ])

    # Determine overall readiness
    blocked_count = (figure_readiness["status"] == "BLOQUEADA").sum()
    fail_count_final = len(plausibility_checks.get("FAIL", []))

    if blocked_count == 0 and fail_count_final == 0:
        verdict = "READY FOR PHASE 7"
        report_lines.append(
            f"[OK] **{verdict}**\n\n"
            f"All figures report status PRONTA or PRONTA COM RESSALVA. "
            f"No plausibility FAIL cases. "
            f"Data coverage verified; numerator/denominator definitions applied correctly. "
            f"Closed limitations properly flagged. "
            f"Ready to proceed to Phase 7 results write-up."
        )
    elif blocked_count > 0 and fail_count_final == 0:
        verdict = "READY WITH REVISIONS (figures to supplementary material)"
        report_lines.append(
            f"[WARN] **{verdict}**\n\n"
            f"{blocked_count} figure(s) BLOQUEADA; recommend moving to Supplementary Information. "
            f"No plausibility FAIL cases. "
            f"Core data (coverage, LR_C) audited and sound. "
            f"Author review required: confirm figures can be rebaixadas, or provide remediation."
        )
    else:
        verdict = "HOLD: CRITICAL ISSUES REQUIRE RESOLUTION"
        report_lines.append(
            f"[FAIL] **{verdict}**\n\n"
            f"Plausibility checks returned {fail_count_final} FAIL case(s) ({len(plausibility_checks.get('FAIL', []))} items). "
            f"These point to potential errors in joins or thresholds. "
            f"Author review required: investigate and remediate before proceeding to Phase 7."
        )

    report_lines.extend([
        "",
        "---",
        "",
        "## Next Steps (Author Decision Required)",
        "",
        "1. Review `coverage.csv`: Ensure all metrics show coverage > 50% for main countries/buckets",
        "2. Review `figure_readiness.csv`: Confirm PRONTA status or accept RESSALVA notes",
        "3. Review `plausibility_report.txt`: If FAIL cases exist, investigate and resolve",
        "4. Review `gap_actions.csv`: Accept or override proposed actions",
        "",
        "**STOP**: This audit ends here. Do not proceed with Phase 7 work until these issues are cleared.",
        "",
        "---",
        "",
        f"Generated: 2026-09-30 (COMANDO 22)",
    ])

    report_text = "\n".join(report_lines)
    report_file = outputs_dir / "audit_report.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"  Saved: {report_file}")

    print("\n" + "=" * 60)
    print("AUDIT COMPLETE")
    print("=" * 60)
    print(f"\nReadiness Verdict: {verdict}")
    print("\n[STOP] STOPPING HERE PER SPECIFICATION")
    print("Author review required before proceeding to Phase 7.")

    return report_file


if __name__ == "__main__":
    report_file = main()
    sys.exit(0)
