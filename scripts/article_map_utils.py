"""Brazil map standard for the article figures (Fig 1, 3, 5a, 5b), one design (Phase 9, final round).

Plain matplotlib axes in degrees (equal aspect), extent [-75, -33, -34.5, 6]. South America background
#F5F5F0 without ocean colour, GADM 4.1 state borders (dark grey 0.5 pt) and Brazil outline (black 1.1 pt),
small dark-grey latitude / longitude labels (7 pt, every 10 degrees; latitude on the left panel only),
very light dashed grid, thin light-grey frame, C87 compass rose at 80% and a real 0-250-500 km scale bar
(the C87 bar was twice as long as its label). State labels: inside the state at the point with the least
marker overlap; SP, RJ, PR, MG and DF are placed outside the state with a thin grey leader line.
Geometry: GADM 4.1 layers of data/external/geo/gadm_brazil.gpkg (scripts/geo_base.py); Natural Earth
`southamerica_admin0` only for the neighbouring countries.
"""

import matplotlib.patches as patches
import matplotlib.ticker as mticker
import numpy as np
import shapely

from craei.countries import current as country_cfg

EXTENT = tuple(country_cfg()["geometry"]["map_extent"])  # lon W, lon E, lat S, lat N (config/countries)
XTICKS = (-70, -60, -50, -40)
YTICKS = (0, -10, -20, -30)
SAM = "#F5F5F0"
TICK = "#444444"
STATE_EDGE, STATE_LW = "#555555", 0.5
BRAZIL_LW = 1.1
OUTSIDE = ("SP", "RJ", "PR", "MG", "DF")  # labels moved out of the state (leader line)
SEA_ANCHOR = {"PR": (-45.0, -31.8), "SP": (-41.0, -29.2), "RJ": (-36.8, -25.6), "MG": (-35.4, -20.8)}  # Atlantic


def compass(ax, extent, scale=0.8):
    """C87 compass rose, `scale` times its original size, upper right."""
    lonW, lonE, latS, latN = extent
    size = min(lonE - lonW, latN - latS) * 0.0325 * scale
    h, d = size, size * 0.35
    cx, cy = lonE - (lonE - lonW) * 0.08, latN - (latN - latS) * 0.08
    polys = [([[cx, cy + h], [cx - d, cy], [cx, cy]], "black"), ([[cx, cy + h], [cx + d, cy], [cx, cy]], "#888888"),
             ([[cx + h, cy], [cx, cy + d], [cx, cy]], "black"), ([[cx + h, cy], [cx, cy - d], [cx, cy]], "#888888"),
             ([[cx, cy - h], [cx + d, cy], [cx, cy]], "#CCCCCC"), ([[cx, cy - h], [cx - d, cy], [cx, cy]], "#EFEFEF"),
             ([[cx - h, cy], [cx, cy - d], [cx, cy]], "#CCCCCC"), ([[cx - h, cy], [cx, cy + d], [cx, cy]], "#EFEFEF")]
    for coords, fc in polys:
        ax.add_patch(patches.Polygon(coords, fc=fc, ec="black", lw=0.3, zorder=10))
    ax.text(cx, cy + h + size * 0.3, "N", fontsize=5.5, weight="bold", ha="center", va="bottom", zorder=11)


def scale_bar(ax, extent, km=500, fs=6.5):
    """500 km bar in four alternating segments (labels 0 / 250 / 500 km), lower left."""
    lonW, lonE, latS, latN = extent
    seg = km / (111.32 * np.cos(np.radians((latS + latN) / 2))) / 4
    bx, by, bh = lonW + (lonE - lonW) * 0.04, latS + (latN - latS) * 0.05, (latN - latS) * 0.018
    for i, fc in enumerate(["black", "white", "black", "white"]):
        ax.add_patch(patches.Rectangle((bx + i * seg, by), seg, bh, fc=fc, ec="black", lw=0.5, zorder=10))
    for val, k in ((0, 0), (km / 2, 2), (km, 4)):
        ax.text(bx + k * seg, by - (latN - latS) * 0.025, f"{val:g}" + (" km" if val == km else ""),
                fontsize=fs, ha="center", va="top", zorder=10)


def base_country_map(ax, extent, adm1, adm0, sam0, left_labels=True, tick_fs=7.0):
    """Standard base map of a country on `ax` (see module docstring); geometry comes from the country config."""
    sam0.plot(ax=ax, color=SAM, edgecolor="none", zorder=0)
    adm0.plot(ax=ax, color=SAM, edgecolor="none", zorder=0.2)
    adm1.boundary.plot(ax=ax, edgecolor=STATE_EDGE, linewidth=STATE_LW, zorder=3)
    adm0.boundary.plot(ax=ax, edgecolor="black", linewidth=BRAZIL_LW, zorder=4)
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks(XTICKS)
    ax.set_yticks(YTICKS)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{abs(v):.0f}°{'W' if v < 0 else 'E'}"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{abs(v):.0f}°" + ("S" if v < 0 else "N" if v > 0 else "")))
    ax.tick_params(axis="both", labelsize=tick_fs, labelcolor=TICK, length=2.0, width=0.4, color="#BBBBBB",
                   pad=1.5, labelleft=left_labels)
    ax.grid(True, ls="--", lw=0.4, color="gray", alpha=0.2, zorder=1)
    for sp in ax.spines.values():
        sp.set_linewidth(0.4)
        sp.set_color("#BBBBBB")
    compass(ax, extent)
    scale_bar(ax, extent)


base_brazil_map = base_country_map  # alias kept (name used before the multi-country interface)


def _overlap(cx, cy, mx, my, rad, marea, half_w):
    """Sum of marker areas that a label of half width `half_w` at each candidate would sit on."""
    if len(mx) == 0:
        return np.zeros(len(cx))
    d = np.hypot(cx[:, None] - mx[None, :], cy[:, None] - my[None, :])
    return ((d < (rad[None, :] + half_w)) * marea[None, :]).sum(axis=1)


def place_state_labels(ax, adm1, adm0, mx, my, marea, deg_per_pt, fs=6.2, extent=EXTENT, colors=None):
    """State labels with the least marker overlap (marker area in pt^2 at lon `mx`, lat `my`).

    Inside the state: a 17 x 17 grid over its bounds kept inside the polygon plus the representative point;
    small penalty for distance to the representative point. SP, RJ, PR and MG sit at fixed Atlantic anchors
    (SEA_ANCHOR), DF in the nearest clear spot outside DF within 5 degrees; each with a thin grey leader line.
    Labels are drawn above the markers; `colors` (postal -> colour) overrides the text colour (dark fills).
    """
    mx, my, marea = (np.asarray(v, float) for v in (mx, my, marea))
    rad = np.sqrt(marea / np.pi) * deg_per_pt
    half_w = 0.55 * fs * deg_per_pt + 0.2  # two letters, degrees
    lonW, lonE, latS, latN = extent
    gx, gy = np.meshgrid(np.arange(lonW + 1, lonE - 0.5, 0.5), np.arange(latS + 4.5, latN - 5, 0.5))
    gx, gy = gx.ravel(), gy.ravel()
    brazil = adm0.geometry.union_all()
    order = [p for p in adm1["postal"] if p not in OUTSIDE] + list(OUTSIDE)
    rows = adm1.set_index("postal")
    for postal in order:
        row = rows.loc[postal]
        g = row.geometry
        if postal in OUTSIDE:
            if postal in SEA_ANCHOR:
                tx, ty = SEA_ANCHOR[postal]
            else:
                near = np.hypot(gx - row["cx"], gy - row["cy"]) < 5.0
                ok = near & shapely.contains_xy(brazil, gx, gy) & ~shapely.contains_xy(g, gx, gy)
                cx, cy = gx[ok], gy[ok]
                k = int(np.argmin(_overlap(cx, cy, mx, my, rad, marea, half_w)
                                  + 4.0 * np.hypot(cx - row["cx"], cy - row["cy"])))
                tx, ty = float(cx[k]), float(cy[k])
            ax.plot([row["cx"], tx], [row["cy"], ty], color="#777777", lw=0.5, zorder=7)
            ax.plot([row["cx"]], [row["cy"]], marker=".", ms=2.5, color="#555555", zorder=7)
        else:
            x0, y0, x1, y1 = g.bounds
            ux, uy = np.meshgrid(np.linspace(x0, x1, 17), np.linspace(y0, y1, 17))
            ux, uy = ux.ravel(), uy.ravel()
            ok = shapely.contains_xy(g, ux, uy)
            cx, cy = np.append(ux[ok], row["cx"]), np.append(uy[ok], row["cy"])
            score = _overlap(cx, cy, mx, my, rad, marea, half_w) + 5.0 * np.hypot(cx - row["cx"], cy - row["cy"])
            k = int(np.argmin(score))
            tx, ty = float(cx[k]), float(cy[k])
        ax.text(tx, ty, postal, fontsize=fs, ha="center", va="center", zorder=8,
                color=(colors or {}).get(postal, "#222222") if postal not in OUTSIDE else "#222222")
