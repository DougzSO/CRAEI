"""Fig 4: excess exposure over the null, forest plot, operating fleet (D133, O20).

Single source w4c_spi_vs_spei.csv, fleet operating, null block_bootstrap_12. Hydro
uses Itaipu b; thermal is water-dependent (itaipu na). Hydro and thermal use
distinct null pools (stated in the footnote).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import FOOT, SCEN, SCEN_COLOR, SCEN_LABEL, fig_text, place_axes, read_csv, save_figure
from matplotlib.lines import Line2D

GROUPS = [("Hydro -- SPEI\n(Itaipu Brazil share)", "hydro", "spei", "b"),
          ("Thermal (water-dep.) -- SPEI", "thermal_water_dependent", "spei", "na"),
          ("Thermal (water-dep.) -- SPI", "thermal_water_dependent", "spi", "na")]
EXPECT = {("hydro", "spei"): [40.75, 43.20, 53.94],  # D102
          ("thermal_water_dependent", "spei"): [20.63, 28.50, 48.06],  # D125
          ("thermal_water_dependent", "spi"): [-1.08, 5.44, 27.50]}  # D125
NOTE = ("Point = median, line = range across 5 GCMs. Hydro and thermal use distinct null "
        "pools (see group labels).")
ROW_STEP = 0.26


def main():
    w = read_csv("w4c_spi_vs_spei.csv")
    w = w[(w["fleet"] == "operating") & (w["null_type"] == "block_bootstrap_12")]
    fig = plt.figure(figsize=(10.66, 6.18))
    ax = place_axes(fig, 2.32, 0.43, 7.35, 4.9)
    ticks, labels = [], []
    for i, (label, grp, hz, ip) in enumerate(GROUPS):
        g = w[(w.group == grp) & (w.hazard == hz) & (w.itaipu == ip)].set_index("scenario")
        assert len(g) == 3, (grp, hz, len(g))
        med = [round(float(g.loc[s, "excess_pp_median"]), 2) for s in SCEN]
        assert all(abs(a - b) <= 1e-3 for a, b in zip(med, EXPECT[(grp, hz)])), (grp, hz, med)
        for j, s in enumerate(SCEN):
            y = i + ROW_STEP * j
            lo, m, hi = g.loc[s, ["excess_pp_min", "excess_pp_median", "excess_pp_max"]]
            ax.plot([lo, hi], [y, y], color=SCEN_COLOR[s], lw=2.5, solid_capstyle="butt", zorder=2)
            ax.plot(m, y, "o", ms=8, mfc=SCEN_COLOR[s], mec="black", mew=0.8, zorder=3)
            ax.text(hi + 3, y, f"{m:+.1f}", va="center", fontsize=9, color="#222222")
        ticks.append(i + ROW_STEP / 2)
        labels.append(label)
    ax.axvline(0, color="black", lw=1.0, zorder=1)
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlim(-22, 75)
    ax.set_xlabel("Excess exposure over the null model (percentage points)", fontsize=11)
    ax.grid(True, axis="x", ls=":", alpha=0.4)
    ax.set_title("Climate Exposure Exceeds Chance Across Hazards and Scenarios, "
                 "Brazil's Operating Fleet", fontsize=13, weight="bold", pad=12)
    ax.legend(handles=[Line2D([0], [0], color=SCEN_COLOR[s], lw=2.5, marker="o", ms=8, mec="black",
                              label=SCEN_LABEL[s]) for s in SCEN],
              title="Scenario", loc="lower right", fontsize=10)
    fig_text(fig, 0.1, 6.02, NOTE, **FOOT)
    save_figure(fig, "fig4_excess_over_null.png")


if __name__ == "__main__":
    main()
