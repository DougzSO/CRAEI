"""Fig 6: share of fuel-class capacity with TX35 >= 30 d/yr, by fuel (D131, D133).

Source: w3_table1.csv at threshold 30 (precedent scripts/w3_table1.py:35), fleets
operating / planned_all, pct_median. Nuclear is excluded from both panels; a fuel
with no row in a fleet is drawn as "n/a".
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import FOOT, SCEN, SCEN_COLOR, SCEN_LABEL, fig_text, place_axes, read_csv, save_figure

THRESHOLD = 30
FUELS = ["bioenergy", "coal", "gas", "multi_fuel", "oil"]
FUEL_LABEL = ["Bioenergy", "Coal", "Gas", "Multi-fuel", "Oil"]
PANELS = [("operating", "Operating fleet"), ("planned_all", "Planned fleet")]
NOTE = ('Bars = share of fuel-class capacity (GW) with >=30 days/yr of TX35 exceedance, median '
        'across 5 GCMs. Nuclear excluded (0% exposure across all scenarios, operating; no planned '
        'capacity). Oil excluded from planned fleet (no committed capacity). "n/a" = no capacity '
        'of that fuel class.')
BAR_W = 0.25


def main():
    t = read_csv("w3_table1.csv")
    t = t[(t["threshold"] == THRESHOLD) & t["group"].isin(FUELS)
          & t["fleet"].isin([f for f, _ in PANELS])]
    fig = plt.figure(figsize=(14.1, 6.76))
    axes = [place_axes(fig, 0.69, 1.29, 6.45, 4.66),
            place_axes(fig, 7.36, 1.29, 6.45, 4.66)]
    n_bars = {}
    for k, (ax, (fleet, title)) in enumerate(zip(axes, PANELS)):
        x = np.arange(len(FUELS))
        n_bars[fleet] = 0
        for j, s in enumerate(SCEN):
            vals = []
            for f in FUELS:
                r = t[(t.fleet == fleet) & (t.group == f) & (t.scenario == s)]
                assert len(r) <= 1
                vals.append(float(r["pct_median"].iloc[0]) if len(r) else np.nan)
            vals = np.array(vals)
            xs = x + (j - 1) * BAR_W
            ok = ~np.isnan(vals)
            n_bars[fleet] += int(ok.sum())
            ax.bar(xs[ok], vals[ok], BAR_W, color=SCEN_COLOR[s], ec="black", lw=0.5,
                   label=SCEN_LABEL[s], zorder=3)
            for xi, v in zip(xs[ok], vals[ok]):
                ax.text(xi, v + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=6.5)
        for xi, f in zip(x, FUELS):
            if t[(t.fleet == fleet) & (t.group == f)].empty:
                ax.text(xi, -5, "n/a", ha="center", va="center", fontsize=9, style="italic",
                        color="gray")
        ax.axhline(0, color="black", lw=1.0, zorder=4)
        ax.set_ylim(-10, 110)
        ax.set_xlim(-0.6, len(FUELS) - 0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(FUEL_LABEL, fontsize=10)
        ax.grid(True, axis="y", ls=":", alpha=0.4, zorder=0)
        ax.set_title(title, fontsize=12, weight="bold")
        if k == 0:
            ax.legend(title="Scenario", loc="upper left", fontsize=9)
        else:
            ax.set_yticklabels([])
    assert n_bars == {"operating": 15, "planned_all": 9}, n_bars
    fig_text(fig, 0.19, 1.29 + 4.66 / 2,
             "Share of fuel-class capacity exceeding TX35 >=30 days/yr (median, %)",
             rotation=90, fontsize=10.5, ha="center", va="center")
    fig_text(fig, 6.97, 0.35, "Projected Heat Exposure of Thermal Generation by Fuel Type, Brazil\n"
             "(Baseline 1985-2014, Future 2041-2070)", fontsize=13, weight="bold", ha="center",
             va="center")
    fig_text(fig, 0.1, 6.6, NOTE, **FOOT)
    save_figure(fig, "fig6_thermal_heat_by_fuel.png")


if __name__ == "__main__":
    main()
