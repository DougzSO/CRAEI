"""Gap action proposals for blocked/failing items (COMANDO 22, Action 4).

For each BLOQUEADA figure or FAIL plausibility check, propose a minimal action:
- Lower to supplementary material
- Aggregate buckets
- Add note to LIMITATIONS.md
- Exclude from results with record in DECISIONS.md
"""

from pathlib import Path

import pandas as pd


def propose_gap_actions(
    figure_readiness: pd.DataFrame,
    plausibility_checks: dict[str, list[str]],
) -> pd.DataFrame:
    """Propose actions for gaps. Returns DataFrame with columns:
    - issue_id: unique identifier
    - issue_type: figure | plausibility
    - description: what is blocked/failing
    - recommended_action: rebaixar | agregar | limitacao | excluir
    - rationale: explanation
    """
    actions = []

    # Process blocked figures
    blocked_figures = figure_readiness[figure_readiness["status"] == "BLOQUEADA"]
    for _, fig in blocked_figures.iterrows():
        issue_id = f"FIG{fig['figure']}"
        if fig["figure"] != "Extended Data":
            action = "rebaixar"
            rationale = (
                f"Move Figure {fig['figure']} to Supplementary Information "
                f"due to: {fig['reason']}"
            )
        else:
            action = "rebaixar"
            rationale = f"Extended Data issue: {fig['reason']}"

        actions.append({
            "issue_id": issue_id,
            "issue_type": "figure",
            "description": fig["reason"],
            "recommended_action": action,
            "rationale": rationale,
        })

    # Process plausibility fails
    for fail_msg in plausibility_checks.get("FAIL", []):
        if "LR_C" in fail_msg:
            issue_id = "PLAUS_LRC"
            rationale = (
                "LR_C out of plausible range; review baseline frequency "
                "(if < 5 months, ratio is unstable; report as percentage difference instead)"
            )
            action = "limitacao"
        elif "Exposure" in fail_msg:
            issue_id = "PLAUS_EXP"
            rationale = "Exposure at extremes; investigate join or threshold"
            action = "limitacao"
        else:
            issue_id = "PLAUS_OTHER"
            rationale = "See message for diagnosis"
            action = "limitacao"

        actions.append({
            "issue_id": issue_id,
            "issue_type": "plausibility",
            "description": fail_msg,
            "recommended_action": action,
            "rationale": rationale,
        })

    # Process warnings as informational (no action needed unless escalated)
    for warn_msg in plausibility_checks.get("WARN", []):
        if "CHECK:" not in warn_msg:  # Skip header lines
            actions.append({
                "issue_id": "INFO",
                "issue_type": "info",
                "description": warn_msg,
                "recommended_action": "monitor",
                "rationale": "Flagged for review; not blocking unless magnitude grows",
            })

    return pd.DataFrame(actions)


def load_and_propose_gaps(
    figure_readiness: pd.DataFrame,
    plausibility_checks: dict[str, list[str]],
) -> pd.DataFrame:
    """Propose actions given readiness and plausibility results."""
    return propose_gap_actions(figure_readiness, plausibility_checks)
