"""Fig 6: share of fuel-class capacity with TX35 >= 30 d/yr, by fuel (D131, D133).

Source: w3_table1.csv at threshold 30 (precedent scripts/w3_table1.py:35), fleets
operating / planned_all, pct_median. All fuel classes with a row are drawn, nuclear
included (a real 0% is shown, D136); a fuel with no row in a fleet is drawn as "n/a".
Fuel-class capacity (GW) and unit count (n) are printed under each label.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import SCEN, SCEN_COLOR, SCEN_LABEL, fig_text, place_axes, read_csv, save_figure
from _style import FS_PANEL, FS_SMALL, FS_TICK, W2

THRESHOLD = 30
FUELS = ["bioenergy", "coal", "gas", "multi_fuel", "nuclear", "oil"]
FUEL_LABEL = ["Bioenergy", "Coal", "Gas", "Multi-fuel", "Nuclear", "Oil"]
PANELS = [("operating", "Operating fleet"), ("planned_all", "Planned fleet")]
BAR_W = 0.25
AXES_TOP, AXES_H = 0.28, 2.35
LABEL_H = 0.12  # extra height for the three-line tick labels


def tick_label(t, fleet, fuel, label):
    """Fuel label with the fuel-class capacity (GW) and number of units."""
    r = t[(t.fleet == fleet) & (t.group == fuel)]
    if r.empty:
        return label
    r = r.drop_duplicates("group")
    gw, n = float(r["gw_total"].iloc[0]), int(r["n_units"].iloc[0])
    return f"{label}\n{gw:.1f} GW\nn={n}"


def main():
    t = read_csv("w3_table1.csv")
    t = t[(t["threshold"] == THRESHOLD) & t["group"].isin(FUELS)
          & t["fleet"].isin([f for f, _ in PANELS])]
    fig_h = AXES_TOP + AXES_H + LABEL_H + 0.40
    fig = plt.figure(figsize=(W2, fig_h))
    axes = [place_axes(fig, 0.50, AXES_TOP, 3.22, AXES_H),
            place_axes(fig, 3.80, AXES_TOP, 3.22, AXES_H)]
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
                ax.text(xi, v + 1.5, f"{v:.0f}%", ha="center", va="bottom", fontsize=FS_SMALL - 0.7,
                        rotation=90)
        for xi, f in zip(x, FUELS):
            if t[(t.fleet == fleet) & (t.group == f)].empty:
                ax.text(xi, -5, "n/a", ha="center", va="center", fontsize=FS_TICK, style="italic",
                        color="gray")
        ax.axhline(0, color="black", lw=1.0, zorder=4)
        ax.set_ylim(-10, 118)
        ax.set_xlim(-0.6, len(FUELS) - 0.4)
        ax.set_xticks(x)
        ax.set_xticklabels([tick_label(t, fleet, f, lab) for f, lab in zip(FUELS, FUEL_LABEL)],
                           fontsize=FS_SMALL)
        ax.grid(True, axis="y", ls=":", alpha=0.4, zorder=0)
        ax.set_title(title, fontsize=FS_PANEL, weight="bold", pad=3)
        if k == 0:
            ax.legend(title="Scenario", loc="upper left", fontsize=FS_SMALL, title_fontsize=FS_SMALL)
        else:
            ax.set_yticklabels([])
    assert n_bars == {"operating": 18, "planned_all": 12}, n_bars
    fig_text(fig, 0.13, AXES_TOP + AXES_H / 2,
             "Capacity with >=30 TX35 days/yr (%)",
             rotation=90, fontsize=FS_TICK, ha="center", va="center")
    save_figure(fig, "fig6_thermal_heat_by_fuel.png")


if __name__ == "__main__":
    main()
