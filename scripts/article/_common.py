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
MAP_EXTENT = (-75.0, -34.0, -34.5, 6.0)  # lon W, lon E, lat S, lat N
GEO_LAYERS = ("brazil_admin1", "brazil_admin0", "southamerica_admin0")


def paths():
    return load_paths()


def params():
    return {k: v["value"] for k, v in load_params().items()}


def tables_dir():
    return Path(paths()["outputs_tables_dir"])


def processed_dir():
    return Path(paths()["processed_dir"])


def article_root():
    env = os.environ.get("CRAEI_ARTICLE_OUT")
    return Path(env) if env else Path(paths()["outputs_dir"]) / "article"


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
    """(adm1 with label points cx/cy, adm0, sam0) from the cached Natural Earth gpkg."""
    import geopandas as gpd

    gpkg = Path(paths()["data_root"]) / "external" / "geo" / "natural_earth_brazil.gpkg"
    adm1, adm0, sam0 = (gpd.read_file(gpkg, layer=layer) for layer in GEO_LAYERS)
    pts = adm1.geometry.representative_point()
    adm1 = adm1.assign(cx=pts.x, cy=pts.y)
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


def save_figure(fig, name):
    path = out_dir("figures") / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
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


FOOT = dict(fontsize=8.5, style="italic", color="#444444", va="center", ha="left")
