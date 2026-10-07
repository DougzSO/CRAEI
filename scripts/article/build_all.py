"""Build every article artifact (tables 0-3, figures 1-6) in order.

Usage:  python scripts/article/build_all.py [--out DIR]

Without --out, files go to <outputs_dir>/article/{figures,tables}. With --out
(sets CRAEI_ARTICLE_OUT) they go to DIR/{figures,tables}, e.g. a temporary folder
used to compare against data/outputs/article/_ref_C87 before promoting.
"""

import argparse
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "table0_parameters", "table1_fleet_capacity", "table2_leave_one_out",
    "table3_coexposure_crosstab", "table3_crosstab",
    "fig1_heat_class_map", "fig2_threshold_curves", "fig3_drought_exposure_map",
    "fig4_excess_over_null", "fig5a_state_coexposure_hydro",
    "fig5b_state_coexposure_thermal", "fig6_thermal_heat_by_fuel",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="output root (default: <outputs_dir>/article)")
    args = ap.parse_args()
    if args.out:
        os.environ["CRAEI_ARTICLE_OUT"] = str(Path(args.out).resolve())
    sys.path.insert(0, str(HERE))
    for name in SCRIPTS:
        print(f"== {name}")
        runpy.run_path(str(HERE / f"{name}.py"), run_name="__main__")
    print(f"\nbuilt {len(SCRIPTS)} scripts")


if __name__ == "__main__":
    main()
