"""Fig 5a (hydropower, main) and Fig 5b (water-dependent thermal, supplementary): extreme heat x extreme
drought co-exposure by state, 3 scenarios (D133, D139, D149, D151, Phase 9).

Source: w3h_state_coexposure.csv, null block12, co_class co_extreme (heat class extreme AND drought
class extreme, same GCM), operating fleet, Itaipu Brazilian share (hydro). Colour = share of the state's
own operating capacity (median across 5 GCMs, five discrete classes); hollow circles = capacity (GW,
median) under both extremes, area proportional to GW (the thermal figure uses a larger GW scale, stated
in the caption); hatched states have no capacity of the technology, dotted states have 3 plants or fewer.
Circles sit on the state label point; labels move away from the circles. Map standard of
article_map_utils; the CSV state join is unchanged (Natural Earth states, D155), only the drawing uses GADM.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import SCEN, SCEN_LABEL, read_csv, save_figure
from _maps import DEG_PER_PT, map_figure, map_legend
from article_map_utils import place_state_labels
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

BOUNDS = [-0.001, 0.001, 25, 50, 75, 100.001]
LABELS = ["0%", ">0-25%", ">25-50%", ">50-75%", ">75-100%"]
COLORS = ["#fff5f0", "#fcbba1", "#fb6a4a", "#de2d26", "#a50f15"]
LOW_N = 3
FIGS = [
    dict(name="fig5a_state_coexposure_hydro.png", group="hydro", itaipu="b", n_states=19, k=40.0,
         sizes=(1, 5, 20), title="Hydro: share of state capacity under both extremes"),
    dict(name="fig5b_state_coexposure_thermal.png", group="thermal_water_dependent", itaipu="na",
         n_states=26, k=120.0, sizes=(0.5, 1, 3), title="Thermal: share of state capacity under both extremes"),
]


def class_color(p):
    return COLORS[int(np.digitize(p, BOUNDS[1:-1], right=False))] if p > 0.001 else COLORS[0]


def state_table(d, group, itaipu, s):
    x = d[(d.group == group) & (d.fleet == "operating") & (d.itaipu == itaipu) & (d["null"] == "block12")
          & (d.co_class == "co_extreme") & (d.scenario == s) & (d.gw_total > 0)]
    return x.set_index("state_postal")


def build(spec, d):
    fig, axes, adm1, adm0 = map_figure()
    cent = adm1.set_index("postal")[["cx", "cy"]]
    for ax, s in zip(axes, SCEN):
        v = state_table(d, spec["group"], spec["itaipu"], s)
        assert v.index.nunique() == spec["n_states"], (spec["group"], len(v))
        assert abs(v["gw_total"].sum() - (102.667 if spec["group"] == "hydro" else 39.1015)) < 1e-3
        sub = adm1[adm1["postal"].isin(v.index)]
        sub.plot(ax=ax, color=[class_color(v.loc[p, "pct_median"]) for p in sub["postal"]],
                 edgecolor="#555555", linewidth=0.5, zorder=2)
        adm1[~adm1["postal"].isin(v.index)].plot(ax=ax, facecolor="#d9d9d9", edgecolor="#888888", hatch="///",
                                                 linewidth=0.4, zorder=2)
        adm1[adm1["postal"].isin(v.index[v["n_plants"] <= LOW_N])].plot(
            ax=ax, facecolor="none", edgecolor="#333333", hatch="....", linewidth=0, zorder=3)
        g = v[v["gw_median"] > 0]
        area = spec["k"] * g["gw_median"].to_numpy()
        x, y = cent.loc[g.index, "cx"].to_numpy(), cent.loc[g.index, "cy"].to_numpy()
        ax.scatter(x, y, s=area, facecolor="none", edgecolor="white", linewidth=2.2, zorder=7)
        ax.scatter(x, y, s=area, facecolor="none", edgecolor="black", linewidth=0.8, zorder=8)
        dark = {p: "white" for p in v.index if v.loc[p, "pct_median"] > 50}
        place_state_labels(ax, adm1, adm0, x, y, area, DEG_PER_PT, colors=dark)
        n_hi = int((v["pct_median"] > 50).sum())
        ax.set_title(f"{SCEN_LABEL[s]} ({n_hi}/{len(v)} states >50%)", fontsize=12, weight="bold", pad=6)
    h = [Patch(fc=c, ec="#555555", lw=0.4, label=lab) for c, lab in zip(COLORS, LABELS)]
    h += [Patch(fc="#d9d9d9", ec="#888888", hatch="///", lw=0.4, label="No capacity"),
          Patch(fc="white", ec="#333333", hatch="....", lw=0.4, label=f"<= {LOW_N} plants")]
    h += [Line2D([0], [0], marker="o", ls="", mfc="none", mec="black", mew=0.8,
                 ms=2 * np.sqrt(spec["k"] * g_ / np.pi), label=f"{g_:g} GW") for g_ in spec["sizes"]]
    map_legend(fig, h, len(h), title=spec["title"], handlelength=3.4, columnspacing=1.4)
    save_figure(fig, spec["name"], journal_width=False)
    plt.close(fig)


def main():
    d = read_csv("w3h_state_coexposure.csv")
    for spec in FIGS:
        build(spec, d)


if __name__ == "__main__":
    main()
