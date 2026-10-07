"""Fig 5a/5b: state choropleth of co-located extreme heat and extreme drought (D133).

Source: w3h_state_coexposure.csv, null block12 (headline, precedent
scripts/w3h_state_coexposure.py:347-350), co_class co_extreme (heat extreme AND drought
extreme, same GCM), operating fleet. States without capacity are gray and hatched.
"""

import matplotlib

matplotlib.use("Agg")
from _common import FOOT, SCEN, fig_text, place_axes, read_csv, save_figure
from _maps import map_figure
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize

FIG_H = 7.63
VMAX = 20.0
CBAR_LABEL = "Median share of capacity under combined extreme heat + extreme drought (%)"


def state_figure(fname, group, itaipu, suptitle, label, n_expected):
    d = read_csv("w3h_state_coexposure.csv")
    d = d[(d.group == group) & (d.fleet == "operating") & (d.itaipu == itaipu)
          & (d["null"] == "block12") & (d.co_class == "co_extreme")]
    n_states = d[d.gw_total > 0].state_postal.nunique()
    assert n_states == n_expected, n_states  # handoff section 7: 19 hydro / 26 thermal

    fig, axes, adm1 = map_figure(FIG_H, 1.58, suptitle)
    norm = Normalize(0, VMAX)
    for ax, s in zip(axes, SCEN):
        v = d[(d.scenario == s) & (d.gw_total > 0)].set_index("state_postal")["pct_median"]
        has = adm1["postal"].isin(v.index)
        assert has.sum() == n_expected
        sub = adm1[has].assign(v=adm1.loc[has, "postal"].map(v))
        sub.plot(ax=ax, column="v", cmap="Reds", norm=norm, edgecolor="#555555", linewidth=0.7,
                 zorder=2)
        adm1[~has].plot(ax=ax, facecolor="#d9d9d9", edgecolor="#888888", hatch="///",
                        linewidth=0.7, zorder=2)
    cax = place_axes(fig, 6.29, 6.26, 4.73, 0.24)
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap="Reds"), cax=cax, orientation="horizontal")
    cb.set_label(CBAR_LABEL, fontsize=9.5)
    note = (f"Gray/hatched states have no {label} capacity (n={n_expected} states with capacity). "
            "Null: block-bootstrap-12. Co-extreme = heat class extreme AND drought class extreme, "
            "same GCM.")
    fig_text(fig, 0.1, 7.48, note, **FOOT)
    save_figure(fig, fname)
