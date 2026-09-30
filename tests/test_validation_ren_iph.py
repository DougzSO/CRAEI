import pandas as pd

from craei.validation import ren_iph


def _make_df(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_audit_coverage_reports_structural_facts():
    df = _make_df(
        [
            {"date": "2015-01-01", "year": 2015, "month": 1, "iph": 1.2},
            {"date": "2015-02-01", "year": 2015, "month": 2, "iph": 0.8},
            {"date": "2016-01-01", "year": 2016, "month": 1, "iph": 1.5},
        ]
    )
    audit = ren_iph.audit_coverage(df)

    assert audit.n_rows == 3
    assert audit.first_date == pd.Timestamp("2015-01-01")
    assert audit.last_date == pd.Timestamp("2016-01-01")
    assert audit.n_duplicate_dates == 0
    assert audit.is_monotonic
    assert audit.n_null_iph == 0
    assert audit.n_negative_iph == 0
    assert audit.months_per_year == {2015: 2, 2016: 1}


def test_audit_coverage_flags_duplicates_and_negatives():
    df = _make_df(
        [
            {"date": "2015-01-01", "year": 2015, "month": 1, "iph": -0.3},
            {"date": "2015-01-01", "year": 2015, "month": 1, "iph": -0.3},
        ]
    )
    audit = ren_iph.audit_coverage(df)

    assert audit.n_duplicate_dates == 1
    assert audit.n_negative_iph == 2


def test_compare_monthly_apa_passes_on_exact_match():
    df = _make_df([{"date": "2017-07-01", "year": 2017, "month": 7, "iph": 1.18}])
    apa_ref = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2017-07-01"),
                "year": 2017,
                "month": 7,
                "iph_reference": 1.18,
                "hydrological_year": "2016/2017",
            }
        ]
    )
    result = ren_iph.compare_monthly_apa(df, apa_ref)

    assert result["pass"] is True
    assert result["n_mismatched"] == 0
    assert result["max_abs_diff"] < 0.015


def test_compare_monthly_apa_reports_real_mismatch_explicitly():
    df = _make_df([{"date": "2017-07-01", "year": 2017, "month": 7, "iph": 0.10}])
    apa_ref = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2017-07-01"),
                "year": 2017,
                "month": 7,
                "iph_reference": 1.18,
                "hydrological_year": "2016/2017",
            }
        ]
    )
    result = ren_iph.compare_monthly_apa(df, apa_ref)

    assert result["pass"] is False
    assert result["n_mismatched"] == 1
    assert len(result["mismatch_table"]) == 1


def test_compare_monthly_apa_reports_missing_month_as_mismatch():
    df = _make_df([{"date": "2017-01-01", "year": 2017, "month": 1, "iph": 0.36}])
    apa_ref = pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2017-01-01"),
                "year": 2017,
                "month": 1,
                "iph_reference": 0.36,
                "hydrological_year": "x",
            },
            {
                "date": pd.Timestamp("2017-07-01"),
                "year": 2017,
                "month": 7,
                "iph_reference": 1.18,
                "hydrological_year": "x",
            },
        ]
    )
    result = ren_iph.compare_monthly_apa(df, apa_ref)

    # The second reference month has no matching acquired row: reported as a
    # mismatch, not silently dropped from the comparison.
    assert result["n_compared"] == 2
    assert result["n_mismatched"] == 1
    assert result["pass"] is False


def test_compare_annual_erse_does_not_force_a_match():
    # Real finding (D60): 2017's derived calendar mean does not reproduce
    # ERSE's reported annual value. The comparison logic must report this,
    # not hide or adjust it.
    df = _make_df(
        [
            {"date": f"2017-{m:02d}-01", "year": 2017, "month": m, "iph": v}
            for m, v in enumerate(
                [0.36, 0.92, 0.67, 0.41, 0.56, 0.47, 1.18, 2.17, 1.22, 0.16, 0.16, 0.27], start=1
            )
        ]
    )
    erse_ref = pd.DataFrame([{"year": 2017, "iph_annual_reference": 0.47}])
    result = ren_iph.compare_annual_erse(df, erse_ref)

    row = result["table"].iloc[0]
    assert row["reference"] == 0.47
    assert not row["pass_at_2dp"]
    assert result["pass"] is False


def test_compare_annual_erse_passes_when_means_genuinely_agree():
    df = _make_df(
        [{"date": f"2020-{m:02d}-01", "year": 2020, "month": m, "iph": 1.0} for m in range(1, 13)]
    )
    erse_ref = pd.DataFrame([{"year": 2020, "iph_annual_reference": 1.0}])
    result = ren_iph.compare_annual_erse(df, erse_ref)

    assert result["pass"] is True
    assert result["table"].iloc[0]["abs_diff"] == 0.0


def test_compute_w5e5_overlap_reports_real_month_count_not_assumed():
    # 2015 has 9 months (jul/aug/sep missing, D60); 2016-2019 have 12 each.
    months_per_year = {2015: 9, 2016: 12, 2017: 12, 2018: 12, 2019: 12}
    rows = []
    for year, n in months_per_year.items():
        months = [m for m in range(1, 13) if not (year == 2015 and 7 <= m <= 9)][:n]
        for m in months:
            rows.append({"date": f"{year}-{m:02d}-01", "year": year, "month": m, "iph": 1.0})
    df = _make_df(rows)

    overlap = ren_iph.compute_w5e5_overlap(df, w5e5_start_year=1984, w5e5_end_year=2019)

    assert overlap.common_start_year == 2015
    assert overlap.common_end_year == 2019
    assert overlap.common_complete_years == [2016, 2017, 2018, 2019]
    assert overlap.common_available_months == 9 + 12 * 4


def test_compute_w5e5_overlap_does_not_assume_twelve_per_year():
    # A naive `n_years * 12` would silently overstate coverage: this test
    # locks in that the function reports the real, possibly-lower count.
    df = _make_df([{"date": "2015-01-01", "year": 2015, "month": 1, "iph": 1.0}])
    overlap = ren_iph.compute_w5e5_overlap(df, w5e5_start_year=2015, w5e5_end_year=2015)

    assert overlap.common_available_months == 1
    assert overlap.common_complete_years == []
