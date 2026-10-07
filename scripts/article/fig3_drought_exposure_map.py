"""Fig 3: drought exposure map (R_D >= 2.0), 3 scenarios, map standard of article_map_utils (D133, Phase 9).

Source: w4g_fd_unit_values.csv (plant x GCM x scenario, ratio = future F_D / baseline F_D)
joined to plants.parquet. A plant is exposed when its median ratio over the 5 GCMs is
>= 2.0. Marker shape = technology, size = capacity (C87 marker sizes). Panel titles give the number of
exposed plants. No suptitle and no note (both in docs/article/drafts/results.md). 17 x 7 in working size.
"""

import matplotlib

matplotlib.use("Agg")
import pandas as pd
from _common import SCEN, SCEN_COLOR, SCEN_LABEL, THERMAL_MARKER_SCALE, marker_size, params, processed_dir, read_csv, save_figure
from _maps import DEG_PER_PT, map_figure, map_legend
from article_map_utils import place_state_labels
from matplotlib.lines import Line2D

MARK = {"hydro": "o", "thermal_water_dependent": "D", "thermal_air_only": "^"}
NOT_EXPOSED = "#2b6cb0"  # blue of the C87 figure (ref. _ref_C87), not the scenario blue
EXPECT = {"ssp126": 339, "ssp370": 433, "ssp585": 770}  # check_headlines.py (Fig 3)


def main():
    rd = params()["drought_class_rd_ratio"]
    fd = read_csv("w4g_fd_unit_values.csv")
    plants = pd.read_parquet(processed_dir() / "plants.parquet")
    med = fd.groupby(["scenario", "plant_uid"], as_index=False)["ratio"].median()
    m = med.merge(plants[["plant_uid", "lat", "lon", "tech_class", "capacity_mw"]],
                  on="plant_uid", how="left")
    assert m["lat"].notna().all() and m["tech_class"].isin(MARK).all()  # join without orphans
    m["exposed"] = m["ratio"] >= rd
    got = m.groupby("scenario")["exposed"].sum().astype(int).to_dict()
    assert got == EXPECT, got

    fig, axes, adm1, adm0 = map_figure()
    for ax, s in zip(axes, SCEN):
        d = m[m.scenario == s].copy()
        d["area"] = marker_size(d["capacity_mw"]).where(
            d["tech_class"] == "hydro", marker_size(d["capacity_mw"], THERMAL_MARKER_SCALE))
        d = d.sort_values("area", ascending=False)
        for tech, mk in MARK.items():
            for exp in (False, True):
                x = d[(d.tech_class == tech) & (d.exposed == exp)]
                ax.scatter(x["lon"], x["lat"], s=x["area"], marker=mk,
                           c=SCEN_COLOR["ssp585"] if exp else NOT_EXPOSED,
                           edgecolors="black", linewidths=0.4, alpha=0.85, zorder=6)
        place_state_labels(ax, adm1, adm0, d["lon"], d["lat"], d["area"], DEG_PER_PT)
        ax.set_title(f"{SCEN_LABEL[s]} ({int(d['exposed'].sum())}/{len(d)} exposed)", fontsize=12,
                     weight="bold", pad=6)
    blue, red = NOT_EXPOSED, SCEN_COLOR["ssp585"]
    h = [Line2D([0], [0], marker="o", ls="", mfc="gray", mec="black", ms=8, label="Hydro"),
         Line2D([0], [0], marker="D", ls="", mfc="gray", mec="black", ms=7, label="Water-dep. thermal"),
         Line2D([0], [0], marker="^", ls="", mfc="gray", mec="black", ms=8, label="Air-cooled thermal"),
         Line2D([0], [0], marker="o", ls="", mfc=blue, mec="black", ms=8, label=f"Not exposed (R_D < {rd:.1f})"),
         Line2D([0], [0], marker="o", ls="", mfc=red, mec="black", ms=8, label=f"Exposed (R_D >= {rd:.1f})")]
    map_legend(fig, h, 5)
    save_figure(fig, "fig3_drought_exposure_map.png", journal_width=False)


if __name__ == "__main__":
    main()
