"""Fig 2: thermal fleet heat exposure vs threshold, single panel (D133, Phase 9).

Source: w3_curves_plot.csv, group all_thermal, fleet operating / planned_all
(precedent scripts/w3_curves.py:39-40). Bands = min-max over 5 GCMs, operating fleet, at every
threshold (the range exists for all eight thresholds; only the bootstrap interval is limited to
20/30/40). Fleet capacity (GW) and number of units in the legend.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import SCEN, SCEN_COLOR, SCEN_LABEL, place_axes, read_csv, save_figure
from _maps import legend_blocks
from _style import W2
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

FLEETS = {"operating": dict(ls="-", marker="o", label="Operating"),
          "planned_all": dict(ls="--", marker="s", label="Planned")}
AXES_TOP, AXES_H = 0.10, 2.55
LEGEND_TOP = AXES_TOP + AXES_H + 0.42


def main():
    t = read_csv("w3_curves_plot.csv")
    t = t[(t["group"] == "all_thermal") & t["fleet"].isin(FLEETS)]
    assert len(t) == 48, len(t)  # 3 scenarios x 2 fleets x 8 thresholds
    assert t.groupby(["scenario", "fleet"]).size().eq(8).all()
    thresholds = sorted(t["threshold"].unique())
    assert thresholds[0] == 10 and len(thresholds) == 8, thresholds

    fig_h = LEGEND_TOP + 0.18 + 0.17 * 3 + 0.05 + 0.04
    fig = plt.figure(figsize=(W2, fig_h))
    ax = place_axes(fig, 0.60, AXES_TOP, 6.35, AXES_H)
    for s in SCEN:
        strong = s == "ssp585"
        for f, st in FLEETS.items():
            d = t[(t.scenario == s) & (t.fleet == f)].sort_values("threshold")
            ax.plot(d["threshold"], d["pct_median"], color=SCEN_COLOR[s], ls=st["ls"],
                    marker=st["marker"], ms=3.4 if strong else 2.8,
                    lw=1.9 if strong else 1.1, alpha=1.0 if strong else 0.75, zorder=3)
        d = t[(t.scenario == s) & (t.fleet == "operating")].sort_values("threshold")
        ax.fill_between(d["threshold"], d["pct_min"], d["pct_max"], color=SCEN_COLOR[s],
                        alpha=0.13, lw=0, zorder=1)
    ax.set_ylim(-3, 101)
    ax.set_xlim(7, 103)
    ax.set_xticks(thresholds)
    ax.set_xlabel("Threshold (TX35 exceedance, days/year)")
    ax.set_ylabel("Thermal capacity exposed (%)")
    ax.grid(True, ls=":", alpha=0.4)
    h1 = [Line2D([0], [0], color=SCEN_COLOR[s], lw=1.9 if s == "ssp585" else 1.1,
                 label=SCEN_LABEL[s]) for s in SCEN]
    top = {f: t[(t.fleet == f) & (t.threshold == 10) & (t.scenario == "ssp585")].iloc[0] for f in FLEETS}
    h2 = [Line2D([0], [0], color="black", ls=st["ls"], marker=st["marker"], ms=3,
                 label=f"{st['label']}: {top[f].gw_total:.1f} GW, n={int(top[f].n_units)}")
          for f, st in FLEETS.items()]
    h3 = [Patch(fc="gray", alpha=0.25, label="Min-max, 5 GCMs")]
    legend_blocks(fig, LEGEND_TOP, [("Scenario", h1, 3), ("Fleet", h2, 3), ("Range", h3, 3)])
    save_figure(fig, "fig2_threshold_curves.png")


if __name__ == "__main__":
    main()
