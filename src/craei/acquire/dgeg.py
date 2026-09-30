"""DGEG monthly hydroelectric generation acquisition (COMANDO 23, auxiliary check).

This is NOT the REN Hydro Productivity Index (IPH; `craei.acquire.ren`).
DGEG publishes gross/net electricity production by technology in GWh -- a
production volume, not REN's productivity ratio. It is acquired only as an
independent auxiliary consistency check (Spec §1.7); it is never treated as
equivalent to IPH and never substituted for it.

Source: DGEG's official "Produção mensal de eletricidade" page
(https://www.dgeg.gov.pt/pt/estatistica/energia/eletricidade/producao-mensal-de-eletricidade/),
one `.xls` per year. URLs were confirmed directly against that page's HTML on
2026-09-30 (each file is served from a random-token media path, e.g.
`/media/qg3lfdte/i015524.xls` for 2015 -- not a predictable pattern, so the
per-year URL is pinned here rather than derived).

Each file is a fixed-layout worksheet ("mensais") with header/title rows,
then one row per series labelled in column 0 (e.g. "Hídrica ") and columns
1-12 holding January-December values in GWh, column 13 a yearly total. Two
"Hídrica" rows exist per file: gross ("Produção bruta") appears first,
net ("Produção líquida") second. This module extracts only the gross row,
matching the "Produção bruta (GWh)" section REN's own published figures are
typically compared against.
"""

from pathlib import Path

import pandas as pd
import requests

from craei.manifest import Manifest

DGEG_XLS_URLS = {
    2015: "https://www.dgeg.gov.pt/media/qg3lfdte/i015524.xls",
    2016: "https://www.dgeg.gov.pt/media/gbagx41l/i015523.xls",
    2017: "https://www.dgeg.gov.pt/media/qe3byrkk/i015673.xls",
    2018: "https://www.dgeg.gov.pt/media/vwhfdwjj/i016548.xls",
    2019: "https://www.dgeg.gov.pt/media/gipbzx02/mensais-2019.xls",
}
SERIES_NAME = "Hídrica"
UNIT = "GWh"
VARIABLE = "gross hydroelectric generation, Portugal mainland (auxiliary check, not IPH)"


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)
    return dest


def _extract_gross_hydro_row(xls_path: Path) -> list[float]:
    """Return the 12 January-December gross-hydro GWh values from one file."""
    df = pd.read_excel(xls_path, sheet_name=0, header=None)
    hidrica_rows = [
        i for i, v in enumerate(df[0]) if isinstance(v, str) and "drica" in v.lower()
    ]
    if not hidrica_rows:
        raise ValueError(f"no 'Hídrica' row found in {xls_path}")
    gross_row = hidrica_rows[0]  # gross appears before net in every observed year
    return [float(v) for v in df.iloc[gross_row, 1:13]]


def run(manifest: Manifest, raw_dir: Path, processed_dir: Path) -> dict | None:
    """Download every year's file, extract the gross-hydro row, and build a
    clean monthly table. Returns the manifest entry, or None if already intact.
    """
    key = "dgeg_hydro_generation"
    if manifest.is_intact(key):
        return None

    raw_out_dir = raw_dir / "validation" / "dgeg"
    raw_out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for year, url in sorted(DGEG_XLS_URLS.items()):
        dest = raw_out_dir / f"dgeg_{year}.xls"
        if not dest.exists():
            _download(url, dest)
        for month_idx, value in enumerate(_extract_gross_hydro_row(dest), start=1):
            rows.append(
                {
                    "date": pd.Timestamp(year, month_idx, 1),
                    "year": year,
                    "month": month_idx,
                    "hydro_generation_gwh": value,
                    "source": "DGEG",
                    "source_url": url,
                }
            )

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "dgeg_hydro_generation.parquet"
    df.to_parquet(out_path, index=False)

    return manifest.register(
        key,
        out_path,
        origin="https://www.dgeg.gov.pt/pt/estatistica/energia/eletricidade/producao-mensal-de-eletricidade/",
        route="per_year_xls_download",
    )
