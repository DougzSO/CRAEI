"""Three-panel Brazil map layout shared by Fig 1, 3, 5a and 5b (D133).

Uses `scripts/article_map_utils.base_brazil_map` for the map chrome (state
boundaries, labels, compass rose, scale bar).
"""

import matplotlib.pyplot as plt
from _common import MAP_EXTENT, SCEN, SCEN_LABEL, fig_text, load_geo, place_axes
from article_map_utils import base_brazil_map

PANEL_LEFTS = (0.10, 5.72, 11.33)
PANEL_W, PANEL_H = 5.35, 5.36
FIG_W = 16.9


def map_figure(fig_h, axes_top, suptitle):
    """Figure with three map panels (one per scenario) and a centered suptitle."""
    adm1, adm0, sam0 = load_geo()
    fig = plt.figure(figsize=(FIG_W, fig_h))
    axes = []
    for left, s in zip(PANEL_LEFTS, SCEN):
        ax = place_axes(fig, left, axes_top, PANEL_W, PANEL_H)
        base_brazil_map(ax, MAP_EXTENT, adm1, adm0, sam0)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(SCEN_LABEL[s], fontsize=12, weight="bold", pad=8)
        axes.append(ax)
    fig_text(fig, FIG_W / 2, 0.28, suptitle, fontsize=14, weight="bold", ha="center",
             va="center")
    return fig, axes, adm1
