"""Fig 1: TX35 heat class raster (0.5 deg grid) + thermal plant markers, 3 scenarios (D133).

Sources: w3g_heat_cell_class.csv (class_median per cell and scenario), plants.parquet
x plant_cell.parquet. Thermal plants only (hydro is outside H1, precedent
scripts/archive/w3_heat_levels.py:43). A marker is red when its cell is extreme.
"""

import matplotlib

matplotlib.use("Agg")
import numpy as np
from _common import BASELINE_FUTURE, CLASS_COLOR, CLASS_ORDER, FOOT, SCEN, SCEN_COLOR, THERMAL_MARKER_SCALE, brazil_plants, fig_text, marker_size, read_csv, save_figure
from _maps import map_figure
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

THERMAL = ["thermal_water_dependent", "thermal_air_only"]
STEP = 0.5
MARK = {"thermal_water_dependent": "o", "thermal_air_only": "D"}
NOTE = ("Background = cell-level heat exposure class (median across 5 GCMs). Markers = thermal "
        "plant location, sized by capacity (MW), colored red if located in a cell classified "
        "extreme. Hydropower excluded (not part of heat hazard definition, H1).")
FIG_H = 8.6


def raster(cc):
    """Class code grid (NaN where the 0.5 deg grid has no cell) and its cell edges."""
    lats = np.arange(cc.cell_lat.min(), cc.cell_lat.max() + STEP / 2, STEP)
    lons = np.arange(cc.cell_lon.min(), cc.cell_lon.max() + STEP / 2, STEP)
    code = cc.assign(code=cc["class_median"].map({c: i for i, c in enumerate(CLASS_ORDER)}))
    grid = (code.pivot(index="cell_lat", columns="cell_lon", values="code")
            .reindex(index=lats, columns=lons))
    return grid, np.append(lons - STEP / 2, lons[-1] + STEP / 2), \
        np.append(lats - STEP / 2, lats[-1] + STEP / 2)


def main():
    plants = brazil_plants()
    th = plants[(plants["country"] == "BRA") & plants["tech_class"].isin(THERMAL)]
    cc_all = read_csv("w3g_heat_cell_class.csv")
    assert len(th) == 745 and th["cell_lat"].notna().all(), len(th)  # join without orphans

    fig, axes, _ = map_figure(FIG_H, 1.31, "Projected TX35 Heat Exposure Classification, Brazil\n"
                              + BASELINE_FUTURE)
    cmap = ListedColormap([CLASS_COLOR[c] for c in CLASS_ORDER])
    n_extreme = {}
    for ax, s in zip(axes, SCEN):
        cc = cc_all[cc_all["scenario"] == s]
        grid, lon_e, lat_e = raster(cc)
        ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(grid.values), cmap=cmap, vmin=-0.5,
                      vmax=3.5, zorder=1, rasterized=True)
        m = th.merge(cc[["cell_lat", "cell_lon", "class_median"]], on=["cell_lat", "cell_lon"],
                     how="left")
        assert len(m) == 745 and m["class_median"].notna().all()
        m["extreme"] = m["class_median"] == "extreme"
        n_extreme[s] = int(m["extreme"].sum())
        m = m.assign(area=marker_size(m["capacity_mw"], THERMAL_MARKER_SCALE)).sort_values("area", ascending=False)
        for tech, mk in MARK.items():
            for ext in (False, True):
                d = m[(m.tech_class == tech) & (m.extreme == ext)]
                ax.scatter(d["lon"], d["lat"], s=d["area"], marker=mk,
                           c=SCEN_COLOR["ssp585"] if ext else SCEN_COLOR["ssp126"],
                           edgecolors="black", linewidths=0.4, alpha=0.9, zorder=6)
    assert n_extreme["ssp585"] == 340, n_extreme  # check_headlines.py (Fig 1)

    blue, red = SCEN_COLOR["ssp126"], SCEN_COLOR["ssp585"]
    h1 = [Line2D([0], [0], marker="o", ls="", mfc=blue, mec="black", ms=8,
                 label="Water-dependent thermal (not extreme)"),
          Line2D([0], [0], marker="D", ls="", mfc=blue, mec="black", ms=7,
                 label="Air-cooled thermal (not extreme)"),
          Line2D([0], [0], marker="o", ls="", mfc=red, mec="black", ms=8,
                 label="Plant in extreme-heat cell")]
    leg1 = fig.legend(handles=h1, loc="center", bbox_to_anchor=(0.5, 1 - 7.35 / FIG_H), ncol=3,
                      fontsize=10)
    fig.add_artist(leg1)
    h2 = [Patch(fc=CLASS_COLOR[c], label=c.capitalize()) for c in CLASS_ORDER]
    fig.legend(handles=h2, loc="center", bbox_to_anchor=(0.5, 1 - 7.8 / FIG_H), ncol=4,
               title="Cell heat class (background)", fontsize=10)
    fig_text(fig, 0.1, 8.43, NOTE, **FOOT)
    save_figure(fig, "fig1_heat_class_map.png")


if __name__ == "__main__":
    main()
