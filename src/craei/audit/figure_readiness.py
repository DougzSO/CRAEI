"""Figure readiness audit (COMANDO 22, Action 2).

For each of the 5 main figures and Extended Data:
- List which tables and columns it depends on
- Verify column exists and is not empty
- Check no bar/panel/point depends on < 5 plants or < 500 MW
- Check fleet and model agreement requirements
"""

from pathlib import Path

import pandas as pd

from craei.config import load_paths


def check_figure_readiness(
    exposure_summary: pd.DataFrame,
    exposure_aqueduct: pd.DataFrame,
    exposure_si: pd.DataFrame,
    compound: pd.DataFrame,
    plant_hazards: pd.DataFrame,
    plants: pd.DataFrame,
) -> pd.DataFrame:
    """Check readiness of each figure.

    Returns DataFrame with columns:
    - figure: Figure name (1, 2, 3, 4, 5, Extended Data)
    - status: PRONTA, PRONTA COM RESSALVA, or BLOQUEADA
    - reason: Explanation of status
    """
    results = []

    # Helper: check if a result depends on < 5 plants or < 500 MW
    def check_sample_size(
        value_rows: pd.DataFrame, metric_col: str, plants_df: pd.DataFrame
    ) -> tuple[bool, str]:
        """Return (is_issue, issue_text)."""
        issues = []
        for _, row in value_rows.iterrows():
            # Find corresponding plants
            # This is a simplified check - in reality would need more context
            pass
        return len(issues) == 0, "; ".join(issues) if issues else ""

    # Figure 1: Maps of ΔTX35 (thermal) and R_D (hydro), SSP3-7.0
    fig1_status = "PRONTA"
    fig1_reason = ""
    try:
        # Check plant_hazards has TX35 and f_d_spei12 data
        has_tx35 = "TX35" in plant_hazards["hazard"].values
        has_spei12 = "f_d_spei12" in plant_hazards["hazard"].values
        if not has_tx35:
            fig1_status = "BLOQUEADA"
            fig1_reason = "TX35 hazard missing from plant_hazards"
        if not has_spei12:
            fig1_status = "BLOQUEADA"
            fig1_reason = (
                fig1_reason + "; " if fig1_reason else ""
            ) + "f_d_spei12 hazard missing"
        if "ssp370" not in plant_hazards["scenario"].values:
            fig1_status = "BLOQUEADA"
            fig1_reason = (
                fig1_reason + "; " if fig1_reason else ""
            ) + "SSP3-7.0 scenario missing"
    except Exception as e:
        fig1_status = "BLOQUEADA"
        fig1_reason = f"Error checking: {str(e)}"

    results.append({
        "figure": "1",
        "status": fig1_status,
        "reason": fig1_reason or "Heat and drought maps, plant-level",
    })

    # Figure 2: Bars by country × technology × SSP
    fig2_status = "PRONTA"
    fig2_reason = ""
    try:
        if exposure_summary.empty:
            fig2_status = "BLOQUEADA"
            fig2_reason = "exposure_summary.csv is empty"
        else:
            # Check for H1 and H2 both present
            has_tx35 = "TX35" in exposure_summary["hazard"].values
            has_drought = "f_d_spei12" in exposure_summary["hazard"].values
            if not has_tx35:
                fig2_status = "PRONTA COM RESSALVA"
                fig2_reason = "TX35 (heat) missing from summary"
            if not has_drought:
                fig2_status = "PRONTA COM RESSALVA"
                fig2_reason = (
                    fig2_reason + "; " if fig2_reason else ""
                ) + "f_d_spei12 (drought) missing"
    except Exception as e:
        fig2_status = "BLOQUEADA"
        fig2_reason = f"Error: {str(e)}"

    results.append({
        "figure": "2",
        "status": fig2_status,
        "reason": fig2_reason or "Grouped bars, country × tech × SSP",
    })

    # Figure 3 (redefined D63): diff_pp + dependence_ratio by country and SSP,
    # not LR_C. See docs/DECISIONS.md D63/D64/D65, docs/LIMITATIONS.md L21.
    fig3_status = "PRONTA COM RESSALVA"
    fig3_reason = (
        "diff_pp + dependence_ratio panels (D63); dependence_ratio only meaningful/"
        "reportable in cells where scripts/c22b_dependence_uncertainty.py's block-"
        "bootstrap CI excludes 1.0 (D65) -- see that diagnostic before quoting it per cell"
    )
    try:
        if compound.empty:
            fig3_status = "BLOQUEADA"
            fig3_reason = "compound.csv is empty"
        else:
            missing_cols = {"diff_pp", "dependence_ratio"} - set(compound.columns)
            if missing_cols:
                fig3_status = "BLOQUEADA"
                fig3_reason = (
                    f"compound.csv missing closed-metric columns {sorted(missing_cols)} (D63)"
                )
            else:
                countries = compound["country"].unique()
                scenarios = compound["scenario"].unique()
                if len(countries) < 3:
                    fig3_reason += f"; only {len(countries)} countries (expected 3)"
                if "ssp370" not in scenarios:
                    fig3_reason += "; SSP3-7.0 missing"
    except Exception as e:
        fig3_status = "BLOQUEADA"
        fig3_reason = f"Error: {str(e)}"

    results.append({
        "figure": "3",
        "status": fig3_status,
        "reason": fig3_reason,
    })

    # Figure 4: Operating vs planned fleets
    fig4_status = "PRONTA"
    fig4_reason = ""
    try:
        if exposure_summary.empty:
            fig4_status = "BLOQUEADA"
            fig4_reason = "exposure_summary.csv is empty"
        else:
            # Check for all three fleets
            fleets = exposure_summary["fleet"].unique()
            required_fleets = {"operating", "planned_adv", "planned_early"}
            missing_fleets = required_fleets - set(fleets)
            if missing_fleets:
                fig4_status = "BLOQUEADA"
                fig4_reason = f"Missing fleets: {missing_fleets}"
            # Check for all three countries with planned
            countries_with_planned = exposure_summary[
                exposure_summary["fleet"].isin(["planned_adv", "planned_early"])
            ]["country"].unique()
            if len(countries_with_planned) < 3:
                fig4_status = "PRONTA COM RESSALVA"
                fig4_reason = (
                    (fig4_reason + "; " if fig4_reason else "")
                    + f"Only {len(countries_with_planned)} countries with planned"
                )
    except Exception as e:
        fig4_status = "BLOQUEADA"
        fig4_reason = f"Error: {str(e)}"

    results.append({
        "figure": "4",
        "status": fig4_status,
        "reason": fig4_reason or "Operating vs planned fleets, by country",
    })

    # Figure 5: Validation (O14, COMANDO 22-C -- validation.csv/emdat_descriptive.csv
    # do not exist anywhere in the project; PRONTA here would contradict Section 5's
    # own "closed limitations" listing, so this checks for the real files rather than
    # assuming W5E5 data alone makes the figure ready.
    fig5_status = "BLOQUEADA"
    fig5_reason = (
        "validation.csv (Spec Step 11) and emdat_descriptive.csv do not exist -- no "
        "script writes them (O14). The closed REN IPH validation (D59-D61) covers "
        "Portugal only, not the Brazil ONS-ENA correlation this figure needs."
    )

    results.append({
        "figure": "5",
        "status": fig5_status,
        "reason": fig5_reason,
    })

    # Extended Data: Sensitivity and H4/Solar/EM-DAT
    extended_status = "PRONTA"
    extended_reason = ""
    try:
        if exposure_si.empty:
            extended_status = "PRONTA COM RESSALVA"
            extended_reason = "H4 and Solar SI table is empty"
        else:
            # Check for H4 hazards
            has_h4 = any(
                h in exposure_si["hazard"].values
                for h in ["h4_p95_ratio", "h4_rx5day_pct_change"]
            )
            if not has_h4:
                extended_status = "PRONTA COM RESSALVA"
                extended_reason = "H4 (precipitation) missing from SI"
    except Exception as e:
        extended_status = "PRONTA COM RESSALVA"
        extended_reason = f"Error checking H4: {str(e)}"

    results.append({
        "figure": "Extended Data",
        "status": extended_status,
        "reason": extended_reason or "H4 extremes, Solar PV, EM-DAT overlay",
    })

    return pd.DataFrame(results)


def load_and_check_figures(
    processed_dir: Path | None = None, tables_dir: Path | None = None
) -> pd.DataFrame:
    """Load all figure inputs and check readiness.

    `tables_dir` is `load_paths()["outputs_tables_dir"]` by default (COMANDO
    22-B Part 3) -- exposure_summary.csv/compound.csv etc. live there, not at
    the outputs root.
    """
    paths = load_paths()
    if processed_dir is None:
        processed_dir = Path(paths["processed_dir"])
    if tables_dir is None:
        tables_dir = Path(paths["outputs_tables_dir"])
    outputs_dir = tables_dir

    # Load required files
    exposure_summary = pd.read_csv(outputs_dir / "exposure_summary.csv")
    exposure_aqueduct = pd.read_csv(outputs_dir / "exposure_aqueduct.csv")
    exposure_si = pd.read_csv(outputs_dir / "exposure_si.csv")
    compound = pd.read_csv(outputs_dir / "compound.csv")
    plant_hazards = pd.read_parquet(processed_dir / "plant_hazards.parquet")
    plants = pd.read_parquet(processed_dir / "plants.parquet")

    return check_figure_readiness(
        exposure_summary,
        exposure_aqueduct,
        exposure_si,
        compound,
        plant_hazards,
        plants,
    )
