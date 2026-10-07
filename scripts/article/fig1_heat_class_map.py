"""Fig 1: TX35 heat class raster (0.5 deg grid) + thermal plant markers, 3 scenarios (D133, Phase 9).

Sources: w3g_heat_cell_class.csv (class_median per cell and scenario), plants.parquet
x plant_cell.parquet. Thermal plants only (hydro is outside H1, precedent
scripts/archive/w3_heat_levels.py:43). Marker shape = technology (diamond water-dependent, triangle air-cooled),
marker colour = heat exposure class of the plant's cell; the raster uses the same class colours, cells
without data are transparent. Map standard of article_map_utils; no suptitle, no note.
"""

import matplotlib

matplotlib.use("Agg")
import numpy as np
from _common import CLASS_COLOR, CLASS_ORDER, SCEN, SCEN_LABEL, THERMAL_MARKER_SCALE, brazil_plants, marker_size, read_csv, save_figure
from _maps import DEG_PER_PT, map_figure, map_legend
from article_map_utils import place_state_labels
from matplotlib.colors import ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

THERMAL = ["thermal_water_dependent", "thermal_air_only"]
STEP = 0.5
MARK = {"thermal_water_dependent": "D", "thermal_air_only": "^"}
CMAP = ListedColormap([CLASS_COLOR[c] for c in CLASS_ORDER])


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

    fig, axes, adm1, adm0 = map_figure()
    n_extreme = {}
    for ax, s in zip(axes, SCEN):
        cc = cc_all[cc_all["scenario"] == s]
        m = th.merge(cc[["cell_lat", "cell_lon", "class_median"]], on=["cell_lat", "cell_lon"], how="left")
        assert len(m) == 745 and m["class_median"].notna().all()
        n_extreme[s] = int((m["class_median"] == "extreme").sum())
        grid, lon_e, lat_e = raster(cc)
        ax.pcolormesh(lon_e, lat_e, np.ma.masked_invalid(grid.values), cmap=CMAP, vmin=-0.5, vmax=3.5,
                      zorder=1, rasterized=True)
        m = m.assign(area=marker_size(m["capacity_mw"], THERMAL_MARKER_SCALE)).sort_values(
            "area", ascending=False)
        for tech, mk in MARK.items():
            for cls in CLASS_ORDER:
                d = m[(m.tech_class == tech) & (m.class_median == cls)]
                ax.scatter(d["lon"], d["lat"], s=d["area"], marker=mk, c=CLASS_COLOR[cls],
                           edgecolors="black", linewidths=0.4, alpha=0.85, zorder=6)
        place_state_labels(ax, adm1, adm0, m["lon"], m["lat"], m["area"], DEG_PER_PT)
        ax.set_title(f"{SCEN_LABEL[s]} ({n_extreme[s]}/{len(m)} extreme)", fontsize=12, weight="bold", pad=6)
    assert n_extreme["ssp585"] == 340, n_extreme  # check_headlines.py (Fig 1)

    h = [Line2D([0], [0], marker="D", ls="", mfc="gray", mec="black", ms=7, label="Water-dep. thermal"),
         Line2D([0], [0], marker="^", ls="", mfc="gray", mec="black", ms=8, label="Air-cooled thermal")]
    h += [Patch(fc=CLASS_COLOR[c], ec="black", lw=0.4, label=f"{c.capitalize()} heat") for c in CLASS_ORDER]
    map_legend(fig, h, 6)
    save_figure(fig, "fig1_heat_class_map.png", journal_width=False)


if __name__ == "__main__":
    main()
