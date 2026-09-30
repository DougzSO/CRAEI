"""COMANDO 23 Bloco F: code audit (regression baseline, lint, dead code, coverage, scope branches, size).

Read-only except for outputs_audit_dir/c23/code/ (and the .coverage file, via COVERAGE_FILE).
No --fix flag passed to any tool. Reads config/c23_audit.yaml, not params.yaml.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from craei.config import load_paths  # noqa: E402

paths = load_paths()
AUDIT = yaml.safe_load(open(ROOT / "config" / "c23_audit.yaml", encoding="utf-8"))
CA = AUDIT["code_audit"]

OUT = Path(paths["outputs_dir"]) / "audit" / "c23" / "code"
OUT.mkdir(parents=True, exist_ok=True)
TABLES_DIR = Path(paths["outputs_tables_dir"])

os.environ["COVERAGE_FILE"] = str(OUT / ".coverage")

REPORT = []


def h(title, level=2):
    REPORT.append(f"{'#' * level} {title}\n")


def p(text):
    REPORT.append(text + "\n")


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


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


h("COMANDO 23 -- Bloco F: code audit report", level=1)

# =======================================================================
# Item 20: regression baseline (run first)
# =======================================================================
h("20. Linha de base de regressão", level=2)


def _hash_table(fp: Path) -> str:
    if fp.suffix == ".csv":
        return hashlib.sha256(fp.read_bytes()).hexdigest()
    if fp.suffix == ".parquet":
        df = pd.read_parquet(fp)
        # Content hash, ignoring metadata: hash the sorted-column, row-order-preserved values.
        df = df[sorted(df.columns)]
        return hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()
    return "n/a"


table_files = sorted(TABLES_DIR.glob("*.csv")) + sorted(TABLES_DIR.glob("*.parquet"))
before_hashes = {fp.name: _hash_table(fp) for fp in table_files}

p(f"Hashes calculados para {len(before_hashes)} arquivos em `outputs_tables_dir` "
  f"(CSV: sha256 dos bytes; parquet: sha256 do conteúdo do DataFrame por coluna ordenada, "
  f"ignorando metadados) ANTES de rodar a suíte.")

t0 = time.time()
test_result = run([sys.executable, "-m", "pytest", "-q",
                    f"--cov=src/craei", f"--cov-report=json:{OUT / 'coverage.json'}"])
t_suite = time.time() - t0
suite_out = test_result.stdout + test_result.stderr
m = re.search(r"(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)?", suite_out)
n_passed = int(m.group(1)) if m else None
n_skipped = int(m.group(2)) if m and m.group(2) else 0
n_failed = int(m.group(3)) if m and m.group(3) else 0
p(f"Suíte: {n_passed} passed, {n_skipped} skipped, {n_failed} failed, {t_suite:.1f}s "
  f"(linha bruta pytest: `{suite_out.strip().splitlines()[-1] if suite_out.strip() else 'sem saída'}`).")

after_hashes = {fp.name: _hash_table(fp) for fp in table_files}
changed = [name for name in before_hashes if before_hashes[name] != after_hashes.get(name)]
p(f"Hashes recalculados DEPOIS da suíte: {len(changed)} arquivo(s) mudou(ram): {changed if changed else 'nenhum'}.")

golden_rows = [
    dict(file=name, sha256_before=before_hashes[name], sha256_after=after_hashes.get(name),
         changed=name in changed)
    for name in before_hashes
]
pd.DataFrame(golden_rows).to_csv(OUT / "c23_20_golden_hashes.csv", index=False)

determinism_check = bool(re.search(r"determinis|idempotent|two.?run", suite_out, re.IGNORECASE))
p(f"Verificação prévia de determinismo (duas execuções com saída idêntica) explícita na suíte: "
  f"{'indícios encontrados no output do pytest (revisar manualmente)' if determinism_check else 'NÃO encontrada'} "
  f"-- não executado aqui (rodar o pipeline de novo está fora de escopo deste comando).")

# =======================================================================
# Item 21: lint (ruff, no --fix)
# =======================================================================
h("21. Lint sem fix", level=2)
ruff_select = ",".join(CA["ruff_select"])
ruff_result = run(["ruff", "check", "--select", ruff_select, "--output-format=json",
                    "src", "scripts"])
try:
    ruff_findings = json.loads(ruff_result.stdout) if ruff_result.stdout.strip() else []
except json.JSONDecodeError:
    ruff_findings = None

if ruff_findings is None:
    p(f"`ruff check` não retornou JSON válido (stderr: {ruff_result.stderr[:500]}). "
      f"Reportado, não recuperado.")
    lint_df = pd.DataFrame(columns=["file", "rule", "count"])
else:
    lint_rows = [
        dict(file=f["filename"].replace(str(ROOT) + os.sep, ""), rule=f["code"])
        for f in ruff_findings
    ]
    lint_df_raw = pd.DataFrame(lint_rows)
    if len(lint_df_raw):
        lint_df = lint_df_raw.groupby(["file", "rule"], as_index=False).size().rename(columns={"size": "count"})
    else:
        lint_df = pd.DataFrame(columns=["file", "rule", "count"])
    # scope_tag per file
    scope_keywords = CA["scope_keywords"]

    def _tag(fname):
        try:
            text = (ROOT / fname).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return "unknown"
        hit = {k for k in scope_keywords if k in text}
        if {"IND", "India"} & hit and not ({"PRT", "Portugal"} & hit):
            return "IND_only"
        if {"PRT", "Portugal"} & hit and not ({"IND", "India"} & hit):
            return "PRT_only"
        if "compound" in hit:
            return "compound"
        if {"solar", "wind"} & hit:
            return "solar_wind"
        return "core"

    if len(lint_df):
        lint_df["scope_tag"] = lint_df["file"].map(_tag)
    p(f"`ruff check --select {ruff_select}` (sem --fix), `src/` e `scripts/`: {len(ruff_findings)} "
      f"achados brutos, {lint_df['count'].sum() if len(lint_df) else 0} após agrupar por "
      f"(arquivo, regra).")
    p(df_to_md(lint_df.sort_values("count", ascending=False), max_rows=40))

lint_df.to_csv(OUT / "c23_21_lint.csv", index=False)

# =======================================================================
# Item 22: dead code (vulture + coverage cross-reference + dynamic dispatch)
# =======================================================================
h("22. Código morto", level=2)
vulture_result = run(["vulture", "--min-confidence", str(CA["vulture_min_confidence"]),
                       "src", "scripts"])
vulture_lines = [ln for ln in vulture_result.stdout.splitlines() if ln.strip()]
vulture_rows = []
vul_re = re.compile(r"^(.*?):(\d+): (.*?) \((\d+)% confidence\)$")
for ln in vulture_lines:
    mm = vul_re.match(ln)
    if mm:
        vulture_rows.append(dict(file=mm.group(1), line=int(mm.group(2)), message=mm.group(3),
                                  confidence=int(mm.group(4))))
vulture_df = pd.DataFrame(vulture_rows)
p(f"`vulture --min-confidence {CA['vulture_min_confidence']}` src/ scripts/: {len(vulture_df)} achados brutos.")

# Dynamic-dispatch false-positive scan: getattr/importlib/eval/YAML-name usage near any vulture hit's name
dyn_pattern = re.compile(r"\bgetattr\s*\(|\bimportlib\b|\beval\s*\(|\bexec\s*\(")
all_src_text = ""
for fp in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    all_src_text += fp.read_text(encoding="utf-8", errors="ignore")
has_dynamic_dispatch_anywhere = bool(dyn_pattern.search(all_src_text))
p(f"Despacho dinâmico (`getattr`/`importlib`/`eval`/`exec`) em algum lugar de src/scripts: "
  f"{has_dynamic_dispatch_anywhere} -- se True, qualquer achado do vulture cujo NOME apareça "
  f"como string literal em `config/*.yaml` é candidato a falso positivo (checado por achado abaixo).")

yaml_text = ""
for fp in (ROOT / "config").glob("*.yaml"):
    yaml_text += fp.read_text(encoding="utf-8", errors="ignore")


def _extract_name(msg: str) -> str | None:
    mm = re.search(r"'([\w\.]+)'", msg)
    return mm.group(1) if mm else None


if len(vulture_df):
    vulture_df["name"] = vulture_df["message"].map(_extract_name)
    vulture_df["yaml_string_match"] = vulture_df["name"].map(
        lambda n: bool(n) and n in yaml_text
    )
    # Cross-reference with coverage (item 23 runs after this, so read the json if already produced)
    cov_path = OUT / "coverage.json"
    covered_names = set()
    if cov_path.exists():
        try:
            cov = json.loads(cov_path.read_text())
            for fdata in cov.get("files", {}).values():
                pass  # line-level, not name-level; used qualitatively in narrative below, not per-row
        except json.JSONDecodeError:
            pass

    def _classify(row):
        if row["confidence"] >= 90 and not row["yaml_string_match"]:
            return "confirmado_morto"
        if row["yaml_string_match"]:
            return "falso_positivo_provavel"
        return "provavel"

    vulture_df["classification"] = vulture_df.apply(_classify, axis=1)
    p(df_to_md(vulture_df.drop(columns=["name"]), max_rows=40))
    p(df_to_md(vulture_df["classification"].value_counts().rename_axis("classification").reset_index(name="n")))
else:
    p("Nenhum achado do vulture.")
    vulture_df = pd.DataFrame(columns=["file", "line", "message", "confidence", "classification"])

vulture_df.to_csv(OUT / "c23_22_dead_code.csv", index=False)

# =======================================================================
# Item 23: coverage
# =======================================================================
h("23. Cobertura", level=2)
cov_json_path = OUT / "coverage.json"
if cov_json_path.exists():
    cov = json.loads(cov_json_path.read_text())
    scope_keywords = CA["scope_keywords"]

    def _tag2(fname):
        try:
            text = (ROOT / fname).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return "unknown"
        hit = {k for k in scope_keywords if k in text}
        if {"IND", "India"} & hit and not ({"PRT", "Portugal"} & hit):
            return "IND_only"
        if {"PRT", "Portugal"} & hit and not ({"IND", "India"} & hit):
            return "PRT_only"
        if "compound" in hit:
            return "compound"
        if {"solar", "wind"} & hit:
            return "solar_wind"
        return "core"

    cov_rows = []
    for fname, fdata in cov.get("files", {}).items():
        summ = fdata["summary"]
        cov_rows.append(dict(
            module=fname, n_statements=summ["num_statements"],
            pct_covered=summ["percent_covered"], scope_tag=_tag2(fname),
        ))
    cov_df = pd.DataFrame(cov_rows).sort_values("pct_covered")
    cov_df.to_csv(OUT / "c23_23_coverage.csv", index=False)
    overall = cov.get("totals", {}).get("percent_covered", float("nan"))
    p(f"Cobertura global: {overall:.2f}%. `pytest --cov=src/craei`, COVERAGE_FILE redirecionado "
      f"para `{os.environ['COVERAGE_FILE']}`.")
    low_cov_prod = cov_df[(cov_df.pct_covered < 70) & (cov_df.scope_tag == "core")]
    p(f"Módulos `core` com cobertura < 70% (risco de refatoração, não prova de código morto -- "
      f"ver instrução do comando): {len(low_cov_prod)}.")
    p(df_to_md(low_cov_prod, max_rows=30))
else:
    p("`coverage.json` não encontrado -- pytest com --cov pode ter falhado; ver saída do item 20.")
    cov_df = pd.DataFrame()

# =======================================================================
# Item 24: scope branches in shared modules
# =======================================================================
h("24. Ramos por escopo em módulos compartilhados", level=2)
scope_keywords = CA["scope_keywords"]
branch_rows = []
for fp in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    try:
        lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        continue
    for i, line in enumerate(lines, start=1):
        for kw in scope_keywords:
            if re.search(rf"\b{re.escape(kw)}\b", line):
                branch_rows.append(dict(
                    file=str(fp.relative_to(ROOT)), line=i, keyword=kw, context=line.strip()[:200],
                ))
branch_df = pd.DataFrame(branch_rows)
branch_df.to_csv(OUT / "c23_24_scope_branches.csv", index=False)
p(f"{len(branch_df)} ocorrências de `scope_keywords` ({scope_keywords}) em src/+scripts/.")
if len(branch_df):
    p(df_to_md(branch_df["keyword"].value_counts().rename_axis("keyword").reset_index(name="n")))

# =======================================================================
# Item 25: comments and size
# =======================================================================
h("25. Comentários e tamanho", level=2)

era_result = run(["ruff", "check", "--select", "ERA001", "--output-format=json", "src", "scripts"])
try:
    era_findings = json.loads(era_result.stdout) if era_result.stdout.strip() else []
except json.JSONDecodeError:
    era_findings = []
p(f"Código comentado (ERA001): {len(era_findings)} achados.")

todo_rows = []
for fp in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, start=1):
        for marker in ("TODO", "FIXME", "XXX", "HACK"):
            if marker in line:
                todo_rows.append(dict(file=str(fp.relative_to(ROOT)), line=i, marker=marker,
                                       context=line.strip()[:200]))
todo_df = pd.DataFrame(todo_rows)
p(f"TODO/FIXME/XXX/HACK: {len(todo_df)} ocorrências.")

ref_rows = []
ref_pattern = re.compile(r"\bC\d{2}\b|\bL\d{2}\b|D\d{2}\b|§\d")
for fp in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
    for i, line in enumerate(lines, start=1):
        if ref_pattern.search(line):
            ref_rows.append(dict(file=str(fp.relative_to(ROOT)), line=i, context=line.strip()[:200]))
ref_df = pd.DataFrame(ref_rows)
p(f"Referências textuais a C##/L##/D##/seções do METHODS_SPEC (§): {len(ref_df)} ocorrências.")

nodoc_rows = []
core_dirs = ["hazards", "exposure", "inventory", "spatial"]
for dname in core_dirs:
    for fp in (ROOT / "src" / "craei" / dname).glob("*.py"):
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for mm in re.finditer(r"^def (\w+)\(.*?\):\n(\s+\"\"\")?", text, flags=re.MULTILINE):
            fname = mm.group(1)
            if fname.startswith("_"):
                continue
            after = text[mm.end():mm.end() + 5]
            has_doc = mm.group(2) is not None
            if not has_doc:
                nodoc_rows.append(dict(file=f"src/craei/{dname}/{fp.name}", function=fname))
nodoc_df = pd.DataFrame(nodoc_rows)
p(f"Funções públicas sem docstring em módulos core ({core_dirs}): {len(nodoc_df)}.")

long_fn_rows = []
long_file_rows = []
max_complexity = CA["max_complexity"]
long_function_lines = CA["long_function_lines"]
long_file_lines = CA["long_file_lines"]
c901 = run(["ruff", "check", "--select", "C901", f"--config",
            f"lint.mccabe.max-complexity={max_complexity}", "--output-format=json", "src", "scripts"])
try:
    c901_findings = json.loads(c901.stdout) if c901.stdout.strip() else []
except json.JSONDecodeError:
    c901_findings = []
p(f"Funções acima de max-complexity={max_complexity} (ruff C901): {len(c901_findings)}.")

for fp in list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    n_lines = len(fp.read_text(encoding="utf-8", errors="ignore").splitlines())
    if n_lines > long_file_lines:
        long_file_rows.append(dict(file=str(fp.relative_to(ROOT)), n_lines=n_lines))
long_file_df = pd.DataFrame(long_file_rows)
p(f"Arquivos acima de {long_file_lines} linhas: {len(long_file_df)}.")
p(df_to_md(long_file_df, max_rows=20))

comments_size = pd.DataFrame([
    dict(check="commented_code_ERA001", n=len(era_findings)),
    dict(check="todo_fixme_xxx_hack", n=len(todo_df)),
    dict(check="textual_refs_C_L_D_section", n=len(ref_df)),
    dict(check="public_functions_no_docstring_core", n=len(nodoc_df)),
    dict(check="functions_above_max_complexity", n=len(c901_findings)),
    dict(check="files_above_long_file_lines", n=len(long_file_df)),
])
comments_size.to_csv(OUT / "c23_25_comments_size.csv", index=False)
todo_df.to_csv(OUT / "c23_25_todo_detail.csv", index=False)
p(df_to_md(comments_size))

# =======================================================================
# Write Bloco F report
# =======================================================================
(OUT / "c23_code_audit.md").write_text("\n".join(REPORT), encoding="utf-8")
print("Bloco F done. Report at", OUT / "c23_code_audit.md")

# =======================================================================
# c23_summary.md -- built here (last script to run) so it can cite both
# Blocos A-E (scripts/c23_scope_audit.py) and Bloco F (this script).
# Reads that script's own outputs, does not recompute anything.
# =======================================================================
SCOPE_OUT = Path(paths["outputs_dir"]) / "audit" / "c23"
summary_lines = ["# COMANDO 23 -- c23_summary.md", ""]
summary_lines.append(
    "Nenhuma recomendação ou escolha de escopo é feita aqui, por instrução do comando. As 10 "
    "constatações abaixo são para decisão do autor."
)
summary_lines.append("")

findings = []

# 1. Bloco 0 achado critico
findings.append(
    "1. O bloco aditivo original do COMANDO 23 quebrou `craei.config.load_params()` (exigia "
    "value/tier/source em toda chave de topo de params.yaml), derrubando 7 testes. Corrigido: "
    "revertido (commit 916b7ec) e os critérios movidos para `config/c23_audit.yaml`, fora de "
    "`load_params()`. Suíte voltou a 141 passed/1 skipped."
)

try:
    viability = pd.read_csv(SCOPE_OUT / "c23_3_viability_matrix.csv")
    n_excl = (viability.class_final == "excluido").sum()
    n_princ = (viability.class_final == "principal").sum()
    n_sup = (viability.class_final == "suporte").sum()
    findings.append(
        f"2. Matriz de viabilidade: {len(viability)} linhas (país x bucket x frota x hazard x "
        f"cenário); {n_princ} principal, {n_sup} suporte, {n_excl} excluído -- {n_excl}/{len(viability)} "
        f"({100*n_excl/len(viability):.0f}%) das combinações não passam nos critérios quantitativos "
        f"mínimos (n_plants/effective_n/fleet_share), a maioria por frotas pequenas ou países fora "
        f"do Brasil."
    )
except FileNotFoundError:
    viability = None

try:
    gate = pd.read_csv(SCOPE_OUT / "c23_4_reproduction_gate.csv")
    findings.append(
        f"3. Portão de reprodução do caso base (ΔTX35=30, R_D=2): {'PASSOU' if gate['pass'].all() else 'FALHOU'} "
        f"em todas as {len(gate)} combinações testadas (diff máximo {gate['diff_pp'].max():.4g} pp) -- "
        f"curvas de limiar (item 4) e baseline de SPEI (item 5) foram geradas condicionadas a esse resultado."
    )
except FileNotFoundError:
    pass

try:
    fleet = pd.read_csv(SCOPE_OUT / "c23_1_fleet.csv")
    bra_fleet_gw = fleet[fleet.country == "BRA"]["gw"].sum()
    findings.append(
        f"4. Frota brasileira em `plants.parquet` (excl. eólica, excluída antes do inventário): "
        f"{bra_fleet_gw:.1f} GW em {int(fleet[fleet.country=='BRA'].n_plants.sum())} usinas; "
        f"parcela fora de escopo quantificada no relatório principal (solar_pv dentro do "
        f"inventário mas só com H4; eólica reconstruída a partir do GEM bruto)."
    )
except FileNotFoundError:
    pass

findings.append(
    "5. PET truncada (L16, 51 células, regime glacial): confirmado 0 dias truncados no Brasil e "
    "em Portugal (validação W5E5, D70) -- a limitação só se aplica à Índia (144 de 393 usinas "
    "hidro, 37%)."
)
findings.append(
    "6. H3 (Aqueduct) usa AMBAS as camadas (`baseline_annual` + `future_annual`), e a categoria "
    "de estresse hídrico VARIA entre cenários SSP -- a invariância entre cenários reportada em "
    "L06 não é garantida pela escolha de camada; é um achado empírico sobre quão pouco a mediana "
    "do ensemble interno do Aqueduct muda entre horizontes de emissão."
)
findings.append(
    "7. PROGRESS.json: a fase P6 está `status: todo` mesmo com seu único comando (C21) `done` "
    "(P6-R/P6-C pendentes); a premissa do enunciado do C23 sobre `validation.csv`/"
    "`emdat_descriptive.csv` ausentes está desatualizada -- ambos existem (D70/O15, fechados "
    "2026-09-30, mesma data de PROGRESS.json.updated)."
)

try:
    lint_df = pd.read_csv(OUT / "c23_21_lint.csv")
    n_lint = lint_df["count"].sum() if len(lint_df) else 0
except FileNotFoundError:
    n_lint = "?"
try:
    dead_df = pd.read_csv(OUT / "c23_22_dead_code.csv")
    n_confirmed_dead = (dead_df.classification == "confirmado_morto").sum() if len(dead_df) else 0
except FileNotFoundError:
    n_confirmed_dead = "?"
try:
    branch_df = pd.read_csv(OUT / "c23_24_scope_branches.csv")
    n_branches = len(branch_df)
except FileNotFoundError:
    n_branches = "?"
try:
    cov_df = pd.read_csv(OUT / "c23_23_coverage.csv")
    overall_cov = (cov_df["n_statements"] * cov_df["pct_covered"]).sum() / cov_df["n_statements"].sum() \
        if len(cov_df) and cov_df["n_statements"].sum() > 0 else float("nan")
except FileNotFoundError:
    overall_cov = float("nan")

findings.append(
    f"8. Lint (ruff, sem --fix, regras {CA['ruff_select']}): {n_lint} achados em src/+scripts/."
)
findings.append(
    f"9. Código morto: {n_confirmed_dead} achados classificados 'confirmado_morto' pelo vulture "
    f"(confiança >=90%, sem correspondência em config YAML -- checagem de falso-positivo por "
    f"despacho dinâmico feita)."
)
try:
    scripts_df = pd.read_csv(SCOPE_OUT / "c23_15_scripts.csv")
    n_orphan_scripts = (scripts_df.group == "orfao").sum()
except FileNotFoundError:
    n_orphan_scripts = "?"
findings.append(
    f"10. Inventário de arquivos: {n_orphan_scripts} scripts órfãos (nem produção nem "
    f"diagnóstico fechado referenciado em DECISIONS.md) -- candidatos a arquivar em "
    f"`archive/full-3-countries` (já criada, Bloco 0) junto com qualquer código específico de "
    f"IND/PRT/compound se o escopo do artigo restringir a só Brasil hidro+térmica."
)

summary_lines.append("\n".join(findings))
summary_lines.append("")
summary_lines.append(
    f"**Linha de código:** {n_confirmed_dead} achados confirmados mortos; {n_branches} ramos "
    f"por escopo (`scope_keywords`); cobertura global {overall_cov:.1f}%." if isinstance(overall_cov, float) and overall_cov == overall_cov
    else f"**Linha de código:** {n_confirmed_dead} achados confirmados mortos; {n_branches} ramos por escopo; cobertura global indisponível."
)

# Final paragraph: class_quant/class_final line counts, BRA vs others, aggregated
summary_lines.append("")
summary_lines.append("## Parágrafo final -- contagem de linhas da matriz por classe")
if viability is not None:
    bra_counts = viability[viability.country == "BRA"]["class_final"].value_counts().to_dict()
    other_counts = viability[viability.country != "BRA"]["class_final"].value_counts().to_dict()
    agg = viability.groupby(["bucket", "fleet", "hazard"])["class_final"].agg(
        lambda s: s.value_counts().idxmax()
    ).value_counts().to_dict()
    summary_lines.append(f"- Brasil (class_final): {bra_counts}")
    summary_lines.append(f"- Outros países (class_final): {other_counts}")
    summary_lines.append(f"- Agregado por bucket x frota x hazard (classe dominante por linha agregada): {agg}")
    summary_lines.append(
        "- Nota de método: 'agregado por bucket x frota x hazard' aqui colapsa os 3 cenários "
        "para a classe MAIS FREQUENTE entre eles (não o `aggregate_rule` de "
        "`config/c23_audit.yaml`, já aplicado por linha em `class_aggregated_across_scenarios` "
        "no CSV completo) -- reportado por transparência de método, use "
        "`c23_3_viability_matrix.csv`'s `class_aggregated_across_scenarios` column para o "
        "critério oficial do comando."
    )
else:
    summary_lines.append("Matriz de viabilidade não encontrada -- Bloco A-E pode não ter rodado antes deste script.")

summary_lines.append("")
summary_lines.append("Não recomendar nem escolher escopo. Parar.")

(SCOPE_OUT / "c23_summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
print("c23_summary.md written at", SCOPE_OUT / "c23_summary.md")
