"""W3h / ST1: GW in extreme heat by state and macro-region (D88 M10; METHODS_SPEC ST1).

Scope of this script: heat only (ST1). Co-exposure by state (ST2) is separate,
pending review of w4_drought_levels.py.

Aborts before writing if (a) total capacity_mw does not match the input units
after state assignment (no loss/duplication); (b) per (group, fleet, itaipu,
scenario, model, class), the sum of MW over states does not match the national
total from the existing w3g_heat_level_classes.csv pipeline (checked PRE-median,
per GCM -- median is not additive, D80/D96/D97).
"""

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

from craei.config import load_paths
from craei.exposure import heat_levels as hl
from craei.exposure.heat_fuel import add_pooled_planned
from craei.geo.state_assignment import add_macro_region, assign_state

COUNTRY, TOL = "BRA", 1e-6
KEEP = ("hydro", "thermal_water_dependent", "thermal_air_only")
THERMAL_GROUPS = ("all_thermal",) + hl.TECH_THERMAL + hl.FUELS
STATE_KEYS = ["group", "fleet", "itaipu", "scenario", "state_postal", "macro_region"]


def find_itaipu(plants):
    named = plants[(plants["country"] == COUNTRY)
                   & plants["plant_name"].str.contains("itaipu", case=False, na=False)]
    big = named[(named["capacity_mw"] - 14000.0).abs() < 1e-6]
    if len(big) != 1:
        raise SystemExit("Itaipu not uniquely identified")
    return set(big["plant_uid"])


def load_macro_map(config_dir=None):
    path = (config_dir or Path("config")) / "params.yaml"
    with open(path, encoding="utf-8") as f:
        params = yaml.safe_load(f)
    return params["brazil_macroregion_map"]["value"]


def state_gw_by_gcm(df, class_col, categories):
    """MW per (state keys, class, model); zero-filled grid, same pattern as hl.gw_by_gcm."""
    keys = STATE_KEYS + ["model", class_col]
    g = df.groupby(keys, observed=True)["capacity_mw"].sum().rename("mw").reset_index()
    g[class_col] = g[class_col].astype(str)
    grid = df[STATE_KEYS + ["model"]].drop_duplicates()
    grid = grid.merge(pd.DataFrame({class_col: list(categories)}), how="cross")
    out = grid.merge(g, on=keys, how="left")
    out["mw"] = out["mw"].fillna(0.0)
    return out


def summarise_state_gw(t, class_col):
    """min/median/max over GCMs of GW, per state, class (median not additive: D80)."""
    keys = [k for k in STATE_KEYS if True] + [class_col]
    out = t.groupby(keys).agg(
        n_gcm=("model", "nunique"),
        gw_min=("mw", "min"), gw_median=("mw", "median"), gw_max=("mw", "max"),
    ).reset_index()
    for c in ("gw_min", "gw_median", "gw_max"):
        out[c] = out[c] / 1000.0
    return out


def check_capacity_parity(units_in, assigned):
    a = float(units_in["capacity_mw"].sum())
    b = float(assigned["capacity_mw"].sum())
    diff = abs(a - b)
    print(f"check (a) capacity parity: input {a:.3f} MW, assigned {b:.3f} MW, "
          f"diff {diff:.2e}")
    return diff < TOL


def check_national_parity(g_state, g_national, class_col):
    """Sum over states (per GCM) must equal the national per-GCM MW, pre-median."""
    keys = ["group", "fleet", "itaipu", "scenario", "model", class_col]
    nat = g_national.groupby(keys, observed=True)["capacity_mw"].sum().rename("mw_nat")
    st = g_state.groupby(keys, observed=True)["capacity_mw"].sum().rename("mw_state")
    m = pd.concat([nat, st], axis=1).fillna(0.0)
    diff = float((m["mw_nat"] - m["mw_state"]).abs().max())
    print(f"check (b) state sum vs national (pre-median, per GCM): "
          f"rows {len(m)}, max|diff| {diff:.2e}")
    return diff < 1e-3  # MW; looser than TOL because of float accumulation over many groups


def main():
    paths = load_paths()
    proc, tab = Path(paths["processed_dir"]), Path(paths["outputs_tables_dir"])

    units = pd.read_parquet(proc / "plant_units.parquet")
    units = units[(units["country"] == COUNTRY) & units["tech_class"].isin(KEEP)]
    units = units.reset_index(drop=True)
    units["uid"] = units.index

    plants = pd.read_parquet(proc / "plants.parquet",
                             columns=["plant_uid", "plant_name", "country",
                                      "capacity_mw", "lat", "lon"])
    bra_plants = plants[plants["country"] == COUNTRY]

    uv = hl.with_itaipu_versions(units, find_itaipu(plants))
    pc = pd.read_parquet(proc / "plant_cell.parquet",
                         columns=["plant_uid", "cell_lat", "cell_lon"])
    c = ["index", "cell_lat", "cell_lon", "model", "scenario", "period", "value"]
    ix = pd.read_parquet(proc / "indices_daily.parquet", columns=c,
                         filters=[("index", "==", "tx35")])
    cv = hl.cell_values(ix)
    del ix
    d = hl.add_classes(hl.unit_values(uv, pc, cv))

    admin1 = gpd.read_file(r"..\data\external\geo\natural_earth_brazil.gpkg",
                           layer="brazil_admin1")
    assigned = assign_state(bra_plants, admin1, lat_col="lat", lon_col="lon",
                            uid_col="plant_uid")
    macro_map = load_macro_map()
    assigned = add_macro_region(assigned, macro_map, postal_col="state_postal")
    n_fallback = int(assigned["nearest_fallback"].sum())
    print(f"state assignment: {len(assigned)} plants, {n_fallback} via nearest fallback")

    if not check_capacity_parity(bra_plants, assigned):
        print("CHECK FAILED (a): nothing written")
        sys.exit(1)

    d_state = d.merge(
        assigned[["plant_uid", "state_postal", "macro_region", "nearest_fallback"]],
        on="plant_uid", how="left")
    if d_state["state_postal"].isna().any():
        print("CHECK FAILED: unit rows without a state after merge")
        sys.exit(1)

    g_national = hl.expand_groups(add_pooled_planned(d))
    g_state = hl.expand_groups(add_pooled_planned(d_state))

    cats = list(hl.LEVEL_LABELS)
    ok_b = check_national_parity(g_state, g_national, "level_fut")
    if not ok_b:
        print("CHECK FAILED (b): nothing written")
        sys.exit(1)
    print("checks (a)-(b): PASS")

    t = state_gw_by_gcm(g_state, "level_fut", cats)
    out = summarise_state_gw(t, "level_fut")
    out = out[out["level_fut"] == "extreme"].rename(columns={"level_fut": "class"})
    out.to_csv(tab / "w3h_state_summary.csv", index=False)
    print(f"written: w3h_state_summary.csv ({len(out)} rows)")

    headline = out[(out["group"] == "all_thermal") & (out["fleet"] == "operating")
                  & (out["itaipu"] == "na") & (out["scenario"] == "ssp585")]
    print("\nall_thermal operating ssp585, extreme class, GW median by state:")
    print(headline[["state_postal", "macro_region", "gw_median"]]
          .sort_values("gw_median", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
