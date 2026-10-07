"""Fig 5a: state co-exposure, hydropower (Itaipu b, Brazilian share); see _fig5_common."""

from _common import BASELINE_FUTURE
from _fig5_common import state_figure


def main():
    state_figure(
        "fig5a_state_coexposure_hydro.png", "hydro", "b",
        "Co-Located Extreme Heat and Extreme Drought Exposure by State -- Hydropower\n"
        + BASELINE_FUTURE.replace(")", ", Itaipu Brazil share)"), "hydropower", 19)


if __name__ == "__main__":
    main()
