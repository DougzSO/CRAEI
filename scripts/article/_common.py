"""Shared helpers for the article artifact scripts (scripts/article/).

Paths come from `craei.config.load_paths`. Output goes to
`<outputs_dir>/article/{figures,tables}`, or to `$CRAEI_ARTICLE_OUT/{figures,tables}`
when that variable is set (used to build into a temporary folder and compare).
"""

import os
import sys
from pathlib import Path

import pandas as pd

from craei.config import load_params, load_paths

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))  # for article_map_utils

SCEN = ["ssp126", "ssp370", "ssp585"]
SCEN_LABEL = {"ssp126": "SSP1-2.6", "ssp370": "SSP3-7.0", "ssp585": "SSP5-8.5"}
# Spectral-style palette shared by all figures (low -> extreme).
SCEN_COLOR = {"ssp126": "#2b83ba", "ssp370": "#fdae61", "ssp585": "#d7191c"}
CLASS_COLOR = {"low": "#2b83ba", "medium": "#abdda4", "high": "#fdae61", "extreme": "#d7191c"}
CLASS_ORDER = ["low", "medium", "high", "extreme"]
BASELINE_FUTURE = "(Baseline 1985-2014, Future 2041-2070)"
DPI = 300
MAP_EXTENT = (-75.0, -33.0, -34.5, 6.0)  # lon W, lon E, lat S, lat N (article_map_utils.EXTENT)


def paths():
    return load_paths()


def params():
    return {k: v["value"] for k, v in load_params().items()}


def tables_dir():
    return Path(paths()["outputs_tables_dir"])


def processed_dir():
    return Path(paths()["processed_dir"])


def article_root():
    """Output root: CRAEI_ARTICLE_OUT, else the preview folder; the official folder only via build_all --promote."""
    env = os.environ.get("CRAEI_ARTICLE_OUT")
    return Path(env) if env else Path(paths()["outputs_dir"]) / "article" / "_preview"


def out_dir(kind):
    d = article_root() / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_csv(name):
    """Production CSV from outputs_tables_dir (UTF-8, falling back to cp1252)."""
    p = tables_dir() / name
    try:
        return pd.read_csv(p)
    except UnicodeDecodeError:
        return pd.read_csv(p, encoding="cp1252")


def write_text(path, text):
    """UTF-8 without BOM, LF line endings."""
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def write_csv(df, path):
    df.to_csv(path, index=False, lineterminator="\n", encoding="utf-8")


def md_table(df):
    """GitHub-style markdown table from a string-converted frame."""
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def load_geo():
    """(adm1, adm0, sam0): GADM 4.1 states (postal code, label point cx/cy) and Brazil outline from
    gadm_brazil.gpkg; neighbouring countries (without Brazil) from the Natural Earth cache."""
    import geopandas as gpd

    geo = Path(paths()["data_root"]) / "external" / "geo"
    adm1 = gpd.read_file(geo / "gadm_brazil.gpkg", layer="brazil_admin1_gadm")
    adm0 = gpd.read_file(geo / "gadm_brazil.gpkg", layer="brazil_admin0_gadm")
    sam0 = gpd.read_file(geo / "natural_earth_brazil.gpkg", layer="southamerica_admin0")
    sam0 = sam0[sam0[next(c for c in sam0.columns if c.lower() == "adm0_a3")] != "BRA"]
    pts = adm1.geometry.representative_point()
    adm1 = adm1.assign(cx=pts.x, cy=pts.y)
    assert len(adm1) == 27 and adm1["postal"].nunique() == 27
    return adm1, adm0, sam0


def brazil_plants():
    """plants.parquet joined with plant_cell.parquet (one row per plant)."""
    plants = pd.read_parquet(processed_dir() / "plants.parquet")
    pc = pd.read_parquet(processed_dir() / "plant_cell.parquet").drop_duplicates("plant_uid")
    return plants.merge(pc, on="plant_uid", how="left")


def marker_size(capacity_mw, scale=1.0):
    """Scatter area (pt^2) of a plant marker: linear in MW, capped, times `scale`."""
    return scale * (5.0 + 0.2 * capacity_mw).clip(upper=300.0)


THERMAL_MARKER_SCALE = 0.55  # thermal markers are drawn smaller than hydro (Fig 1, Fig 3)
MAP_MARKER_SCALE = 0.30  # markers on the 180 mm three-panel maps (panels are 2.3 in wide)


def save_figure(fig, name, journal_width=True):
    """Save at the exact figure size (no tight cropping); journal_width=True requires 1 or 2 columns.

    The three-panel maps are kept at their 17 x 7 in working size (journal reduction comes later).
    """
    path = out_dir("figures") / name
    w_in = fig.get_size_inches()[0]
    if journal_width:
        assert min(abs(w_in - 90 / 25.4), abs(w_in - 180 / 25.4)) < 1e-6, w_in
    fig.savefig(path, dpi=DPI, facecolor="white")
    print("written:", path)
    return path


def place_axes(fig, left_in, top_in, width_in, height_in, **kw):
    """Axes at an absolute position in inches (top measured from the figure top)."""
    w, h = fig.get_size_inches()
    return fig.add_axes([left_in / w, 1 - (top_in + height_in) / h, width_in / w,
                         height_in / h], **kw)


def fig_text(fig, x_in, y_in, text, **kw):
    """Text at an absolute position in inches (y measured from the figure top)."""
    w, h = fig.get_size_inches()
    return fig.text(x_in / w, 1 - y_in / h, text, **kw)




def hydro_context_note():
    """Hydropower compound-context sentence with the V3 ratios computed from the data (D139).

    Ratio = co-extreme share / extreme-drought share, national operating fleet, mean across
    5 GCMs (table3_coexposure_gcm_mean.csv, canonical pool).
    """
    d = read_csv("table3_coexposure_gcm_mean.csv")
    d = d[(d["group"] == "hydro") & (d["fleet"] == "operating") & (d["pool"] == "catchment")]
    parts, ratios = [], []
    for s in SCEN:
        x = d[d["scenario"] == s]
        assert len(x) == 16
        co = float(x[(x.heat_class == "extreme") & (x.drought_class == "extreme")].pct_mean.iloc[0])
        dr = float(x[x.drought_class == "extreme"].pct_mean.sum())
        ratios.append(f"{100 * co / dr:.0f}%")
        parts.append(f"{co:.1f} of {dr:.1f}%")
    return (
        "Heat is shown as regional climatic context at the plant cell (TX35 class), not as a heat "
        "hazard to hydropower, which is outside H1. Compound = extreme drought class (catchment) "
        "and extreme heat class (plant cell), same GCM. For the national operating fleet, the "
        f"compound share is {', '.join(ratios[:-1])} and {ratios[-1]} of the extreme-drought "
        "share alone (SSP1-2.6 / SSP3-7.0 / SSP5-8.5; mean across 5 GCMs: "
        f"{', '.join(parts)})."), ratios


def heat_drought_note():
    """O47: observed heat x drought dependence against the GCMs (E1, e1_hedge_observed.csv)."""
    o = read_csv("e1_hedge_observed.csv")
    o = o[(o["fleet"] == "operating") & (o["h_channel"] == "spi") & (o["t_channel"] == "heat")].iloc[0]
    assert o["D_lo_b12"] < 1 < o["D_hi_b12"]
    return (f"In W5E5 observations the heat x drought pair shows no dependence (D = {o['D']:.2f}, 95% CI "
            f"{o['D_lo_b12']:.2f}-{o['D_hi_b12']:.2f} includes 1), whereas the GCMs give a baseline D of "
            f"about {o['D_gcm_baseline_median']:.1f}; GCM heat x drought co-exposure is therefore probably "
            "inflated relative to observations (E1, D143).")
