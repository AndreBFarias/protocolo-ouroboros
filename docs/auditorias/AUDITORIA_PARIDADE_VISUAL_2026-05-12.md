---
titulo: Auditoria de paridade visual dashboard × mockups - sessão 2026-05-12
data: 2026-05-12
auditor: agente Opus background
escopo: comparação textual dashboard atual vs mockups canônicos, Onda V-3 e ROTEIRO_TELAS
referencias:
  - docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md
  - docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md
  - docs/sprints/backlog/ROTEIRO_TELAS_2026-05-06.md
---

# Auditoria paridade visual 2026-05-12

## TL;DR

Cobertura textual estimada ~85-90% — todas as 11 sub-sprints da Onda V-3 (incluindo V-4-Revisor, V-SHELL-FIX e V-FINAL-FIX) já foram concluídas e estão em `docs/sprints/concluidos/`. **Onda V-3 está OBSOLETA como criação nova**; o que falta é validação visual real ao vivo e modularização (5 páginas ainda violam limite 800L). ROTEIRO_TELAS_2026-05-06 foi **EXECUTADO_INTEGRALMENTE** via Onda U+T+Q em 2026-05-06; permanece em backlog apenas como documento histórico.

## Inventário

- Mockups canônicos: **29 arquivos** em `novo-mockup/mockups/*.html` (00-shell, 01..28)
- Páginas Streamlit: **39 arquivos** em `src/dashboard/paginas/*.py` (inclui auxiliares `revisor_logic`, `pagamentos_valores`, `extracao_tripla`, `grafo_obsidian`, `styleguide`, `__init__`)
- Páginas mapeáveis a mockup: **28 (uma por mockup 01..28)**; cluster Bem-estar tem prefixo `be_` em 17 arquivos
- CSS por página: **29 arquivos** em `src/dashboard/css/paginas/` (1:1 com páginas, exceto auxiliares)

Mapa página↔mockup (28 telas):

| # | Mockup | Página Streamlit |
|---|---|---|
| 01 | 01-visao-geral.html | visao_geral.py |
| 02 | 02-extrato.html | extrato.py |
| 03 | 03-contas.html | contas.py |
| 04 | 04-pagamentos.html | pagamentos.py |
| 05 | 05-projecoes.html | projecoes.py |
| 06 | 06-busca-global.html | busca.py |
| 07 | 07-catalogacao.html | catalogacao.py |
| 08 | 08-completude.html | completude.py |
| 09 | 09-revisor.html | revisor.py |
| 10 | 10-validacao-arquivos.html | validacao_arquivos.py + extracao_tripla.py |
| 11 | 11-categorias.html | categorias.py |
| 12 | 12-analise.html | analise_avancada.py |
| 13 | 13-metas.html | metas.py |
| 14 | 14-skills-d7.html | skills_d7.py |
| 15 | 15-irpf.html | irpf.py |
| 16 | 16-inbox.html | inbox.py |
| 17 | 17-bem-estar-hoje.html | be_hoje.py |
| 18 | 18-humor-heatmap.html | be_humor.py |
| 19 | 19-diario-emocional.html | be_diario.py |
| 20 | 20-rotina.html | be_rotina.py + be_tarefas.py + be_alarmes.py + be_contadores.py |
| 21 | 21-recap.html | be_recap.py |
| 22 | 22-eventos.html | be_eventos.py |
| 23 | 23-memorias.html | be_memorias.py |
| 24 | 24-medidas.html | be_medidas.py + be_treinos.py |
| 25 | 25-ciclo.html | be_ciclo.py |
| 26 | 26-cruzamentos.html | be_cruzamentos.py |
| 27 | 27-privacidade.html | be_privacidade.py |
| 28 | 28-rotina-toml.html | be_editor_toml.py |

## Comparação textual (8 amostras)

### visao_geral
- Mockup: `novo-mockup/mockups/01-visao-geral.html` (73 linhas, 4 KPIs + cluster-grid 3x2 + atividade-recente)
- Página: `src/dashboard/paginas/visao_geral.py` (782 linhas; modularizada com `componentes/atividade_recente.py` e `componentes/cards_clusters.py`, vide linhas 99-103)
- Macro: page-header canônico + 4 KPIs agentic-first + 6 cluster-cards + Atividade Recente + Sprint Atual (UX-V-FINAL-FIX defeitos 3 e 4 fechados em commit `9c2ff28`)
- Componentes presentes: kpi-grid, cluster-cards, atividade_recente_html, sparkline, link sem sublinhado
- Componentes ausentes: nenhum estrutural; pode haver micro-ajustes de espaçamento residuais não detectáveis sem render
- Veredito: **PARIDADE_ALTA** (saiu de 996L para 782L conforme prometia UX-V-2.7-FIX)

### extrato
- Mockup: `novo-mockup/mockups/02-extrato.html` (188 linhas, filt-bar inline + lista por dia + pílulas tipadas)
- Página: `src/dashboard/paginas/extrato.py` (1497 linhas — VIOLA limite 800L)
- Macro: filt-bar canônica em `_pilula_tipo` (linha 333), `_lista_por_dia_html` (linha 465), bloco UX-V-3.1 marcado em linha 312 e 872
- CSS: `src/dashboard/css/paginas/extrato.css` define `.t02-filt-bar` (linha 27) e `.t02-filt-counter` (linha 46)
- Componentes presentes: filt-bar inline, lista por dia, pílulas tipadas (banco/forma), counter, right-cards
- Componentes ausentes: nada estrutural identificável; tamanho 1497L indica débito de modularização (existe `sprint_INFRA_split_extrato.md` em backlog)
- Veredito: **PARIDADE_ALTA** com débito infra (split pendente)

### busca
- Mockup: `novo-mockup/mockups/06-busca-global.html` (157 linhas, search-bar + 4 facetas laterais + res-group com snippet+highlight)
- Página: `src/dashboard/paginas/busca.py` (1162 linhas — VIOLA limite 800L)
- Macro: `_highlight_termo` em linha 363, `_renderizar_facetas_laterais` em linha 748, colunas `[1, 3]` (linha 514)
- Componentes presentes: facet-card lateral (Tipo/Período/Fonte), snippet highlight com `<mark>` token-escape (linha 392), grupos
- Componentes ausentes: faceta "Pessoa" coletada mas não renderizada (decisão explícita por mockup pedir 4 facetas, comentário linhas 765-784)
- Veredito: **PARIDADE_ALTA** com débito infra

### catalogacao
- Mockup: `novo-mockup/mockups/07-catalogacao.html` (138 linhas, grid de thumbs com badges + sidebar 3 facetas)
- Página: `src/dashboard/paginas/catalogacao.py` (1048 linhas — VIOLA limite 800L)
- Macro: `_renderizar_grid_thumbs` (linha 394) com sidebar 3 facetas (TIPO/PERÍODO/FONTE), badges de extensão (linhas 631-665)
- Componentes presentes: KPIs+tipos (decisão híbrida do dono em 2026-05-07), grid de thumbs, badges, ouroboros-doc-thumb
- Veredito: **PARIDADE_ALTA**; bug roteamento `?tab=Catalogação` corrigido por UX-V-3.3-FIX-ROTA (em concluidos/)

### projecoes
- Mockup: `novo-mockup/mockups/05-projecoes.html` (162 linhas, 3 cenários + marcos sobrepostos + slider personalizado)
- Página: `src/dashboard/paginas/projecoes.py` (871 linhas — VIOLA limite 800L)
- Macro: cards de cenários (linhas 196-225), `_card_marcos_html` (linha 264) com até 5 marcos do realista, slider mínimo R$ 100 (UX-V-FINAL-FIX defeito 6, linha 701-708)
- Componentes presentes: 3 cenários, marcos sobrepostos com cores, slider personalizado, aporte_mensal funcional (defeito 1 da V-FINAL-FIX)
- Veredito: **PARIDADE_ALTA** com débito infra (sprint_INFRA_split_projecoes.md em backlog)

### irpf
- Mockup: `novo-mockup/mockups/15-irpf.html` (152 linhas, dropdown ano + categorias + barras coloridas + botões expand/baixar + checklist)
- Página: `src/dashboard/paginas/irpf.py` (484 linhas — dentro do limite)
- Macro: 4 artefatos + checklist 5 itens + botão "Gerar pacote" (linhas 9-19); `<button>baixar</button>` em linha 311; checklist em linha 415
- Componentes presentes: categorias completas, barras coloridas, botões expand+baixar inline, checklist
- Veredito: **PARIDADE_ALTA**

### inbox
- Mockup: `novo-mockup/mockups/16-inbox.html` (87 linhas — mais simples; dropzone + KPIs + chips)
- Página: `src/dashboard/paginas/inbox.py` (540 linhas — dentro do limite)
- Macro: dropzone (linha 114), 5 KPIs em kpi-grid (linhas 270-281), inbox-tipo-chips (linha 132)
- Componentes presentes: dropzone, 5 KPIs (Aguardando/Extraído/Falhou + outros), chips de tipo
- Veredito: **PARIDADE_ALTA**

### revisor
- Mockup: `novo-mockup/mockups/09-revisor.html` (107 linhas, 4-way OFX×Rascunho×Opus×Humano + tabs filtro + trace)
- Página: `src/dashboard/paginas/revisor.py` (1196 linhas — VIOLA limite 800L)
- Macro: card 4-way OFX/Rascunho/Opus/Humano (linhas 610-613), tabs filtro "Só rascunhos" (linhas 401, 510-511), `_trace_raciocinio_html` (linha 636), `Apuração 4-way` (linha 711)
- Componentes presentes: 4 painéis, tabs filtro (mês atual, divergentes, rascunhos), trace de raciocínio, pills APURADO/DIVERGENTE/RASCUNHO
- Veredito: **PARIDADE_ALTA** com débito infra (sprint_INFRA_split_revisor.md em backlog)

## Onda V-3 (11 sub-sprints originalmente propostas em 2026-05-07/08)

Todas residem em `docs/sprints/concluidos/` com `status: concluída`:

1. **UX-V-3.1-EXTRATO-FILT** — `sprint_ux_v_3_1_extrato_filt.md` → **OBSOLETA** (concluída; filt-bar + lista por dia implementadas em extrato.py:312-529)
2. **UX-V-3.2-BUSCA-FACET** — `sprint_ux_v_3_2_busca_facet.md` → **OBSOLETA** (concluída; facetas + snippet em busca.py:363-841)
3. **UX-V-3.3-CATALOGACAO-FIX-ROTA** — `sprint_ux_v_3_3_catalogacao_fix_rota.md` → **OBSOLETA** (concluída; bug roteamento M5 fechado)
4. **UX-V-3.3-CATALOGACAO-GRID** — `sprint_ux_v_3_3_catalogacao_grid.md` → **OBSOLETA** (concluída; grid de thumbs em catalogacao.py:394-665)
5. **UX-V-3.4-IRPF-FINISH** — `sprint_ux_v_3_4_irpf_finish.md` → **OBSOLETA** (concluída; 2 categorias + botões expand/baixar + checklist em irpf.py)
6. **UX-V-3.5-BE-HOJE-CARDS** — `sprint_ux_v_3_5_be_hoje_cards.md` → **OBSOLETA** (concluída; `_card_status_casal` em be_hoje.py:406)
7. **UX-V-3.6-BE-HUMOR-DEMO** — `sprint_ux_v_3_6_be_humor_demo.md` → **OBSOLETA** (concluída; sparkline + `_streak_humor_alto` em be_humor.py:382)
8. **UX-V-3.7-BE-DIARIO** — `sprint_ux_v_3_7_be_diario.md` → **OBSOLETA** (concluída; 4 tabs Trigger/Vitória/Reflexão/Observação em be_diario.py:75-78)
9. **UX-V-4-REVISOR** — `sprint_ux_v_4_revisor.md` → **OBSOLETA** (concluída; layout 4-pane + tabs + trace em revisor.py:610-869)
10. **UX-V-SHELL-FIX** — `sprint_ux_v_SHELL_FIX.md` → **OBSOLETA** (concluída; M9.1-M9.4 do shell global fechados)
11. **UX-V-FINAL-FIX** — `sprint_ux_v_final_fix.md` → **OBSOLETA** (concluída em commit `9c2ff28`; 7 defeitos pós-Onda V fechados)

**Conclusão Onda V-3**: a auditoria 2026-05-08 declarou que "0 sprints criadas em backlog" — entre 2026-05-08 e 2026-05-12 (4 dias) o time as escreveu, executou e arquivou. Nenhuma sub-sprint V-3 precisa ser criada agora.

## ROTEIRO_TELAS_2026-05-06

**Status: EXECUTADO_INTEGRALMENTE.**

Verificação em `docs/sprints/concluidos/`:
- Onda U (4 sprints): `sprint_ux_u_01_sidebar_canonica.md`, `sprint_ux_u_02_topbar_canonica.md`, `sprint_ux_u_03_page_header_canonico.md`, `sprint_ux_u_04_filtros_pagina.md` — todas `concluida_em: 2026-05-06`
- Onda T (telas, agrupadas): `sprint_ux_t_01_visao_geral_canonica.md`, `t_02_extrato_canonico`, `t_03_contas_canonico`, `t_04_pagamentos_canonico`, `t_05_projecoes_canonico`, `t_06_10_cluster_documentos`, `t_11_16_clusters_analise_metas_sistema_inbox`, `t_17_28_cluster_bem_estar`, `t_29_shell_index_revalida` — todas concluídas
- Onda Q (gates finais): `sprint_ux_q_01_auditoria_visual_completa.md`, `q_02_regressao_integradora`, `q_03_fechamento` — todas concluídas

O documento `docs/sprints/backlog/ROTEIRO_TELAS_2026-05-06.md` permanece em `backlog/` apenas como **artefato histórico de planejamento**, não como sprint pendente.

**Próximas decisões necessárias**: mover ROTEIRO_TELAS para `docs/auditorias/` ou `docs/redesign/historico/` para evitar confusão com backlog vivo.

## Gaps remanescentes (máximo 5)

1. **Modularização das 5 páginas que violam 800L**: `extrato.py = 1497L`, `revisor.py = 1196L`, `busca.py = 1162L`, `catalogacao.py = 1048L`, `analise_avancada.py = 957L`. Há specs `sprint_INFRA_split_extrato.md`, `_split_catalogacao.md`, `_split_projecoes.md`, `_split_recap.md`, `_split_revisor.md` em `backlog/` mas **falta spec para busca.py e analise_avancada.py**. Também `be_recap.py = 825L`, `completude.py = 845L`, `contas.py = 869L`, `projecoes.py = 871L`, `skills_d7.py = 826L` estão acima de 800L.

2. **Validação visual ao vivo pós-V-FINAL-FIX**: a auditoria 2026-05-08 só inspecionou estado pré-V-FINAL-FIX (que foi mergeada em commit `9c2ff28`). Não há registro de re-auditoria side-by-side desde então; os 70-75% honestos da 2026-05-08 podem ser ~85-90% hoje, mas faltam screenshots/MCP playwright para confirmar.

3. **Spec `extracao_tripla.json` populado**: arquivo `data/output/extracao_tripla.json` existe (vide find), mas sem inspeção do conteúdo não dá pra confirmar se a coluna Opus em Validação Tripla saiu do estado 100% vazio reportado na auditoria 2026-05-08. UX-V-2.4-FIX está em `concluidos/` mas precisa validação humana com >=3 amostras.

4. **Page-header canônico em 100% das páginas**: UX-U-03 (page_header.py existe em `componentes/`) precisa auditoria para confirmar que TODAS as 28 páginas adotaram o helper (não houve verificação programática textual nesta auditoria).

5. **WCAG 2.1 AA / regressão integradora**: ROTEIRO_TELAS Q-02 prometia `pytest tests/ -q >= 2530`; estado atual (segundo MEMORY 2026-04-26) é 1530 passed — gap potencial de 1000 testes não auditado aqui. Pode ser falsa positiva (baseline desatualizada) mas merece checagem.

## Recomendação

- **Onda V-3**: **ARQUIVAR**. Todas as 11 sub-sprints estão em `concluidos/`. Não criar nada novo sob a égide V-3.
- **ROTEIRO_TELAS_2026-05-06**: **ARQUIVAR** (mover de `backlog/` para `docs/redesign/historico/` ou `docs/auditorias/redesign-2026-05-06/`).
- **Próxima sprint a propor**:
  1. `UX-INFRA-SPLIT-RESTANTES` (~8h): específica para `busca.py`, `analise_avancada.py`, `be_recap.py`, `completude.py`, `contas.py`, `projecoes.py`, `skills_d7.py` reduzirem para ≤800L.
  2. `UX-AUDIT-VISUAL-2026-05-12` (~3h): re-auditoria side-by-side ao vivo com MCP playwright/claude-in-chrome para confirmar score ≥85% pós-V-FINAL-FIX e gerar `AUDITORIA_PARIDADE_VISUAL_2026-05-13.md` com prints.
- **NÃO recomendar**: criar Onda V-5/V-6 ou nova leva. O sistema já entregou tudo o que a auditoria 2026-05-08 listou; falta apenas medição honesta.

*"O que termina sem fechamento volta cobrando juros." — princípio do arquivar canônico*
