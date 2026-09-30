"""COMANDO 23-D: fix the null, test PET/SPI, and diagnose (read-only except outputs_audit_dir/c23/c23d/).

Does not alter production tables. Does not decide scope. Reads config/c23_audit.yaml.
"""

import gc
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from craei.config import load_datasets, load_paths  # noqa: E402
from craei.hazards.consolidate import _baseline_future  # noqa: E402

paths = load_paths()
datasets = load_datasets()
AUDIT = yaml.safe_load(open(ROOT / "config" / "c23_audit.yaml", encoding="utf-8"))
SA = AUDIT["scope_audit"]
TS = AUDIT["threshold_sweeps"]

PROC = Path(paths["processed_dir"])
TABLES = Path(paths["outputs_tables_dir"])
OUT = Path(paths["outputs_dir"]) / "audit" / "c23" / "c23d"
OUT.mkdir(parents=True, exist_ok=True)

SCENARIOS = [s for s in datasets["scenarios"] if s != "historical"]
MODELS = datasets["models"]
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
hazards = pd.read_parquet(PROC / "plant_hazards.parquet")
bra_plants = plants[plants.country == "BRA"]
bucket_of = hazards.drop_duplicates("plant_uid").set_index("plant_uid")["bucket"]

h("COMANDO 23-D -- fix null, test PET/SPI, diagnose", level=1)

# =======================================================================
# Item 1: diagnose the "DIVERGENT" reproduction (diff 94.7)
# =======================================================================
h("1. Diagnóstico da reprodução DIVERGENTE (diff 94,7)", level=2)

p("**Causa: unidade/escala, não erro de chave.** `craei.hazards.consolidate._f_d_r_d` "
  "(produção) escala F_D para PERCENTUAL antes de persistir: "
  "`f_d[\"f_d\"] = f_d[\"f_d\"] * 100.0` (linha ~148 de `src/craei/hazards/consolidate.py`) -- "
  "`plant_hazards.parquet`'s `baseline_value`/`future_value` para `f_d_spei12` estão em "
  "**0-100 (percentual)**. O script `scripts/c23c_checks.py` (COMANDO 23-C, item 1) chamou "
  "`_baseline_future` corretamente (chaves certas, resolveu o bug do merge "
  "`historical` vs `ssp*`), mas **não multiplicou por 100** -- seu `f_d` recomputado ficou em "
  "0-1 (fração). `ratio` (R_D) não é afetado (a escala cancela: future/baseline com ambos "
  "em fração OU ambos em percentual dá o mesmo número), mas a comparação direta "
  "`baseline_value_recomp` (fração, ex. 0,065) vs `baseline_value_prod` (percentual, ex. 6,5) "
  "produz diferenças de até ~99x o valor -- explicando o máximo observado de 94,7 (um caso "
  "com F_D próximo de 94,7% vs 0,947 recomputado, diff = 94,7 - 0,947 ≈ 93,75, na faixa "
  "do que foi medido).")

from craei.hazards.consolidate import _f_d_r_d  # noqa: E402 -- import the real production function directly

spei = pd.read_parquet(PROC / "spei.parquet")
hydro_bra = bra_plants[bra_plants.plant_uid.isin(
    hazards[hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river"])]["plant_uid"]
)]
hydro_key = pd.DataFrame({
    "plant_uid": hydro_bra.plant_uid, "bucket": hydro_bra.plant_uid.map(bucket_of),
    "id": hydro_bra.plant_uid,
})
tw_bra = bra_plants[bra_plants.plant_uid.isin(hazards[hazards.bucket == "thermal_water_dependent"]["plant_uid"])]
tw_cells = tw_bra.merge(plant_cell, on="plant_uid", how="left").dropna(subset=["cell_lat", "cell_lon"])
tw_key = pd.DataFrame({
    "plant_uid": tw_cells.plant_uid, "bucket": "thermal_water_dependent",
    "id": tw_cells["cell_lat"].astype(str) + "_" + tw_cells["cell_lon"].astype(str),
})

catchment_spei = spei[(spei["scale"] == "catchment") & (spei["id"].isin(set(hydro_key["id"])))]
cell_spei = spei[(spei["scale"] == "cell") & (spei["id"].isin(set(tw_key["id"])))]
del spei
gc.collect()

# Call craei.hazards.consolidate._f_d_r_d DIRECTLY (item 1's instruction), threshold=-1.5.
r_hydro_res, _ = _f_d_r_d(catchment_spei, hydro_key[hydro_key.bucket == "hydro_reservoir"], "SPEI_12",
                          "f_d_spei12", -1.5)
r_hydro_ror, _ = _f_d_r_d(catchment_spei, hydro_key[hydro_key.bucket == "hydro_run_of_river"], "SPEI_12",
                          "f_d_spei12", -1.5)
r_tw, _ = _f_d_r_d(cell_spei, tw_key, "SPEI_12", "f_d_spei12", -1.5)
recompute_direct = pd.concat([r_hydro_res, r_hydro_ror, r_tw], ignore_index=True)

prod_fd = hazards[(hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]))
                   & (hazards.hazard == "f_d_spei12")]
cmp_direct = recompute_direct.merge(
    prod_fd[["plant_uid", "model", "scenario", "baseline_value", "future_value", "ratio"]],
    on=["plant_uid", "model", "scenario"], suffixes=("_recomp", "_prod"),
)
cmp_direct["diff_baseline"] = (cmp_direct["baseline_value_recomp"] - cmp_direct["baseline_value_prod"]).abs()
cmp_direct["diff_future"] = (cmp_direct["future_value_recomp"] - cmp_direct["future_value_prod"]).abs()
cmp_direct["diff_ratio"] = (cmp_direct["ratio_recomp"] - cmp_direct["ratio_prod"]).abs()
diff_by_bucket = cmp_direct.groupby("bucket")[["diff_baseline", "diff_future", "diff_ratio"]].max().reset_index()
diff_by_bucket.to_csv(OUT / "c23d_1_diff_by_bucket.csv", index=False)
p(f"**Chamando `craei.hazards.consolidate._f_d_r_d` diretamente** (não uma reimplementação), "
  f"{len(cmp_direct)} linhas comparadas. Diferença máxima após o ajuste (usando a função de "
  f"produção real, sem reimplementar nada), por bucket:")
p(df_to_md(diff_by_bucket))
overall_max = cmp_direct[["diff_baseline", "diff_future", "diff_ratio"]].max().max()
p(f"Diferença máxima geral: {overall_max:.2e} -- "
  f"{'EXATA (ponto flutuante)' if overall_max < 1e-9 else 'AINDA DIVERGENTE, investigar mais'}.")
p("**Colunas comparadas**: `baseline_value`, `future_value` (ambas agora produzidas por "
  "`_f_d_r_d`, já escaladas x100 internamente -- chamando a função real em vez de reimplementar "
  "elimina o risco de esquecer esse fator) e `ratio` (R_D, não afetado pela escala). **Chaves "
  "do merge**: `plant_uid`, `model`, `scenario` (as mesmas 3 chaves do C23-C, já corretas -- o "
  "erro nunca esteve nas chaves, só na escala de F_D).")

# =======================================================================
# Item 2: corrected null -- (a) year-block bootstrap of real historical
# SPEI-12, (b) standardized 12-month moving sum of white noise.
# =======================================================================
h("2. Nulo corrigido -- bootstrap em blocos e ruído branco", level=2)

rng = np.random.default_rng(23)
N_SIM = 2000
N_MONTHS = 360  # matches production n=360 baseline fit (D54)
BLOCK = 12

bra_hydro_uids = set(hazards[(hazards.bucket.isin(["hydro_reservoir", "hydro_run_of_river"]))
                              & hazards.plant_uid.isin(bra_plants.plant_uid)]["plant_uid"])
bra_hydro_ids = set(hydro_key[hydro_key.plant_uid.isin(bra_hydro_uids)]["id"])
spei_bra_hist = catchment_spei[(catchment_spei.period == "baseline") & catchment_spei.id.isin(bra_hydro_ids)]

# Pool of real historical series (id, model), each a clean (NaN-dropped) 1D array.
real_series_pool = []
for (sid, model), g in spei_bra_hist.groupby(["id", "model"]):
    x = g.sort_values("month")["SPEI_12"].to_numpy()
    x = x[~np.isnan(x)]
    if len(x) >= N_MONTHS:
        real_series_pool.append(x[-N_MONTHS:])  # most recent N_MONTHS, matches production window
p(f"Pool de séries reais para bootstrap em blocos: {len(real_series_pool)} séries "
  f"(id x modelo), cada uma com {N_MONTHS} meses.")


def _block_bootstrap_series(pool, n_months, block, rng):
    base_series = pool[rng.integers(0, len(pool))]
    n_blocks = n_months // block
    starts = rng.integers(0, len(base_series) - block + 1, size=n_blocks)
    return np.concatenate([base_series[s:s + block] for s in starts])


def _white_noise_moving_sum(n_months, block, rng):
    noise = rng.normal(0, 1, size=n_months + block - 1)
    roll = np.convolve(noise, np.ones(block), mode="valid")  # length n_months
    return (roll - roll.mean()) / roll.std()


null_results = {"block_bootstrap": [], "white_noise_ms12": []}
for kind in null_results:
    for _ in range(N_SIM):
        if kind == "block_bootstrap":
            baseline = _block_bootstrap_series(real_series_pool, N_MONTHS, BLOCK, rng)
            future = _block_bootstrap_series(real_series_pool, N_MONTHS, BLOCK, rng)
        else:
            baseline = _white_noise_moving_sum(N_MONTHS, BLOCK, rng)
            future = _white_noise_moving_sum(N_MONTHS, BLOCK, rng)
        null_results[kind].append((baseline, future))

# R_D >= 2 rate under each null (fixed SPEI threshold -1.5, matching production)
rate_rows = []
for kind, sims in null_results.items():
    rd_vals, fd_base_vals = [], []
    for baseline, future in sims:
        fd_b = (baseline <= -1.5).mean()
        fd_f = (future <= -1.5).mean()
        fd_base_vals.append(fd_b)
        if fd_b > 0:
            rd_vals.append(fd_f / fd_b)
    rd_arr = np.array(rd_vals)
    rate_rows.append(dict(
        null=kind, n_sim=N_SIM, n_rd_defined=len(rd_vals),
        pct_rd_ge_2=100 * (rd_arr >= 2.0).mean() if len(rd_arr) else np.nan,
        mean_fd_baseline_pct=100 * np.mean(fd_base_vals),
        pct_fd_baseline_zero=100 * np.mean(np.array(fd_base_vals) == 0),
    ))
rate_df = pd.DataFrame(rate_rows)
rate_df.to_csv(OUT / "c23d_2_null_rates.csv", index=False)
p(f"Taxa de R_D>=2 sob cada nulo (limiar SPEI=-1,5, N_SIM={N_SIM}, janelas de {N_MONTHS} meses, "
  f"semente fixa=23):")
p(df_to_md(rate_df))

# False-positive curve: R_D threshold 1-4 and SPEI threshold -0.5..-2.5, for both nulls.
rd_thresholds = np.arange(TS["drought_rd_ratio"]["start"], TS["drought_rd_ratio"]["stop"] + 0.001,
                           TS["drought_rd_ratio"]["step"])
spei_thresholds = np.arange(TS["drought_spei_threshold"]["start"], TS["drought_spei_threshold"]["stop"] - 0.001,
                             TS["drought_spei_threshold"]["step"])
curve_rows = []
for kind, sims in null_results.items():
    for spei_th in spei_thresholds:
        fd_pairs = [((b <= spei_th).mean(), (f <= spei_th).mean()) for b, f in sims]
        rd_all = np.array([fb_f / fb_b for fb_b, fb_f in fd_pairs if fb_b > 0])
        for rd_th in rd_thresholds:
            curve_rows.append(dict(
                null=kind, spei_threshold=float(spei_th), rd_threshold=float(rd_th),
                pct_false_positive=100 * (rd_all >= rd_th).mean() if len(rd_all) else np.nan,
                n_rd_defined=len(rd_all),
            ))
fp_curve_df = pd.DataFrame(curve_rows)
fp_curve_df.to_csv(OUT / "c23d_2_false_positive_curve.csv", index=False)
p(f"Curva de falso-positivo (R_D 1-4 x SPEI -0,5 a -2,5), {len(fp_curve_df)} linhas, salva em "
  f"`c23d_2_false_positive_curve.csv`. Amostra no ponto de produção (SPEI=-1,5, R_D>=2):")
sample = fp_curve_df[(fp_curve_df.spei_threshold.round(2) == -1.5) & (fp_curve_df.rd_threshold == 2.0)]
p(df_to_md(sample))

# =======================================================================
# Item 3: excess over null, BRA operating, by GW and by plant, GCM range
# =======================================================================
h("3. Excesso sobre o nulo -- Brasil, operante", level=2)

null_rate_bb = rate_df.loc[rate_df.null == "block_bootstrap", "pct_rd_ge_2"].iloc[0]
null_rate_wn = rate_df.loc[rate_df.null == "white_noise_ms12", "pct_rd_ge_2"].iloc[0]
p(f"Taxa de referência do nulo (R_D>=2, SPEI=-1,5): bootstrap em blocos = {null_rate_bb:.2f}%, "
  f"ruído branco padronizado = {null_rate_wn:.2f}%.")

item3_rows = []
for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
    bucket_uids = set(hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")]["plant_uid"])
    fl = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(bucket_uids)]
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
            gw_shares.append(100 * exposed_mw.sum() / fl["capacity_mw"].sum())
            plant_shares.append(100 * exposed.sum() / len(fl))
        item3_rows.append(dict(
            bucket=bucket, scenario=scenario,
            observed_gw_pct_median=float(np.median(gw_shares)), observed_gw_pct_min=float(np.min(gw_shares)),
            observed_gw_pct_max=float(np.max(gw_shares)),
            observed_plant_pct_median=float(np.median(plant_shares)), observed_plant_pct_min=float(np.min(plant_shares)),
            observed_plant_pct_max=float(np.max(plant_shares)),
            excess_gw_pct_vs_block_bootstrap=float(np.median(gw_shares)) - null_rate_bb,
            excess_plant_pct_vs_block_bootstrap=float(np.median(plant_shares)) - null_rate_bb,
            excess_gw_pct_vs_white_noise=float(np.median(gw_shares)) - null_rate_wn,
            excess_plant_pct_vs_white_noise=float(np.median(plant_shares)) - null_rate_wn,
        ))
item3_df = pd.DataFrame(item3_rows)
item3_df.to_csv(OUT / "c23d_3_excess_over_null.csv", index=False)
p(df_to_md(item3_df, max_rows=30))

# =======================================================================
# Item 4: SPI-12 in place of SPEI-12, same buckets, same null
# =======================================================================
h("4. SPI-12 no lugar de SPEI-12", level=2)
p("`spei.parquet`'s `SPI_12` column usada diretamente -- sem reajuste de distribuição "
  "(SPI usa só precipitação, já ajustado na mesma passada que gerou o arquivo; nenhum "
  "`fit_baseline*` chamado aqui).")


def _f_d_r_d_spi(spei_scale, plant_key, threshold):
    valid = spei_scale[spei_scale["SPI_12"].notna()].copy()
    valid["severe"] = valid["SPI_12"] <= threshold
    f_d = valid.groupby(["id", "model", "scenario", "period"], as_index=False).agg(f_d=("severe", "mean"))
    f_d["f_d"] = f_d["f_d"] * 100.0
    bf = _baseline_future(f_d, ["id", "model", "scenario"], "f_d")
    bf["ratio"] = np.where((bf["baseline_value"] == 0) | bf["baseline_value"].isna(), np.nan,
                            bf["future_value"] / bf["baseline_value"])
    return plant_key.merge(bf, on="id", how="inner")


spi_hydro_res = _f_d_r_d_spi(catchment_spei, hydro_key[hydro_key.bucket == "hydro_reservoir"], -1.5)
spi_hydro_ror = _f_d_r_d_spi(catchment_spei, hydro_key[hydro_key.bucket == "hydro_run_of_river"], -1.5)
spi_tw = _f_d_r_d_spi(cell_spei, tw_key, -1.5)
spi_all = pd.concat([spi_hydro_res, spi_hydro_ror, spi_tw], ignore_index=True)

item4_rows = []
for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
    bkey = hydro_key[hydro_key.bucket == bucket] if bucket != "thermal_water_dependent" else tw_key
    fl = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(bkey.plant_uid)]
    if fl.empty:
        continue
    for scenario in SCENARIOS:
        sub = spi_all[(spi_all.bucket == bucket) & (spi_all.scenario == scenario)
                      & spi_all.plant_uid.isin(fl.plant_uid)]
        gw_shares = []
        for model, g in sub.groupby("model"):
            s = g.set_index("plant_uid")["ratio"].reindex(fl.plant_uid)
            exposed = (s >= 2.0).fillna(False)
            exposed_mw = fl.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
            gw_shares.append(100 * exposed_mw.sum() / fl["capacity_mw"].sum())
        # SPI baseline F_D
        base_fd = sub.groupby("model")["baseline_value"].median().median()
        item4_rows.append(dict(
            bucket=bucket, scenario=scenario, spi_gw_pct_median=float(np.median(gw_shares)) if gw_shares else np.nan,
            spi_baseline_fd_pct=base_fd,
            excess_vs_block_bootstrap_null=(float(np.median(gw_shares)) - null_rate_bb) if gw_shares else np.nan,
        ))
item4_df = pd.DataFrame(item4_rows)
item4_df.to_csv(OUT / "c23d_4_spi12_comparison.csv", index=False)
p(df_to_md(item4_df, max_rows=30))
p(f"Comparação direta com SPEI-12 (item 3, mesmos buckets/cenários, mesmo nulo "
  f"bootstrap={null_rate_bb:.2f}%): ver `c23d_3_excess_over_null.csv` vs `c23d_4_spi12_comparison.csv`.")

# =======================================================================
# Item 5: sign agreement -- future F_D > historical F_D, per bucket/scenario
# =======================================================================
h("5. Concordância de sinal (sem critério de ordem entre cenários)", level=2)
item5_rows = []
for bucket in ["hydro_reservoir", "hydro_run_of_river", "thermal_water_dependent"]:
    for scenario in SCENARIOS:
        hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12") & (hazards.scenario == scenario)]
        per_model_sign = hz.groupby("model")[["future_value", "baseline_value"]].apply(
            lambda g: (g["future_value"] > g["baseline_value"]).mean() >= 0.5
        )
        n_models_pos = int(per_model_sign.sum())
        item5_rows.append(dict(bucket=bucket, scenario=scenario, n_gcm_future_gt_baseline=n_models_pos,
                                n_gcm_total=len(per_model_sign)))
item5_df = pd.DataFrame(item5_rows)
item5_df.to_csv(OUT / "c23d_5_sign_agreement.csv", index=False)
p("Em quantos dos 5 GCMs a F_D futura excede a F_D histórica (maioria das plantas do bucket "
  "concordando em sinal, por modelo, sem qualquer teste de ordenação entre cenários):")
p(df_to_md(item5_df))

# =======================================================================
# Item 6: BRA thermal by fuel group, TX35 exposure by GW and by plant
# =======================================================================
h("6. Térmica brasileira por grupo de combustível", level=2)

from craei.inventory.plants import plant_uid as _plant_uid_fn  # noqa: E402

gem_path = Path(paths["gem_file"])
if gem_path.exists():
    gem_raw = pd.read_excel(gem_path, sheet_name="Power facilities")
    gem_raw = gem_raw[gem_raw["Country/area"] == "Brazil"].copy()
    status_norm = gem_raw["Status"].astype(str).str.strip().str.lower()
    status_to_fleet = {"operating": "operating", "construction": "planned_adv",
                        "pre-construction": "planned_adv", "announced": "planned_early"}
    gem_raw["fleet"] = status_norm.map(status_to_fleet)
    type_norm = gem_raw["Type"].astype(str).str.strip().str.lower()
    thermal = gem_raw[type_norm.isin({"coal", "oil/gas", "bioenergy", "nuclear"}) & gem_raw["fleet"].notna()
                       & gem_raw["Capacity (MW)"].notna() & gem_raw["Latitude"].notna()
                       & gem_raw["Longitude"].notna()].copy()
    thermal["computed_plant_uid"] = thermal.apply(
        lambda r: _plant_uid_fn(str(r["Plant / Project name"]), r["Latitude"], r["Longitude"]), axis=1
    )
    fuel_raw = thermal["Fuel (combustion only)"].astype(str).str.lower()

    def _fuel_group(fuel_str, type_str):
        if type_str == "nuclear":
            return "nuclear"
        if type_str == "coal" or "coal" in fuel_str:
            return "coal"
        if type_str == "bioenergy" or "bioenergy" in fuel_str:
            return "bioenergy"
        if "fossil gas" in fuel_str or "fossil liquids" in fuel_str or type_str == "oil/gas":
            return "gas_oil"
        return "other"

    thermal["fuel_group"] = [
        _fuel_group(f, t) for f, t in zip(fuel_raw, type_norm[thermal.index])
    ]
    plant_fuel = thermal.groupby("computed_plant_uid", as_index=False).agg(
        fuel_group=("fuel_group", lambda s: s.mode().iat[0]),
    )

    n_gem_uids = set(plant_fuel["computed_plant_uid"])
    n_plants_uids = set(bra_plants[bra_plants.tech_class.isin(
        ["thermal_water_dependent", "thermal_air_only"]
    )]["plant_uid"])
    n_match = len(n_gem_uids & n_plants_uids)
    p(f"**Correspondência plant_uid**: {n_match} de {len(n_plants_uids)} usinas térmicas "
      f"brasileiras em `plants.parquet` casam com um `plant_uid` recomputado do GEM bruto "
      f"({len(n_gem_uids)} plant_uid distintos computados do lado do GEM) -- "
      f"{'100%' if n_match == len(n_plants_uids) else f'{100*n_match/len(n_plants_uids):.1f}%'} "
      f"de correspondência.")

    plants_with_fuel = bra_plants.merge(plant_fuel, left_on="plant_uid", right_on="computed_plant_uid", how="left")
    plants_with_fuel["fuel_group"] = plants_with_fuel["fuel_group"].fillna("unmatched")
    fuel_summary = plants_with_fuel[plants_with_fuel.tech_class.isin(
        ["thermal_water_dependent", "thermal_air_only"]
    )].groupby(["fuel_group", "fleet"], as_index=False).agg(
        n_plants=("plant_uid", "count"), gw=("capacity_mw", "sum")
    )
    fuel_summary["gw"] = fuel_summary["gw"] / 1000.0

    tx35 = hazards[(hazards.bucket.isin(["thermal_water_dependent", "thermal_air_only"]))
                   & (hazards.hazard == "TX35")]
    fuel_exposure_rows = []
    for fuel_group in plants_with_fuel["fuel_group"].dropna().unique():
        for fleet in ["operating", "planned_adv", "planned_early"]:
            fl = plants_with_fuel[(plants_with_fuel.fuel_group == fuel_group)
                                   & (plants_with_fuel.fleet == fleet)
                                   & plants_with_fuel.tech_class.isin(["thermal_water_dependent", "thermal_air_only"])]
            if fl.empty:
                continue
            for scenario in SCENARIOS:
                hz = tx35[(tx35.scenario == scenario) & tx35.plant_uid.isin(fl.plant_uid)]
                gw_shares, plant_shares = [], []
                for model, g in hz.groupby("model"):
                    s = g.set_index("plant_uid")["delta"].reindex(fl.plant_uid)
                    exposed = (s >= 30).fillna(False)
                    exposed_mw = fl.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
                    gw_shares.append(100 * exposed_mw.sum() / fl["capacity_mw"].sum())
                    plant_shares.append(100 * exposed.sum() / len(fl))
                if gw_shares:
                    fuel_exposure_rows.append(dict(
                        fuel_group=fuel_group, fleet=fleet, scenario=scenario,
                        tx35_gw_pct_median=float(np.median(gw_shares)),
                        tx35_plant_pct_median=float(np.median(plant_shares)),
                    ))
    fuel_exposure_df = pd.DataFrame(fuel_exposure_rows)
    fuel_summary.to_csv(OUT / "c23d_6_fuel_summary.csv", index=False)
    fuel_exposure_df.to_csv(OUT / "c23d_6_fuel_tx35_exposure.csv", index=False)
    p(df_to_md(fuel_summary.sort_values("gw", ascending=False)))
    p(df_to_md(fuel_exposure_df, max_rows=40))
else:
    p(f"GEM bruto não encontrado em {gem_path} -- item não executado.")

# =======================================================================
# Item 7: leave-one-out of the 5 largest BRA hydro plants by GW
# =======================================================================
h("7. Leave-one-out das 5 maiores hidros brasileiras", level=2)

bra_hydro_operating = bra_plants[(bra_plants.tech_class == "hydro") & (bra_plants.fleet == "operating")]
top5 = bra_hydro_operating.nlargest(5, "capacity_mw")[["plant_name", "capacity_mw", "hydro_type"]]
p("As 5 maiores hidrelétricas operantes do Brasil por GW:")
p(df_to_md(top5))

loo_rows = []
for bucket in ["hydro_reservoir", "hydro_run_of_river"]:
    fl_full = bra_plants[(bra_plants.fleet == "operating") & bra_plants.plant_uid.isin(
        hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12")]["plant_uid"]
    )]
    if fl_full.empty:
        continue
    for scenario in SCENARIOS:
        hz = hazards[(hazards.bucket == bucket) & (hazards.hazard == "f_d_spei12") & (hazards.scenario == scenario)]

        def _share_for(fl_df):
            shares = []
            for model, g in hz[hz.plant_uid.isin(fl_df.plant_uid)].groupby("model"):
                s = g.set_index("plant_uid")["ratio"].reindex(fl_df.plant_uid)
                exposed = (s >= 2.0).fillna(False)
                exposed_mw = fl_df.set_index("plant_uid")["capacity_mw"].where(exposed, 0.0)
                shares.append(100 * exposed_mw.sum() / fl_df["capacity_mw"].sum())
            return float(np.median(shares)) if shares else np.nan

        full_share = _share_for(fl_full)
        for _, plant_row in top5.iterrows():
            plant_uid_val = bra_hydro_operating[bra_hydro_operating.plant_name == plant_row.plant_name]["plant_uid"].iloc[0]
            if plant_uid_val not in set(fl_full.plant_uid):
                continue
            fl_loo = fl_full[fl_full.plant_uid != plant_uid_val]
            loo_share = _share_for(fl_loo)
            loo_rows.append(dict(
                bucket=bucket, scenario=scenario, plant_removed=plant_row.plant_name,
                capacity_mw=plant_row.capacity_mw, share_full_pct=full_share, share_loo_pct=loo_share,
                delta_pp=loo_share - full_share if pd.notna(loo_share) else np.nan,
            ))
loo_df = pd.DataFrame(loo_rows)
loo_df.to_csv(OUT / "c23d_7_leave_one_out.csv", index=False)
p(df_to_md(loo_df, max_rows=40))

# =======================================================================
# Item 8: ONS ENA/EAR availability by subsystem or basin (no download)
# =======================================================================
h("8. Disponibilidade ONS (ENA e EAR) por subsistema ou bacia", level=2)
p("**Verificação só em fontes locais já registradas (`docs/DECISIONS.md`), sem baixar nada "
  "novo:**")
p("- **ENA (Energia Natural Afluente) diário por subsistema**: já documentado "
  "(`docs/DECISIONS.md` linha 246) -- `https://dados.ons.org.br/dataset/ena-diario-por-"
  "subsistema` (CKAN API oficial confirmada), dados de 2000-01-01 até o presente (2026), "
  "um arquivo por ano, formatos CSV/XLSX (Parquet a partir de 2021). **Granularidade: só "
  "por subsistema** (Norte/Nordeste/Sul/Sudeste), não por bacia nem por usina -- confirma o "
  "gap documentado em L20/D62 (sem mapeamento oficial planta-subsistema).")
p("- **EAR (Energia Armazenada, reservatórios)**: **nenhum registro local** em "
  "`docs/DECISIONS.md`, `docs/LIMITATIONS.md` ou `config/paths.local.yaml` sobre "
  "disponibilidade, URL ou período -- diferente do ENA, o EAR nunca foi investigado neste "
  "projeto. Por regra (\"nunca inferir\"), reportado como **desconhecido**, não pesquisado "
  "agora (comando pede só verificar dados JÁ registrados, não buscar novos).")
p("- Nenhum dado foi baixado para responder este item.")

(OUT / "c23d_report.md").write_text("\n".join(REPORT), encoding="utf-8")
print("C23-D done. Report at", OUT / "c23d_report.md")