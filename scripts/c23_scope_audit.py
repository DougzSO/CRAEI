"""COMANDO 23 Blocos A-E: scope audit (data inventory, feasibility, geography, governance, file inventory).

Read-only except for outputs_audit_dir/c23/. Reads config/c23_audit.yaml for
frozen criteria (not config/params.yaml -- see that file's header for why).
Does not call craei.config.load_params().
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from craei.config import load_datasets, load_paths  # noqa: E402

paths = load_paths()
datasets = load_datasets()
AUDIT = yaml.safe_load(open(ROOT / "config" / "c23_audit.yaml", encoding="utf-8"))
SA = AUDIT["scope_audit"]
TS = AUDIT["threshold_sweeps"]

PROC = Path(paths["processed_dir"])
TABLES = Path(paths["outputs_dir"]) / "tables"
OUT = Path(paths["outputs_dir"]) / "audit" / "c23"
OUT.mkdir(parents=True, exist_ok=True)

REPORT = []  # list of markdown strings, Blocos A-E
UNKNOWN = "desconhecido"


def h(title, level=2):
    REPORT.append(f"{'#' * level} {title}\n")


def p(text):
    REPORT.append(text + "\n")


def df_to_md(df, max_rows=60):
    """Manual pipe-table formatter (tabulate not installed, not allowed to add packages)."""
    shown = df.head(max_rows)
    cols = [str(c) for c in shown.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in shown.iterrows():
        vals = []
        for v in row:
            if isinstance(v, float):
                vals.append(f"{v:.4g}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    out = "\n".join(lines) + "\n"
    if len(df) > max_rows:
        out += f"\n(+{len(df) - max_rows} more rows, see CSV)\n"
    return out


# ---------------------------------------------------------------------
# Load core tables
# ---------------------------------------------------------------------
plants = pd.read_parquet(PROC / "plants.parquet")
plant_cell = pd.read_parquet(PROC / "plant_cell.parquet")
catchment_w = pd.read_parquet(PROC / "catchment_weights.parquet")
hazards = pd.read_parquet(PROC / "plant_hazards.parquet")
aqueduct = pd.read_parquet(PROC / "plant_aqueduct.parquet")
exposure_summary = pd.read_csv(TABLES / "exposure_summary.csv")
exposure_aqueduct = pd.read_csv(TABLES / "exposure_aqueduct.csv")
compound = pd.read_csv(TABLES / "compound.csv")

MODELS = datasets["models"]
# datasets["scenarios"] includes "historical" (the baseline forcing run); plant_hazards.parquet
# only carries the 3 future SSPs (baseline/future are columns, not scenario rows, for the
# hazards actually computed) -- SCENARIOS here is the future-SSP set used throughout this script.
SCENARIOS = [s for s in datasets["scenarios"] if s != "historical"]
N_MODELS = len(MODELS)

h("COMANDO 23 -- C23 scope audit report (Blocos A-E)", level=1)
p(f"Generated read-only from processed/ and outputs/tables/ as of this run. "
  f"Frozen criteria: `config/c23_audit.yaml` (scope_audit.version={SA['version']}).")
p("**Achado de Bloco 0 (registro):** o bloco aditivo original em `config/params.yaml` quebrou "
  "`craei.config.load_params()` (exige `value`/`tier`/`source` em toda chave de topo), derrubando "
  "7 testes (`test_config`, `test_exposure_aggregate` x5, `test_hazards_consolidate`). Revertido "
  "no commit `916b7ec`; critérios movidos para `config/c23_audit.yaml`, lido diretamente via "
  "`yaml.safe_load`, sem passar por `load_params()`. Suíte voltou a 141 passed / 1 skipped.")

# =======================================================================
# BLOCO A -- Data inventory
# =======================================================================
h("Bloco A -- Inventário de dados", level=1)

# --- Item 1: fleet table ---------------------------------------------
h("1. Frota", level=2)

fleet_tbl = (
    plants.groupby(["country", "tech_class", "fleet"], as_index=False)
    .agg(n_plants=("plant_uid", "count"), gw=("capacity_mw", "sum"))
)
fleet_tbl["gw"] = fleet_tbl["gw"] / 1000.0
med_max = (
    plants.groupby(["country", "tech_class", "fleet"])["capacity_mw"]
    .agg(median_mw="median", max_mw="max")
    .reset_index()
)
fleet_tbl = fleet_tbl.merge(med_max, on=["country", "tech_class", "fleet"])

country_gw = plants.groupby("country")["capacity_mw"].sum() / 1000.0
country_fleet_gw = plants.groupby(["country", "fleet"])["capacity_mw"].sum() / 1000.0

fleet_tbl["share_of_country_gw_pct"] = fleet_tbl.apply(
    lambda r: 100 * (r["gw"] * 1000 / 1000) / country_gw[r["country"]] if country_gw[r["country"]] > 0 else np.nan,
    axis=1,
)
fleet_tbl["share_of_country_fleet_gw_pct"] = fleet_tbl.apply(
    lambda r: 100 * r["gw"] / country_fleet_gw[(r["country"], r["fleet"])]
    if country_fleet_gw.get((r["country"], r["fleet"]), 0) > 0
    else np.nan,
    axis=1,
)
fleet_tbl = fleet_tbl.sort_values(["country", "fleet", "tech_class"])
fleet_tbl.to_csv(OUT / "c23_1_fleet.csv", index=False)

p("Tecnologias presentes em `plants.parquet` (GEM já filtra `wind` e `geothermal` em "
  "`_TYPE_EXCLUDED`, `src/craei/inventory/plants.py`, antes deste ponto -- portanto eólica "
  "**não existe em nenhuma tabela processada do pipeline**, não apenas fora da matriz de "
  "hazards): " + ", ".join(sorted(plants["tech_class"].unique())) + ".")
p("**Status GEM mapeado para frota** (`_STATUS_TO_FLEET`): operating<-operating; "
  "planned_adv<-construction,pre-construction; planned_early<-announced. Excluídos antes do "
  "inventário: shelved, shelved-inferred, cancelled, cancelled-inferred, mothballed, retired.")

h("Brasil", level=3)
p(df_to_md(fleet_tbl[fleet_tbl.country == "BRA"].drop(columns=["country"])))
h("Índia e Portugal", level=3)
p(df_to_md(fleet_tbl[fleet_tbl.country != "BRA"]))

# out-of-scope share: solar is IN plants.parquet (H4 only); wind is excluded
# upstream of plants.parquet entirely. Quantifying wind's out-of-scope GW
# requires the raw GEM file (read-only, no hazard recompute) since it is not
# in plants.parquet by construction.
gem_path = Path(paths["gem_file"])
wind_summary = None
if gem_path.exists():
    try:
        gem_raw = pd.read_excel(gem_path, sheet_name="Power facilities")
        iso_by_name = {"Brazil": "BRA", "India": "IND", "Portugal": "PRT"}
        gem_raw = gem_raw[gem_raw["Country/area"].isin(iso_by_name)].copy()
        gem_raw["iso3"] = gem_raw["Country/area"].map(iso_by_name)
        type_norm = gem_raw["Type"].astype(str).str.strip().str.lower()
        status_norm = gem_raw["Status"].astype(str).str.strip().str.lower()
        status_ok = status_norm.isin(
            {"operating", "construction", "pre-construction", "announced"}
        )
        wind_rows = gem_raw[(type_norm == "wind") & status_ok & gem_raw["Capacity (MW)"].notna()]
        wind_summary = (
            wind_rows.groupby("iso3")["Capacity (MW)"].agg(["count", "sum"]).rename(
                columns={"count": "n_plants", "sum": "gw"}
            )
        )
        wind_summary["gw"] = wind_summary["gw"] / 1000.0
    except Exception as exc:  # noqa: BLE001
        wind_summary = f"ERROR reading raw GEM file: {exc}"
else:
    wind_summary = f"GEM raw file not found at {gem_path}"

out_of_scope_gw_solar = plants[plants.tech_class == "solar_pv"].groupby("country")["capacity_mw"].sum() / 1000.0

p("**Parcela fora do escopo (item 1):**")
p("- Solar (dentro de `plants.parquet`, só recebe H4, não entra na matriz de viabilidade "
  "principal H1/H2/H3): " + ", ".join(f"{c}={v:.3f} GW" for c, v in out_of_scope_gw_solar.items()) + ".")
if isinstance(wind_summary, pd.DataFrame):
    p("- Eólica (excluída no inventário, reconstruída aqui a partir do GEM bruto, mesmo filtro "
      "de país/status do pipeline, leitura read-only, nenhum hazard recomputado): " +
      ", ".join(f"{c}={r.gw:.3f} GW ({int(r.n_plants)} usinas)" for c, r in wind_summary.iterrows()) + ".")
else:
    p(f"- Eólica: {wind_summary}")

# --- Item 2: hazards by bucket -----------------------------------------
h("2. Hazards por bucket", level=2)

bucket_hazard = (
    hazards.groupby(["bucket", "hazard"], as_index=False)
    .agg(
        n_valid=("plant_uid", lambda s: s[hazards.loc[s.index, "future_value"].notna()].nunique()),
        n_rows=("plant_uid", "count"),
        n_future_na=("future_value", lambda s: s.isna().sum()),
    )
)
bucket_hazard["state"] = np.where(
    bucket_hazard["n_future_na"] == 0, "computed_and_aggregated", "computed_partial_or_na"
)
bucket_hazard.to_csv(OUT / "c23_2_hazards.csv", index=False)
p(df_to_md(bucket_hazard))

p("**Aplicabilidade por bucket (Methods Spec §1.4, linha 382):** TX35/TX40 (H1) aplicam-se aos "
  "dois buckets térmicos (thermal_water_dependent, thermal_air_only). SPEI-12 catchment-scale "
  "(H2, F_D/R_D) aplica-se a hydro_reservoir e hydro_run_of_river; SPEI-3 catchment-scale é "
  "adicional (não substituto) só para hydro_run_of_river. Para thermal_water_dependent, H2 é "
  "SPEI-12 **cell-scale** (não catchment), já que a térmica não tem bacia hidrográfica própria -- "
  "usa a célula ISIMIP ligada à planta (`plant_cell.parquet`) diretamente, sem `catchment_weights`. "
  "H3 (Aqueduct) só se aplica a thermal_water_dependent com `cooling_bound=upper` (freshwater "
  "assumido) -- fora de `plant_hazards.parquet`, em `plant_aqueduct.parquet`. H4 (p95 "
  "exceedance ratio, Rx5day) aplica-se a todos os 5 buckets, incluindo solar.")
p("Buckets em `plant_hazards.parquet`: " + ", ".join(sorted(hazards["bucket"].unique())) + ". "
  "`f_d_spei3` só existe para hydro_run_of_river (confirmar abaixo).")
spei3_buckets = sorted(hazards[hazards.hazard == "f_d_spei3"]["bucket"].unique())
p(f"Buckets com `f_d_spei3`: {spei3_buckets}.")

# item 2b
h("2b. Natureza de cada coluna de hazard", level=3)
col_nature = pd.DataFrame(
    [
        {"column": "baseline_value/future_value (TX35,TX40)", "type": "continuous (day count)",
         "threshold": "TX>=35C / TX>=40C (fixed, not swept in production)"},
        {"column": "baseline_value/future_value (f_d_spei12, f_d_spei3)", "type": "continuous (F_D fraction)",
         "threshold": "SPEI<=-1.5 (per Methods; production threshold is fixed)"},
        {"column": "delta/ratio", "type": "continuous (F_D difference / R_D ratio)", "threshold": "n/a"},
        {"column": "h4_p95_ratio", "type": "continuous (exceedance frequency ratio)",
         "threshold": "baseline wet-day p95, 5% by construction"},
        {"column": "h4_rx5day_pct_change", "type": "continuous (% change)", "threshold": "n/a"},
        {"column": "exposure_summary.csv share columns", "type": "binary at aggregation time",
         "threshold": "plant counted exposed iff its own F_D/TX/H4 metric crosses the Methods §2 "
                       "operational threshold per bucket -- the per-plant binary flag itself is "
                       "not a stored column, it is computed inside craei.exposure.aggregate from "
                       "the continuous plant_hazards.parquet columns"},
    ]
)
col_nature.to_csv(OUT / "c23_2b_column_nature.csv", index=False)
p(df_to_md(col_nature))
p("Todas as colunas numéricas em `plant_hazards.parquet` são **contínuas**; nenhuma coluna "
  "binária é persistida lá. O limiar é aplicado só na agregação (`exposure_summary.csv`), não "
  "em `plant_hazards.parquet` -- portanto não há custo de rederivação a partir de `spei.parquet` "
  "para mudar um limiar: os valores contínuos (F_D, R_D) já existem por planta/modelo/cenário; "
  "só a contagem de exceedance na agregação muda. Rederivar F_D/R_D em si (a partir de "
  "`spei.parquet`) exigiria reajustar a distribuição SPEI por série, custo relatado no item 4 "
  "(curvas), não feito aqui.")

es_check = exposure_summary[["median_share", "min_share", "max_share", "median_gw", "min_gw", "max_gw"]].describe()
p("`exposure_summary.csv` reporta `median_share`/`median_gw` -- checagem de unidade: "
  f"correlação share vs (gw/country_gw) não recomputada aqui (exigiria juntar por país, feito no "
  f"item 4 gate de reprodução). Colunas presentes: {exposure_summary.columns.tolist()}.")
p("A mediana entre GCMs é calculada **sobre a fração** (share), não a fração da mediana bruta "
  "em GW dividida por outro número: `median_share` e `median_gw` são columns irmãs produzidas "
  "do mesmo `median()` por linha de `(country,tech_class,fleet,scenario,hazard)` sobre os 5 "
  "modelos -- ambas agregam por contagem/GW de planta, não por bucket ponderado por outra coisa; "
  "confirmado pelos nomes de coluna, não recomputado aqui (recomputar é o portão de reprodução "
  "do item 4).")

# =======================================================================
# BLOCO B -- Feasibility (viability matrix + threshold curves + baseline)
# =======================================================================
h("Bloco B -- Viabilidade", level=1)
h("3. Matriz de viabilidade", level=2)

p("**Critério de classificação, interpretação aplicada (não especificada literalmente no "
  "COMANDO, registrada aqui para revisão):** `class_quant = \"excluido\"` se `sample_fail` "
  "(n_plants < min_plants OU effective_n < min_effective_n) OU `materiality_fail` "
  "(fleet_share_pct < min_fleet_share_pct); senão `\"suporte\"` se `saturated` "
  "(median_share <= 5% ou >= 95%) OU `sign_fail` (agreement < min_gcm_sign_agreement/5, só para "
  "H1/H2/H4); senão `\"principal\"`. `class_final` aplica `limitation_downgrade` "
  "(principal->suporte) quando `limitation_flag` está setado. `class_precedence` do "
  "c23_audit.yaml (excluido > suporte > principal) usada literalmente nesta ordem de checagem.")

HAZARD_TO_H = {
    "TX35": "H1", "TX40": "H1",
    "f_d_spei12": "H2", "f_d_spei3": "H2",
    "h4_p95_ratio": "H4", "h4_rx5day_pct_change": "H4",
}
LIMITATION_CELLS = {
    # (country, bucket): reason -- derived from LIMITATIONS.md, not invented here.
    ("IND", "hydro_run_of_river"): "L16 PET truncation, glacial catchments (Himalaya)",
    ("IND", "hydro_reservoir"): "L16 PET truncation, glacial catchments (Himalaya)",
    ("PRT", "thermal_water_dependent"): "L14 mainland-only scope, small n",
}

rows = []
for country in SA["matrix_countries"]:
    for bucket in sorted(hazards["bucket"].unique()):
        if bucket == "solar":
            continue  # out_of_scope_technologies: solar excluded from the viability matrix
        # bucket assignment lives in plant_hazards, not plants.parquet directly
        bucket_plant_uids = set(hazards[hazards.bucket == bucket]["plant_uid"].unique())
        sub_plants = plants[(plants.country == country) & (plants.plant_uid.isin(bucket_plant_uids))]
        if sub_plants.empty:
            continue
        country_gw_total = plants[plants.country == country]["capacity_mw"].sum() / 1000.0
        for fleet in sorted(sub_plants["fleet"].unique()):
            fl_plants = sub_plants[sub_plants.fleet == fleet]
            fleet_gw = fl_plants["capacity_mw"].sum() / 1000.0
            fleet_share_pct = 100 * fleet_gw / country_gw_total if country_gw_total > 0 else np.nan
            for hz in sorted(hazards[hazards.bucket == bucket]["hazard"].unique()):
                hz_rows_all = hazards[
                    (hazards.bucket == bucket) & (hazards.hazard == hz)
                    & hazards.plant_uid.isin(fl_plants.plant_uid)
                ]
                if hz_rows_all.empty:
                    continue
                n_plants = fl_plants.plant_uid.nunique()
                basin_ids = fl_plants["basin_id"].dropna()
                n_basins = basin_ids.nunique() if len(basin_ids) > 0 else np.nan
                cells_catch = catchment_w[catchment_w.plant_uid.isin(fl_plants.plant_uid)][["cell_lat", "cell_lon"]]
                cells_direct = plant_cell[plant_cell.plant_uid.isin(fl_plants.plant_uid)][["cell_lat", "cell_lon"]]
                n_distinct_cells = pd.concat([cells_catch, cells_direct]).drop_duplicates().shape[0]
                if bucket.startswith("hydro"):
                    effective_n = min(n_distinct_cells, n_basins) if not np.isnan(n_basins) else n_distinct_cells
                else:
                    effective_n = n_distinct_cells  # no basin concept for thermal/solar (report n/a)

                # Metric column per hazard (craei.exposure.aggregate.build_exposure_si): H4's
                # h4_p95_ratio is a ratio (threshold 1.0 = no change), h4_rx5day_pct_change and
                # the two TX hazards are a delta (threshold 0 = no change). f_d_spei12/f_d_spei3
                # sign is read off R_D (ratio, threshold 1.0), consistent with the headline H2 use.
                value_col = "ratio" if hz in ("f_d_spei12", "f_d_spei3", "h4_p95_ratio") else "delta"
                h_type = HAZARD_TO_H.get(hz, "other")

                for scenario in sorted(hz_rows_all["scenario"].unique()):
                    hz_rows = hz_rows_all[hz_rows_all.scenario == scenario]
                    vals = hz_rows[value_col].dropna()
                    n_gcm_present = hz_rows["model"].nunique()
                    # per-plant median over models, then fleet capacity share above threshold
                    # reuses the same logic as craei.exposure.aggregate for H1/H2 headline hazards;
                    # for non-headline hazards (TX40, f_d_spei3, H4) there is no Spec class
                    # threshold, so "median_share"/"change vs baseline" is reported descriptively
                    # (fraction of capacity with a positive median delta/ratio-above-1), flagged
                    # clearly as descriptive, not a Spec exposure class.
                    per_model_share = []
                    for model, g in hz_rows.groupby("model"):
                        gp = g.merge(fl_plants[["plant_uid", "capacity_mw"]], on="plant_uid")
                        if hz in ("f_d_spei12", "f_d_spei3"):
                            exposed_mw = gp.loc[gp["ratio"] >= 2.0, "capacity_mw"].sum()  # R_D>=2 descriptive marker
                        elif hz in ("TX35", "TX40"):
                            exposed_mw = gp.loc[gp["delta"] >= 30, "capacity_mw"].sum()  # DeltaTX35>=30 descriptive
                        else:
                            exposed_mw = gp.loc[gp["delta"].fillna(0) > 0, "capacity_mw"].sum() if "h4_rx5day" in hz \
                                else gp.loc[gp["ratio"].fillna(0) > 1, "capacity_mw"].sum()
                        total_mw = gp["capacity_mw"].sum()
                        per_model_share.append(exposed_mw / total_mw if total_mw > 0 else np.nan)
                    per_model_share = pd.Series(per_model_share, dtype=float).dropna()
                    median_share = per_model_share.median() if len(per_model_share) else np.nan
                    min_share = per_model_share.min() if len(per_model_share) else np.nan
                    max_share = per_model_share.max() if len(per_model_share) else np.nan

                    # baseline comparison: median future value vs median baseline value (per model, then median)
                    base_med = hz_rows.groupby("model")["baseline_value"].median().median()
                    fut_med = hz_rows.groupby("model")["future_value"].median().median()
                    change_vs_hist = fut_med - base_med if pd.notna(base_med) and pd.notna(fut_med) else np.nan

                    if h_type in SA["sign_criterion_applies_to"]:
                        per_model_sign = hz_rows.groupby("model")[value_col].median()
                        per_model_sign = per_model_sign.dropna()
                        if len(per_model_sign) > 0:
                            pos = (per_model_sign > (1.0 if value_col == "ratio" else 0.0)).sum()
                            neg = len(per_model_sign) - pos
                            n_gcm_agree = max(pos, neg)
                        else:
                            n_gcm_agree = np.nan
                    else:
                        n_gcm_agree = np.nan  # H3-style N/A (not applicable here since H3 isn't in plant_hazards)

                    sample_fail = (n_plants < SA["min_plants"]) or (
                        pd.notna(effective_n) and effective_n < SA["min_effective_n"]
                    )
                    materiality_fail = pd.notna(fleet_share_pct) and fleet_share_pct < SA["min_fleet_share_pct"]
                    saturated = pd.notna(median_share) and (
                        median_share * 100 <= SA["saturation_low_pct"]
                        or median_share * 100 >= SA["saturation_high_pct"]
                    )
                    sign_fail = (
                        pd.notna(n_gcm_agree) and n_gcm_agree < SA["min_gcm_sign_agreement"]
                    ) if h_type in SA["sign_criterion_applies_to"] else False

                    limitation_reason = LIMITATION_CELLS.get((country, bucket))
                    limitation_flag = limitation_reason is not None

                    if sample_fail or materiality_fail:
                        class_quant = "excluido"
                    elif saturated or sign_fail:
                        class_quant = "suporte"
                    else:
                        class_quant = "principal"
                    class_final = class_quant
                    if class_quant == "principal" and limitation_flag:
                        class_final = "suporte"

                    rows.append(dict(
                        country=country, bucket=bucket, fleet=fleet, hazard=hz, h_type=h_type,
                        scenario=scenario, n_plants=n_plants, n_distinct_cells=n_distinct_cells,
                        n_basins=n_basins, effective_n=effective_n, gw=fleet_gw,
                        fleet_share_pct=fleet_share_pct, median_share=median_share,
                        min_share=min_share, max_share=max_share, change_vs_hist=change_vs_hist,
                        n_gcm_agree=n_gcm_agree, n_gcm_present=n_gcm_present,
                        sample_fail=sample_fail, materiality_fail=materiality_fail,
                        saturated=saturated, sign_fail=sign_fail,
                        limitation_flag=limitation_flag, limitation_reason=limitation_reason,
                        class_quant=class_quant, class_final=class_final,
                    ))

viability = pd.DataFrame(rows)


def _aggregate_rule(group):
    classes = set(group)
    if classes == {"principal"}:
        return "principal"
    if classes == {"excluido"}:
        return "excluido"
    return "suporte"


agg_class = viability.groupby(["country", "bucket", "fleet", "hazard"])["class_final"].apply(_aggregate_rule)
agg_class.name = "class_aggregated_across_scenarios"
viability = viability.merge(agg_class.reset_index(), on=["country", "bucket", "fleet", "hazard"], how="left")
viability.to_csv(OUT / "c23_3_viability_matrix.csv", index=False)

p(f"Matriz gerada: {len(viability)} linhas (país x bucket x frota x hazard x cenário, H3/solar "
  f"excluídos por definição de `out_of_scope_technologies`/H3 não estar em `plant_hazards.parquet`).")
p("Distribuição de `class_final`:")
p(df_to_md(viability["class_final"].value_counts().rename_axis("class_final").reset_index(name="n")))
p("Amostra (Brasil, hydro_reservoir):")
p(df_to_md(viability[(viability.country == "BRA") & (viability.bucket == "hydro_reservoir")].head(12)))

# --- Item 4: threshold curves (BRA only, hydro + thermal) --------------
h("4. Curvas de limiar (Brasil, hidro e térmica)", level=2)

TOL = TS["baseline_reproduction_tolerance_pp"]
bra_plants = plants[plants.country == "BRA"]
bucket_of = hazards.drop_duplicates("plant_uid")[["plant_uid", "bucket"]].set_index("plant_uid")["bucket"]


def _capacity_share(fl_plants_df, value_series_by_model, threshold, op=">="):
    """Median (over models) capacity share with value crossing threshold, given
    {model: Series(plant_uid -> value)}."""
    shares = []
    for model, s in value_series_by_model.items():
        s = s.reindex(fl_plants_df.plant_uid)
        exposed = (s >= threshold) if op == ">=" else (s <= threshold)
        exposed_mw = fl_plants_df.set_index("plant_uid")["capacity_mw"].where(exposed.fillna(False), 0.0)
        total_mw = fl_plants_df["capacity_mw"].sum()
        shares.append(exposed_mw.sum() / total_mw if total_mw > 0 else np.nan)
    return float(np.median(shares)) if shares else np.nan


# --- 4a. Reproduction gate at the base point (ΔTX35=30, SPEI=-1.5, R_D=2) --
p("**Portão de reprodução (base: ΔTX35=30, SPEI=-1,5, R_D=2):**")
gate_rows = []
for scenario in SCENARIOS:
    for bucket in ["thermal_water_dependent", "thermal_air_only"]:
        fl = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(
            hazards[(hazards.bucket == bucket) & (hazards.hazard == "TX35")]["plant_uid"]
        )]
        if fl.empty:
            continue
        hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "TX35") & (hazards.scenario == scenario)
                      & hazards.plant_uid.isin(fl.plant_uid)]
        by_model = {m: g.set_index("plant_uid")["delta"] for m, g in hz.groupby("model")}
        my_share = _capacity_share(fl, by_model, 30.0, ">=")
        ref = exposure_summary[
            (exposure_summary.country == "BRA") & (exposure_summary.tech_class == bucket)
            & (exposure_summary.fleet == "operating") & (exposure_summary.scenario == scenario)
            & (exposure_summary.hazard == "TX35")
        ]
        ref_share = ref["median_share"].iloc[0] if len(ref) else np.nan
        gate_rows.append(dict(bucket=bucket, hazard="TX35", scenario=scenario, fleet="operating",
                               recomputed_share=my_share, reference_share=ref_share,
                               diff_pp=abs((my_share - ref_share) * 100) if pd.notna(ref_share) and pd.notna(my_share) else np.nan))

for scenario in SCENARIOS:
    for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
        fl = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(
            hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")]["plant_uid"]
        )]
        if fl.empty:
            continue
        hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12") & (hazards.scenario == scenario)
                      & hazards.plant_uid.isin(fl.plant_uid)]
        by_model = {m: g.set_index("plant_uid")["ratio"] for m, g in hz.groupby("model")}
        my_share = _capacity_share(fl, by_model, 2.0, ">=")
        ref = exposure_summary[
            (exposure_summary.country == "BRA") & (exposure_summary.tech_class == bucket)
            & (exposure_summary.fleet == "operating") & (exposure_summary.scenario == scenario)
            & (exposure_summary.hazard == "f_d_spei12")
        ]
        ref_share = ref["median_share"].iloc[0] if len(ref) else np.nan
        gate_rows.append(dict(bucket=bucket, hazard="f_d_spei12", scenario=scenario, fleet="operating",
                               recomputed_share=my_share, reference_share=ref_share,
                               diff_pp=abs((my_share - ref_share) * 100) if pd.notna(ref_share) and pd.notna(my_share) else np.nan))

gate_df = pd.DataFrame(gate_rows)
gate_df["pass"] = gate_df["diff_pp"] <= TOL
gate_df.to_csv(OUT / "c23_4_reproduction_gate.csv", index=False)
p(df_to_md(gate_df))
gate_pass = bool(gate_df["pass"].all()) if len(gate_df) else False
p(f"**Gate geral: {'PASSA' if gate_pass else 'FALHA'}** (tolerância {TOL} pp). "
  f"Nota: para ΔTX35 e R_D, a reprodução é exata por construção -- estou reaplicando o mesmo "
  f"filtro de classificação (`delta>=30`, `ratio>=2`) sobre as mesmas colunas já persistidas em "
  f"`plant_hazards.parquet`/`exposure_summary.csv`, não recomputando a partir de dados brutos; "
  f"qualquer diferença acima da tolerância indicaria um bug na minha replicação da regra de "
  f"agregação de `craei.exposure.aggregate`, não uma divergência real de dados.")

curve_rows = []
grid2d_rows = []

if gate_pass:
    # --- 4b. heat_dtx35_days sweep (thermal only; no recompute needed --
    # already have delta in plant_hazards) ---
    sweep = TS["heat_dtx35_days"]
    thresholds = np.arange(sweep["start"], sweep["stop"] + 0.01, sweep["step"])
    for bucket in ["thermal_water_dependent", "thermal_air_only"]:
        fl = bra_plants[bra_plants.plant_uid.isin(
            hazards[(hazards.bucket == bucket) & (hazards.hazard == "TX35")]["plant_uid"]
        )]
        if fl.empty:
            continue
        for fleet in ["operating", "planned_adv", "planned_early"]:
            fl_f = fl[fl.fleet == fleet]
            if fl_f.empty:
                continue
            for scenario in SCENARIOS:
                hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "TX35") & (hazards.scenario == scenario)
                              & hazards.plant_uid.isin(fl_f.plant_uid)]
                by_model = {m: g.set_index("plant_uid")["delta"] for m, g in hz.groupby("model")}
                for th in thresholds:
                    curve_rows.append(dict(
                        curve="heat_dtx35_days", country="BRA", bucket=bucket, fleet=fleet,
                        scenario=scenario, threshold=float(th),
                        median_share=_capacity_share(fl_f, by_model, th, ">="),
                    ))
    p(f"Curva `heat_dtx35_days`: 0-90 dias passo 5, thermal_water_dependent + thermal_air_only, "
      f"Brasil, sem recompute (reusa `delta` já em `plant_hazards.parquet`). hydro N/A (H1 não "
      f"se aplica a hidro, Methods Spec §1.4).")

    # --- 4c. drought_rd_ratio sweep (hydro + thermal_water; no recompute needed) ---
    sweep = TS["drought_rd_ratio"]
    thresholds = np.arange(sweep["start"], sweep["stop"] + 0.001, sweep["step"])
    for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
        fl = bra_plants[bra_plants.plant_uid.isin(
            hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")]["plant_uid"]
        )]
        if fl.empty:
            continue
        for fleet in ["operating", "planned_adv", "planned_early"]:
            fl_f = fl[fl.fleet == fleet]
            if fl_f.empty:
                continue
            for scenario in SCENARIOS:
                hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12") & (hazards.scenario == scenario)
                              & hazards.plant_uid.isin(fl_f.plant_uid)]
                by_model = {m: g.set_index("plant_uid")["ratio"] for m, g in hz.groupby("model")}
                for th in thresholds:
                    curve_rows.append(dict(
                        curve="drought_rd_ratio", country="BRA", bucket=bucket, fleet=fleet,
                        scenario=scenario, threshold=float(th),
                        median_share=_capacity_share(fl_f, by_model, th, ">="),
                    ))
    p("Curva `drought_rd_ratio`: 1,0-4,0 passo 0,25, hydro_reservoir + hydro_run_of_river + "
      "thermal_water_dependent, Brasil, sem recompute (reusa `ratio`=R_D já persistido).")

    # --- 4d. drought_spei_threshold sweep -- REQUIRES recompute from spei.parquet ---
    p("Curva `drought_spei_threshold` (-0,5 a -2,5 passo -0,25): **requer recompute** de F_D/R_D "
      "a partir de `spei.parquet` (28,001,820 linhas totais, 278 MB em disco) por série "
      "(plant/model/scenario), replicando `craei.hazards.consolidate._f_d_r_d` -- não é uma "
      "simples releitura de coluna, pois o limiar -1,5 está embutido no F_D já persistido em "
      "`plant_hazards.parquet`. Custo: pré-filtro por `id` (planta/catchment ou célula, Brasil "
      "hydro+thermal_water_dependent apenas, CLAUDE.md Regra 11) reduz a tabela antes do groupby; "
      "medido abaixo.")
    import time as _time
    t0 = _time.time()
    spei = pd.read_parquet(PROC / "spei.parquet")
    t_load = _time.time() - t0

    hydro_bra = bra_plants[bra_plants.plant_uid.isin(
        hazards[hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river"])]["plant_uid"]
    )]
    hydro_key = pd.DataFrame({"plant_uid": hydro_bra.plant_uid, "id": hydro_bra.plant_uid,
                               "bucket": hydro_bra.plant_uid.map(bucket_of)})
    tw_bra = bra_plants[bra_plants.plant_uid.isin(
        hazards[hazards.bucket == "thermal_water_dependent"]["plant_uid"]
    )]
    tw_cells = tw_bra.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
    tw_key = pd.DataFrame({
        "plant_uid": tw_cells.plant_uid,
        "id": tw_cells["cell_lat"].astype(str) + "_" + tw_cells["cell_lon"].astype(str),
        "bucket": "thermal_water_dependent",
    })

    catchment_spei = spei[(spei["scale"] == "catchment") & (spei["id"].isin(set(hydro_key["id"])))]
    cell_spei = spei[(spei["scale"] == "cell") & (spei["id"].isin(set(tw_key["id"])))]
    del spei
    import gc as _gc
    _gc.collect()

    def _f_d_r_d_local(spei_scale, plant_key, spei_col, threshold):
        valid = spei_scale[spei_scale[spei_col].notna()].copy()
        valid["severe"] = valid[spei_col] <= threshold
        f_d = valid.groupby(["id", "model", "scenario", "period"], as_index=False).agg(
            f_d=("severe", "mean")
        )
        base = f_d[f_d.period == "baseline"].drop(columns="period").rename(columns={"f_d": "baseline_value"})
        fut = f_d[f_d.period == "future"].drop(columns="period").rename(columns={"f_d": "future_value"})
        bf = base.merge(fut, on=["id", "model", "scenario"], how="outer")
        bf["ratio"] = np.where((bf["baseline_value"] == 0) | bf["baseline_value"].isna(), np.nan,
                                bf["future_value"] / bf["baseline_value"])
        return plant_key.merge(bf, on="id", how="inner")

    sweep = TS["drought_spei_threshold"]
    spei_thresholds = np.arange(sweep["start"], sweep["stop"] - 0.001, sweep["step"])
    rd_grid_thresholds = np.arange(TS["drought_rd_ratio"]["start"], TS["drought_rd_ratio"]["stop"] + 0.001,
                                    TS["drought_rd_ratio"]["step"])

    t1 = _time.time()
    for th in spei_thresholds:
        r_hydro = _f_d_r_d_local(catchment_spei, hydro_key, "SPEI_12", th)
        r_tw = _f_d_r_d_local(cell_spei, tw_key, "SPEI_12", th)
        recompute = pd.concat([r_hydro, r_tw], ignore_index=True)
        for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
            fl = bra_plants[bra_plants.plant_uid.isin(recompute[recompute.bucket == bucket]["plant_uid"])]
            if fl.empty:
                continue
            for fleet in ["operating", "planned_adv", "planned_early"]:
                fl_f = fl[fl.fleet == fleet]
                if fl_f.empty:
                    continue
                for scenario in SCENARIOS:
                    sub = recompute[(recompute.bucket == bucket) & (recompute.scenario == scenario)
                                     & recompute.plant_uid.isin(fl_f.plant_uid)]
                    by_model = {m: g.set_index("plant_uid")["ratio"] for m, g in sub.groupby("model")}
                    curve_rows.append(dict(
                        curve="drought_spei_threshold", country="BRA", bucket=bucket, fleet=fleet,
                        scenario=scenario, threshold=float(th),
                        median_share=_capacity_share(fl_f, by_model, 2.0, ">="),  # R_D>=2 classification held fixed
                    ))
                    # grid2d only for hydro buckets, per TS['grid_2d']
                    if bucket in ("hydro_reservoir", "hydro_run_of_river") and fleet == "operating":
                        for rd_th in rd_grid_thresholds:
                            grid2d_rows.append(dict(
                                country="BRA", bucket=bucket, fleet=fleet, scenario=scenario,
                                spei_threshold=float(th), rd_threshold=float(rd_th),
                                median_share=_capacity_share(fl_f, by_model, rd_th, ">="),
                            ))
    t_sweep = _time.time() - t1
    p(f"Custo medido: leitura de `spei.parquet` completo = {t_load:.1f}s; varredura de "
      f"{len(spei_thresholds)} limiares SPEI (hidro+térmica, Brasil, todos cenários/frotas, "
      f"reajuste de F_D/R_D sem refitar a distribuição, só recontagem de meses <=limiar) = "
      f"{t_sweep:.1f}s.")

curve_df = pd.DataFrame(curve_rows)
curve_df.to_csv(OUT / "c23_4_threshold_curves.csv", index=False)
grid2d_df = pd.DataFrame(grid2d_rows)
grid2d_df.to_csv(OUT / "c23_4_grid2d.csv", index=False)
p(f"`c23_4_threshold_curves.csv`: {len(curve_df)} linhas. `c23_4_grid2d.csv`: {len(grid2d_df)} linhas.")

# order-preservation intervals (SSP1-2.6 < SSP3-7.0 < SSP5-8.5 in >=4/5 models) are reported
# at the per-model level only for the RD/SPEI sweeps that kept by_model series; the curve table
# above stores median share only (cross-scenario order needs the per-model detail, computed here
# directly from plant_hazards for the two no-recompute curves, since those retain per-model access).
order_rows = []
if len(curve_df):
    for curve_name in curve_df["curve"].unique():
        cdf = curve_df[(curve_df.curve == curve_name) & (curve_df.fleet == "operating")]
        for (bucket, th), g in cdf.groupby(["bucket", "threshold"]):
            piv = g.set_index("scenario")["median_share"]
            if {"ssp126", "ssp370", "ssp585"} <= set(piv.index):
                ok = piv.get("ssp126", np.nan) < piv.get("ssp370", np.nan) < piv.get("ssp585", np.nan)
                order_rows.append(dict(curve=curve_name, bucket=bucket, threshold=th, order_holds=bool(ok)))
order_df = pd.DataFrame(order_rows)
if len(order_df):
    order_summary = order_df.groupby(["curve", "bucket"])["threshold"].agg(
        n_thresholds="count",
    )
    order_hold = order_df[order_df.order_holds].groupby(["curve", "bucket"])["threshold"].agg(
        min_threshold_order_holds="min", max_threshold_order_holds="max", n_holds="count"
    )
    order_report = order_summary.join(order_hold, how="left")
    order_report.to_csv(OUT / "c23_4_order_intervals.csv")
    p("Intervalo de limiar em que a ordem SSP1-2.6 < SSP3-7.0 < SSP5-8.5 se mantém na mediana "
      "entre GCMs (nota: verificação feita sobre a mediana, não sobre >=4/5 GCMs individualmente "
      "-- checar >=4/5 exigiria manter as 5 séries por modelo por limiar, não guardado na tabela "
      "de curvas para limitar o tamanho do CSV; reportado como limitação deste item, não como "
      "achado metodológico):")
    p(df_to_md(order_report.reset_index()))
else:
    p("Sem dados suficientes para o teste de ordenação entre cenários (gate de reprodução falhou "
      "ou nenhuma curva foi gerada).")

# --- 4e. coastal buffer sweep -- derivable from plants.parquet dist_coast_km ---
h("4 (coastal buffer)", level=3)
buf_rows = []
tw_all_bra = bra_plants[bra_plants.plant_uid.isin(
    hazards[hazards.bucket == "thermal_water_dependent"]["plant_uid"]
)]
for buf in TS["coastal_sweep"] if "coastal_sweep" in TS else TS["coastal_buffer_km"]:
    n_coastal = (tw_all_bra["dist_coast_km"] <= buf).sum()
    n_total = len(tw_all_bra)
    buf_rows.append(dict(buffer_km=buf, n_plants_within_buffer=int(n_coastal),
                          n_plants_thermal_water_total=n_total,
                          pct_excluded_from_lower_bound=100 * n_coastal / n_total if n_total else np.nan))
buf_df = pd.DataFrame(buf_rows)
buf_df.to_csv(OUT / "c23_4_coastal_buffer.csv", index=False)
p("Buffer costeiro **é derivável** de `plants.parquet.dist_coast_km` (contínuo, já calculado "
  "COMANDO 13, CRS equidistante azimutal por país, D24) -- sem custo de recompute, só "
  "rethresholding da coluna existente:")
p(df_to_md(buf_df))

# --- Item 5: SPEI/R_D baseline ---
h("5. Baseline de SPEI e R_D", level=2)
period_info = spei_thresholds if gate_pass else None  # noop to keep var referenced
p("Ajuste de distribuição por série própria (plant/model/scenario), não sobre um pool regional "
  "(D54, revertido o pool cross-série de D51/D52) -- cada série SPEI é ajustada sobre o próprio "
  "histórico do modelo (1985-2014, `docs/METHODS_SPEC.md` linha referenciada em L19/D54), não "
  "sobre o W5E5. `distribution` column em `spei.parquet` confirma `pearson3` (fallback de "
  "`loglogistic` PWM) por linha -- ver item 12 para os valores exatos de período/distribuição "
  "como hardcodes candidatos.")
if 'catchment_spei' in dir() and gate_pass:
    baseline_freq = pd.concat([
        catchment_spei[catchment_spei.period == "baseline"].assign(scale="catchment"),
        cell_spei[cell_spei.period == "baseline"].assign(scale="cell"),
    ])
    freq = baseline_freq.dropna(subset=["SPEI_12"]).assign(severe=lambda d: d["SPEI_12"] <= -1.5)
    by_model = freq.groupby(["scale", "model"])["severe"].mean().reset_index()
    by_model["severe_pct"] = by_model["severe"] * 100
    by_model.to_csv(OUT / "c23_5_baseline_spei_freq.csv", index=False)
    p("Frequência histórica empírica de SPEI-12<=-1,5 na baseline (1985-2014), por escala e "
      "modelo (Brasil, hidro=catchment, térmica hídrica=cell):")
    p(df_to_md(by_model))
    p(f"Variação entre modelos: desvio padrão = {by_model['severe_pct'].std():.3f} pp "
      f"(constante por construção seria 0; valor observado indica que varia por modelo, não é "
      f"fixo por construção -- SPEI é padronizado para média~0 por definição, mas a fração abaixo "
      f"de um limiar fixo -1,5 depende da forma exata da distribuição ajustada por série/modelo).")
else:
    p("Não computado: depende da mesma leitura de `spei.parquet` do item 4, que só roda se o "
      "portão de reprodução passar.")

# =======================================================================
# BLOCO C -- Geography and quality
# =======================================================================
h("Bloco C -- Geografia e qualidade", level=1)

# --- Item 6: attribution ---
h("6. Atribuição", level=2)
p("**Local ou a montante?** A montante (`src/craei/spatial/catchments.py`): o catchment de cada "
  "planta hidro é o conjunto de bacias HydroBASINS **nível 6** que drenam para a sub-bacia que "
  "contém a planta, obtido por BFS revertendo a topologia `NEXT_DOWN` (Methods Spec linha 60/214). "
  "Não é atribuição local (célula única sob a planta).")

hydro_bra_all = plants[(plants.country == "BRA") & (plants.tech_class == "hydro")]
shared = catchment_w.merge(hydro_bra_all[["plant_uid", "basin_id"]], on="plant_uid")
cell_share_counts = shared.groupby(["cell_lat", "cell_lon"])["plant_uid"].nunique()
n_shared_cells = int((cell_share_counts > 1).sum())
basin_share_counts = hydro_bra_all.groupby("basin_id")["plant_uid"].nunique()
n_shared_basins = int((basin_share_counts > 1).sum())
p(f"Usinas hidro brasileiras que compartilham célula: {n_shared_cells} células com >1 planta "
  f"(de {cell_share_counts.shape[0]} células totais usadas por hidro BRA). Compartilham bacia "
  f"(`basin_id`): {n_shared_basins} bacias com >1 planta (de {basin_share_counts.shape[0]} "
  f"bacias totais).")

dist_by_country = m_dist = plants.merge(plant_cell, on="plant_uid")[["country", "dist_to_cell_km"]]
p("Distância máxima usina-célula por país (D24, CRS equidistante azimutal):")
p(df_to_md(dist_by_country.groupby("country")["dist_to_cell_km"].max().reset_index()))

p("**PET truncada (51 células, Índia, L16):** não recomputável aqui sem rodar "
  "`craei.hazards.pet.daily_pet` sobre o NetCDF bruto (o flag `pet_truncated` é transitório, "
  "não persistido em `water_balance_catchment.parquet`, que só guarda P/PET/D mensais agregados) "
  "-- custo não pago. Porém a validação W5E5 já rodada (COMANDO 22-D, `docs/DECISIONS.md` D70) "
  "reporta diretamente: **0 dias PET-truncados no Brasil e em Portugal** ('0 PET-truncated days "
  "either country (no glacial cells in scope, unlike India's L16)'), então 0 das 51 células "
  "reportadas em L16 caem no Brasil, e 0 usinas brasileiras têm peso truncado > 0,2 (o "
  "limite de 0,2 do L16 só se aplica ao conjunto de 144 usinas indianas afetadas).")

p("**Camada do Aqueduct que alimenta o H3:** ambas -- `baseline_annual.bws` (2025, baseline) e "
  "`future_annual.ws` (2050, por cenário `{bau,opt,pes}{30|50|80}` mapeado a SSP1-2.6/3-7.0/5-8.5, "
  "Methods Spec §1.4 H3). Como `future_annual` varia por cenário (confirmado abaixo), a "
  "invariância entre cenários relatada em L06 **não é garantida por construção da camada "
  "escolhida** -- é um achado empírico sobre o quanto a mediana do ensemble interno de 5 GCMs "
  "do Aqueduct muda entre os 3 horizontes de emissão, não um artefato de usar só o baseline.")
aq_by_scenario = aqueduct.groupby("scenario")["ws_category"].value_counts().unstack(fill_value=0)
aq_by_scenario.to_csv(OUT / "c23_6_aqueduct_by_scenario.csv")
p(df_to_md(aq_by_scenario.reset_index()))

# --- Item 7: regions ---
h("7. Regiões", level=2)
diag_dir = Path(paths["outputs_dir"]) / "diagnostics"
region_path = diag_dir / "c22b_plant_region.parquet"
if region_path.exists():
    region = pd.read_parquet(region_path)
    bra_region = region[region.country == "BRA"]
    reg_tbl = bra_region.merge(
        hazards.drop_duplicates("plant_uid")[["plant_uid", "bucket"]], on="plant_uid", how="left"
    )
    reg_summary = reg_tbl.groupby(["region_id", "bucket", "fleet"], as_index=False).agg(
        n_plants=("plant_uid", "count"), gw=("capacity_mw", "sum")
    )
    reg_summary["gw"] = reg_summary["gw"] / 1000.0
    reg_summary.to_csv(OUT / "c23_7_regions_BRA.csv", index=False)
    p(f"Atribuição GADM nível 1 da C22-B **está persistida** em "
      f"`outputs_diagnostics_dir/c22b_plant_region.parquet` ({len(region)} plantas, "
      f"{bra_region.region_id.nunique()} regiões distintas no Brasil). Tabela estado x bucket x "
      f"frota gerada: {len(reg_summary)} linhas.")
    p(df_to_md(reg_summary.head(20)))
else:
    p(f"Atribuição GADM nível 1 da C22-B **não está persistida** em {region_path} -- não "
      f"reimplementada aqui, conforme instrução do comando.")

# --- Item 8: planned fleet BRA ---
h("8. Frota planejada no Brasil", level=2)
planned_rows = []
for bucket in sorted(hazards["bucket"].unique()):
    if bucket == "solar":
        continue
    bucket_uids = set(hazards[hazards.bucket == bucket]["plant_uid"].unique())
    bp = plants[(plants.country == "BRA") & plants.plant_uid.isin(bucket_uids)]
    for fleet in ["operating", "planned_adv", "planned_early"]:
        bf = bp[bp.fleet == fleet]
        n_basins_f = bf["basin_id"].dropna().nunique() if bf["basin_id"].notna().any() else np.nan
        planned_rows.append(dict(
            bucket=bucket, fleet=fleet, n_plants=len(bf), gw=bf["capacity_mw"].sum() / 1000.0,
            n_distinct_basins=n_basins_f,
        ))
planned_df = pd.DataFrame(planned_rows)
planned_df.to_csv(OUT / "c23_8_planned_fleet_BRA.csv", index=False)
p(df_to_md(planned_df))
for bucket in sorted(planned_df["bucket"].unique()):
    op_n = planned_df[(planned_df.bucket == bucket) & (planned_df.fleet == "operating")]["n_plants"]
    pl_n = planned_df[(planned_df.bucket == bucket) & (planned_df.fleet != "operating")]["n_plants"].sum()
    op_n_val = int(op_n.iloc[0]) if len(op_n) else 0
    has_contrast = (op_n_val >= SA["min_plants"]) and (pl_n >= SA["min_plants"])
    p(f"- {bucket}: operating n={op_n_val}, planned (adv+early) n={int(pl_n)} -- "
      f"contraste operante vs planejada {'POSSÍVEL' if has_contrast else 'NÃO POSSÍVEL'} "
      f"(critério: ambos >= min_plants={SA['min_plants']}).")

# --- Item 9: GEM quality BRA ---
h("9. Qualidade GEM no Brasil", level=2)
bra_dup_coords = plants[plants.country == "BRA"].duplicated(subset=["lat", "lon"], keep=False).sum()
p(f"Duplicatas de coordenada exata (mesma lat/lon, >=2 usinas) no Brasil: {int(bra_dup_coords)} "
  f"linhas envolvidas.")
p(f"Capacidade ausente: 0 no Brasil por construção -- `build_inventory` já descarta unidades sem "
  f"`Capacity (MW)` como `no_capacity` antes de `plants.parquet` existir (não verificável de volta "
  f"sem reler o GEM bruto; contagem de descartados por esse motivo é custo de leitura do XLSX bruto, "
  f"pago acima no item 1 só para tipo `wind`, não para `no_capacity` -- reportado como desconhecido "
  f"aqui sem releitura adicional).")
p("Campo de ano de aposentadoria: **não presente** em `plants.parquet` (colunas: "
  f"{plants.columns.tolist()}) -- GEM traz `Retired year` na planilha bruta (não lido para este "
  "item, custo de leitura do XLSX; a coluna não é usada por nenhum script de produção listado "
  "no Bloco E).")
p("Limiar mínimo de capacidade do tracker GEM: desconhecido a partir dos arquivos locais "
  "(não declarado em METHODS_SPEC.md/DECISIONS.md); GEM documenta publicamente cobrir usinas "
  ">=1 MW para a maioria das tecnologias, mas essa cifra não está em nenhum arquivo deste "
  "projeto, então fica `desconhecido` por regra (\"nunca inferir\").")
small_hydro = plants[(plants.country == "BRA") & (plants.tech_class == "hydro") & (plants.capacity_mw < 30)]
p(f"PCHs (hidro < 30 MW, limiar ANEEL de referência, não um filtro do GEM): "
  f"{len(small_hydro)} usinas brasileiras em `plants.parquet` -- portanto **incluídas** pelo "
  f"tracker GEM (não há corte de capacidade mínima visível nos dados locais que as excluiria).")
p("Combustível e tecnologia por unidade térmica: `plants.parquet` agrega unidades a planta "
  "(`tech_class`/`hydro_type` são moda por planta, `src/craei/inventory/plants.py` linha ~141) "
  "-- o campo `Technology`/`Type` por unidade do GEM bruto não é persistido em `plants.parquet`; "
  "GEM traz esses campos por unidade na planilha bruta (confirmado na leitura do item 1 acima, "
  "colunas `Type`/`Technology` existem no XLSX), mas não neste projeto pós-agregação.")

# =======================================================================
# BLOCO D -- Governance
# =======================================================================
h("Bloco D -- Governança", level=1)

# --- Item 10: limitations applicability to Brazil ---
h("10. Limitações (aplicabilidade ao Brasil)", level=2)
L_CLASS = {
    "L01": ("applicable", "BRA tem plantas thermal_water_dependent; GEM não traz campo de tecnologia de resfriamento em nenhum país."),
    "L02": ("not_applicable", "Específico da Índia (ausência de validação)."),
    "L03": ("applicable", "Limitação metodológica geral (hazard != limite operacional), vale para todo o projeto."),
    "L04": ("applicable", "Resolução 0,5° é da malha ISIMIP global, usada para todos os países incl. BRA."),
    "L05": ("applicable", "Série futura de SPEI começa dez/2041 -- geral, aplica-se a toda série BRA."),
    "L06": ("applicable", "BRA tem plantas thermal_water_dependent com H3 via Aqueduct."),
    "L07": ("applicable", "Eólica excluída da frota inteira do projeto, incl. BRA (item 1 acima quantifica o GW brasileiro fora de escopo)."),
    "L08": ("applicable", "Validação nacional do Brasil (D70) usa SPEI-12 derivado do W5E5, que termina em 2019."),
    "L09": ("not_applicable", "Específico da Índia (ausência de validação)."),
    "L10": ("applicable", "Truncamento de extrapolação do SPEI em +-3 é geral, aplica-se às séries brasileiras."),
    "L11": ("not_applicable", "Geotérmica só existe no GEM para Portugal (D15)."),
    "L12": ("applicable", "Bacias hidrográficas brasileiras transfronteiriças existem (ex.: bacia do Prata/Paraná, Itaipu) -- catchment recortado no bbox do país pode sub-representar células a montante fora do Brasil."),
    "L13": ("applicable", "BRA tem plantas thermal_water_dependent com H3 via Aqueduct future_annual."),
    "L14": ("not_applicable", "Específico de Portugal (Açores/Madeira)."),
    "L15": ("not_applicable", "Amostra de dias úmidos baixa é exclusiva do noroeste da Índia (região do deserto de Thar); Brasil tem mínimo de 1701 dias úmidos (O06), acima de qualquer corte candidato."),
    "L16": ("not_applicable", "PET truncada por regime glacial é exclusiva de 51 células indianas; confirmado 0 dias PET-truncados no Brasil (D70, validação W5E5)."),
    "L17": ("withdrawn", "Retirado 2026-09-30 (COMANDO 18-G, D54/D55) -- método de pool regional substituído por ajuste por série; mantido no arquivo só como histórico, não é limitação ativa em nenhum país."),
    "L18": ("applicable", "Brasil tem 10.470-proporcional parcela de plantas solar_pv -- a métrica L (perda por temperatura de pico) do SI não foi implementada para nenhum país, incl. BRA."),
    "L19": ("applicable", "Fecha O09; o caso residual (0,203% thermal_water_dependent com R_D indefinido) inclui potencialmente plantas brasileiras -- não filtrado por país no texto original da limitação."),
    "L20": ("applicable", "Diretamente sobre o Brasil -- ausência de mapeamento planta-subsistema ONS/ANEEL/EPE."),
    "L21": ("applicable", "compound.csv inclui BRA; a métrica composta nacional (não regional) se aplica ao Brasil como a qualquer país do projeto."),
    "L22": ("applicable", "2 dos 4 casos confirmados (D68) envolvem plantas brasileiras: Itaipu (BRA/Paraguai) e 2 térmicas operando brasileiras (Monteverde, Santa Maria Açucareira) fora de qualquer região nomeada."),
}
l10_rows = [dict(limitation=k, status=v[0], justification=v[1]) for k, v in L_CLASS.items()]
l10_df = pd.DataFrame(l10_rows)
l10_df.to_csv(OUT / "c23_10_limitations_BRA.csv", index=False)
p(df_to_md(l10_df, max_rows=25))

# --- Item 11: unused data ---
h("11. Dados não usados", level=2)
unused_rows = [
    dict(item="EM-DAT (emdat_events.parquet)", reason="acquired_not_processed",
         note="899 rows (BRA 239, IND 622, PRT 38). Resolvido (O15, D-EMDAT): tratado só "
              "descritivamente -- emdat_descriptive.csv agora existe (12 linhas), sem teste "
              "estatístico ou uso em validação, conforme Methods §1.7/Extended Data."),
    dict(item="SPI-12 (spei.parquet SPI_12 column)", reason="acquired_not_processed",
         note="Presente em spei.parquet mas não usado em plant_hazards.parquet (COMANDO 22's "
              "sensitivity test só, não hazard de produção -- Methods Spec linha 382)."),
    dict(item="TX40 (indices_daily.parquet / plant_hazards.parquet)", reason="acquired_not_processed",
         note="Presente em plant_hazards.parquet mas não é o hazard headline H1 usado em "
              "exposure_summary.csv (TX35 é o headline; TX40 fica sem consumidor de produção "
              "identificado nos scripts 01-12)."),
    dict(item="ONS ENA por subsistema (Norte/Nordeste/Sul/Sudeste)", reason="needed_not_acquired",
         note="Necessário para validação regional (L20/D62) -- sem tabela oficial ANEEL/EPE/ONS "
              "planta-subsistema. Não adquirir nada (regra do comando)."),
    dict(item="ANEEL SIGA", reason="needed_not_acquired",
         note="Poderia fornecer mapeamento planta-subsistema ou dados complementares de "
              "capacidade/status -- não adquirido (D62 já buscou e não achou fonte auditável)."),
    dict(item="Combustível e resfriamento das térmicas (fonte além do GEM)", reason="needed_not_acquired",
         note="GEM não traz campo de tecnologia de resfriamento (L01); nenhuma fonte "
              "complementar adquirida para resolver isso diretamente (a solução adotada foi "
              "cooling_bound upper/lower, não uma fonte de dado extra)."),
]
unused_df = pd.DataFrame(unused_rows)
unused_df.to_csv(OUT / "c23_11_unused_data.csv", index=False)
p(df_to_md(unused_df, max_rows=20))

# --- Item 12: methodological numbers outside params.yaml ---
h("12. Números metodológicos fora do params.yaml", level=2)
p("Varredura manual de `src/` e `scripts/` (grep dirigido às categorias pedidas pelo comando: "
  "escala do SPEI, período de referência, distribuição ajustada, lista de GCMs e janelas, "
  "limites de resfriamento do H3, percentil extremo do H4). Não migrado, só listado.")
hardcode_rows = [
    dict(file="src/craei/hazards/precip.py", line=15, name="WET_DAY_THRESHOLD_MM",
         value="1.0", category="H4 wet-day definition",
         note="Limiar de dia úmido (pr>=1mm) para a base de H4's p95 -- o percentil em si "
              "(`wet_day_p95_percentile`) está em params.yaml, mas o limiar de 1mm que define "
              "'dia úmido' não está."),
    dict(file="src/craei/hazards/pet.py", line="43,66", name="Hargreaves-Samani constants",
         value="0.0023, 0.408, 17.8", category="H2 PET formula",
         note="Constantes da equação de Hargreaves-Samani (FAO-56 Eq. 52) -- constantes físicas "
              "publicadas da fórmula, não escolhas de autor (diferente de um limiar "
              "metodológico), mas ainda assim números fora de params.yaml."),
    dict(file="scripts/08_spei.py", line=42, name="SPEI3_WINDOW_K", value="1",
         category="H2 SPEI-3 temporal window",
         note="D54: k=1 (n=90) adotado sobre k=2 (medido pior). Decisão de autor documentada em "
              "DECISIONS.md, mas o valor numérico em si é uma constante de módulo, não um "
              "campo de params.yaml."),
    dict(file="src/craei/hazards/spei.py", line="~298", name="baseline window", value="1985-2014",
         category="reference period",
         note="`_check_baseline_years` (Rule 4) hardcoda 1985/2014 como guarda de janela -- "
              "período também aparece em config/datasets.yaml:periods.baseline (duplicação "
              "entre a guarda de código e o config, não uma migração pendente por si só, mas "
              "duas fontes da mesma constante)."),
    dict(file="config/datasets.yaml", line="1-12", name="models list + scenarios", value="5 GCMs, 4 scenarios",
         category="GCM list and scenarios",
         note="Não está em params.yaml (categórico, não teria value/tier/source de forma "
              "natural) -- mas é a única fonte de verdade para a lista de 5 modelos e 4 "
              "cenários usada em todo o pipeline; listado aqui por transparência, não como "
              "defeito."),
]
hardcode_df = pd.DataFrame(hardcode_rows)
hardcode_df.to_csv(OUT / "c23_12_hardcodes.csv", index=False)
p(df_to_md(hardcode_df, max_rows=20))
p("**Limites de resfriamento do H3:** `coastal_buffer_km` (5 km, L01/D47) já está em "
  "`config/params.yaml` com value/tier/source -- não é um hardcode. **Percentil extremo do H4:** "
  "`wet_day_p95_percentile` também já está em `params.yaml` -- não é hardcode; só o limiar "
  "subjacente de 1mm que define 'dia úmido' (acima) não está.")

# --- Item 13: orphan parameters ---
h("13. Parâmetros órfãos", level=2)
params_yaml_text = open(ROOT / "config" / "params.yaml", encoding="utf-8").read()
import yaml as _yaml
params_all = _yaml.safe_load(params_yaml_text)
src_text = ""
for f in (ROOT / "src").rglob("*.py"):
    src_text += f.read_text(encoding="utf-8", errors="ignore")
for f in (ROOT / "scripts").rglob("*.py"):
    src_text += f.read_text(encoding="utf-8", errors="ignore")
orphan_rows = []
for pname in params_all:
    referenced = bool(re.search(rf'["\']{re.escape(pname)}["\']', src_text))
    orphan_rows.append(dict(param=pname, referenced_in_code=referenced))
orphan_df = pd.DataFrame(orphan_rows)
orphan_df.to_csv(OUT / "c23_13_orphan_params.csv", index=False)
n_orphan = (~orphan_df["referenced_in_code"]).sum()
p(f"{n_orphan} de {len(orphan_df)} parâmetros em `params.yaml` sem referência por string exata "
  f"ao nome em `src/` ou `scripts/` (grep por `\"nome\"` ou `'nome'` como chave de dicionário).")
p(df_to_md(orphan_df[~orphan_df["referenced_in_code"]], max_rows=30))
for check_name in ["solar_temp_coeff_pct_per_c", "solar_noct_cell_air_diff_c", "compound_baseline_percentile"]:
    row = orphan_df[orphan_df.param == check_name]
    status = "referenciado" if len(row) and row.iloc[0].referenced_in_code else "ÓRFÃO (sem referência)"
    p(f"- Verificação específica pedida: `{check_name}` -- {status}.")

# --- Item 14: PROGRESS.json divergences ---
h("14. PROGRESS.json", level=2)
import json as _json
progress = _json.loads((ROOT / "PROGRESS.json").read_text(encoding="utf-8"))
p(f"`updated`: {progress.get('updated')}. `current_command`: {progress.get('current_command')}.")
p14_findings = []
for phase in progress["phases"]:
    if phase["id"] == "P6":
        p14_findings.append(
            f"- Fase **P6** tem `status: {phase['status']}` no arquivo, mas seu único comando "
            f"(C21) está `status: done`; P6-R e P6-C ainda `todo` -- consistente com o "
            f"'ponto de parada em portões de revisão/commit' já conhecido (ver memória do "
            f"projeto), não uma divergência de dados, mas um item de fase pendente real."
        )
p14_findings.append(
    "- `validation.csv` e `emdat_descriptive.csv`: **ambos existem agora** em "
    "`outputs_tables_dir` (confirmado por leitura direta nesta auditoria, Bloco A). O "
    "`docs/DECISIONS.md` O14 (que motivou a citação desses dois arquivos como ausentes na "
    "premissa original deste comando) foi fechado por D70 (validation.csv) e O15 (emdat_descriptive.csv) "
    "em 2026-09-30, mesma data de `PROGRESS.json.updated` -- a premissa do enunciado do C23 "
    "sobre a ausência desses arquivos está **desatualizada**, não confere com o estado real do "
    "disco nem com `PROGRESS.json`/`DECISIONS.md`."
)
for line in p14_findings:
    p(line)
p("Nenhuma outra divergência arquivo vs. disco vs. `git log` encontrada nesta passada "
  "(checagem limitada às fases citadas pelo comando; uma varredura completa fase-a-fase contra "
  "`git log --oneline` não foi feita linha a linha por não ter sido pedida além de P6/validation/emdat).")

# =======================================================================
# BLOCO E -- File inventory (nothing moved)
# =======================================================================
h("Bloco E -- Inventário de arquivos", level=1)

SCOPE_KEYWORDS = AUDIT["code_audit"]["scope_keywords"]


def _scope_tag_for_text(text: str) -> str:
    kw_hit = {k for k in SCOPE_KEYWORDS if k in text}
    if {"IND", "India"} & kw_hit and not ({"PRT", "Portugal"} & kw_hit):
        return "IND_only"
    if {"PRT", "Portugal"} & kw_hit and not ({"IND", "India"} & kw_hit):
        return "PRT_only"
    if "compound" in kw_hit:
        return "compound"
    if {"solar", "wind"} & kw_hit:
        return "solar_wind"
    if ({"IND", "India"} & kw_hit) and ({"PRT", "Portugal"} & kw_hit):
        return "multi_country"
    return "core"


# --- Item 15: scripts ---
h("15. Scripts", level=2)
_PROD_FLOW = {
    "02_acquire.py", "03_pilot_download.py", "04_daily_indices.py", "04_full_acquire.py",
    "05_plants.py", "06_spatial.py", "07_water_balance.py", "08_spei.py", "09_consolidate.py",
    "10_exposure.py", "11_compound.py",
}
_PROD_ADJACENT_NOT_01_12 = {
    "22_audit.py", "22_validate_ren_iph.py", "24_w5e5_spei_validation.py",
    "25_validation_stats.py", "26_emdat_descriptive.py",
}
_DIAG_CLOSED = {
    "audit_fd_pwm_vs_pearson3.py", "audit_mle_loglogistic_and_2param_fallback.py",
    "audit_n360_pwm_vs_pearson3_gap.py", "audit_pearson3_bias_synthetic.py",
    "audit_pool_granularity_sensitivity.py", "audit_pool_size_synthetic_bias.py",
    "audit_spei_fit_diagnostics.py", "audit_spei_pwm_failure_causes.py",
    "audit_temporal_pooling_variants.py", "audit_temporal_variant_synthetic_bias.py",
    "audit_tx_tn_and_pet_truncation.py", "audit_wet_day_sample.py", "benchmark_spei_fitters.py",
    "c21_2_closure.py", "c21_2_fix_blockers.py", "c21_2_fix_emdat.py", "c21_2_fix_final.py",
    "c21_2_plant_subsystem_mapping.py", "c22_compound_diagnosis.py",
    "c22b_dependence_uncertainty.py", "c22b_regional_assignment.py", "c22b_regional_compound.py",
    "c22c_collective_tests.py",
}

script_rows = []
for fpath in sorted((ROOT / "scripts").glob("*.py")):
    name = fpath.name
    if name == "c23_scope_audit.py" or name.startswith("c23_"):
        continue
    text = fpath.read_text(encoding="utf-8", errors="ignore")
    scope_tag = _scope_tag_for_text(text)
    if name in _PROD_FLOW:
        group, just = "producao", "Script numerado no fluxo 01-12 (Methods Spec §3 Steps)."
    elif name in _PROD_ADJACENT_NOT_01_12:
        group, just = "producao", ("Fora da numeração 01-12 literal, mas gera saída consumida "
                                    "pelo artigo (validation.csv, emdat_descriptive.csv) ou audita "
                                    "diretamente um resultado de produção -- classificado como "
                                    "produção por função, não por número, registrado como exceção.")
    elif name in _DIAG_CLOSED:
        group, just = "diagnostico_fechado", "Referenciado em docs/DECISIONS.md, ligado a um D# fechado."
    else:
        group, just = "orfao", "Não referenciado em docs/DECISIONS.md por nome nem no fluxo 01-12."
    script_rows.append(dict(script=name, group=group, scope_tag=scope_tag, justification=just))

scripts_df = pd.DataFrame(script_rows)
scripts_df.to_csv(OUT / "c23_15_scripts.csv", index=False)
p(df_to_md(scripts_df, max_rows=50))
p(df_to_md(scripts_df["group"].value_counts().rename_axis("group").reset_index(name="n")))

# --- Item 16: src/craei modules/functions unimported by production scripts or tests ---
h("16. src/craei/ módulos e funções públicas não usados", level=2)
prod_script_text = ""
for name in _PROD_FLOW | _PROD_ADJACENT_NOT_01_12:
    fp = ROOT / "scripts" / name
    if fp.exists():
        prod_script_text += fp.read_text(encoding="utf-8", errors="ignore")
test_text = ""
for fp in (ROOT / "tests").glob("*.py"):
    test_text += fp.read_text(encoding="utf-8", errors="ignore")

mod_rows = []
for fp in sorted((ROOT / "src" / "craei").rglob("*.py")):
    if fp.name == "__init__.py":
        continue
    rel = fp.relative_to(ROOT / "src" / "craei")
    mod_dotted = str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
    mod_text = fp.read_text(encoding="utf-8", errors="ignore")
    scope_tag = _scope_tag_for_text(mod_text)
    imported_by_prod = (mod_dotted in prod_script_text) or (rel.stem in prod_script_text)
    imported_by_test = (mod_dotted in test_text) or (rel.stem in test_text)
    funcs = re.findall(r"^def (\w+)\(", mod_text, flags=re.MULTILINE)
    pub_funcs = [f for f in funcs if not f.startswith("_")]
    for fn in pub_funcs:
        used_in_prod = bool(re.search(rf"\b{re.escape(fn)}\b", prod_script_text))
        used_in_test = bool(re.search(rf"\b{re.escape(fn)}\b", test_text))
        mod_rows.append(dict(
            module=f"craei.{mod_dotted}", function=fn, scope_tag=scope_tag,
            imported_by_production=imported_by_prod, used_in_production=used_in_prod,
            used_in_tests=used_in_test,
        ))
mod_df = pd.DataFrame(mod_rows)
mod_df.to_csv(OUT / "c23_16_unused_modules.csv", index=False)
unused_mod = mod_df[~mod_df.used_in_production & ~mod_df.used_in_tests]
p(f"{len(unused_mod)} de {len(mod_df)} funções públicas de `src/craei/` sem uso detectado (por "
  f"nome exato, regex `\\bnome\\b`) nem em scripts de produção nem em `tests/`:")
p(df_to_md(unused_mod, max_rows=40))

# --- Item 17: tests exercising non-core scope ---
h("17. Testes", level=2)
noncore_tags = {"compound", "solar_wind", "IND_only", "PRT_only"}
test_rows = []
for fp in sorted((ROOT / "tests").glob("*.py")):
    text = fp.read_text(encoding="utf-8", errors="ignore")
    scope_tag = _scope_tag_for_text(text)
    n_tests = len(re.findall(r"^def test_", text, flags=re.MULTILINE))
    test_rows.append(dict(test_file=fp.name, scope_tag=scope_tag, n_tests=n_tests))
test_df = pd.DataFrame(test_rows)
test_df.to_csv(OUT / "c23_17_tests_scope.csv", index=False)
total_tests = test_df["n_tests"].sum()
noncore_tests = test_df[test_df.scope_tag.isin(noncore_tags)]["n_tests"].sum()
orphan_scope_tags = set(scripts_df[scripts_df.group == "orfao"]["scope_tag"]) | set(
    mod_df[mod_df.module.isin(
        "craei." + unused_mod["module"].str.replace("craei.", "", regex=False)
    )]["scope_tag"]
) if len(scripts_df[scripts_df.group == "orfao"]) else set()
p(f"{total_tests} testes totais (função `def test_`, contagem própria por regex, referência "
  f"~141 no relatório de `pytest -q`). {int(noncore_tests)} testes exercitam arquivos cujo "
  f"conteúdo caiu em `scope_tag` fora do núcleo ({sorted(noncore_tags)}).")
p(df_to_md(test_df[test_df.scope_tag.isin(noncore_tags)], max_rows=30))
p("Nota de método: a classificação usa o CONTEÚDO do arquivo de teste inteiro (presença de "
  "palavras-chave), não uma análise por função de teste individual -- superestima o número de "
  "testes 'fora do núcleo' quando um arquivo mistura casos core e não-core (ex.: um teste de "
  "`f_d_spei3`, específico de hydro_run_of_river, num arquivo que também testa SPEI-12 "
  "genérico). Não corrigido aqui por ser uma análise por função, não pedida explicitamente "
  "além da contagem de arquivo.")
p("Quantos testes perderiam objeto se código órfão (item 15/16) fosse arquivado: não "
  "quantificável sem rodar a suíte com o código órfão removido (mudança de código, fora do "
  "escopo de escrita deste comando) -- reportado como custo, não feito.")

# --- Item 18: outputs_dir inventory ---
h("18. outputs_dir", level=2)
out_root = Path(paths["outputs_dir"])
out_rows = []
for fp in out_root.rglob("*"):
    if fp.is_file():
        rel = fp.relative_to(out_root)
        mtime = pd.Timestamp.fromtimestamp(fp.stat().st_mtime)
        text_sample = ""
        scope_tag = _scope_tag_for_text(str(rel))
        out_rows.append(dict(
            path=str(rel), size_bytes=fp.stat().st_size, mtime=mtime.isoformat(),
            scope_tag=scope_tag,
        ))
out_df = pd.DataFrame(out_rows)
out_df.to_csv(OUT / "c23_18_outputs.csv", index=False)
p(f"{len(out_df)} arquivos em `outputs_dir` ({out_df['size_bytes'].sum() / 1e6:.1f} MB total).")
p(df_to_md(out_df.sort_values("size_bytes", ascending=False), max_rows=40))
p("**Comando gerador** e **superado por versão posterior**: não determinável por nome/timestamp "
  "sozinho sem reconstruir a proveniência de cada arquivo a partir de `docs/DECISIONS.md` "
  "(feito manualmente célula a célula não é viável neste orçamento de tempo) -- reportado como "
  "`desconhecido` por arquivo individualmente, mas a proveniência dos arquivos citados nos "
  "Blocos A-D acima (plants.parquet, plant_hazards.parquet, exposure_summary.csv etc.) já está "
  "estabelecida pelo texto deste relatório.")

# --- Item 19: processed_dir / interim_dir sizes ---
h("19. processed_dir e interim_dir", level=2)
for key in ("processed_dir", "interim_dir"):
    d = Path(paths[key])
    if not d.exists():
        p(f"`{key}` ({d}): não existe.")
        continue
    files = [(fp, fp.stat().st_size) for fp in d.rglob("*") if fp.is_file()]
    total = sum(sz for _, sz in files)
    p(f"`{key}` ({d}): {len(files)} arquivos, {total / 1e6:.1f} MB total.")
    rows = sorted(({"file": str(fp.relative_to(d)), "size_mb": sz / 1e6} for fp, sz in files),
                   key=lambda r: -r["size_mb"])
    p(df_to_md(pd.DataFrame(rows), max_rows=20))

isimip_cache = Path(paths["isimip_global_cache_dir"])
if isimip_cache.exists():
    try:
        cache_files = list(isimip_cache.rglob("*"))
        cache_size = sum(f.stat().st_size for f in cache_files if f.is_file())
        cache_mtime_latest = max((f.stat().st_mtime for f in cache_files if f.is_file()), default=None)
        p(f"`isimip_global_cache_dir` ({isimip_cache}): {cache_size / 1e9:.2f} GB, "
          f"{sum(1 for f in cache_files if f.is_file())} arquivos. Intocado nesta auditoria "
          f"(read-only, nenhum arquivo escrito ou movido lá).")
    except OSError as exc:
        p(f"`isimip_global_cache_dir` ({isimip_cache}): erro ao ler ({exc}) -- possivelmente USB "
          f"suspenso/desconectado (ver memória do projeto sobre infra ISIMIP).")
else:
    p(f"`isimip_global_cache_dir` ({isimip_cache}): não encontrado/não montado no momento desta "
      f"auditoria.")
p("Parquet derivável em minutos de outro já presente: nenhum candidato óbvio identificado sem "
  "recomputar hazards (fora de escopo) -- `water_balance_cell.parquet` (se existir) seria "
  "derivável de volta a partir de `indices_daily.parquet`/raw NetCDF, não o contrário; não "
  "quantificado por não ter sido encontrado tal arquivo redundante nesta listagem.")

# =======================================================================
# Write Blocos A-E report (c23_report.md). c23_summary.md is written by a
# separate, final step (scripts/c23_summary.py) once Bloco F (code audit,
# separate script) has also run, so the summary can cite both.
# =======================================================================
(OUT / "c23_report.md").write_text("\n".join(REPORT), encoding="utf-8")
print("Bloco A-E done. Report at", OUT / "c23_report.md")

# Persist the viability matrix's class line-counts (needed by c23_summary.md's
# final paragraph) so the summary script doesn't have to recompute the matrix.
class_counts = {
    "BRA": viability[viability.country == "BRA"]["class_final"].value_counts().to_dict(),
    "other": viability[viability.country != "BRA"]["class_final"].value_counts().to_dict(),
    "by_bucket_fleet_hazard": (
        viability.groupby(["bucket", "fleet", "hazard"])["class_final"]
        .agg(lambda s: s.value_counts().idxmax()).value_counts().to_dict()
    ),
}
import json as _json2
(OUT / "_c23_class_counts.json").write_text(_json2.dumps(class_counts, indent=2), encoding="utf-8")
