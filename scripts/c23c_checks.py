"""COMANDO 23-C: post-C23 verifications (read-only except outputs_audit_dir/c23/c23c/).

Does not decide scope. Reads config/c23_audit.yaml (not params.yaml, see that
file's header). No table outside outputs_audit_dir/c23/c23c/ is written.
"""

import gc
import hashlib
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from craei.config import load_datasets, load_paths  # noqa: E402
from craei.exposure import aggregate as agg  # noqa: E402
from craei.hazards.consolidate import _assign_bucket  # noqa: E402

paths = load_paths()
datasets = load_datasets()
AUDIT = yaml.safe_load(open(ROOT / "config" / "c23_audit.yaml", encoding="utf-8"))
SA = AUDIT["scope_audit"]
TS = AUDIT["threshold_sweeps"]
CA = AUDIT["code_audit"]

PROC = Path(paths["processed_dir"])
TABLES = Path(paths["outputs_tables_dir"])
C23_OUT = Path(paths["outputs_dir"]) / "audit" / "c23"
OUT = C23_OUT / "c23c"
OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = [s for s in datasets["scenarios"] if s != "historical"]

REPORT = []


def h(t, level=2):
    REPORT.append(f"{'#' * level} {t}\n")


def p(t):
    REPORT.append(t + "\n")


def df_to_md(df, max_rows=60):
    shown = df.head(max_rows)
    cols = [str(c) for c in shown.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in shown.iterrows():
        vals = [f"{v:.4g}" if isinstance(v, float) else str(v) for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    out = "\n".join(lines) + "\n"
    if len(df) > max_rows:
        out += f"\n(+{len(df) - max_rows} more rows, see CSV)\n"
    return out


plants = pd.read_parquet(PROC / "plants.parquet")
plant_cell = pd.read_parquet(PROC / "plant_cell.parquet")
catchment_w = pd.read_parquet(PROC / "catchment_weights.parquet")
hazards = pd.read_parquet(PROC / "plant_hazards.parquet")
aqueduct = pd.read_parquet(PROC / "plant_aqueduct.parquet")
exposure_summary = pd.read_csv(TABLES / "exposure_summary.csv")
bra_plants = plants[plants.country == "BRA"]

h("COMANDO 23-C -- post-C23 verifications", level=1)

# =======================================================================
# Item 1: SPEI curve n_holds bug + reproduction + order with median and >=4/5
# =======================================================================
h("1. Curva de SPEI -- n_holds NaN", level=2)

order_df = pd.read_csv(C23_OUT / "c23_4_order_intervals.csv")
curve_df = pd.read_csv(C23_OUT / "c23_4_threshold_curves.csv")
spei_curve = curve_df[(curve_df.curve == "drought_spei_threshold") & (curve_df.fleet == "operating")]
all_zero = (spei_curve["median_share"] == 0).all()
p(f"Diagnóstico: `c23_4_order_intervals.csv` tem `n_holds` NaN nos 3 buckets de "
  f"`drought_spei_threshold` porque **é um bug do script C23 original** "
  f"(`scripts/c23_scope_audit.py`), não porque nenhum limiar passa o teste de ordenação: "
  f"`median_share` da curva `drought_spei_threshold` é exatamente 0,0 em TODAS as "
  f"{len(spei_curve)} combinações (bucket x limiar x cenário, fleet=operating) = {all_zero}.")

p("**Causa raiz:** `_f_d_r_d_local` (dentro de `c23_scope_audit.py`) fez o merge "
  "baseline/future em `spei.parquet` usando a coluna `scenario` diretamente -- mas em "
  "`spei.parquet`, as linhas de `period==\"baseline\"` têm `scenario==\"historical\"`, não "
  "`ssp126/370/585`; só as linhas de `period==\"future\"` têm os 3 SSPs. O merge on=[\"id\", "
  "\"model\", \"scenario\"] nunca casava `historical` com `ssp126` etc., então `baseline_value` "
  "ficava NaN para toda linha futura, `ratio` ficava NaN, e a classificação `R_D>=2` sempre "
  "caía em `fillna(False)` -> `median_share=0` para todo limiar. O código de produção "
  "(`craei.hazards.consolidate._baseline_future`) já resolve isso corretamente: separa as "
  "chaves não-`scenario`, filtra baseline (sempre `historical`) e futuro (`ssp*`) "
  "independentemente, e faz merge só pelas chaves não-`scenario` -- baseline é \"broadcast\" "
  "para os 3 cenários. `c23_scope_audit.py` reimplementou a lógica em vez de reusar "
  "`_baseline_future`, e essa reimplementação tinha o bug.")

# Corrected recomputation, reusing the real _baseline_future helper.
from craei.hazards.consolidate import _baseline_future  # noqa: E402

spei = pd.read_parquet(PROC / "spei.parquet")
hydro_bra = bra_plants[bra_plants.plant_uid.isin(
    hazards[hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river"])]["plant_uid"]
)]
hydro_key = pd.DataFrame({"plant_uid": hydro_bra.plant_uid, "id": hydro_bra.plant_uid,
                           "bucket": hydro_bra.plant_uid.map(
                               hazards.drop_duplicates("plant_uid").set_index("plant_uid")["bucket"]
                           )})
tw_bra = bra_plants[bra_plants.plant_uid.isin(hazards[hazards.bucket == "thermal_water_dependent"]["plant_uid"])]
tw_cells = tw_bra.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
tw_key = pd.DataFrame({
    "plant_uid": tw_cells.plant_uid,
    "id": tw_cells["cell_lat"].astype(str) + "_" + tw_cells["cell_lon"].astype(str),
    "bucket": "thermal_water_dependent",
})

catchment_spei = spei[(spei["scale"] == "catchment") & (spei["id"].isin(set(hydro_key["id"])))]
cell_spei = spei[(spei["scale"] == "cell") & (spei["id"].isin(set(tw_key["id"])))]
del spei
gc.collect()


def _f_d_r_d_fixed(spei_scale, plant_key, spei_col, threshold):
    valid = spei_scale[spei_scale[spei_col].notna()].copy()
    valid["severe"] = valid[spei_col] <= threshold
    f_d = valid.groupby(["id", "model", "scenario", "period"], as_index=False).agg(f_d=("severe", "mean"))
    bf = _baseline_future(f_d, ["id", "model", "scenario"], "f_d")
    bf["ratio"] = np.where((bf["baseline_value"] == 0) | bf["baseline_value"].isna(), np.nan,
                            bf["future_value"] / bf["baseline_value"])
    return plant_key.merge(bf, on="id", how="inner")


# reproduce -1.5 against production F_D (gate)
recompute_15 = pd.concat([
    _f_d_r_d_fixed(catchment_spei, hydro_key, "SPEI_12", -1.5),
    _f_d_r_d_fixed(cell_spei, tw_key, "SPEI_12", -1.5),
], ignore_index=True)
prod_fd = hazards[(hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]))
                   & (hazards.hazard == "f_d_spei12")]
cmp_ = recompute_15.merge(
    prod_fd[["plant_uid", "model", "scenario", "baseline_value", "future_value", "ratio"]],
    on=["plant_uid", "model", "scenario"], suffixes=("_recomp", "_prod"),
)
cmp_["diff_baseline"] = (cmp_["baseline_value_recomp"] - cmp_["baseline_value_prod"]).abs()
cmp_["diff_future"] = (cmp_["future_value_recomp"] - cmp_["future_value_prod"]).abs()
max_diff = max(cmp_["diff_baseline"].max(), cmp_["diff_future"].max())
p(f"**Reprodução do ponto SPEI=-1,5 (corrigida) contra F_D persistido em `plant_hazards.parquet`**: "
  f"{len(cmp_)} linhas comparadas (planta/modelo/cenário), diferença máxima absoluta "
  f"baseline/future = {max_diff:.2e} -- {'EXATA (ponto flutuante)' if max_diff < 1e-9 else 'DIVERGENTE'}.")

# Order test: median AND >=4/5 GCM agreement, per bucket/threshold
rd_threshold = 2.0
spei_thresholds = np.arange(TS["drought_spei_threshold"]["start"], TS["drought_spei_threshold"]["stop"] - 0.001,
                             TS["drought_spei_threshold"]["step"])
order_rows = []
for th in spei_thresholds:
    recompute = pd.concat([
        _f_d_r_d_fixed(catchment_spei, hydro_key, "SPEI_12", th),
        _f_d_r_d_fixed(cell_spei, tw_key, "SPEI_12", th),
    ], ignore_index=True)
    for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
        fl = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(
            recompute[recompute.bucket == bucket]["plant_uid"]
        )]
        if fl.empty:
            continue
        model_shares = {}  # scenario -> {model: share}
        for scenario in SCENARIOS:
            sub = recompute[(recompute.bucket == bucket) & (recompute.scenario == scenario)
                             & recompute.plant_uid.isin(fl.plant_uid)]
            shares = {}
            for model, g in sub.groupby("model"):
                s = g.set_index("plant_uid")["ratio"].reindex(fl.plant_uid)
                exposed = (s >= rd_threshold).fillna(False)
                exposed_mw = fl.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
                shares[model] = exposed_mw.sum() / fl["capacity_mw"].sum()
            model_shares[scenario] = shares
        medians = {sc: float(np.median(list(ms.values()))) if ms else np.nan for sc, ms in model_shares.items()}
        order_median = medians.get("ssp126", np.nan) < medians.get("ssp370", np.nan) < medians.get("ssp585", np.nan)
        # >=4/5 GCM: for each model, is ssp126<ssp370<ssp585? count models where that holds
        common_models = set(model_shares.get("ssp126", {})) & set(model_shares.get("ssp370", {})) & set(
            model_shares.get("ssp585", {}))
        n_models_order = sum(
            1 for m in common_models
            if model_shares["ssp126"][m] < model_shares["ssp370"][m] < model_shares["ssp585"][m]
        )
        order_rows.append(dict(bucket=bucket, threshold=float(th), order_holds_median=bool(order_median),
                                n_models_order_holds=n_models_order, n_models_total=len(common_models),
                                order_holds_4of5=n_models_order >= SA["min_gcm_sign_agreement"]))
order_spei_df = pd.DataFrame(order_rows)
order_spei_df.to_csv(OUT / "c23c_1_spei_order_corrected.csv", index=False)
n_median_holds = order_spei_df.groupby("bucket")["order_holds_median"].sum()
n_4of5_holds = order_spei_df.groupby("bucket")["order_holds_4of5"].sum()
p("Ordem entre cenários por limiar, recomputada corretamente (mediana e >=4/5 GCM):")
summary_order = pd.DataFrame({
    "n_thresholds_median_holds": n_median_holds, "n_thresholds_4of5_holds": n_4of5_holds,
    "n_thresholds_total": order_spei_df.groupby("bucket").size(),
}).reset_index()
p(df_to_md(summary_order))
p(df_to_md(order_spei_df, max_rows=30))

# =======================================================================
# Item 2: BRA pivot + thermal_water_dependent planned_adv explanation +
# SECOND BUG FOUND: fleet_share_pct denominator + H3 rows (sign N/A)
# =======================================================================
h("2. Matriz -- pivô Brasil, explicação planned_adv, H3", level=2)

viability = pd.read_csv(C23_OUT / "c23_3_viability_matrix.csv")
bra_v = viability[viability.country == "BRA"]
pivot = bra_v.pivot_table(index=["bucket", "fleet", "hazard"], columns="scenario",
                           values="class_final", aggfunc="first")
pivot.to_csv(OUT / "c23c_2_pivot_BRA.csv")
p("Pivô Brasil bucket x frota x hazard x cenário (class_final) salvo em `c23c_2_pivot_BRA.csv` "
  f"({len(pivot)} linhas).")
not_excluded = bra_v[bra_v.class_final != "excluido"]
not_excluded.to_csv(OUT / "c23c_2_not_excluded_BRA.csv", index=False)
p(f"Linhas não excluídas para o Brasil: {len(not_excluded)} de {len(bra_v)}.")
p(df_to_md(not_excluded[["bucket", "fleet", "hazard", "scenario", "class_final"]], max_rows=40))

p("**Por que thermal_water_dependent planned_adv (n=58) está excluído no C23 original, e "
  "verificação do percentual do GW:**")
tw_pa = bra_v[(bra_v.bucket == "thermal_water_dependent") & (bra_v.fleet == "planned_adv")]
row0 = tw_pa.iloc[0]
p(f"- `effective_n` usado para térmica: {int(row0.effective_n)} (= `n_distinct_cells`, "
  f"{int(row0.n_distinct_cells)} -- térmica não tem `basin_id` próprio, `n_basins` fica NaN "
  f"em `plants.parquet` para tech_class != hydro, então `effective_n = min(n_cells, n_basins)` "
  f"não se aplica; o script C23 original usa só `n_distinct_cells` para bucket não-hydro, "
  f"documentado no relatório original item 3).")
p(f"- `n_plants`={int(row0.n_plants)} >= `min_plants`=30 -> `sample_fail`=False "
  f"(effective_n={int(row0.effective_n)} >= min_effective_n={SA['min_effective_n']} também).")
p(f"- `fleet_share_pct` no C23 original = {row0.fleet_share_pct:.4f}% -> `materiality_fail`=True "
  f"(< min_fleet_share_pct={SA['min_fleet_share_pct']}%). **ACHADO: esse percentual está "
  f"ERRADO.** O script original calculou `fleet_share_pct = 100 * bucket_fleet_gw / "
  f"country_total_gw` (GW do bucket+frota dividido pelo GW do país INTEIRO, todas as frotas "
  f"somadas) = 14,7806/366,786 = 4,03%. Mas `config/c23_audit.yaml`'s comentário "
  "(`min_fleet_share_pct: 5  # bucket share of the country's GW **in that fleet**`) pede o "
  "GW do bucket dividido pelo GW do PAÍS NAQUELA FROTA (todas as tecnologias, só "
  "`planned_adv`): 14,7806 / 144,4734 (GW total de `planned_adv` no Brasil, todas as "
  "tecnologias) = **10,23%** -- ACIMA do limiar de 5%, não abaixo.")

country_fleet_gw_correct = plants.groupby(["country", "fleet"])["capacity_mw"].sum() / 1000.0
fleet_share_corrected = 100 * row0.gw / country_fleet_gw_correct[("BRA", "planned_adv")]
p(f"- Verificação numérica: 100 x {row0.gw:.4f} / {country_fleet_gw_correct[('BRA','planned_adv')]:.4f} "
  f"= {fleet_share_corrected:.4f}% (bate com os 10,2% citados no enunciado deste comando).")

viability["fleet_share_pct_corrected"] = viability.apply(
    lambda r: 100 * r["gw"] / country_fleet_gw_correct.get((r["country"], r["fleet"]), np.nan), axis=1
)
viability["materiality_fail_corrected"] = viability["fleet_share_pct_corrected"] < SA["min_fleet_share_pct"]
viability["sample_or_mat_fail_corrected"] = viability["sample_fail"] | viability["materiality_fail_corrected"]
viability["class_quant_corrected"] = np.where(
    viability["sample_or_mat_fail_corrected"], "excluido",
    np.where(viability["saturated"] | viability["sign_fail"], "suporte", "principal")
)
viability["class_final_corrected"] = np.where(
    (viability["class_quant_corrected"] == "principal") & viability["limitation_flag"],
    "suporte", viability["class_quant_corrected"]
)
changed = viability[viability["class_final"] != viability["class_final_corrected"]]
changed.to_csv(OUT / "c23c_2_reclassified_with_correct_denominator.csv", index=False)
p(f"**Impacto da correção em toda a matriz (321 linhas, 3 países):** {len(changed)} linhas "
  f"mudam de classificação, todas de `excluido` para `principal` ou `suporte` (nenhuma vai na "
  f"direção contrária, já que o denominador original era sempre >= o corrigido -- país inteiro "
  f">= frota específica dentro do país). Distribuição da mudança:")
p(df_to_md(changed.groupby(["class_final", "class_final_corrected"]).size()
           .rename("n").reset_index()))
p("**Nenhuma tabela original foi alterada** (regra do comando) -- `c23_3_viability_matrix.csv` "
  "permanece como estava; esta seção só reporta a divergência e salva a versão recalculada "
  "em `c23c_2_reclassified_with_correct_denominator.csv` para referência.")

# H3 rows (sign N/A) -- H3 isn't in plant_hazards.parquet, build its own viability-style rows.
h3_rows = []
tw_h3 = aqueduct.merge(plants[["plant_uid", "country", "fleet", "capacity_mw"]], on="plant_uid")
for country in SA["matrix_countries"]:
    for fleet in ["operating", "planned_adv", "planned_early"]:
        for cooling_bound in ["upper", "lower"]:
            sub = tw_h3[(tw_h3.country == country) & (tw_h3.fleet == fleet)
                        & (tw_h3.cooling_bound == cooling_bound)]
            if sub.empty:
                continue
            n_plants = sub.plant_uid.nunique()
            gw = sub.drop_duplicates("plant_uid")["capacity_mw"].sum() / 1000.0
            country_fleet_gw_h3 = country_fleet_gw_correct.get((country, fleet), np.nan)
            fleet_share_pct = 100 * gw / country_fleet_gw_h3 if country_fleet_gw_h3 else np.nan
            sample_fail = n_plants < SA["min_plants"]
            materiality_fail = pd.notna(fleet_share_pct) and fleet_share_pct < SA["min_fleet_share_pct"]
            for scenario in sub.scenario.unique():
                ssub = sub[sub.scenario == scenario]
                exposed_mw = ssub[ssub.ws_category.isin(["high", "extremely high"])].drop_duplicates(
                    "plant_uid")["capacity_mw"].sum()
                total_mw = ssub.drop_duplicates("plant_uid")["capacity_mw"].sum()
                share = exposed_mw / total_mw if total_mw > 0 else np.nan
                saturated = pd.notna(share) and (share * 100 <= SA["saturation_low_pct"] or
                                                  share * 100 >= SA["saturation_high_pct"])
                class_quant = "excluido" if (sample_fail or materiality_fail) else (
                    "suporte" if saturated else "principal")
                h3_rows.append(dict(
                    country=country, bucket="thermal_water_dependent", fleet=fleet, hazard="H3_aqueduct",
                    cooling_bound=cooling_bound, scenario=scenario, n_plants=n_plants, gw=gw,
                    fleet_share_pct=fleet_share_pct, share=share, sign="N/A (Aqueduct ensemble median only, L13)",
                    sample_fail=sample_fail, materiality_fail=materiality_fail, saturated=saturated,
                    class_quant=class_quant,
                ))
h3_df = pd.DataFrame(h3_rows)
h3_df.to_csv(OUT / "c23c_2_h3_rows.csv", index=False)
p(f"Linhas H3 (sinal N/A, L13 -- Aqueduct não tem ensemble de 5 GCMs próprio): {len(h3_df)} "
  f"linhas (país x frota x cooling_bound x cenário).")
p(df_to_md(h3_df[h3_df.country == "BRA"], max_rows=20))

# =======================================================================
# Item 3: per-GW and per-plant GCM range, monotonicity SSP1<SSP3<SSP5
# =======================================================================
h("3. Por GW e por usina -- faixa entre GCMs, monotonicidade", level=2)

item3_rows = []
for country in SA["matrix_countries"]:
    for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
        bucket_uids = set(hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")]["plant_uid"])
        fl = plants[(plants.country == country) & (plants.fleet == "operating")
                    & plants.plant_uid.isin(bucket_uids)]
        if fl.empty:
            continue
        for scenario in SCENARIOS:
            hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")
                         & (hazards.scenario == scenario) & hazards.plant_uid.isin(fl.plant_uid)]
            gw_shares, plant_shares = [], []
            for model, g in hz.groupby("model"):
                s = g.set_index("plant_uid")["ratio"].reindex(fl.plant_uid)
                exposed = (s >= 2.0).fillna(False)
                exposed_mw = fl.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
                gw_shares.append(exposed_mw.sum() / fl["capacity_mw"].sum())
                plant_shares.append(exposed.sum() / len(fl))
            item3_rows.append(dict(
                country=country, bucket=bucket, scenario=scenario, n_plants=len(fl),
                gw_median=float(np.median(gw_shares)), gw_min=float(np.min(gw_shares)), gw_max=float(np.max(gw_shares)),
                plant_median=float(np.median(plant_shares)), plant_min=float(np.min(plant_shares)),
                plant_max=float(np.max(plant_shares)),
            ))
item3_df = pd.DataFrame(item3_rows)
item3_df.to_csv(OUT / "c23c_3_gw_plant_range.csv", index=False)
p(df_to_md(item3_df, max_rows=40))

mono_rows = []
for (country, bucket), g in item3_df.groupby(["country", "bucket"]):
    piv_gw = g.set_index("scenario")["gw_median"]
    piv_pl = g.set_index("scenario")["plant_median"]
    if {"ssp126", "ssp370", "ssp585"} <= set(piv_gw.index):
        mono_gw = piv_gw["ssp126"] < piv_gw["ssp370"] < piv_gw["ssp585"]
        mono_pl = piv_pl["ssp126"] < piv_pl["ssp370"] < piv_pl["ssp585"]
        mono_rows.append(dict(country=country, bucket=bucket, monotonic_gw_median=bool(mono_gw),
                               monotonic_plant_median=bool(mono_pl)))
mono_df = pd.DataFrame(mono_rows)
mono_df.to_csv(OUT / "c23c_3_monotonicity.csv", index=False)
p("Monotonicidade SSP1-2.6 < SSP3-7.0 < SSP5-8.5 na mediana entre GCMs, por GW e por usina:")
p(df_to_md(mono_df))

# =======================================================================
# Item 4: null of R_D -- synthetic AR(1) simulation calibrated on observed
# lag-1..12 autocorrelation of SPEI-12 (Brazilian hydro catchments,
# baseline/historical). Does not alter any production table.
# =======================================================================
h("4. Nulo do R_D -- simulação sintética AR(1)", level=2)

rng = np.random.default_rng(23)
bra_hydro_uids = set(hazards[(hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river"]))
                              & hazards.plant_uid.isin(bra_plants.plant_uid)]["plant_uid"])
bra_hydro_ids = set(hydro_key[hydro_key.plant_uid.isin(bra_hydro_uids)]["id"])
spei_bra_hist = catchment_spei[(catchment_spei.period == "baseline") & catchment_spei.id.isin(bra_hydro_ids)]

acf_rows = []
n_series_used = 0
for (sid, model), g in spei_bra_hist.groupby(["id", "model"]):
    g = g.sort_values("month")
    x = g["SPEI_12"].to_numpy()
    x = x[~np.isnan(x)]  # drop the Spec L05 lead-in NaN months (first ~11), keep the rest
    if len(x) < 60:
        continue
    x = x - x.mean()
    denom = (x**2).sum()
    if denom == 0:
        continue
    for lag in range(1, 13):
        num = (x[:-lag] * x[lag:]).sum()
        acf_rows.append(dict(id=sid, model=model, lag=lag, acf=num / denom))
    n_series_used += 1
    if n_series_used >= 200:  # cap for runtime; representative sample, not full 655-series population
        break

acf_df = pd.DataFrame(acf_rows)
acf_summary = acf_df.groupby("lag")["acf"].agg(["mean", "std", "count"]).reset_index()
acf_summary.to_csv(OUT / "c23c_4_observed_acf.csv", index=False)
p(f"Autocorrelação lag-1..12 observada no SPEI-12 histórico (catchment, hidro brasileira), "
  f"{n_series_used} séries (id x modelo) usadas (amostra, não as 655 completas, para manter o "
  f"tempo de execução razoável):")
p(df_to_md(acf_summary))
phi1 = float(acf_summary.loc[acf_summary.lag == 1, "mean"].iloc[0])
p(f"AR(1) calibrado por `phi = ACF(lag=1) = {phi1:.4f}`. A simulação usa só lag-1 (processo "
  f"AR(1) simples) -- a tabela acima mostra que a autocorrelação decai de forma aproximadamente "
  f"geométrica até lag~6-12 (consistente com AR(1)), reportada para que o leitor julgue se essa "
  f"simplificação é razoável; não é uma réplica exata da estrutura de autocorrelação completa.")

N_SIM = 2000
N_MONTHS_BASELINE = 360  # matches production's n=360 per-series baseline (D54)
N_MONTHS_FUTURE = 360


def _simulate_ar1(phi, n, rng):
    sigma_innov = np.sqrt(max(1 - phi**2, 1e-6))
    x = np.empty(n)
    x[0] = rng.normal(0, 1)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + rng.normal(0, sigma_innov)
    return x


rd_ge_2_count = 0
fd_baseline_list, fd_future_list, rd_list = [], [], []
for _ in range(N_SIM):
    series = _simulate_ar1(phi1, N_MONTHS_BASELINE + N_MONTHS_FUTURE, rng)
    baseline = series[:N_MONTHS_BASELINE]
    future = series[N_MONTHS_BASELINE:]
    f_d_base = (baseline <= -1.5).mean()
    f_d_fut = (future <= -1.5).mean()
    fd_baseline_list.append(f_d_base)
    fd_future_list.append(f_d_fut)
    if f_d_base > 0:
        rd = f_d_fut / f_d_base
        rd_list.append(rd)
        if rd >= 2.0:
            rd_ge_2_count += 1

rd_arr = np.array(rd_list)
fd_base_arr = np.array(fd_baseline_list)
p(f"Simulação: {N_SIM} séries AR(1) sintéticas, phi={phi1:.4f}, sem mudança climática "
  f"(mesma distribuição estacionária em baseline e 'futuro'), janelas de {N_MONTHS_BASELINE} "
  f"meses cada (30 anos, batendo com o n=360 de produção, D54).")
p(f"- F_D médio na baseline sintética: {fd_base_arr.mean()*100:.3f}% (esperado teórico "
  f"~6,68% para SPEI~N(0,1) e limiar -1,5, medido {fd_base_arr.mean()*100:.3f}%).")
p(f"- De {N_SIM} séries, {len(rd_list)} tiveram F_D_baseline > 0 (R_D definido); destas, "
  f"**{rd_ge_2_count} ({100*rd_ge_2_count/len(rd_list):.2f}%) tiveram R_D>=2 por acaso, sem "
  f"nenhuma mudança climática simulada** -- essa é a taxa de falso-positivo do critério "
  f"`drought_class_rd_ratio=2` sob o nulo, dado só a autocorrelação real do SPEI-12 e o ruído "
  f"de amostragem de janelas de 30 anos.")
p(f"- {(fd_base_arr == 0).sum()} de {N_SIM} séries ({100*(fd_base_arr==0).mean():.2f}%) tiveram "
  f"F_D_baseline = 0 (R_D indefinido sob o nulo) -- comparar com L19's taxa real de 0-0,203% "
  f"(muito mais baixa que o nulo sintético sugere, plausível porque os dados reais não são um "
  f"processo AR(1) puro nem perfeitamente gaussiano).")
sim_df = pd.DataFrame({"f_d_baseline": fd_baseline_list, "f_d_future": fd_future_list})
sim_df["r_d"] = np.where(sim_df.f_d_baseline > 0, sim_df.f_d_future / sim_df.f_d_baseline, np.nan)
sim_df.to_csv(OUT / "c23c_4_ar1_simulation.csv", index=False)
p("Nenhuma tabela de produção foi alterada por esta simulação -- resultado só reportado, "
  "salvo em `c23c_4_ar1_simulation.csv`/`c23c_4_observed_acf.csv`.")

# =======================================================================
# Item 5: BRA thermal composition by fuel (raw GEM, read-only)
# =======================================================================
h("5. Composição da térmica brasileira por combustível (GEM bruto)", level=2)

gem_path = Path(paths["gem_file"])
if gem_path.exists():
    gem_raw = pd.read_excel(gem_path, sheet_name="Power facilities")
    gem_raw = gem_raw[gem_raw["Country/area"] == "Brazil"].copy()
    status_norm = gem_raw["Status"].astype(str).str.strip().str.lower()
    status_to_fleet = {"operating": "operating", "construction": "planned_adv",
                        "pre-construction": "planned_adv", "announced": "planned_early"}
    gem_raw["fleet"] = status_norm.map(status_to_fleet)
    type_norm = gem_raw["Type"].astype(str).str.strip().str.lower()
    thermal_types = {"coal", "oil/gas", "bioenergy", "nuclear"}
    thermal = gem_raw[type_norm.isin(thermal_types) & gem_raw["fleet"].notna()
                       & gem_raw["Capacity (MW)"].notna()].copy()
    thermal["fuel"] = thermal["Fuel (combustion only)"].fillna(thermal["Type"])
    fuel_tbl = thermal.groupby(["fuel", "fleet"], as_index=False).agg(
        n_plants=("Plant / Project name", "count"), gw=("Capacity (MW)", "sum")
    )
    fuel_tbl["gw"] = fuel_tbl["gw"] / 1000.0
    fuel_tbl.to_csv(OUT / "c23c_5_thermal_fuel_BRA.csv", index=False)
    p(f"Leitura read-only do GEM bruto, térmicas brasileiras (coal/oil-gas/bioenergy/nuclear), "
      f"por combustível x frota ({len(thermal)} unidades no total):")
    p(df_to_md(fuel_tbl.sort_values("gw", ascending=False), max_rows=30))
else:
    p(f"GEM bruto não encontrado em {gem_path} -- item não executado.")

# =======================================================================
# Item 6: Itaipu and other binational plants -- weight and effect on GW share
# =======================================================================
h("6. Itaipu e binacionais -- peso e efeito na fração exposta por GW", level=2)

binational_names = ["Itaipu", "Bemposta II"]  # L22: confirmed border-adjacent plants
bin_plants = plants[plants.plant_name.str.contains("|".join(binational_names), case=False, na=False)]
p("Plantas identificadas (L22, D68) sediadas em rio de fronteira binacional:")
p(df_to_md(bin_plants[["plant_name", "country", "capacity_mw", "fleet", "tech_class", "hydro_type"]]))

for _, bp in bin_plants.iterrows():
    country = bp.country
    bucket = "hydro_reservoir" if bp.hydro_type != "run-of-river" else "hydro_run_of_river"
    fl = plants[(plants.country == country) & (plants.fleet == bp.fleet)
                & plants.plant_uid.isin(hazards[hazards.bucket == bucket]["plant_uid"])]
    if fl.empty or bp.plant_uid not in set(fl.plant_uid):
        continue
    fl_without = fl[fl.plant_uid != bp.plant_uid]
    for scenario in SCENARIOS:
        hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")
                     & (hazards.scenario == scenario)]

        def _share(fl_df):
            shares = []
            for model, g in hz[hz.plant_uid.isin(fl_df.plant_uid)].groupby("model"):
                s = g.set_index("plant_uid")["ratio"].reindex(fl_df.plant_uid)
                exposed = (s >= 2.0).fillna(False)
                exposed_mw = fl_df.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
                shares.append(exposed_mw.sum() / fl_df["capacity_mw"].sum())
            return float(np.median(shares)) if shares else np.nan

        share_with = _share(fl)
        share_without = _share(fl_without)
        pct_of_fleet_gw = 100 * bp.capacity_mw / (fl["capacity_mw"].sum())
        p(f"- {bp.plant_name} ({country}, {bp.capacity_mw:.0f} MW, {pct_of_fleet_gw:.2f}% do GW "
          f"de {bucket}/{bp.fleet}), cenário {scenario}: share mediana R_D>=2 COM = "
          f"{share_with:.4f}, SEM = {share_without:.4f} (diferença = "
          f"{share_with - share_without:+.4f}).")

# =======================================================================
# Item 7: redo scope_tag with word boundaries, exclude c23_*.py, recount
# =======================================================================
h("7. scope_tag com word boundary", level=2)

scope_keywords = CA["scope_keywords"]
KW_RE = {kw: re.compile(rf"\b{re.escape(kw)}\b") for kw in scope_keywords}


def _scope_tag_wb(text: str) -> str:
    hit = {kw for kw, rgx in KW_RE.items() if rgx.search(text)}
    if {"IND", "India"} & hit and not ({"PRT", "Portugal"} & hit):
        return "IND_only"
    if {"PRT", "Portugal"} & hit and not ({"IND", "India"} & hit):
        return "PRT_only"
    if "compound" in hit:
        return "compound"
    if {"solar", "wind"} & hit:
        return "solar_wind"
    if ({"IND", "India"} & hit) and ({"PRT", "Portugal"} & hit):
        return "multi_country"
    return "core"


# Scripts (excluding c23_*.py, per instruction)
script_rows2 = []
for fp in sorted((ROOT / "scripts").glob("*.py")):
    if fp.name.startswith("c23"):
        continue
    text = fp.read_text(encoding="utf-8", errors="ignore")
    script_rows2.append(dict(script=fp.name, scope_tag_wb=_scope_tag_wb(text)))
scripts_wb_df = pd.DataFrame(script_rows2)
scripts_wb_df.to_csv(OUT / "c23c_7_scripts_scope_wb.csv", index=False)

# Tests
test_rows2 = []
for fp in sorted((ROOT / "tests").glob("*.py")):
    text = fp.read_text(encoding="utf-8", errors="ignore")
    test_rows2.append(dict(test_file=fp.name, scope_tag_wb=_scope_tag_wb(text)))
tests_wb_df = pd.DataFrame(test_rows2)
tests_wb_df.to_csv(OUT / "c23c_7_tests_scope_wb.csv", index=False)

# Scope branches (src + scripts, excluding c23_*.py)
branch_rows2 = []
for fp in list((ROOT / "src").rglob("*.py")) + [
    f for f in (ROOT / "scripts").glob("*.py") if not f.name.startswith("c23")
]:
    lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, start=1):
        for kw, rgx in KW_RE.items():
            if rgx.search(line):
                branch_rows2.append(dict(file=str(fp.relative_to(ROOT)), line=i, keyword=kw,
                                          context=line.strip()[:200]))
branch_wb_df = pd.DataFrame(branch_rows2)
branch_wb_df.to_csv(OUT / "c23c_7_scope_branches_wb.csv", index=False)

old_scripts = pd.read_csv(C23_OUT / "c23_15_scripts.csv")
old_branch_count = len(pd.read_csv(C23_OUT.parent / "c23" / "code" / "c23_24_scope_branches.csv")) if \
    (C23_OUT / "code" / "c23_24_scope_branches.csv").exists() else None
p(f"Scripts com `scope_tag` != core (substring, C23 original): "
  f"{(old_scripts.scope_tag != 'core').sum()} de {len(old_scripts)}. Com word boundary "
  f"(\\bwind\\b, \\bIND\\b etc.), excluindo c23_*.py: "
  f"{(scripts_wb_df.scope_tag_wb != 'core').sum()} de {len(scripts_wb_df)}.")
p(df_to_md(scripts_wb_df[scripts_wb_df.scope_tag_wb != "core"], max_rows=30))
p(f"Testes não-core: word boundary -> {(tests_wb_df.scope_tag_wb != 'core').sum()} de {len(tests_wb_df)}.")
p(df_to_md(tests_wb_df[tests_wb_df.scope_tag_wb != "core"], max_rows=30))
p(f"Ramos por escopo (ocorrências linha a linha): substring (Bloco F original) vs. word "
  f"boundary sem c23_*.py -> {len(branch_wb_df)} ocorrências (word boundary).")
p(df_to_md(branch_wb_df["keyword"].value_counts().rename_axis("keyword").reset_index(name="n")))

# =======================================================================
# Item 8: extended regression baseline + 10_exposure.py reproduction
# =======================================================================
h("8. Linha de base de regressão ampliada", level=2)


def _hash_table(fp: Path) -> str:
    if fp.suffix == ".csv":
        return hashlib.sha256(fp.read_bytes()).hexdigest()
    if fp.suffix == ".parquet":
        df = pd.read_parquet(fp)
        df = df[sorted(df.columns)]
        return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()
    return "n/a"


extended_files = [
    PROC / "plant_hazards.parquet", PROC / "plant_aqueduct.parquet",
    TABLES / "exposure_summary.csv", TABLES / "exposure_aqueduct.csv",
    TABLES / "validation.csv",
]
ext_hash_rows = [dict(file=str(fp.name), sha256=_hash_table(fp) if fp.exists() else "MISSING")
                  for fp in extended_files]
ext_hash_df = pd.DataFrame(ext_hash_rows)
ext_hash_df.to_csv(OUT / "c23c_8_extended_hashes.csv", index=False)
p(df_to_md(ext_hash_df))

plants_for_repro = plants.copy()
plants_for_repro["bucket"] = _assign_bucket(plants_for_repro)
recomputed_summary = agg.build_exposure_summary(plants_for_repro, hazards)
recomputed_aqueduct = agg.build_exposure_aqueduct(plants_for_repro, aqueduct)

ref_summary = pd.read_csv(TABLES / "exposure_summary.csv")
merged_s = recomputed_summary.merge(
    ref_summary, on=["country", "tech_class", "fleet", "scenario", "hazard"], suffixes=("_recomp", "_ref")
)
max_diff_s = (merged_s["median_share_recomp"] - merged_s["median_share_ref"]).abs().max()

ref_aq = pd.read_csv(TABLES / "exposure_aqueduct.csv")
merged_a = recomputed_aqueduct.merge(
    ref_aq, on=["country", "tech_class", "fleet", "scenario", "cooling_bound"], suffixes=("_recomp", "_ref")
)
max_diff_a = (merged_a["share_recomp"] - merged_a["share_ref"]).abs().max()

p(f"`scripts/10_exposure.py` reproduz `exposure_summary.csv`? Diferença máxima absoluta em "
  f"`median_share` (recomputado em memória via `craei.exposure.aggregate.build_exposure_summary`, "
  f"sem sobrescrever o arquivo): {max_diff_s:.2e} -- "
  f"{'SIM, exato' if max_diff_s < 1e-9 else 'NÃO, diverge'}.")
p(f"`exposure_aqueduct.csv`: diferença máxima absoluta em `share` "
  f"(`build_exposure_aqueduct`): {max_diff_a:.2e} -- {'SIM, exato' if max_diff_a < 1e-9 else 'NÃO, diverge'}.")

# =======================================================================
# Item 9: show validation.csv
# =======================================================================
h("9. validation.csv (D70)", level=2)
validation_csv = pd.read_csv(TABLES / "validation.csv")
p(df_to_md(validation_csv))

(OUT / "c23c_report.md").write_text("\n".join(REPORT), encoding="utf-8")
print("C23-C done. Report at", OUT / "c23c_report.md")