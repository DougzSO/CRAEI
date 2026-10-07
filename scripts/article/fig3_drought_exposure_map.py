"""Fig 3: drought exposure map (R_D >= 2.0), 3 scenarios (D133).

Source: w4g_fd_unit_values.csv (plant x GCM x scenario, ratio = future F_D / baseline F_D)
joined to plants.parquet. A plant is exposed when its median ratio over the 5 GCMs is
>= 2.0. Marker shape = technology, size = capacity.
"""

import matplotlib

matplotlib.use("Agg")
import pandas as pd
from _common import BASELINE_FUTURE, FOOT, SCEN, SCEN_COLOR, THERMAL_MARKER_SCALE, fig_text, marker_size, params, processed_dir, read_csv, save_figure
from _maps import map_figure
from matplotlib.lines import Line2D

MARK = {"hydro": "o", "thermal_water_dependent": "D", "thermal_air_only": "^"}
NOTE = ("Marker shape = technology; marker size proportional to capacity (MW). Exposed = R_D >= "
        "2.0 (ratio of future-to-baseline frequency of SPEI <= -1.5).")
FIG_H = 8.05
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

    fig, axes, _ = map_figure(FIG_H, 1.31, "Projected Drought Exposure (SPEI-12 Frequency Ratio), "
                              "Brazil\n" + BASELINE_FUTURE)
    for ax, s in zip(axes, SCEN):
        d = m[m.scenario == s].copy()
        d["area"] = marker_size(d["capacity_mw"]).where(
            d["tech_class"] == "hydro", marker_size(d["capacity_mw"], THERMAL_MARKER_SCALE))
        d = d.sort_values("area", ascending=False)
        for tech, mk in MARK.items():
            for exp in (False, True):
                x = d[(d.tech_class == tech) & (d.exposed == exp)]
                ax.scatter(x["lon"], x["lat"], s=x["area"], marker=mk,
                           c=SCEN_COLOR["ssp585"] if exp else SCEN_COLOR["ssp126"],
                           edgecolors="black", linewidths=0.4, alpha=0.85, zorder=6)
    blue, red = SCEN_COLOR["ssp126"], SCEN_COLOR["ssp585"]
    h = [Line2D([0], [0], marker="o", ls="", mfc="gray", mec="black", ms=8, label="Hydro"),
         Line2D([0], [0], marker="D", ls="", mfc="gray", mec="black", ms=7,
                label="Water-dep. thermal"),
         Line2D([0], [0], marker="^", ls="", mfc="gray", mec="black", ms=8,
                label="Air-cooled thermal"),
         Line2D([0], [0], marker="o", ls="", mfc=blue, mec="black", ms=8,
                label=f"Not exposed (R_D < {rd:.1f})"),
         Line2D([0], [0], marker="o", ls="", mfc=red, mec="black", ms=8,
                label=f"Exposed (R_D >= {rd:.1f})")]
    fig.legend(handles=h, loc="center", bbox_to_anchor=(0.5, 1 - 7.35 / FIG_H), ncol=5,
               fontsize=10)
    fig_text(fig, 0.1, 7.87, NOTE, **FOOT)
    save_figure(fig, "fig3_drought_exposure_map.png")


if __name__ == "__main__":
    main()
