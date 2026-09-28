import pandas as pd

from craei.hazards import heat


def _synthetic_tasmax():
    # 2000: 3 days >=35C in Jan (2 of them >=40), 1 day >=35C in Feb.
    # 2001: 1 day >=35C, none >=40C.
    dates = pd.to_datetime(
        [
            "2000-01-10", "2000-01-11", "2000-01-12", "2000-01-20",
            "2000-02-05",
            "2001-01-01",
        ]
    )
    values = [35.0, 41.0, 42.0, 20.0, 36.0, 35.5]
    return pd.DataFrame(
        {
            "date": dates,
            "cell_lat": ["A"] * 6,
            "cell_lon": ["A"] * 6,
            "model": ["gfdl-esm4"] * 6,
            "scenario": ["historical"] * 6,
            "tasmax_c": values,
        }
    )


def test_annual_hot_day_counts_tx35():
    daily = _synthetic_tasmax()
    out = heat.annual_hot_day_counts(daily, threshold_c=35.0)
    out = out.set_index("year")["value"]
    assert out.loc[2000] == 4  # 35, 41, 42, 36
    assert out.loc[2001] == 1


def test_annual_hot_day_counts_tx40():
    daily = _synthetic_tasmax()
    out = heat.annual_hot_day_counts(daily, threshold_c=40.0)
    out = out.set_index("year")["value"]
    assert out.loc[2000] == 2  # 41, 42
    assert out.loc[2001] == 0


def test_monthly_hot_day_counts_sum_equals_annual():
    daily = _synthetic_tasmax()
    annual = heat.annual_hot_day_counts(daily, threshold_c=35.0)
    monthly = heat.monthly_hot_day_counts(daily, threshold_c=35.0)
    monthly["year"] = monthly["month"].values.astype("datetime64[Y]").astype(int) + 1970

    summed = monthly.groupby("year")["value"].sum()
    for year, expected in annual.set_index("year")["value"].items():
        assert summed.loc[year] == expected


def test_monthly_hot_day_counts_january_2000():
    daily = _synthetic_tasmax()
    out = heat.monthly_hot_day_counts(daily, threshold_c=35.0)
    jan = out[out["month"] == pd.Timestamp("2000-01-01")].iloc[0]
    assert jan["value"] == 3
