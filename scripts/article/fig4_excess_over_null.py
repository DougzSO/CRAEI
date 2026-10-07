"""Fig 4: excess exposure over the stationary resampling null, forest plot, operating fleet (D133, O20, O46, O51).

Single source w4c_spi_vs_spei.csv, fleet operating, null block_bootstrap_12; k/5 from
w6_agreement_k.csv (GCMs sharing the sign of the median, D114). Hydro uses Itaipu b; thermal is
water-dependent (itaipu na, 618 plants). Rows: hydro SPEI and SPI, thermal SPEI and SPI. Value labels sit
in a right-hand column inside the axes (median, k/5). Null pools, rates and the interpretive title are in
the caption (docs/article/drafts/results.md).
"""

from decimal import ROUND_HALF_UP, Decimal

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import SCEN, SCEN_COLOR, SCEN_LABEL, place_axes, read_csv, save_figure
from _maps import legend_blocks
from _style import FS_TICK, W2
from matplotlib.lines import Line2D

GROUPS = [("Hydro, SPEI", "hydro", "spei", "b"), ("Hydro, SPI", "hydro", "spi", "b"),
          ("Thermal (water-dep.), SPEI", "thermal_water_dependent", "spei", "na"),
          ("Thermal (water-dep.), SPI", "thermal_water_dependent", "spi", "na")]
EXPECT = {("hydro", "spei"): [40.75, 43.20, 53.94],  # D102
          ("hydro", "spi"): [17.40, 3.03, 38.60],  # D125
          ("thermal_water_dependent", "spei"): [20.63, 28.50, 48.06],  # D125
          ("thermal_water_dependent", "spi"): [-1.08, 5.44, 27.50]}  # D125
KEY = {("hydro", "spei"): "hydro spei", ("hydro", "spi"): "hydro spi",
       ("thermal_water_dependent", "spei"): "thermal_water_dependent spei",
       ("thermal_water_dependent", "spi"): "thermal_water_dependent spi"}
ROW_STEP = 0.26
AXES_TOP, AXES_H = 0.24, 2.45
XLIM = (-25, 85)
LABEL_X = 84.5  # right edge of the value-label column


def fmt1(x):
    """One decimal, halves rounded up (40.75 -> 40.8), with sign."""
    d = Decimal(str(round(float(x), 2))).quantize(Decimal("0.1"), ROUND_HALF_UP)
    return f"{d:+}"


def kappa(k):
    """k of 5 for the 4 x 3 numbers, from w6_agreement_k.csv."""
    a = k[k["number"].str.contains("excess over null")].copy()
    a["key"] = a["number"].str.replace(" excess over null (block12), operating", "", regex=False)
    return {(r.key, r.scenario): int(r.k_of_5) for r in a.itertuples()}


def main():
    w = read_csv("w4c_spi_vs_spei.csv")
    w = w[(w["fleet"] == "operating") & (w["null_type"] == "block_bootstrap_12")]
    ks = kappa(read_csv("w6_agreement_k.csv"))
    fig_h = AXES_TOP + AXES_H + 0.46 + 0.18 + 0.17 + 0.05 + 0.04
    fig = plt.figure(figsize=(W2, fig_h))
    ax = place_axes(fig, 1.70, AXES_TOP, 5.30, AXES_H)
    ticks, labels = [], []
    for i, (label, grp, hz, ip) in enumerate(GROUPS):
        g = w[(w.group == grp) & (w.hazard == hz) & (w.itaipu == ip)].set_index("scenario")
        assert len(g) == 3, (grp, hz, len(g))
        med = [round(float(g.loc[s, "excess_pp_median"]), 2) for s in SCEN]
        assert all(abs(a - b) <= 1e-3 for a, b in zip(med, EXPECT[(grp, hz)])), (grp, hz, med)
        for j, s in enumerate(SCEN):
            y = i + ROW_STEP * j
            lo, m, hi = g.loc[s, ["excess_pp_min", "excess_pp_median", "excess_pp_max"]]
            assert XLIM[0] < lo and hi < XLIM[1] - 13, (grp, hz, s, lo, hi)
            k = ks[(KEY[(grp, hz)], s)]
            ax.plot([lo, hi], [y, y], color=SCEN_COLOR[s], lw=1.6, solid_capstyle="butt", zorder=2)
            ax.plot(m, y, "o", ms=4.2, mfc=SCEN_COLOR[s], mec="black", mew=0.5, zorder=3)
            ax.text(LABEL_X, y, f"{fmt1(m)}  ({k}/5)", va="center", ha="right", fontsize=FS_TICK,
                    color="#222222")
        gw, n = float(g["gw_total_mw"].iloc[0]) / 1000.0, int(g["n_plants"].iloc[0])
        ticks.append(i + ROW_STEP)
        labels.append(f"{label}\n{gw:.1f} GW, n={n}")
    ax.axvline(0, color="black", lw=0.7, zorder=1)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels)
    ax.set_ylim(len(GROUPS) - 0.05, -0.3)
    ax.set_xlim(*XLIM)
    ax.set_xlabel("Excess over resampling null (percentage points)")
    ax.text(LABEL_X, -0.38, "median (k/5)", ha="right", va="bottom", fontsize=FS_TICK, style="italic")
    ax.grid(True, axis="x", ls=":", alpha=0.4)
    handles = [Line2D([0], [0], color=SCEN_COLOR[s], lw=1.6, marker="o", ms=4.2, mec="black", mew=0.5,
                      label=SCEN_LABEL[s]) for s in SCEN]
    legend_blocks(fig, AXES_TOP + AXES_H + 0.46, [("Scenario (median, range across 5 GCMs)", handles, 1)])
    save_figure(fig, "fig4_excess_over_null.png")


if __name__ == "__main__":
    main()
