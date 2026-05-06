# Redesign Ouroboros — Índice mestre

> Índice das 19 sprints da reforma de UI do dashboard Streamlit para casar 1:1
> com os 28 mockups HTML em `novo-mockup/`. Plano canônico em
> `~/.claude/plans/lazy-noodling-wind.md`.

## Contexto e justificativa

Em 2026-05-04 o dono pediu reforma estrutural do dashboard, escolhendo:
- **Escopo cheio**: visual + Inbox real + Extração Tripla + cluster Bem-estar (12 telas).
- **Reescrita 1:1** com mockups HTML (não reskin). Mockup é fonte de verdade.

Mockups vivem em `novo-mockup/mockups/` (28 telas) com tokens canônicos em
`novo-mockup/_shared/tokens.css` e componentes em `novo-mockup/_shared/components.css`.

## Relação com plano ativo `pure-swinging-mitten`

O plano `~/.claude/plans/pure-swinging-mitten.md` Onda 6 reservou IDs
`UX-01..UX-09` para fixes pontuais (callout_html, WCAG-AA, drill-down Sankey,
pyvis fallback). A reescrita 1:1 com mockups **absorve esses 9 fixes** — cada
spec UX-RD-XX declara explicitamente quais UX-01..09 ela depreca.

## Branch

`git checkout -b ux/redesign-v1` — todas as 19 sprints partem dela.

## Validação canônica (padrão `(p)` do VALIDATOR_BRIEF)

Cada sprint é executada por subagente `executor-sprint` (contexto fresco) e
validada **visualmente pelo dono Opus principal** (não despacha
`validador-sprint`). Validação obrigatória:
1. Diff comparativo lado-a-lado mockup HTML × dashboard reformado.
2. Screenshot salvo em `docs/auditorias/redesign/<sprint-id>.png`.
3. Comando runtime real: `./run.sh --dashboard` + URL específica.
4. `make lint` + `make smoke` 10/10 + `pytest tests/ -q` baseline mantida.
5. Spec movida para `concluidos/` com `concluida_em: YYYY-MM-DD`.

## Tabela de sprints

| ID | Nome | Onda | Estimativa | Depende de | Mockup |
|---|---|---|---|---|---|
| UX-RD-01 | Tokens novos + paleta migrada | 0 | 2h | — | `_shared/tokens.css` |
| UX-RD-02 | tema_css.py reescrito sobre componentes shared | 0 | 3h | UX-RD-01 | `_shared/components.css` |
| UX-RD-03 | Shell global: sidebar 8-clusters + atalhos | 0 | 4h | UX-RD-02 | `00-shell-navegacao.html` |
| UX-RD-04 | Visão Geral reescrita | 1 | 3h | UX-RD-03 | `01-visao-geral.html` |
| UX-RD-05 | Skills D7 + Styleguide | 1 | 2h | UX-RD-03 | `14-skills-d7.html` + `styleguide.html` |
| UX-RD-06 | Extrato reescrito | 2 | 4h | UX-RD-03 | `02-extrato.html` |
| UX-RD-07 | Contas + Pagamentos | 2 | 3h | UX-RD-03 | `03-contas.html` + `04-pagamentos.html` |
| UX-RD-08 | Projeções | 2 | 2h | UX-RD-03 | `05-projecoes.html` |
| UX-RD-09 | Busca Global + Catalogação | 3 | 4h | UX-RD-03 | `06-busca-global.html` + `07-catalogacao.html` |
| UX-RD-10 | Completude + Revisor | 3 | 4h | UX-RD-03 | `08-completude.html` + `09-revisor.html` |
| UX-RD-11 | Extração Tripla (substitui validação por arquivo) | 3 | 4h | UX-RD-03 | `10-validacao-arquivos.html` (era extração tripla) |
| UX-RD-12 | Categorias | 4 | 3h | UX-RD-03 | `11-categorias.html` |
| UX-RD-13 | Análise (sankey + comparativo + heatmap) | 4 | 4h | UX-RD-03 | `12-analise.html` |
| UX-RD-14 | IRPF + Metas | 4 | 3h | UX-RD-03 | `15-irpf.html` + `13-metas.html` |
| UX-RD-15 | Inbox real | 5 | 4h | UX-RD-03 | `16-inbox.html` |
| UX-RD-16 | Bridge vault Bem-estar (estende mobile_cache) | 6 | 4h | UX-RD-03 + MOB-bridge-3 | — (backend) |
| UX-RD-17 | Bem-estar Hoje + Humor heatmap | 6 | 4h | UX-RD-16 | `17-bem-estar-hoje.html` + `18-humor-heatmap.html` |
| UX-RD-18 | Diário emocional + Eventos | 6 | 4h | UX-RD-16 | `19-diario-emocional.html` + `22-eventos.html` |
| UX-RD-19 | Bem-estar resto consolidado | 6 | 4h | UX-RD-16 | `20-rotina.html` + `21-recap.html` + `23-26` + `28` |

**Total estimado**: ~67h. Distribuído em sessões de 2-4h cada (1-2 sprints/sessão).

## Ordem recomendada

1. **Onda 0** (UX-RD-01..03) — sequencial, bloqueante.
2. **Onda 1** (UX-RD-04, 05) — sequencial após Onda 0.
3. **Ondas 2-4** (UX-RD-06..14) — podem paralelizar; default sequencial.
4. **Onda 5** (UX-RD-15) — independente após Onda 0.
5. **Onda 6** (UX-RD-16..19) — UX-RD-16 paralelizável com 2-5; demais sequencial após bridge.

## Specs absorvidas/depreciadas

| Spec | Status | Sprint que absorve |
|---|---|---|
| UX-01 (callout_html) | DEPRECADA | UX-RD-02 (tokens cobrem todos os callouts) |
| UX-02 (treemap WCAG) | DEPRECADA | UX-RD-12 (categorias usa palette nova compliant) |
| UX-03 (drill-down sankey/heatmap) | DEPRECADA | UX-RD-13 |
| UX-04 (Revisor responsivo) | DEPRECADA | UX-RD-10 |
| UX-05 (pyvis fallback) | DEPRECADA | UX-RD-09 (Grafo+Obsidian fora do escopo redesign — confirma fora) |
| UX-06 (logs falha grafo) | NÃO ABSORVIDA | mantida no plano ativo, backend |
| UX-07 (snapshot dinâmico contas) | DEPRECADA | UX-RD-07 |
| UX-08 (deep-link teste 13 abas) | RE-AVALIAR | UX-RD-03 mantém URL deep-link com novo shell |
| UX-09 (cleanup acentuação) | NÃO ABSORVIDA | sprint pequena de higiene, separada |

## Fase Corretiva pós-Onda 6 (2026-05-05) — 14 sprints UX-RD-FIX (ARQUIVADA em 2026-05-06)

A auditoria honesta `docs/auditorias/AUDITORIA_REDESIGN_2026-05-05.md` (após Onda 6 marcada concluída em 2026-05-04) revelou **score real 64/100** vs meta 95+. Treze classes de divergências mockup × dashboard foram catalogadas e atribuídas a **14 sprints corretivas**. Todas executadas em 2026-05-05 com gauntlet verde (lint+smoke+pytest).

**Resultado**: métricas DOM passaram, mas em revisão visual em 2026-05-06 o dono constatou que **a percepção integrada continuou quebrada** — sidebar mistura widgets antigos (logo escudo, Granularidade/Mês/Pessoa selectbox, Busca Global text input) com shell HTML novo, KPIs semânticos errados na Visão Geral, layout esparso, bugs Plotly. A abordagem transversal (1 fix mexe em N páginas) não isolou shell global × conteúdo de tela.

**Decisão (2026-05-06)**: arquivar a Fase Corretiva e adotar abordagem por tela. Os fixes aplicados (UX-RD-FIX-01..14) **permanecem no código** — apenas as specs movem para `arquivadas/2026-05-tentativa-fix-transversal/`. Roteiro substituto em `ROTEIRO_TELAS_2026-05-06.md`.

Decisão arquitetural confirmada (2026-05-05, dono): **Decisão A** — criar 5 páginas Bem-estar reais (Treinos, Marcos, Alarmes, Contadores, Tarefas). Páginas órfãs (Memórias, Rotina, Cruzamentos, Privacidade, Editor TOML) acessíveis via deep-link interno `?secao=` (FIX-14).

| ID | Tema | Onda corretiva | Esforço | Depende de |
|---|---|--:|--:|---|
| FIX-01 | Lint acentuação 11 .md | C1 | 1h | -- |
| FIX-02 | Bug Despesa R$ 0,00 no Extrato | C1 | 2h | -- |
| FIX-03 | KPI grid minmax 220→180 | C1 | 30min | -- |
| FIX-04 | Material Symbols vazando | C1 | 2h | -- |
| FIX-05 | Breadcrumb clicável | C1 | 1h | -- |
| FIX-06 | H1 duplicado (remover st.title) | C1 | 1h | -- |
| FIX-07 | 23 glyphs SVG portados | C2 | 1d | -- |
| FIX-08 | Tipografia escala fina | C2 | 1d | -- |
| FIX-09 | Plotly modebar + Dracula | C2 | 1d | -- |
| FIX-10 | Criar 5 páginas Bem-estar reais | C3 | 2d | -- |
| FIX-11 | Deep-link 12 abas Bem-estar | C4 | 4h | FIX-10 |
| FIX-12 | Acessibilidade WCAG | C5 | 4h | -- |
| FIX-14 | Rota interna 5 órfãs | C5 | 6h | FIX-10, FIX-11 |
| FIX-13 | Citação filosófica em .py | C5 | 2h | TODAS |

**Total estimado**: ~7-8 dias úteis. Paralelizável em 9 worktrees (C1+C2). FIX-13 obrigatoriamente última.

Critério global de pronto: 29 telas com fidelidade ≥85%, deep-link funcional, lint exit 0, smoke 10/10, pytest baseline mantida, zero TODO inline, citação em todos os .py novos. Após FIX-13 → re-auditoria gera `AUDITORIA_REDESIGN_2026-05-12.md` confirmando ≥95/100.

---

## Fase Tela-a-Tela (2026-05-06) — Onda U + T + Q (CONCLUÍDA)

Após arquivar a Fase Corretiva, o dono pediu reorganização por **peça completa**: cada sprint entrega ou (a) uma peça estruturante universal (Onda U) ou (b) uma tela inteira 1:1 com mockup (Onda T) ou (c) quality gate final (Onda Q). Total: **36 sprints** em ~5-6 semanas.

Roteiro canônico: `docs/sprints/backlog/ROTEIRO_TELAS_2026-05-06.md`. Plano operacional: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`.

| Onda | Sprints | Foco | Status |
|---|--:|---|---|
| **U** | 4 (U-01..U-04) | Estruturantes universais (sidebar, topbar, page-header, filtros página) | **CONCLUÍDA** em 2026-05-06 |
| **T** | 29 (T-01..T-29) | Uma tela por sprint, layout 1:1 + funcional + dados + validação humana | **CONCLUÍDA** em 2026-05-06 (merge `550e2b1`) |
| **Q** | 3 (Q-01..Q-03) | Auditoria visual + regressão funcional + fechamento | **CONCLUÍDA** em 2026-05-06 |

**Garantias**: validação humana obrigatória entre cada sprint; captura side-by-side mockup × dashboard automática; reversibilidade (commits isolados); quality gates por onda.

---

## Fase Modularização (2026-05-06+) — Onda M (próxima fase)

Após Onda T+Q+U fecharem, auditoria visual em 2026-05-06 expôs débito arquitetural significativo:

- **17 páginas com `_CSS_LOCAL_*`** — CSS espalhado, com fallbacks duplicados.
- **`tema_css.py` com 1675 linhas** — CSS hard-coded em Python.
- **`instalar_fix_sidebar_padding` com 211 linhas e 56 `setProperty`** afetando todas as páginas.
- **17 helpers HTML em `tema.py`** sem fronteira única.

Commit `928628c` ("topbar polish") evidenciou o problema: regras JS universais bagunçaram layouts de outras páginas. Revertido em `2817706`.

**Onda M — 4 sprints + 4 sub-sprints** (specs em `backlog/`, índice em `INDICE_ONDA_M_MODULARIZACAO.md`):

| Sprint | Foco | Esforço |
|---|---|---|
| UX-M-01 | Tokens CSS centralizados (copy `novo-mockup/_shared/tokens.css`) | 3-5h |
| UX-M-02 | Componentes universais HTML (consolidar em `ui.py`) | 8-10h |
| UX-M-03 | CSS canônico do mockup (copy `novo-mockup/_shared/components.css`) | 4-6h |
| UX-M-04 | Shell consolidado em CSS estático | 5-7h |
| UX-M-02.A..D | Migração de 30+ páginas em 4 clusters | 16h (paralelo) |

**Total**: 36-44h. Meta: zero `_CSS_LOCAL_*`, ≤10 `setProperty`, fonte canônica em `novo-mockup/_shared/`.

Padrões canônicos descobertos: `(w)` JS runtime global afetando todas páginas (anti-padrão).

---

## Observabilidade da reforma

A skill `/auditar-cobertura-total` continua válida — não há contrato de
cobertura D7 sendo alterado. O que muda é só apresentação visual.

## Riscos materializados

| Risco | Mitigação | Sprint dona |
|---|---|---|
| Quebrar drill-down `?cluster=X&tab=Y` | UX-RD-03 reescreve shell preservando query params | UX-RD-03 |
| Perder Sprint 100 deep-link tabs | UX-RD-03 + cada UX-RD-XX da Onda 2-4 mantém âncora `tab=` | UX-RD-03 |
| Bridge Syncthing ausente no desktop | UX-RD-16 começa com `AskUserQuestion` confirmando path real | UX-RD-16 |
| pytest baseline 2.018 quebra | Cada sprint atualiza testes no escopo, nunca como follow-up | todas |
| Reskin parcial deixa inconsistência visual | Onda 0 é gate — dashboard quebrado é aceitável até Onda 0 fechar | UX-RD-01..03 |
| Frankenstein tokens vs hardcoded hex | `/validar-sprint` grep `#[0-9a-fA-F]{6}` em src/dashboard/ | todas |

---

*"Cada bloco é uma sprint pequena, lê-se de cima para baixo, executa-se em ordem." — adaptado de INSTRUCOES_PARA_CLAUDE_CODE.md*
