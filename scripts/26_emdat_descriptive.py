"""COMANDO 22-D, O15 (author-authorized): EM-DAT descriptive summary table.

METHODS_SPEC.md line 115 and 447 already settle EM-DAT's role: "EM-DAT is
used only descriptively in Supplementary Information" / "EM-DAT descriptive
overlay" (Extended Data, not main). No statistical test and no validation
language -- this script only counts and sums `emdat_events.parquet`
(already scoped to BRA/IND/PRT and the four Spec event types by the
acquisition step), grouped by country x event_type, with the observed year
range per group. No filtering beyond what `emdat_events.parquet` already
carries.
"""

from pathlib import Path

import pandas as pd

from craei.config import load_paths


def main() -> None:
    paths = load_paths()
    processed_dir = Path(paths["processed_dir"])
    outputs_tables_dir = Path(paths["outputs_tables_dir"])

    events = pd.read_parquet(processed_dir / "emdat_events.parquet")

    out = events.groupby(["country", "event_type"], as_index=False).agg(
        n_events=("start_year", "size"),
        first_year=("start_year", "min"),
        last_year=("end_year", "max"),
        total_deaths=("deaths", "sum"),
        total_affected=("affected", "sum"),
        total_economic_damage=("economic_damage", "sum"),
        n_with_deaths=("deaths", "count"),
        n_with_affected=("affected", "count"),
        n_with_economic_damage=("economic_damage", "count"),
    )
    out = out.sort_values(["country", "event_type"]).reset_index(drop=True)

    out_path = outputs_tables_dir / "emdat_descriptive.csv"
    out.to_csv(out_path, index=False)
    print(f"wrote {out_path}: {len(out)} rows (purely descriptive, no statistical test)")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
