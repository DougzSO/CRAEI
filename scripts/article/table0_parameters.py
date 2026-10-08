"""Table 0: framework parameters (article/tables/table0_parameters.{csv,md}).

Numeric parameters come from config/params.yaml; descriptive entries (model
list, periods, inventory cutoff, Itaipu convention) follow Methods Spec and
docs/HANDOFF_v46.md section 2. Planned hydro capacity is computed from plant_units.
"""

import pandas as pd
from _common import SCEN_LABEL, country_iso, md_table, out_dir, params, processed_dir, write_csv, write_text

GCMS = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL"]
ITAIPU_TOTAL_MW, ITAIPU_BRAZIL_MW = 14000, 7000  # scripts/th1_fleet_gw.py:73, heat_levels.py:43
GEM_CUTOFF = "2026-08-09"


def main():
    p = params()
    u = pd.read_parquet(processed_dir() / "plant_units.parquet")
    ph = u[(u["country"] == country_iso()) & (u["tech_class"] == "hydro")
           & u["fleet"].isin(["planned_adv", "planned_early"])]
    n, adv, early = len(ph), ph[ph.fleet == "planned_adv"].capacity_mw.sum(), \
        ph[ph.fleet == "planned_early"].capacity_mw.sum()
    assert n == 28, n
    scen = ", ".join(SCEN_LABEL.values())
    rows = [
        ("GCMs (n=5)", ", ".join(GCMS)),
        ("Baseline period", "1985-2014 (model-native historical)"),
        ("Future period", "2041-2070"),
        ("Scenarios", scen),
        ("Bias adjustment", "W5E5 v2.0, ISIMIP3BASD v2.5.0"),
        ("Itaipu capacity (b, headline)", f"{ITAIPU_BRAZIL_MW:,} MW (Brazil share)"),
        ("Itaipu capacity (a, sensitivity)", f"{ITAIPU_TOTAL_MW:,} MW (full binational plant)"),
        ("Planned hydro units", f"{n} units: {adv:,.0f} MW advanced-stage + {early:,.0f} MW early-stage"),
        ("Heat thresholds", f"TX{p['heat_tx35_threshold_c']}, TX{p['heat_tx40_threshold_c']} (deg C)"),
        ("Drought threshold (SPEI)", f"SPEI <= {p['drought_spei_threshold']}"),
        ("Drought exposure ratio", f"R_D >= {p['drought_class_rd_ratio']:.1f} (future F_D / baseline F_D)"),
        ("SPEI clipping range", f"[-{p['spei_clip_bound']}, {p['spei_clip_bound']}]"),
        ("GEM inventory cutoff", GEM_CUTOFF),
        ("Bootstrap n (CI, production default)", f"{p['n_boot']:,}"),
        ("Bootstrap n (robustness check only, W3d/W3f-3)",
         "5,000 (C80/D126; not the project default)"),
    ]
    df = pd.DataFrame(rows, columns=["Parameter", "Value"])
    d = out_dir("tables")
    write_csv(df, d / "table0_parameters.csv")
    write_text(d / "table0_parameters.md",
               "# Table 0 -- Framework Parameters\n\n" + md_table(df) + "\n")


if __name__ == "__main__":
    main()
