"""REN IPH validation against independent official references (COMANDO 22).

Three distinct claims, never conflated (per the author's explicit instruction):

A) acquisition/implementation validation -- can the acquired series be checked
   directly against an independent, official published number? (APA monthly,
   ERSE/REN annual)
B) long-term climatological validation -- NOT claimed here. Five years of
   overlap with W5E5 (2015-2019) is enough to catch acquisition/implementation
   bugs, not to establish long-term statistical robustness.
C) DGEG hydro generation -- an auxiliary sanity check only. DGEG measures
   production (MWh); REN's IPH is a productivity/hydrological-regime ratio.
   Broad co-movement is expected, equality is not, and none is imposed here.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TWO_DECIMAL_TOLERANCE = 0.015  # half a cent above the largest rounding step the
# published references (2 decimals) can introduce; a real discrepancy is much larger.


@dataclass(frozen=True)
class CoverageAudit:
    n_rows: int
    first_date: pd.Timestamp
    last_date: pd.Timestamp
    n_duplicate_dates: int
    is_monotonic: bool
    n_null_iph: int
    n_negative_iph: int
    months_per_year: dict[int, int]
    iph_min: float
    iph_max: float


def audit_coverage(df: pd.DataFrame) -> CoverageAudit:
    """Structural audit of the acquired REN IPH table -- no reference data needed."""
    return CoverageAudit(
        n_rows=len(df),
        first_date=df["date"].min(),
        last_date=df["date"].max(),
        n_duplicate_dates=int(df["date"].duplicated().sum()),
        is_monotonic=bool(df["date"].is_monotonic_increasing),
        n_null_iph=int(df["iph"].isna().sum()),
        n_negative_iph=int((df["iph"] < 0).sum()),
        months_per_year=df.groupby("year").size().to_dict(),
        iph_min=float(df["iph"].min()),
        iph_max=float(df["iph"].max()),
    )


def load_apa_reference(path: Path) -> pd.DataFrame:
    ref = pd.read_csv(path)
    ref["date"] = pd.to_datetime(ref["date"] + "-01", format="%Y-%m-%d")
    ref["year"] = ref["date"].dt.year
    ref["month"] = ref["date"].dt.month
    return ref


def compare_monthly_apa(df: pd.DataFrame, apa_ref: pd.DataFrame) -> dict:
    """Compare the acquired series against the APA monthly reference, by exact
    (year, month) match. Every mismatch is reported explicitly, never hidden.
    """
    merged = apa_ref.merge(
        df[["year", "month", "iph"]],
        on=["year", "month"],
        how="left",
        suffixes=("_ref", "_extracted"),
    )
    merged["extracted"] = merged["iph"]
    merged["missing"] = merged["extracted"].isna()
    merged["abs_diff"] = (merged["extracted"].round(2) - merged["iph_reference"]).abs()
    merged["mismatch"] = merged["missing"] | (merged["abs_diff"] > TWO_DECIMAL_TOLERANCE)

    compared = merged[~merged["missing"]]
    mismatches = merged[merged["mismatch"]]

    return {
        "n_compared": len(apa_ref),
        "n_matched": int((~merged["mismatch"]).sum()),
        "n_mismatched": int(merged["mismatch"].sum()),
        "max_abs_diff": float(compared["abs_diff"].max()) if len(compared) else None,
        "mean_abs_diff": float(compared["abs_diff"].mean()) if len(compared) else None,
        "mismatch_table": mismatches[
            ["date", "hydrological_year", "iph_reference", "extracted", "abs_diff"]
        ],
        "pass": bool(merged["mismatch"].sum() == 0),
    }


def compare_annual_erse(df: pd.DataFrame, erse_ref: pd.DataFrame) -> dict:
    """Compare each ERSE/REN annual reference year against a *derived* annual
    value (calendar-year arithmetic mean of the acquired monthly series).

    This derived quantity is reported for the record, but it is NOT assumed
    to be the same quantity REN itself uses for its annual/civil-year figure.
    Confirmed directly (COMANDO 23, Part A1) by inspecting every raw REN
    response saved during acquisition (`check_annual_field_in_raw_response`):
    the `RegimeYearly` endpoint used for acquisition carries no annual field,
    no per-month weight, and no production/afluência denominator of any kind
    -- only the 12 monthly values. A simple calendar mean of those 12 values
    does not reproduce ERSE's published annual figure in general (2017 is the
    clearest case: ERSE reports 0.47, a low-productivity year, while the
    derived mean is far higher because 2017's mid-year monthly values happen
    to be unusually high and a simple mean over-weights them relative to
    whatever REN's real aggregation applies). No official description of
    REN's annual aggregation formula was found (checked REN/ERSE/DGEG
    published technical documentation, COMANDO 23 Part A3) with which to
    reproduce it exactly, so this comparison is retained as a documented
    methodological limitation of the annual figure, not evidence against the
    monthly series (see `compare_monthly_apa`, which independently PASSes).
    Rows are still reported per year, not suppressed.
    """
    rows = []
    for _, ref_row in erse_ref.iterrows():
        year = int(ref_row["year"])
        months = df.loc[df["year"] == year, "iph"]
        derived = float(months.mean()) if len(months) else None
        reference = float(ref_row["iph_annual_reference"])
        abs_diff = abs(round(derived, 2) - reference) if derived is not None else None
        rel_diff = abs_diff / reference if abs_diff is not None else None
        rows.append(
            {
                "year": year,
                "reference": reference,
                "derived_calendar_mean": derived,
                "n_months_used": int(len(months)),
                "abs_diff": abs_diff,
                "rel_diff": rel_diff,
                "pass_at_2dp": bool(abs_diff is not None and abs_diff <= TWO_DECIMAL_TOLERANCE),
            }
        )
    result = pd.DataFrame(rows)
    return {
        "table": result,
        "pass": bool(result["pass_at_2dp"].all()),
        "n_years": len(result),
        "n_pass": int(result["pass_at_2dp"].sum()),
    }


def check_annual_field_in_raw_response(raw_response: dict) -> bool:
    """Whether a raw REN `RegimeYearly` JSON response exposes any annual/
    aggregate field beyond the 12 monthly values (COMANDO 23, Part A1).

    Checked directly against every saved raw response (2015-2025): the only
    keys are `xAxis`/`yAxis`/`legend`/`plotOptions`/`chart`/`series`, and
    `series` always has exactly one entry whose `data` is the 12 monthly
    values -- no annual total, weight, production or afluência field exists
    anywhere in the payload. This function lets that fact be asserted by a
    test against the real saved fixtures rather than only stated in prose.
    """
    series = raw_response.get("series", [])
    if len(series) != 1:
        return True  # an extra series would be a candidate annual/aux field
    known_keys = {"xAxis", "yAxis", "legend", "plotOptions", "chart", "series"}
    return bool(set(raw_response.keys()) - known_keys)


def compare_dgeg_auxiliary(df: pd.DataFrame, dgeg_df: pd.DataFrame) -> dict:
    """Auxiliary consistency check: REN IPH (productivity ratio) vs DGEG gross
    hydro generation (GWh, a production volume). These are different physical
    quantities -- broad co-movement is expected (both track wet/dry years),
    exact agreement is not, and no threshold is imposed as pass/fail here.
    """
    merged = df[["date", "year", "month", "iph"]].merge(
        dgeg_df[["date", "hydro_generation_gwh"]], on="date", how="inner"
    )
    monthly_pearson = float(merged["iph"].corr(merged["hydro_generation_gwh"], method="pearson"))
    monthly_spearman = float(merged["iph"].corr(merged["hydro_generation_gwh"], method="spearman"))

    annual = merged.groupby("year").agg(
        iph_mean=("iph", "mean"), hydro_generation_gwh_sum=("hydro_generation_gwh", "sum")
    )
    annual_pearson = float(annual["iph_mean"].corr(annual["hydro_generation_gwh_sum"], "pearson"))
    annual_spearman = float(annual["iph_mean"].corr(annual["hydro_generation_gwh_sum"], "spearman"))

    return {
        "n_months_compared": int(len(merged)),
        "years_compared": sorted(int(y) for y in annual.index),
        "monthly_table": merged,
        "annual_table": annual.reset_index(),
        "monthly_pearson_r": monthly_pearson,
        "monthly_spearman_r": monthly_spearman,
        "annual_pearson_r": annual_pearson,
        "annual_spearman_r": annual_spearman,
    }


@dataclass(frozen=True)
class Overlap:
    ren_start_year: int
    ren_end_year: int
    w5e5_start_year: int
    w5e5_end_year: int
    common_start_year: int
    common_end_year: int
    common_complete_years: list[int]
    common_available_months: int


def compute_w5e5_overlap(df: pd.DataFrame, w5e5_start_year: int, w5e5_end_year: int) -> Overlap:
    """The real REN/W5E5 overlap actually usable by the study.

    Reports the true available month count within the overlap years, not an
    assumed 12-per-year figure -- 2015 has only 9 real months (see the
    jul/ago/set gap documented in `craei.acquire.ren`), so the common period's
    real month count can be below `12 * n_years`.
    """
    ren_start_year, ren_end_year = int(df["year"].min()), int(df["year"].max())
    common_start = max(ren_start_year, w5e5_start_year)
    common_end = min(ren_end_year, w5e5_end_year)
    complete_years = [
        y
        for y in range(common_start, common_end + 1)
        if int((df["year"] == y).sum()) == 12
    ]
    available_months = int(df[(df["year"] >= common_start) & (df["year"] <= common_end)].shape[0])
    return Overlap(
        ren_start_year=ren_start_year,
        ren_end_year=ren_end_year,
        w5e5_start_year=w5e5_start_year,
        w5e5_end_year=w5e5_end_year,
        common_start_year=common_start,
        common_end_year=common_end,
        common_complete_years=complete_years,
        common_available_months=available_months,
    )
