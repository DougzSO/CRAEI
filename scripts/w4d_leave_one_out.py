"""W4d: leave-one-out of the 5 largest Brazilian operating hydro plants (D113, O19, D135).

Metric (drought, not heat): share of the bucket's operating capacity with R_D >= 2.0
(`ratio` of hazard f_d_spei12 in plant_hazards.parquet), capacity-weighted, median over
the 5 GCMs. Raw share, no null (differs from the D102 excess-over-null headline).
Logic and filters follow scripts/c23d_checks.py:445-487 (item 7), which produced the
earlier w4d_leave_one_out.csv with Itaipu as a whole asset (version a, 14,000 MW).
This script writes both Itaipu versions: b (Brazilian share, 7,000 MW, headline,
D102) and a (whole asset, sensitivity).

Usage: python scripts/w4d_leave_one_out.py [--out DIR]   (default: outputs_tables_dir)
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from craei.config import load_params, load_paths
from craei.hazards import drought_levels as dl
from craei.inventory.fleet import apply_foreign_share

COUNTRY = "BRA"
BUCKETS = ["hydro_reservoir", "hydro_run_of_river"]
SCENARIOS = ["ssp126", "ssp370", "ssp585"]
ITAIPU_TOTAL_MW, ITAIPU_FOREIGN_MW = 14000.0, 7000.0  # scripts/th1_fleet_gw.py:73, heat_levels.py:43
N_TOP = 5


def share(hz, fleet):
    """Median over GCMs of the capacity share (%) of `fleet` with R_D >= threshold."""
    rd = load_params()["drought_class_rd_ratio"]["value"]
    cap = fleet.set_index("plant_uid")["capacity_mw"]
    out = []
    for _, g in hz[hz.plant_uid.isin(cap.index)].groupby("model"):
        s = g.set_index("plant_uid")["ratio"].reindex(cap.index)
        exposed = (s >= rd).fillna(False)
        out.append(100 * cap.where(exposed, 0.0).sum() / cap.sum())
    return float(np.median(out)) if out else np.nan


def build(plants, hazards):
    itaipu = dl.find_plant(plants, COUNTRY, "itaipu", ITAIPU_TOTAL_MW)
    versions = {"a": plants,
                "b": apply_foreign_share(plants, itaipu, ITAIPU_TOTAL_MW, ITAIPU_FOREIGN_MW)}
    rows = []
    for ver, pl in versions.items():
        bra = pl[pl["country"] == COUNTRY]
        hydro_op = bra[(bra["tech_class"] == "hydro") & (bra["fleet"] == "operating")]
        top = hydro_op.nlargest(N_TOP, "capacity_mw")
        for bucket in BUCKETS:
            uids = set(hazards[(hazards.bucket == bucket)
                               & (hazards.hazard == "f_d_spei12")]["plant_uid"])
            full = bra[(bra["fleet"] == "operating") & bra["plant_uid"].isin(uids)]
            for scen in SCENARIOS:
                hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")
                             & (hazards.scenario == scen)]
                s_full = share(hz, full)
                for _, p in top.iterrows():
                    if p["plant_uid"] not in set(full["plant_uid"]):
                        continue
                    s_loo = share(hz, full[full["plant_uid"] != p["plant_uid"]])
                    rows.append(dict(itaipu=ver, bucket=bucket, scenario=scen,
                                     plant_removed=p["plant_name"],
                                     capacity_mw=p["capacity_mw"], share_full_pct=s_full,
                                     share_loo_pct=s_loo, delta_pp=s_loo - s_full))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    paths = load_paths()
    proc = Path(paths["processed_dir"])
    plants = pd.read_parquet(proc / "plants.parquet")
    hazards = pd.read_parquet(proc / "plant_hazards.parquet")
    t = build(plants, hazards)
    assert len(t) == 30, len(t)  # 2 versions x (3 + 2 plants) x 3 scenarios
    ref = pd.read_csv(Path(paths["outputs_tables_dir"]) / "w4d_leave_one_out.csv")
    a = t[t.itaipu == "a"].drop(columns="itaipu").reset_index(drop=True)
    num = ["capacity_mw", "share_full_pct", "share_loo_pct", "delta_pp"]
    if len(ref) == len(a):  # regression of version a against the C23d audit output
        gap = float(np.abs(a[num].to_numpy() - ref[num].to_numpy()).max())
        assert gap < 1e-9, gap
        print("version a reproduces the previous w4d_leave_one_out.csv, max |diff|", gap)
    out = Path(args.out) if args.out else Path(paths["outputs_tables_dir"])
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "w4d_leave_one_out.csv", index=False, encoding="utf-8", lineterminator="\n")
    print("written:", out / "w4d_leave_one_out.csv")


if __name__ == "__main__":
    main()
