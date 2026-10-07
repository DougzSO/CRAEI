
import numpy as np
import matplotlib.patches as patches

def compass_rose(ax, extent, transform):
    lonW, lonE, latS, latN = extent
    lon_span = lonE - lonW
    lat_span = latN - latS
    size = min(lon_span, lat_span) * 0.0325
    h = size
    d = size * 0.35
    cx = lonE - lon_span * 0.08
    cy = latN - lat_span * 0.08
    polys = [
        ([[cx, cy+h], [cx-d, cy], [cx, cy]], "black"),
        ([[cx, cy+h], [cx+d, cy], [cx, cy]], "#888888"),
        ([[cx+h, cy], [cx, cy+d], [cx, cy]], "black"),
        ([[cx+h, cy], [cx, cy-d], [cx, cy]], "#888888"),
        ([[cx, cy-h], [cx+d, cy], [cx, cy]], "#CCCCCC"),
        ([[cx, cy-h], [cx-d, cy], [cx, cy]], "#EFEFEF"),
        ([[cx-h, cy], [cx, cy-d], [cx, cy]], "#CCCCCC"),
        ([[cx-h, cy], [cx, cy+d], [cx, cy]], "#EFEFEF"),
    ]
    for coords, fc in polys:
        ax.add_patch(patches.Polygon(coords, fc=fc, ec="black", lw=0.3,
                                      transform=transform, zorder=10))
    ax.text(cx, cy + h + size * 0.3, "N", fontsize=6, weight="bold",
            ha="center", va="bottom", transform=transform, zorder=11)


def scale_bar(ax, extent, escala_km, transform):
    lonW, lonE, latS, latN = extent
    lon_span = lonE - lonW
    lat_span = latN - latS
    lat_mid = (latS + latN) / 2
    km_per_deg = 111.32 * np.cos(np.radians(lat_mid))
    bar_deg = escala_km / km_per_deg
    bx = lonW + lon_span * 0.04
    by = latS + lat_span * 0.05
    bh = lat_span * 0.018
    seg = bar_deg / 2
    colors = ["black", "white", "black", "white"]
    for i, fc in enumerate(colors):
        ax.add_patch(patches.Rectangle((bx + i * seg, by), seg, bh, fc=fc, ec="black",
                                        lw=0.5, transform=transform, zorder=10))
    dy = -lat_span * 0.025
    half_km = escala_km // 2
    for val, xp in [(0, bx), (half_km, bx + bar_deg), (escala_km, bx + 2 * bar_deg)]:
        lbl = f"{val:g}" if val < escala_km else f"{escala_km:g} km"
        ax.text(xp, by + dy, lbl, fontsize=6.5, ha="center", va="top",
                transform=transform, zorder=10)


def base_brazil_map(ax, extent, adm1, adm0, sam0, state_labels=True):
    sam0.plot(ax=ax, color="#f2f2f2", edgecolor="none", zorder=0)
    adm1.boundary.plot(ax=ax, edgecolor="#555555", linewidth=0.7, zorder=3)
    adm0.boundary.plot(ax=ax, edgecolor="black", linewidth=1.4, zorder=4)
    if state_labels:
        for _, row in adm1.iterrows():
            ax.text(row["cx"], row["cy"], row["postal"], fontsize=6.2,
                    ha="center", va="center", zorder=5, color="#222222")
    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])
    compass_rose(ax, extent, ax.transData)
    scale_bar(ax, extent, 500, ax.transData)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
