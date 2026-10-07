"""Print layout shared by the article figures (Phase 9, D153).

Neutral journal dimensions until the target journal is adjusted (O52): one column 90 mm, two columns
180 mm, 300 dpi, text legible at 100% (>= 5.5 pt). Figures are saved at exactly these widths (no tight
cropping), the height follows the content.
"""

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

MM = 1 / 25.4
W1, W2 = 90 * MM, 180 * MM  # inches
DPI = 300
FS_TITLE, FS_PANEL, FS_LABEL, FS_TICK, FS_LEGEND, FS_NOTE, FS_SMALL = 8.5, 7.5, 7.0, 6.5, 6.5, 6.2, 5.5
FOOT = dict(fontsize=FS_NOTE, style="italic", color="#444444", va="top", ha="left")
NOTE_CHARS = 150  # characters per note line at FS_NOTE on a 180 mm figure
LINE_IN = FS_NOTE * 1.4 / 72  # note line height, inches


def apply_rc():
    plt.rcParams.update({
        "font.size": FS_LABEL, "axes.labelsize": FS_LABEL, "axes.titlesize": FS_PANEL,
        "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK, "legend.fontsize": FS_LEGEND,
        "legend.title_fontsize": FS_LEGEND, "axes.linewidth": 0.6, "xtick.major.width": 0.5,
        "ytick.major.width": 0.5, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "lines.linewidth": 1.0, "figure.dpi": 100, "savefig.dpi": DPI})


apply_rc()


def wrap(text, chars=NOTE_CHARS):
    return textwrap.wrap(text, width=chars)


def note_height(text, chars=NOTE_CHARS):
    return len(wrap(text, chars)) * LINE_IN + 0.08


def add_note(fig, text, top_in, left_in=0.06, chars=NOTE_CHARS):
    """Wrapped italic note whose first line starts `top_in` below the figure top."""
    w, h = fig.get_size_inches()
    for i, line in enumerate(wrap(text, chars)):
        fig.text(left_in / w, 1 - (top_in + i * LINE_IN) / h, line, **FOOT)


def title(fig, text, y_in=0.07, size=FS_TITLE):
    w, h = fig.get_size_inches()
    return fig.text(0.5, 1 - y_in / h, text, fontsize=size, weight="bold", ha="center", va="top",
                    linespacing=1.15)
