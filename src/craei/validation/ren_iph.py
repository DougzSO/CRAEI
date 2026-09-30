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
    to be the same quantity REN itself uses for its annual/civil-year figure
    -- the monthly endpoint used for acquisition exposes no annual field and
    no per-month weighting scheme, and a simple mean does not reproduce the
    reference in general (see the module docstring's point A/B distinction
    and `reports/ren_iph_validation.md` Section 5 for the evidence: 2017 is
    the clearest case -- high mid-year monthly values during a year ERSE
    records as a low-productivity year overall, consistent with the annual
    figure being production-weighted rather than equally-weighted across
    months). Rows are still reported per year, not suppressed.
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
