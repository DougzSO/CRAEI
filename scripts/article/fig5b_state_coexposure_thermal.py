"""Fig 5b: state co-exposure, water-dependent thermal; see _fig5_common."""

from _common import BASELINE_FUTURE
from _fig5_common import state_figure


def main():
    state_figure(
        "fig5b_state_coexposure_thermal.png", "thermal_water_dependent", "na",
        "Co-Located Extreme Heat and Extreme Drought Exposure by State -- Water-Dependent "
        "Thermal\n" + BASELINE_FUTURE, "water-dependent thermal", 26)


if __name__ == "__main__":
    main()
