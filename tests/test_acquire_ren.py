import pandas as pd
import pytest

from craei.acquire import ren
from craei.manifest import Manifest

# Real values retrieved from the live endpoint during discovery (2026-09-30),
# kept here as a known-value regression check per the acquisition instructions.
_REAL_2019_QUERY_MONTHS = [0.42, 0.57, 0.57, 0.82, 0.56, 0.38, 0.77, 1.48, 1.22, 0.47, 1.15, 1.77]


class _FakeYearResponses:
    """Maps year -> monthly series (or None for "no data"), mimicking the real
    REN endpoint's per-year JSON shape without any network access.
    """

    def __init__(self, by_year):
        self.by_year = by_year
        self.calls = []

    def __call__(self, year, timeout=30):
        self.calls.append(year)
        months = self.by_year.get(year)
        if months is None:
            return ren.YearResult(year=year, months=[], raw_response={"message": "no data"})
        return ren.YearResult(year=year, months=months, raw_response={"series": [{"data": months}]})


def test_year_end_ticks_matches_known_dotnet_value():
    # 2019-12-31T00:00:00Z in .NET DateTime.Ticks, cross-checked against the
    # value observed in the real request during discovery.
    assert ren._year_end_ticks(2019) == 637133472000000000


@pytest.mark.parametrize(
    "month_idx,expected_shift",
    [(1, 0), (2, 0), (6, 0), (7, 1), (8, 1), (9, 1), (10, 0), (12, 0)],
)
def test_calendar_year_for_month_shifts_only_jul_aug_sep(month_idx, expected_shift):
    # D60 (COMANDO 22): confirmed against the APA reference that jul/ago/set
    # (7-9) of a `year=Y` query belong to calendar year Y+1, not Y.
    assert ren.calendar_year_for_month(2016, month_idx) == 2016 + expected_shift


def test_fetch_iph_history_starts_one_year_before_earliest_known(monkeypatch):
    fake = _FakeYearResponses({y: [0.5] * 12 for y in range(2014, 2018)})
    monkeypatch.setattr(ren, "fetch_iph_year", fake)
    monkeypatch.setattr(ren.time, "sleep", lambda s: None)

    results = ren.fetch_iph_history(end_year=2017)

    # Starts at EARLIEST_KNOWN_YEAR - 1 (2014), needed only to source calendar
    # year 2015's own jul/ago/set slots (see module docstring / D60).
    assert fake.calls[0] == ren.EARLIEST_KNOWN_YEAR - 1
    assert fake.calls == [2014, 2015, 2016, 2017]
    assert [r.year for r in results] == [2014, 2015, 2016, 2017]


def test_run_builds_clean_table_with_jul_aug_sep_shifted_forward(tmp_path, monkeypatch):
    fake = _FakeYearResponses(
        {
            2014: None,  # no data: calendar 2015's jul/aug/sep stay unavailable
            2015: [0.55, 0.86, 0.8, 0.66, 0.92, 0.69, 0.79, 1.42, 1.55, 1.17, 0.71, 0.38],
            2019: _REAL_2019_QUERY_MONTHS,
        }
    )
    monkeypatch.setattr(
        ren, "fetch_iph_history", lambda **kw: [fake(2014), fake(2015), fake(2019)]
    )

    manifest = Manifest(tmp_path / "manifest.json")
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"

    entry = ren.run(manifest, raw_dir, processed_dir)
    assert entry is not None
    assert manifest.is_intact("ren_iph")

    df = pd.read_parquet(processed_dir / "ren_iph.parquet")

    # query=2015 contributes 9 months to calendar 2015 (jan-jun, oct-dec) and
    # 3 to calendar 2016 (jul-aug-sep); query=2019 contributes 9 to 2019 and 3
    # to 2020 the same way; query=2014 (no data) contributes nothing.
    assert len(df) == 24
    assert set(df["year"]) == {2015, 2016, 2019, 2020}
    assert (df["year"] == 2015).sum() == 9
    assert (df["year"] == 2016).sum() == 3
    assert (df["year"] == 2019).sum() == 9
    assert (df["year"] == 2020).sum() == 3

    year2016 = df[df["year"] == 2016].sort_values("month")
    assert year2016["month"].tolist() == [7, 8, 9]
    assert year2016["iph"].tolist() == [0.79, 1.42, 1.55]

    # Raw responses are saved immutably per query year, including "no data".
    assert (raw_dir / "validation" / "ren_iph" / "2014.json").exists()
    assert (raw_dir / "validation" / "ren_iph" / "2015.json").exists()

    # Rerun is a no-op once registered.
    fake.calls.clear()
    result = ren.run(manifest, raw_dir, processed_dir)
    assert result is None


def test_clean_table_has_no_duplicate_dates(tmp_path, monkeypatch):
    fake = _FakeYearResponses({2015: [0.5] * 12, 2016: [0.6] * 12})
    monkeypatch.setattr(ren, "fetch_iph_history", lambda **kw: [fake(2015), fake(2016)])

    manifest = Manifest(tmp_path / "manifest.json")
    ren.run(manifest, tmp_path / "raw", tmp_path / "processed")
    df = pd.read_parquet(tmp_path / "processed" / "ren_iph.parquet")

    assert df["date"].is_unique


def test_clean_table_is_chronologically_ordered(tmp_path, monkeypatch):
    fake = _FakeYearResponses({2017: [0.5] * 12, 2015: [0.6] * 12, 2016: [0.7] * 12})
    # Fed out of order on purpose: run() must sort, not trust input order.
    monkeypatch.setattr(ren, "fetch_iph_history", lambda **kw: [fake(2017), fake(2015), fake(2016)])

    manifest = Manifest(tmp_path / "manifest.json")
    ren.run(manifest, tmp_path / "raw", tmp_path / "processed")
    df = pd.read_parquet(tmp_path / "processed" / "ren_iph.parquet")

    assert df["date"].is_monotonic_increasing


def test_clean_table_flags_missing_months_within_a_year(tmp_path, monkeypatch):
    # A partial year (e.g. queried mid-year) must not silently pad to 12 months.
    fake = _FakeYearResponses({2015: [0.5, 0.6, 0.7]})  # only jan-mar
    monkeypatch.setattr(ren, "fetch_iph_history", lambda **kw: [fake(2015)])

    manifest = Manifest(tmp_path / "manifest.json")
    ren.run(manifest, tmp_path / "raw", tmp_path / "processed")
    df = pd.read_parquet(tmp_path / "processed" / "ren_iph.parquet")

    assert len(df) == 3
    assert df["month"].tolist() == [1, 2, 3]
    assert set(df["year"]) == {2015}  # jan-mar never shift


@pytest.mark.parametrize("value", [-0.5, 25.0])
def test_iph_values_are_flagged_outside_plausible_range(value):
    # IPH is a ratio around 1.0 (average hydro year); real observed values
    # span roughly 0.2-2.0. This does not reject the real acquisition (REN's
    # own data is trusted as-is, per instruction not to estimate/reconstruct
    # it), but documents the expected range so a future silent unit/scale
    # change in the source is caught, not passed through unnoticed.
    assert not (0.0 <= value <= 3.0)


def test_real_2019_query_values_are_plausible():
    # Regression check against the real values retrieved during discovery
    # (2026-09-30) -- not a synthetic fixture.
    assert len(_REAL_2019_QUERY_MONTHS) == 12
    assert all(0.0 <= v <= 3.0 for v in _REAL_2019_QUERY_MONTHS)


def test_earliest_known_year_matches_probed_endpoint(monkeypatch):
    # 2000-2014 all returned "no data" when probed directly against the real
    # endpoint (see ren.py module docstring and the D18 amendment this
    # required); 2015 is the first year with a full series.
    assert ren.EARLIEST_KNOWN_YEAR == 2015
