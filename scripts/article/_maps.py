"""Shared layout for the article figures: three-panel Brazil maps (Fig 1, 3, 5a, 5b) and the block legend.

One map design (scripts/article_map_utils.py): 17 x 7 in at 300 dpi, three equal-aspect panels almost
touching, scenario panel titles, one-line legend below. No suptitle and no footnote: explanations are in
the caption (docs/article/drafts/results.md). The block legend serves the non-map figures (Fig 2, 4).
"""

import matplotlib.pyplot as plt
from _common import load_geo
from article_map_utils import EXTENT, base_country_map
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

MAP_W, MAP_H = 17.0, 7.0
MAP_LEFT, PANEL_W, PANEL_GAP = 0.50, 5.40, 0.08
MAP_TOP = 0.50
PANEL_H = PANEL_W * (EXTENT[3] - EXTENT[2]) / (EXTENT[1] - EXTENT[0])
DEG_PER_PT = (EXTENT[1] - EXTENT[0]) / (PANEL_W * 72)  # degrees of longitude per point on a panel
LEGEND_Y = MAP_TOP + PANEL_H + 0.78  # legend centre, inches from the top
LEG_ROW = 0.17  # inches per block-legend row
NO_LINE = ("None", "", " ")


def map_figure():
    """17 x 7 in figure with three map panels; returns (fig, axes, adm1, adm0)."""
    adm1, adm0, sam0 = load_geo()
    fig = plt.figure(figsize=(MAP_W, MAP_H))
    axes = []
    for k in range(3):
        left = MAP_LEFT + k * (PANEL_W + PANEL_GAP)
        ax = fig.add_axes([left / MAP_W, 1 - (MAP_TOP + PANEL_H) / MAP_H, PANEL_W / MAP_W, PANEL_H / MAP_H])
        base_country_map(ax, EXTENT, adm1, adm0, sam0, left_labels=k == 0)
        axes.append(ax)
    return fig, axes, adm1, adm0


def rect_in(fig, left_in, top_in, w_in, h_in):
    w, h = fig.get_size_inches()
    return [left_in / w, 1 - (top_in + h_in) / h, w_in / w, h_in / h]


def map_legend(fig, handles, ncol, title=None, **kw):
    """One-row legend centred below the maps (title above it when given)."""
    leg = fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, 1 - LEGEND_Y / MAP_H), ncol=ncol,
                     fontsize=10, title=title, title_fontsize=10, **kw)
    return leg


def _icon_w(h):
    if isinstance(h, Line2D):
        base = 0.24 if h.get_linestyle() not in NO_LINE else 0.14
        return max(base, h.get_markersize() / 72 * 1.15)
    return 0.16


def _draw_icon(ax, h, x, y):
    """Draw legend handle `h` (Line2D or Patch) centred vertically at (x, y), x = left edge, inches."""
    w = _icon_w(h)
    if isinstance(h, Line2D):
        if h.get_linestyle() not in NO_LINE:
            ax.plot([x, x + w], [y, y], color=h.get_color(), ls=h.get_linestyle(),
                    lw=h.get_linewidth(), solid_capstyle="butt", clip_on=False)
        if h.get_marker() not in ("None", "", None):
            ax.plot([x + w / 2], [y], marker=h.get_marker(), ms=h.get_markersize(), ls="none",
                    mfc=h.get_markerfacecolor(), mec=h.get_markeredgecolor(),
                    mew=h.get_markeredgewidth(), clip_on=False)
    else:
        ax.add_patch(Rectangle((x, y - 0.045), w, 0.09, fc=h.get_facecolor(), ec=h.get_edgecolor(),
                               hatch=h.get_hatch(), lw=h.get_linewidth(), clip_on=False))
    return w


def legend_blocks(fig, top_in, blocks, fs=6.3):
    """Block legend under the plots: bold header per block, icons + labels, vertical dividers.

    `blocks` = list of (header, handles, rows). Handles are Line2D / Patch, filled column by column over
    `rows` rows. Blocks share the figure width: leftover width is spread evenly between them.
    Returns the legend height in inches.
    """
    W, _ = fig.get_size_inches()
    total = W - 0.12
    height_in = 0.18 + LEG_ROW * max(r for _, _, r in blocks) + 0.05
    ax = fig.add_axes(rect_in(fig, 0.06, top_in, total, height_in))
    ax.set_xlim(0, total)
    ax.set_ylim(0, height_in)
    ax.axis("off")
    ax.plot([0, total], [height_in, height_in], color="#AAAAAA", lw=0.6, clip_on=False)
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()

    def text_w(s, **kw):
        t = ax.text(0, 0, s, fontsize=fs, **kw)
        bb = t.get_window_extent(rend)
        t.remove()
        return inv.transform((bb.x1, 0))[0] - inv.transform((bb.x0, 0))[0]

    layout = []
    for header, handles, rows in blocks:
        ncol = -(-len(handles) // rows)
        cols = [handles[c * rows:(c + 1) * rows] for c in range(ncol)]
        col_w = [max(_icon_w(h) + 0.05 + text_w(h.get_label()) for h in col) for col in cols]
        layout.append((header, cols, col_w, max(text_w(header, weight="bold"),
                                                sum(col_w) + 0.16 * (ncol - 1))))
    extra = (total - sum(b[3] for b in layout)) / len(layout)
    assert extra > 0.10, f"legend blocks too wide: spare {extra:.2f} in per block"
    x0 = 0.0
    rows_max = max(r for _, _, r in blocks)
    for i, (header, cols, col_w, w) in enumerate(layout):
        off = (rows_max - blocks[i][2]) * LEG_ROW / 2
        x = x0 + extra / 2
        ax.text(x, height_in - 0.08, header, fontsize=fs, weight="bold", va="center")
        for col, cw in zip(cols, col_w):
            for r, h in enumerate(col):
                y = height_in - 0.19 - off - LEG_ROW * (r + 0.5)
                iw = _draw_icon(ax, h, x, y)
                ax.text(x + iw + 0.05, y, h.get_label(), fontsize=fs, va="center")
            x += cw + 0.16
        x0 += w + extra
        if i < len(layout) - 1:
            ax.plot([x0, x0], [0.03, height_in - 0.03], color="#AAAAAA", lw=0.6, clip_on=False)
    return height_in
