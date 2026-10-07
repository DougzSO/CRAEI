"""Fig 7: E1, hydrothermal hedge failure, Design A (D140-D143, D153).

(a) Observed D (W5E5 1986-2014, block-12 CI) against the five GCM baseline D values, for the control
pair (hydro SPI x thermal SPI) and the heat pair (hydro SPI x thermal heat); (b) change of P(H and T)
from baseline to future (variant A) for the control pair: median marginal and dependence components
and the five GCM totals; (c) D by macro_region, thermal capacity restricted to the region against
national hydro. Sources: e1_hedge_observed.csv, e1_hedge_metrics.csv, e1_hedge_delta.csv,
e1_hedge_summary.csv, e1_colocation.csv. Operating thermal fleet, 618 plants, 39.1015 GW.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from _common import SCEN, SCEN_LABEL, place_axes, read_csv, save_figure
from _style import FS_PANEL, FS_SMALL, FS_TICK, W2
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

PAIRS = [("spi", "SPI x SPI (control)"), ("heat", "SPI x heat")]
REGION = {"Sudeste": "Southeast", "Centro-Oeste": "Center-West", "Nordeste": "Northeast",
          "Norte": "North", "Sul": "South"}
C_OBS, C_GCM, C_MARG, C_DEP = "#111111", "#8c8c8c", "#4575b4", "#f46d43"
AXES_TOP, AXES_H = 0.30, 2.10


def panel_a(ax, obs, met):
    for i, (tc, label) in enumerate(PAIRS):
        o = obs[(obs.t_channel == tc)].iloc[0]
        g = met[(met.t_channel == tc)]["D"].to_numpy()
        y = i
        ax.plot(g, y + np.linspace(-0.12, 0.12, len(g)), "D", ms=3.0, mfc="white", mec=C_GCM, mew=0.7,
                zorder=3)
        ax.plot([np.median(g)] * 2, [y - 0.22, y + 0.22], color=C_GCM, lw=1.4, zorder=2)
        ax.plot([o.D_lo_b12, o.D_hi_b12], [y + 0.32] * 2, color=C_OBS, lw=1.5, solid_capstyle="butt")
        ax.plot(o.D, y + 0.32, "o", ms=3.8, mfc=C_OBS, mec="black", zorder=4)
        ax.text(o.D_hi_b12 + 0.15, y + 0.32, f"{o.D:.2f}", va="center", fontsize=FS_TICK)
    ax.axvline(1, color="black", lw=0.6, ls="--", zorder=1)
    ax.set_yticks([0, 1])
    ax.set_yticklabels([p[1] for p in PAIRS])
    ax.set_ylim(2.55, -0.45)
    ax.set_xlim(0, 10.2)
    ax.set_xlabel("D (1 = independence)")
    ax.grid(True, axis="x", ls=":", alpha=0.4)
    ax.legend(handles=[Line2D([0], [0], marker="o", color=C_OBS, ms=3.5, lw=1.5, label="Observed (95% CI)"),
                       Line2D([0], [0], marker="D", ls="", mfc="white", mec=C_GCM, ms=3, label="GCM baseline"),
                       Line2D([0], [0], color=C_GCM, lw=1.4, label="GCM median")],
              loc="lower right", fontsize=FS_SMALL - 0.3, frameon=True, framealpha=0.9)


def panel_b(ax, delta, summ):
    x = np.arange(3)
    for j, s in enumerate(SCEN):
        r = summ[summ.scenario == s].iloc[0]
        marg, dep = r.median_dP_marginal, r.median_dP_dependence
        ax.bar(j, marg, 0.55, color=C_MARG, ec="black", lw=0.4, zorder=3)
        ax.bar(j, dep, 0.55, bottom=marg, color=C_DEP, ec="black", lw=0.4, zorder=3)
        g = delta[delta.scenario == s]["dP_HT_A"].to_numpy()
        ax.plot(j + np.linspace(-0.16, 0.16, len(g)), np.sort(g), "o", ms=2.6, mfc="white", mec="black",
                mew=0.6, zorder=5)
        ax.plot([j - 0.33, j + 0.33], [r.median_dP_HT_A] * 2, color="black", lw=1.4, zorder=6)
        ax.text(j, max(g.max(), marg + dep) + 0.012, f"{r.median_dP_HT_A:+.3f}", ha="center",
                fontsize=FS_TICK)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([SCEN_LABEL[s] for s in SCEN])
    ax.set_ylabel("Change in P(H and T)")
    ax.set_ylim(-0.04, 0.25)
    ax.grid(True, axis="y", ls=":", alpha=0.4)
    ax.legend(handles=[Patch(fc=C_MARG, ec="black", lw=0.4, label="Marginals"),
                       Patch(fc=C_DEP, ec="black", lw=0.4, label="Dependence"),
                       Line2D([0], [0], color="black", lw=1.4, label="Total (median)"),
                       Line2D([0], [0], marker="o", ls="", mfc="white", mec="black", ms=2.6,
                              label="Single GCM")],
              loc="upper left", fontsize=FS_SMALL, frameon=True, framealpha=0.9)


def panel_c(ax, col, nat_d):
    reg = col[col.region != "ALL"].sort_values("gw", ascending=False).reset_index(drop=True)
    for i, r in reg.iterrows():
        ax.plot([r.gcm_D_min, r.gcm_D_max], [i - 0.2] * 2, color=C_GCM, lw=1.0, solid_capstyle="butt")
        ax.plot([r.gcm_D_median] * 2, [i - 0.32, i - 0.08], color=C_GCM, lw=1.4)
        ax.plot([r.obs_D_lo, r.obs_D_hi], [i + 0.18] * 2, color=C_OBS, lw=1.5, solid_capstyle="butt")
        ax.plot(r.obs_D, i + 0.18, "o", ms=3.6, mfc=C_OBS, mec="black", zorder=4)
    ax.axvline(1, color="black", lw=0.6, ls="--", zorder=1)
    ax.axvline(nat_d, color=C_OBS, lw=0.6, ls=":", zorder=1)
    ax.set_yticks(range(len(reg)))
    ax.set_yticklabels([f"{REGION[r.region]}\n{r.gw:.1f} GW, n={int(r.n_plants)}"
                        for r in reg.itertuples()])
    ax.set_ylim(len(reg) + 1.25, -0.55)
    ax.set_xlim(0, 11)
    ax.set_xlabel("D (SPI x SPI)")
    ax.grid(True, axis="x", ls=":", alpha=0.4)
    ax.legend(handles=[Line2D([0], [0], color=C_GCM, lw=1.0, label="GCM baseline range"),
                       Line2D([0], [0], color=C_GCM, lw=1.4, marker="|", ms=5, label="GCM median"),
                       Line2D([0], [0], marker="o", color=C_OBS, ms=3.4, lw=1.5, label="Observed (95% CI)"),
                       Line2D([0], [0], color=C_OBS, lw=0.6, ls=":", label="National observed D"),
                       Line2D([0], [0], color="black", lw=0.6, ls="--", label="D = 1")],
              loc="lower right", fontsize=FS_SMALL - 0.4, frameon=True, framealpha=0.9, handlelength=1.6)


def main():
    obs = read_csv("e1_hedge_observed.csv")
    obs = obs[(obs.fleet == "operating") & (obs.h_channel == "spi") & obs.t_channel.isin(["spi", "heat"])]
    assert len(obs) == 2
    met = read_csv("e1_hedge_metrics.csv")
    met = met[(met.fleet == "operating") & (met.h_channel == "spi") & met.t_channel.isin(["spi", "heat"])
              & (met.variant == "B") & (met.period == "baseline") & (met.block == 12)]
    assert met.groupby("t_channel").size().eq(5).all()
    delta = read_csv("e1_hedge_delta.csv")
    delta = delta[(delta.fleet == "operating") & (delta.h_channel == "spi") & (delta.t_channel == "spi")
                  & (delta.block == 12)]
    summ = read_csv("e1_hedge_summary.csv")
    summ = summ[(summ.fleet == "operating") & (summ.h_channel == "spi") & (summ.t_channel == "spi")]
    col = read_csv("e1_colocation.csv")
    o_spi = obs[obs.t_channel == "spi"].iloc[0]
    assert abs(o_spi.D - 4.8294) < 1e-3
    assert abs(summ[summ.scenario == "ssp585"].median_dP_HT_A.iloc[0] - 0.095) < 1e-3
    assert abs(col[col.region == "ALL"].gw.iloc[0] - 39.1015) < 1e-2

    fig_h = AXES_TOP + AXES_H + 0.40
    fig = plt.figure(figsize=(W2, fig_h))
    ax_a = place_axes(fig, 0.95, AXES_TOP, 1.30, AXES_H)
    ax_b = place_axes(fig, 3.00, AXES_TOP, 1.50, AXES_H)
    ax_c = place_axes(fig, 5.55, AXES_TOP, 1.50, AXES_H)
    panel_a(ax_a, obs, met)
    panel_b(ax_b, delta, summ)
    panel_c(ax_c, col, o_spi.D)
    ax_a.set_title("(a) Observed against GCMs", fontsize=FS_PANEL, weight="bold", loc="left", pad=3)
    ax_b.set_title("(b) Joint stress, SPI x SPI", fontsize=FS_PANEL, weight="bold", loc="left", pad=3)
    ax_c.set_title("(c) Macro-regions", fontsize=FS_PANEL, weight="bold", loc="left", pad=3)
    save_figure(fig, "fig7_e1_hedge.png")


if __name__ == "__main__":
    main()
