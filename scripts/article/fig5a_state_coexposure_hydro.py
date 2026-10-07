"""Fig 5a: state compound climate context, hydropower (Itaipu b, Brazilian share) (D133, D139).

Heat is regional climatic context at the plant cell, not a hydropower heat hazard (hydropower is
outside H1, D88). See _fig5_common. The footnote ratios come from the national Table 3 (mean
across 5 GCMs) while the map shows state medians.
"""

from _common import BASELINE_FUTURE, hydro_context_note
from _fig5_common import state_figure


def main():
    text, _ = hydro_context_note()
    state_figure(
        "fig5a_state_coexposure_hydro.png", "hydro", "b",
        "Regional Compound Climate Context by State -- Hydropower: Extreme Basin Drought and "
        "Extreme Plant-Cell Heat\n" + BASELINE_FUTURE.replace(")", ", Itaipu Brazil share)"),
        "hydropower", 19,
        cbar_label="Median share of capacity with extreme basin drought and extreme cell heat (%)",
        note_tail=text)


if __name__ == "__main__":
    main()
