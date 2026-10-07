"""Fig 8: E3, association of the drought index with observed natural inflow (ONS ENA), D144-D147, D153.

(a) Spearman rho between regional W5E5 SPEI-12 (hydro capacity weighted) and the standardized monthly
ENA anomaly, lag 0-6 months (index at t-L), 2000-2019, block-12 bootstrap CI; the shaded band marks the
lags of the pre-specified criterion (0-3). (b) Hit rate at lag 0: lift of P(ENA <= P20 | SPEI-12 <= -1.5)
over the 20% base rate with block-12 CI; regions with fewer than 10 signal months are not reportable.
Sources: e3_spearman.csv, e3_hit_rate.csv. Regions are macro_region approximations of the ONS submarkets.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from _common import place_axes, read_csv, save_figure
from _style import FS_PANEL, FS_SMALL, W2
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

GROUPS = ["SE/CO", "S", "NE", "N"]
COLOR = {"SE/CO": "#d95f02", "S": "#7570b3", "NE": "#1b9e77", "N": "#e7298a"}
AXES_TOP, AXES_H = 0.30, 2.20


def main():
    sp = read_csv("e3_spearman.csv")
    sp = sp[sp["index"] == "SPEI_12"]
    hr = read_csv("e3_hit_rate.csv")
    hr = hr[(hr["index"] == "SPEI_12") & (hr["lag"] == 0)].set_index("group")
    assert len(sp) == 28 and len(hr) == 4
    se = sp[(sp.group == "SE/CO") & (sp.lag == 0)].iloc[0]
    assert abs(se.rho - 0.370) < 1e-3 and se.n == 240 and se.ci_lo > 0
    assert int(hr.loc["S", "n_signal"]) == 2 and not bool(hr.loc["S", "reportable"])

    fig_h = AXES_TOP + AXES_H + 0.40
    fig = plt.figure(figsize=(W2, fig_h))
    ax_a = place_axes(fig, 0.55, AXES_TOP, 3.55, AXES_H)
    ax_b = place_axes(fig, 4.65, AXES_TOP, 2.35, AXES_H)

    ax_a.axvspan(-0.4, 3.4, color="#999999", alpha=0.12, lw=0, zorder=0)
    for k, g in enumerate(GROUPS):
        d = sp[sp.group == g].sort_values("lag")
        x = d["lag"].to_numpy() + (k - 1.5) * 0.11
        ax_a.errorbar(x, d["rho"], yerr=[d["rho"] - d["ci_lo"], d["ci_hi"] - d["rho"]], fmt="o-",
                      ms=2.8, lw=0.8, elinewidth=0.8, capsize=1.2, color=COLOR[g], zorder=3)
    ax_a.axhline(0, color="black", lw=0.6)
    ax_a.set_xlim(-0.5, 6.5)
    ax_a.set_ylim(-0.3, 1.2)
    ax_a.set_yticks([-0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax_a.set_xticks(range(7))
    ax_a.set_xlabel("Lag (months)")
    ax_a.set_ylabel("Spearman rho")
    ax_a.grid(True, axis="y", ls=":", alpha=0.4)
    cap = sp[sp.lag == 0].set_index("group")
    handles = [Line2D([0], [0], marker="o", color=COLOR[g], ms=3, lw=0.8,
                      label=f"{g}: {cap.loc[g, 'gw']:.1f} GW, n={int(cap.loc[g, 'n_plants'])}")
               for g in GROUPS]
    handles.append(Patch(fc="#999999", alpha=0.25, label="Lags 0-3 (criterion)"))
    ax_a.legend(handles=handles, loc="upper right", fontsize=FS_SMALL, frameon=True, framealpha=0.9)
    ax_a.set_title("(a) Association by lag", fontsize=FS_PANEL, weight="bold", loc="left", pad=3)

    for i, g in enumerate(GROUPS):
        r = hr.loc[g]
        if bool(r["reportable"]):
            ax_b.plot([r.lift_lo, r.lift_hi], [i, i], color=COLOR[g], lw=1.6, solid_capstyle="butt")
            ax_b.plot(r.lift, i, "o", ms=4.2, mfc=COLOR[g], mec="black", mew=0.5, zorder=3)
            ax_b.text(1.25, i - 0.30, f"{int(r.n_signal)} signal months, HSS {r.HSS:.2f}", va="center",
                      fontsize=FS_SMALL)
        else:
            ax_b.text(1.25, i, f"not reportable ({int(r.n_signal)} signal months)", va="center",
                      fontsize=FS_SMALL, style="italic", color="#555555")
    ax_b.axvline(1, color="black", lw=0.6, ls="--")
    ax_b.set_yticks(range(len(GROUPS)))
    ax_b.set_yticklabels(GROUPS)
    ax_b.set_ylim(len(GROUPS) - 0.5, -0.5)
    ax_b.set_xlim(0, 8)
    ax_b.set_xlabel("Lift over base rate (1 = no skill)")
    ax_b.grid(True, axis="x", ls=":", alpha=0.4)
    ax_b.set_title("(b) Hit rate at lag 0", fontsize=FS_PANEL, weight="bold", loc="left", pad=3)
    save_figure(fig, "fig8_e3_ena.png")


if __name__ == "__main__":
    main()
