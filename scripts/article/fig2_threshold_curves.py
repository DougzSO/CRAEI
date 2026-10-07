"""Fig 2: thermal fleet heat exposure vs threshold, single panel (D133).

Source: w3_curves_plot.csv, group all_thermal, fleet operating / planned_all
(precedent scripts/w3_curves.py:39-40). Bands = min-max over 5 GCMs, operating
fleet, only where the range was reported (thresholds 20/30/40).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import BASELINE_FUTURE, FOOT, SCEN, SCEN_COLOR, SCEN_LABEL, fig_text, place_axes, read_csv, save_figure
from matplotlib.lines import Line2D

FLEETS = {"operating": dict(ls="-", marker="o", label="Operating"),
          "planned_all": dict(ls="--", marker="s", label="Planned")}
BAND_THRESHOLDS = [20, 30, 40]
NOTE = ("Shaded bands = min-max across 5 GCMs (operating fleet only, thresholds 20/30/40 d/yr). "
        "SSP5-8.5 consistently shows the highest exposure share across all thresholds.")


def main():
    t = read_csv("w3_curves_plot.csv")
    t = t[(t["group"] == "all_thermal") & t["fleet"].isin(FLEETS)]
    assert len(t) == 48, len(t)  # 3 scenarios x 2 fleets x 8 thresholds
    assert t.groupby(["scenario", "fleet"]).size().eq(8).all()

    fig = plt.figure(figsize=(9.93, 6.74))
    ax = place_axes(fig, 0.76, 0.64, 9.09, 5.16)
    for s in SCEN:
        strong = s == "ssp585"
        for f, st in FLEETS.items():
            d = t[(t.scenario == s) & (t.fleet == f)].sort_values("threshold")
            ax.plot(d["threshold"], d["pct_median"], color=SCEN_COLOR[s], ls=st["ls"],
                    marker=st["marker"], ms=5.5 if strong else 4.5,
                    lw=3.2 if strong else 1.8, alpha=1.0 if strong else 0.7, zorder=3)
        d = t[(t.scenario == s) & (t.fleet == "operating")
              & t["threshold"].isin(BAND_THRESHOLDS)].sort_values("threshold")
        ax.fill_between(d["threshold"], d["pct_min"], d["pct_max"], color=SCEN_COLOR[s],
                        alpha=0.12, lw=0, zorder=1)
    ax.set_ylim(-5, 101)
    ax.set_xlabel("Threshold (TX35 exceedance, days/year)", fontsize=12)
    ax.set_ylabel("Share of thermal fleet capacity exceeding threshold (median, %)", fontsize=12)
    ax.grid(True, ls=":", alpha=0.4)
    ax.set_title("Thermal Fleet Heat Exposure Increases With Scenario Severity, Brazil\n"
                 + BASELINE_FUTURE, fontsize=13, weight="bold", pad=12)
    h1 = [Line2D([0], [0], color=SCEN_COLOR[s], lw=3.2 if s == "ssp585" else 1.8,
                 label=SCEN_LABEL[s]) for s in SCEN]
    leg1 = ax.legend(handles=h1, title="Scenario (SSP5-8.5 emphasized)", loc="upper right",
                     fontsize=10)
    ax.add_artist(leg1)
    h2 = [Line2D([0], [0], color="black", ls=st["ls"], marker=st["marker"], label=st["label"])
          for st in FLEETS.values()]
    ax.legend(handles=h2, title="Fleet", loc="center right", fontsize=10)
    fig_text(fig, 0.1, 6.6, NOTE, **FOOT)
    save_figure(fig, "fig2_threshold_curves.png")


if __name__ == "__main__":
    main()
