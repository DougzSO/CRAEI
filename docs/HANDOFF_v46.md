# Contexto completo consolidado (v46) para novo chat — CRAEI

Último commit confirmado: C87, hash 51e48e4, HEAD -> main. Push ainda não confirmado nesta sessão — executar git push e confirmar antes de iniciar qualquer trabalho novo. Histórico recente:

```text
51e48e4 (HEAD -> main) C87: Group E figure redesign (D133) - Fig1 raster+thermal markers, Fig2 single-panel, Fig4 forest plot (O20 resolved), Fig5 split a/b with shared map chrome, Fig6 grouped bars; new scripts/article_map_utils.py
44c59eb (origin/main, origin/HEAD) C86: docs reorganization (D131 fig/table renumbering, D132 split), archive 4 pre-C66 orphans
76c9f82 C85: Table 3 scope fixed + EOL bugfix (core.autocrlf, .gitattributes), w5_table3_coexposure.py, D130
d655a13 C84: backfill D129 into DECISIONS.md (METHODS_SPEC Appendix C fix, C83)
0831ab4 C82: W5 sensitivity table extended to 12 families (W4c/W4f/W4b-agreement), D128
```

Mudança de ferramenta a partir de agora: o autor passará a usar Claude Code (não mais este chat) para: (a) ajustes visuais nas figuras do Grupo E a partir de inspeção real dos PNGs, (b) reorganização/limpeza de repositório e código, (c) reestruturação do pipeline para workflow sequencial e organizado, (d) generalização multi-país. Este documento serve de handoff de contexto para o Claude Code.

Working tree após C87: limpo (a confirmar com git status na próxima sessão). pytest: 225 passed, 1 skipped, 4 warnings pré-existentes, não re-rodado desde o commit C81 (nenhuma alteração em src/craei/ nas sessões de figuras).

## 1. Regras de trabalho (vigentes, acumuladas)

- Respostas sucintas; comandos prontos para PowerShell. Checkpoints antes de escritas de risco.
- Nunca inventar números: ausente = "TO BE DEFINED" + item O-xx.
- Grep obrigatório em docs/DECISIONS.md, docs/STATUS_LOG.md, docs/CRAEI_work_plan_v2.md, CLAUDE.md, docs/OPEN_ITEMS.md antes de criar IDs C/D/O.
- Conferir BOM/CRLF/LF do arquivo inteiro (caminho absoluto, .NET CurrentDirectory ≠ $PWD) antes de editar; preservar bytes fora da edição.
- .gitattributes (* text=auto eol=lf, C85) normaliza EOL no commit — warnings de "CRLF will be replaced by LF" no git add são esperados e corretos, não erro.
- PowerShell 5.1: usar [System.IO.File]::WriteAllText($path, $content, (New-Object System.Text.UTF8Encoding($false))) para UTF-8 sem BOM.
- Heredocs longos quebram silenciosamente — dividir em passos menores. Scripts Python >3 linhas: heredoc → _tmp_*.py via WriteAllText (caminho absoluto) → executar → remover sempre (lição desta sessão: 3 temporários órfãos escaparam da limpeza em um momento, _tmp_fig3.py/_tmp_fig6.py/_tmp_grep_null.py).
- Ao colar texto longo de volta no terminal/chat, desconfiar de palavras concatenadas sem espaço (artefato de wrap) — verificar no arquivo real (.Contains()) antes de assumir corrupção de dado.
- Arquivos de produção: escrever temporário, git --no-pager diff --no-index, só promover após confirmar ausência de drift.
- data_root é diretório irmão do repo — nunca presumir data\... relativo dentro de CRAEI\; artefatos de artigo (data/outputs/article/) estão fora do Git.
- Pacote craei está em src/craei/, não na raiz. Scripts utilitários específicos de geração de figura/artigo vão em scripts/, não em src/craei/ (ex. scripts/article_map_utils.py).
- Antes de escrever lógica de domínio nova, grep por precedente em scripts/*.py — e, quando o schema permite múltiplos valores válidos para uma métrica (threshold, null, scenario), sempre buscar o valor "headline"/produção já usado no próprio script-fonte antes de escolher arbitrariamente (aplicado com sucesso repetidas vezes nesta sessão).
- Geometria/mapas: usar cache local (data/external/geo/natural_earth_brazil.gpkg) — nunca baixar sob demanda. representative_point() preferível a centroid para rotular polígonos em CRS geográfico.
- Evitar dependências novas por conveniência (ex. tabulate para to_markdown()) — preferir implementação manual quando simples.
- Ao combinar resultados com nulos/pools diferentes na mesma figura, sinalizar isso explicitamente.
- Máquina: 6,2 GB RAM. spei.parquet: 463 MB; preferir leitura seletiva.
- Fluxo de revisão de figuras: gerar com checks de dado rigorosos antes de cada savefig; revisão visual em lote feita separadamente (agora via Claude Code).

## 2. Projeto e resultado central (inalterado)

Pipeline Python de exposição de hidrelétricas e térmicas brasileiras (até agora Brasil-only) a calor e seca projetados. ISIMIP3b, 5 GCMs (GFDL-ESM4, IPSL-CM6A-LR, MPI-ESM1-2-HR, MRI-ESM2-0, UKESM1-0-LL), baseline 1985–2014, futuro 2041–2070, SSP126/370/585; bias-adjustment W5E5 v2.0/ISIMIP3BASD v2.5.0; inventário GEM cutoff 2026-08-09.

- H1 calor: TX35/TX40, dias/ano. Hidro intencionalmente ausente de H1 (confirmado por precedente scripts/archive/w3_heat_levels.py:43, tech_class != "hydro").
- H2 seca: SPEI-12 (Hargreaves, clip [−3,3]); F_D = % meses SPEI≤−1,5; R_D = futuro/baseline; exposição se R_D≥2,0.
- Itaipu: versão b = 7.000 MW (headline/D102), versão a = 14.000 MW (sensibilidade).
- Headline hidro — D102/W4b: +40,75/+43,20/+53,94 pp (SSP126/370/585), Itaipu b.
- Headline térmico — D125/W4c: SPEI +20,63/+28,50/+48,06 pp; SPI −1,08/+5,44/+27,50 pp.
- n_sim de produção = 2.000 fixo.

## 3. Estado fechado (tabela resumo)

| Item | Commit/decisão | Resultado |
|---|---|---|
| O38–O39, D121–D122 | C75–C76 | Reprodutibilidade + TH1 fleet/GW |
| O18, D123/D125 | C77/C79 | SPI vs SPEI, bug corrigido, nulo térmico próprio |
| W4f, D124 | C78 | Grade hidro SPEI×R_D |
| W3d/W3f-3, D126 | C80 | n_boot=5000, sem mudança |
| METHODS_SPEC §9, D127 | C81 | DR6-PE1 atualizados |
| W5 sensitivity, D128 | C82 | 4→12 famílias |
| Appendix C fix, D129 | C83/C84 | Fig2/4/Table2 falsos-bloqueios |
| Table 3 escopo + EOL bugfix, D130 | C85 | 192 linhas; .gitattributes |
| Docs reorganization, D131/D132 | C86 | Renumeração Fig/Table |
| Grupo E redesign completo, O20 resolvido, D133 | C87 | 6 figuras + Table 3 crosstab, scripts/article_map_utils.py |

Outros sem mudança: W3a-g calor; TH1 D91-98; ST1/ST2 D99-100; W4b sinal O21/D120; W4h D97/D106; DR7/O19 D113; O33 aberto; O40 mitigado; O41 fechado.

## 4. Infraestrutura de caminhos

```text
data_root:           .../CLIMATE RISK FRAMEWORK/data   (IRMÃO do repo CRAEI)
raw_dir:             D:/Douglas/OUTROS/CRAEI_raw_data/raw
processed_dir:       .../data/processed   (16 parquets)
outputs_dir:         .../data/outputs
outputs_tables_dir:  .../data/outputs/tables
outputs_figures_dir: .../data/outputs/figures
data/outputs/article/{figures,tables} — subpasta manual, fora do Git, artigo
data/external/geo/natural_earth_brazil.gpkg — cache de geometria, 3 layers: brazil_admin0, southamerica_admin0, brazil_admin1 (col. postal, 27 rows = 26+DF)
```

Nome do arquivo de geometria é Brazil-específico — ponto relevante para a generalização multi-país planejada (§13).

processed_dir: 16 parquets — catchment_weights, dgeg_hydro_generation, emdat_events, indices_daily, plants, plant_aqueduct, plant_cell, plant_hazards, plant_units, ren_iph, spei, spei_w5e5, truncated_pet_cells, water_balance_catchment, water_balance_catchment_w5e5, water_balance_cell.

Pacote craei: src/craei/__init__.py. Módulos: src/craei/exposure/heat_levels.py (with_itaipu_versions), src/craei/hazards/drought_levels.py (find_plant).

Novo nesta sessão: scripts/article_map_utils.py — compass_rose(), scale_bar(), base_brazil_map() (consolidado, usado por Fig 1/3/5a/5b). Nome também Brazil-específico (base_brazil_map) — candidato a generalizar/renomear na reestruturação multi-país.

## 5. Schemas confirmados (evitar re-grep)

- plant_units.parquet (14.280, 7.808 BRA): plant_uid, gem_row, unit_name, country, fleet, fuel_class, bio_subtype, tech_class, water_dependent, hydro_type, capacity_mw, gem_unit_id. BRA fleet: operating 4.919, planned_adv 2.834, planned_early 55. BRA tech_class: solar_pv 6.704, thermal_water_dependent 788, hydro 222, thermal_air_only 94.
- plants.parquet (12.459, 6.926 BRA): plant_uid, plant_name, country, fleet, tech_class, water_dependent, hydro_type, capacity_mw, lat, lon, dist_coast_km, coastal_2/5/10km, basin_id.
- plant_cell.parquet (12.459): plant_uid, cell_lat, cell_lon, dist_to_cell_km.
- Itaipu: plant_uid=8080ad0c..., lat −25.4078/lon −54.5892, capacity_mw=14000.0 (convenção a).
- w3_table1.csv (243): group (6 fuel-classes: bioenergy, coal, gas, multi_fuel, nuclear, oil + 2 tech-aggregates + total), fleet (4 categorias: operating, planned_adv, planned_early, planned_all), threshold {20,30,40}. Headline threshold=30 (precedente scripts/w3_table1.py:35, HEAD_GROUPS).
- w3_curves_plot.csv (648): mesmo schema, threshold {10,20,30,40,50,60,80,100}. Filtro Fig 2 headline: group=="all_thermal" & fleet∈[operating,planned_all] (precedente scripts/w3_curves.py:39-40).
- w3g_heat_cell_class.csv (1.404=468×3): cell_lat, cell_lon, scenario, class_median∈{low,medium,high,extreme}. Grade real 0.5°×0.5° com lacunas — diffs únicos entre valores ordenados incluem 1.0/2.5/3.0 além de 0.5 (domínio mascarado, não contíguo); grid completo deve ser construído via np.arange(min,max+step,step) + reindex, buracos = NaN/transparente.
- w4g_fd_unit_values.csv (13.815=921×5×3): plant_uid, model, scenario, baseline_value, future_value, ratio. Join com plants.parquet sem órfãos.
- w4b_excess_over_null.csv (108 linhas): fleet∈{operating,planned_adv,planned_early} (sem planned_all). itaipu∈{a,b}. null_type: 6 valores.
- w4c_spi_vs_spei.csv (324 linhas, pós-fix D125): group∈{hydro,thermal_water_dependent}, hazard∈{spei,spi}, fleet, itaipu∈{a,b,na}, scenario, null_type. Fonte única usada na Fig 4 (forest plot, filtro fleet=="operating" & null_type=="block_bootstrap_12").
- w3h_state_coexposure.csv (2.952 linhas): group, fleet, itaipu, scenario, null∈{block12,year,anystart}, state_postal, macro_region, co_class∈{co_extreme,co_hi_ext}. null="block12" é headline (precedente scripts/w3h_state_coexposure.py:347-350). co_extreme = heat=extreme AND drought=extreme, mesmo GCM — nunca confundir com co_hi_ext. 27 estados = 26+DF; hidro em 19 estados, térmica em 26.
- w4d_leave_one_out.csv (15 linhas): bucket∈{hydro_reservoir,hydro_run_of_river}.
- table3_coexposure.csv (192 linhas, C85): group, fleet, itaipu, scenario, heat_class, drought_class, pool, null, gw_median, pct_median. Fatorial completo: 2 grupos × 2 fleets × 3 cenários × 16 células (4×4) = 192.

## 6. Funções de produção reutilizadas (não reinventar)

- dl.find_plant(plants, country, name_part, mw, tol=1e-6) — src/craei/hazards/drought_levels.py:18.
- hl.with_itaipu_versions(units, itaipu_uids, total_mw=14000.0, foreign_mw=7000.0) — src/craei/exposure/heat_levels.py:43.
- Precedente de filtro (th1_fleet_gw.py:102): (fleet=="operating") & (itaipu.isin(["na","b"])).
- scripts/geo_base.py (O26): gera cache natural_earth_brazil.gpkg.
- scripts/article_map_utils.py (novo, C87): compass_rose(), scale_bar(), base_brazil_map(ax, extent, adm1, adm0, sam0, state_labels=True).

## 7. Grupo E — estado atual (C87, commitado)

| Figura | Design atual (v3) | Validação | Arquivo |
|---|---|---|---|
| Fig 1 | Raster real (pcolormesh, grade 0.5°) classe de calor + marcadores só térmica (círculo water-dep./losango air-only), cor=vermelho se célula extreme, hidro excluído por design | 745 plantas térmicas, join sem órfãos, 340 extreme (SSP5-8.5 amostra) PASS | fig1_heat_class_map.png |
| Fig 2 | 1 painel único, 6 linhas (3 cenários×2 fleets), SSP5-8.5 enfatizado visualmente (linha grossa/alpha) | 48 linhas PASS | fig2_threshold_curves.png |
| Fig 3 | 3 subplots/cenário, marcador por tech_class, cor exposto/não por R_D≥2.0 | join sem órfãos, progressão 339/433/770 PASS | fig3_drought_exposure_map.png |
| Fig 4 | Forest plot horizontal, 1 painel, 3 grupos×3 cenários (O20 resolvido) | 3 regressões D102/D125 (tol 1e-3) PASS | fig4_excess_over_null.png |
| Fig 5a/5b | Split hidro/térmica, mesmo chrome de Fig 1/3 via base_brazil_map(), sem marcadores, escala contínua | 19/26 estados PASS | fig5a_state_coexposure_hydro.png, fig5b_state_coexposure_thermal.png |
| Fig 6 | Barras agrupadas, 2 painéis (operating/planned)×6 fuels×3 cenários; nuclear excluído (operating), nuclear+oil excluído (planned) | assert contagem PASS | fig6_thermal_heat_by_fuel.png |

Table 3: table3_crosstab_main.csv/md (operating/ssp585, hidro+térmica lado a lado) + table3_crosstab_supplementary.md (10 combos restantes) + long-form original (table3_coexposure_crosstab.csv/md, C85).

Todos os artefatos vivem em data/outputs/article/{figures,tables}/, fora do Git.

## 8. O20 — RESOLVIDO e registrado (D133, C87)

Fig 4 usa forest plot horizontal, fonte única w4c_spi_vs_spei.csv, nota de pools distintos hidro/térmica. Decisão formalmente registrada em docs/DECISIONS.md como D133, cobrindo também todo o redesign Fig 1/2/5/6 e o novo utilitário scripts/article_map_utils.py.

## 9. IDs — estado atual

Usados: C75–C87, D121–D133. Confirmados livres: D134, O42, O44, O45, O46. Próximo commit = C88.

## 10. Pendências conhecidas do Grupo E (a resolver via Claude Code, inspeção visual real)

- Nenhum PNG foi inspecionado visualmente em nenhuma sessão até agora — todas as validações foram por dado/regressão/schema/contagem. Este é o próximo passo natural, agora pelo Claude Code com capacidade de ver as imagens.
- Warning não resolvido: UserWarning: tight_layout incompatible with Axes em Fig 5a/5b (causado por fig.colorbar(ax=axes) + plt.tight_layout() redundante com bbox_inches="tight"). Não bloqueante, mas pendente de limpeza — provavelmente só remover o plt.tight_layout() explícito.
- Possível necessidade de ajuste fino de legendas/posicionamento/sobreposição de texto que só aparece em inspeção visual (ex. rosa-dos-ventos ainda grande demais, legendas cortadas, sobreposição de siglas de estado com marcadores).
- scripts/article_map_utils.py tem nome e função (base_brazil_map) Brasil-específicos — se a generalização multi-país (§13) avançar, este utilitário precisa ser parametrizado por país/geometria.

## 11. Mapa de tarefas atualizado

| Grupo | Conteúdo | Status |
|---|---|---|
| A–H (C75-C87) | ver §3 | DONE |
| Grupo E (figuras+tabelas) | Table 0-3 + Fig 1-6, redesign completo | DONE e commitado (C87), fora do Git os artefatos |
| Próximo (via Claude Code) | Revisão visual real dos PNGs → ajustes finos → possível commit C88+ | PENDENTE, não iniciado |
| Nova frente 1 (via Claude Code) | Reorganização/limpeza de repositório e código | PENDENTE, não iniciado |
| Nova frente 2 (via Claude Code) | Pipeline sequencial/estruturado (workflow organizado) | PENDENTE, não iniciado |
| Nova frente 3 (via Claude Code) | Generalização multi-país (python main.py BRA/PRT/IND), skip de fases já concluídas com log explícito | PENDENTE, não iniciado, maior escopo |
| H | Fase final do artigo (após ajustes de Grupo E) | Último |

## 12. Lições de processo acumuladas (consolidado)

- Checar precedente "headline" no script-fonte antes de escolher threshold/null/scenario/group quando o schema permite múltiplos valores.
- .NET CurrentDirectory ≠ $PWD — sempre caminho absoluto (Join-Path $root ...), inclusive para ReadAllBytes/ReadAllText.
- Heredocs longos quebram silenciosamente — dividir em passos menores; sempre remover _tmp_*.py ao final (checar git status periodicamente para órfãos).
- Desconfiar de concatenações sem espaço em texto colado de volta — verificar no arquivo real antes de supor corrupção.
- .gitattributes (C85) normaliza EOL no commit — warning "CRLF will be replaced by LF" é esperado, não erro.
- data_root é irmão do repo — caminhos de data/outputs/article/ são absolutos fora de CRAEI\.
- Evitar dependência nova por conveniência (tabulate) quando dá para implementar manualmente.
- Grid "regular" de dados geográficos pode ter lacunas reais — nunca inferir step a partir de diff de valores únicos ordenados sem checar todos os diffs distintos.
- representative_point() > centroid para rotular polígonos em CRS geográfico.

## 13. Plano de ação — próximas frentes (para execução via Claude Code)

### Frente 1 — Ajustes visuais do Grupo E

- Autor inspeciona os 7 PNGs atuais (fig1 a fig6b) e a Table 3 em data/outputs/article/.
- Lista única de ajustes (posicionamento, legendas, cortes, sobreposições, estética fina).
- Aplicar via Claude Code, reexecutando os scripts _tmp_fig*_v3.py-equivalentes (não preservados como arquivos permanentes — terá que recriar a lógica a partir da descrição de design em §7, ou localizar se algum script intermediário foi salvo em scripts/ nesta transição).
- Atenção: nenhum dos scripts de geração de figura (_tmp_fig1_v3.py etc.) foi promovido a arquivo permanente em scripts/ — só scripts/article_map_utils.py foi. Se o Claude Code precisar regenerar uma figura do zero, a lógica completa está descrita em §7 mas o código-fonte exato não existe mais no disco (foi _tmp_* removido após uso). Recomenda-se, nesta próxima fase, promover os scripts de figura a arquivos permanentes em scripts/ ou scripts/article/ em vez de usar padrão _tmp_* descartável — isso também serve à Frente 2 (organização).

### Frente 2 — Reorganização e limpeza de repositório/pipeline

Objetivo do autor: workflow "organizado, estruturado e sequencial". Sugestão de escopo a validar com o autor via Claude Code:

- Auditar scripts/ (produção vs. scripts/archive/ vs. artefatos de uma sessão só).
- Definir uma ordem de execução canônica (fases W1→W5 e além) documentada e, idealmente, executável (ex. scripts/run_pipeline.py ou main.py orquestrador — ver Frente 3, que já pede isso).
- Mover scripts de geração de figura de artigo (atualmente informais/_tmp_*) para um local permanente e nomeado (ex. scripts/article/fig1_heat_map.py etc.).
- Revisar docs/ pós-C86 (já reorganizado) para ver se a nova estrutura de pipeline exige mais ajuste documental.

### Frente 3 — Generalização multi-país

Objetivo do autor: python main.py Brazil ou python main.py BRA funcionar, e também python main.py PRT, python main.py IND, etc.

Requisito explícito: se uma fase já está concluída/pronta para aquele país (ex. aquisição de dados), pular automaticamente para a próxima, com log explícito disso (não re-executar trabalho já feito, e não falhar silenciosamente — avisar no log qual fase foi pulada e por quê).

Implicações a mapear (não resolvidas ainda, só identificadas):

- Código atual é fortemente Brasil-específico em vários pontos: COUNTRY = "BRA" hardcoded em scripts (ex. w3_heat_levels.py:101), nome de arquivo natural_earth_brazil.gpkg, função base_brazil_map(), filtros country=="BRA" espalhados.
- Itaipu é um caso-especial Brasil/Paraguai (convenção a/b) — não generaliza trivialmente; precisa de abstração tipo "plantas compartilhadas entre países" ou ficar como exceção documentada.
- plant_units, plants, etc. já têm coluna country — base para filtro genérico existe, mas os scripts não leem isso de forma parametrizada ainda.
- Geometria: natural_earth_brazil.gpkg precisaria virar um cache genérico por país ou um gpkg global com filtro dinâmico.
- Esse é o maior escopo de trabalho das 3 frentes — provavelmente requer um desenho de arquitetura dedicado (ex. um CountryConfig ou config/countries/{BRA,PRT,IND}.yaml) antes de tocar em código.

Esta frente não foi iniciada nesta sessão — é puramente planejamento para a próxima etapa com Claude Code.
