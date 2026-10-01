import pandas as pd

from craei.inventory import units as U


def test_units_roundtrip_parquet_with_mixed_type_text_columns(tmp_path):
    names = ["u1", 3, "--", None]
    ids = [1, "G2", 3.5, None]
    rows = [
        {
            "Country/area": "Brazil", "Plant / Project name": f"P{i}",
            "Unit / Phase name": names[i], "GEM unit/phase ID": ids[i],
            "Capacity (MW)": 10.0, "Status": "operating", "Type": "hydropower",
            "Technology": "run-of-river", "Latitude": -10.0 - i, "Longitude": -50.0,
        }
        for i in range(4)
    ]
    units = U.build_units(pd.DataFrame(rows))
    path = tmp_path / "units.parquet"
    units.to_parquet(path, index=False)
    back = pd.read_parquet(path)
    assert len(back) == 4
    assert set(back.unit_name.dropna()) == {"u1", "3", "--"}
    assert set(back.gem_unit_id.dropna()) == {"1", "G2", "3.5"}
    assert int(back.unit_name.isna().sum()) == 1