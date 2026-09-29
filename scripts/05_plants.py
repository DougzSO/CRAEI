"""COMANDO 13: plant inventory (Spec §3 Step 1).

Filters GEM to the 3 study countries/fleets, aggregates units to plants,
classifies technology (D15) and computes distance to coast (D24). Writes
`plants.parquet` and a `plants_discarded.csv` report.
"""

from pathlib import Path

import pandas as pd

from craei.config import load_datasets, load_paths
from craei.inventory import plants as inv


def main() -> None:
    paths = load_paths()
    datasets_cfg = load_datasets()
    raw_dir = Path(paths["raw_dir"])
    processed_dir = Path(paths["processed_dir"])

    gem_path = next((raw_dir / "gem").glob("*.xlsx"))
    coastline_path = raw_dir / "boundaries" / "ne_10m_coastline.shp"

    gem = inv.load_gem(gem_path)
    plants, discarded, n_units_in_scope = inv.build_inventory(gem)
    kept_units = n_units_in_scope - len(discarded)
    plants = inv.add_coastal_distance(plants, coastline_path, datasets_cfg["bboxes"])

    # basin_id (COMANDO 17-B Action 6) comes from COMANDO 14's own output, not
    # recomputed here -- plant_uid is a deterministic name/lat/lon hash, so
    # this is a plain join against an existing artifact, not a dependency
    # inversion. Only present once COMANDO 14 has run against this plant set.
    catchment_validation_path = processed_dir / "catchment_validation.csv"
    if catchment_validation_path.exists():
        plants = inv.attach_basin_id(plants, catchment_validation_path)
        print(f"basin_id attached from {catchment_validation_path}")
    else:
        plants["basin_id"] = pd.array([pd.NA] * len(plants), dtype="Int64")
        print(f"{catchment_validation_path} not found -- basin_id left null; rerun after C14")

    out_path = inv.write_plants(plants, discarded, processed_dir)

    print(f"{len(plants)} plants aggregated from {kept_units} kept GEM units")
    print(f"discarded {len(discarded)} units:")
    print(discarded["reason"].value_counts().to_string())
    dup = plants["plant_uid"].duplicated().sum()
    print(f"duplicate plant_uid: {dup}")
    total_out = kept_units + len(discarded)
    ok = total_out == n_units_in_scope
    print(f"kept units + discarded units = {total_out} = units in scope {n_units_in_scope}: {ok}")

    by_country = plants.groupby(["country", "fleet", "tech_class"]).agg(
        n=("plant_uid", "count"), mw=("capacity_mw", "sum")
    )
    print(by_country.to_string())
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
