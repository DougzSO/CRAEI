"""REN DataHub hydro productivity index (IPH) acquisition (validation, Spec §1.7).

The real network request behind the monthly "Indice de produtibilidade
hidroelectrica" chart at
https://datahub.ren.pt/pt/eletricidade/regimes/modules/mensal/hidrica-prod/
indice-de-produtibilidade-hidroeletrica/ was found by instrumenting a real
browser (`scripts/debug_ren_iph_network.py`), since it is neither of the
generic `servicebus.ren.pt/datahubapi` endpoints documented on REN's public
API page nor reachable by direct HTTP from this machine (that host times out
at the TCP level, consistent with a WAF blocking non-browser clients). The
actual call is a plain POST to `datahub.ren.pt/service/` (a different host),
which IS reachable directly:

    POST https://datahub.ren.pt/service/Electricity/RegimeYearly/2900
         ?culture=pt-PT&dayToSearchString={ticks}&isShare=true

`dayToSearchString` is a .NET `DateTime.Ticks` value (100-ns intervals since
0001-01-01) for the last day of the target year; the response's `series[0]
.data` is 12 monthly IPH values, positionally ordered January-first per the
response's own `xAxis.categories` (`jan`...`dez`). Querying a year with no
published data returns HTTP 400 with a JSON body carrying a `"message"` key
(an HTML no-results snippet) instead of a `"series"` key -- observed
directly, not assumed; any other 4xx/5xx is a real error.

Confirmed directly against this endpoint (not assumed): every year 2000-2014
returns no data; 2015 is the first year with a full 12-month series. This
contradicts D18 in `docs/DECISIONS.md` ("REN series has years before 2015,
author confirmed manually") -- see the D18 amendment this discovery required.

**Critical, non-obvious date-mapping bug found and fixed (COMANDO 22, D60)**:
positions 7-9 of a `year=Y` query's series (the `jul`/`ago`/`set` slots) hold
calendar year Y+1's data, not year Y's -- positions 1-6 (`jan`-`jun`) and
10-12 (`out`-`dez`) are calendar year Y as their labels suggest. Found by
cross-checking the raw acquired series against an independent published
reference (APA 2018, Tabela 7, sourced from REN's own monthly statistics):
every one of 33 compared months matched to within 0.01 (pure 2-decimal
rounding) only after applying this Y+1 shift to jul/ago/set; without it, 9 of
33 months were off by up to 1.38 (clearly wrong, not a rounding artifact).
The cause is presumed to be REN's internal "ano hidrológico" (Oct-Sep)
convention leaking into this civil-year-labeled endpoint's Jul-Sep slots
specifically -- not confirmed with REN directly, but the shift itself is
confirmed empirically, independent of the cause. `run()` below applies this
shift when building the calendar-dated output; a year=Y query's jul/ago/set
values are attributed to calendar year Y+1, so building calendar year Y+1's
Jul-Sep requires fetching query year Y (one year *earlier* than Y+1 itself).
A practical consequence: calendar year 2015's Jul/Aug/Sep are unavailable
(would need query year 2014, which returns no data at all).
"""

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

from craei.manifest import Manifest

SERVICE_URL = "https://datahub.ren.pt/service/Electricity/RegimeYearly/2900"
MODULE_REFERER = (
    "https://datahub.ren.pt/pt/eletricidade/regimes/modules/mensal/"
    "hidrica-prod/indice-de-produtibilidade-hidroeletrica/"
)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": MODULE_REFERER,
    "Accept": "*/*",
}
_DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=UTC)
_MONTH_NAMES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

EARLIEST_KNOWN_YEAR = 2015  # confirmed by probing 2000-2014 (all "no data"), see module docstring.


def _year_end_ticks(year: int) -> int:
    dt = datetime(year, 12, 31, tzinfo=UTC)
    return int((dt - _DOTNET_EPOCH).total_seconds() * 10_000_000)


def calendar_year_for_month(query_year: int, month_idx: int) -> int:
    """The true calendar year for `month_idx` (1-12) of a `year=query_year` query.

    See the module docstring: jul/ago/set (7-9) belong to `query_year + 1`,
    confirmed against the APA reference (COMANDO 22, D60).
    """
    return query_year + 1 if 7 <= month_idx <= 9 else query_year


@dataclass(frozen=True)
class YearResult:
    year: int
    months: list[float | None]  # length 0-12, January-first; None = no data at all
    raw_response: dict


def fetch_iph_year(year: int, timeout: int = 30) -> YearResult:
    """Fetch one year's monthly IPH series. Raises on a real HTTP error."""
    ticks = _year_end_ticks(year)
    response = requests.post(
        SERVICE_URL,
        data=b"",
        headers=_HEADERS,
        params={"culture": "pt-PT", "dayToSearchString": ticks, "isShare": "true"},
        timeout=timeout,
    )
    # The service returns HTTP 400 (not 200) for a year with no published
    # data, with a JSON body carrying a "message" key (an HTML no-results
    # snippet) instead of a "series" key -- observed directly, not assumed;
    # any other 4xx/5xx is a real error and still raises.
    if response.status_code == 400:
        payload = response.json()
        if "message" in payload:
            return YearResult(year=year, months=[], raw_response=payload)
    response.raise_for_status()
    payload = response.json()
    if "message" in payload:
        return YearResult(year=year, months=[], raw_response=payload)
    series = payload["series"][0]["data"]
    return YearResult(year=year, months=list(series), raw_response=payload)


def fetch_iph_history(
    start_year: int = EARLIEST_KNOWN_YEAR - 1,
    end_year: int | None = None,
    sleep_s: float = 0.5,
) -> list[YearResult]:
    """Fetch every year from `start_year` to `end_year` (default: current year).

    Starts one year before `EARLIEST_KNOWN_YEAR` (i.e. 2014): per the jul/ago/
    set shift documented in the module docstring, calendar year 2015's own
    Jul-Sep values would come from a `year=2014` query, so it must be queried
    even though the year itself has no other published data (confirmed: it
    returns "no data" for every month, see `calendar_year_for_month`).
    """
    if end_year is None:
        end_year = datetime.now(UTC).year
    results = []
    for year in range(start_year, end_year + 1):
        results.append(fetch_iph_year(year))
        time.sleep(sleep_s)
    return results


def run(manifest: Manifest, raw_dir: Path, processed_dir: Path) -> dict | None:
    """Acquire the full available IPH history, save raw responses, register, and
    build a clean table. Returns the manifest entry for the clean parquet, or
    None if already intact.
    """
    key = "ren_iph"
    if manifest.is_intact(key):
        return None

    results = fetch_iph_history()

    raw_out_dir = raw_dir / "validation" / "ren_iph"
    raw_out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for result in results:
        raw_path = raw_out_dir / f"{result.year}.json"
        raw_path.write_text(
            json.dumps(result.raw_response, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        for month_idx, value in enumerate(result.months, start=1):
            if value is None:
                continue
            calendar_year = calendar_year_for_month(result.year, month_idx)
            rows.append(
                {
                    "date": datetime(calendar_year, month_idx, 1),
                    "year": calendar_year,
                    "month": month_idx,
                    "iph": value,
                    "source": "REN DataHub",
                    "source_url": MODULE_REFERER,
                }
            )

    df = (
        pd.DataFrame(rows)
        .drop_duplicates(subset=["date"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "ren_iph.parquet"
    df.to_parquet(out_path, index=False)

    return manifest.register(
        key, out_path, origin=SERVICE_URL, route="browser_discovered_direct_http"
    )
