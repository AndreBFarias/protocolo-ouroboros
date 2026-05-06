# Roteiro Tela-a-Tela 2026-05-06 — 36 sprints (Onda U + T + Q)

> **Origem**: pedido do dono em 2026-05-06 para reorganização após constatar que a abordagem de fixes transversais (UX-RD-FIX-01..14, arquivada em `docs/sprints/arquivadas/2026-05-tentativa-fix-transversal/`) entregou métricas DOM verdes mas percepção visual integrada continuou quebrada (sidebar misturando antigo+novo, KPIs semânticos errados na Home, layout esparso, bugs Plotly).
>
> **Plano operacional canônico**: `~/.claude/plans/auditoria-honesta-da-magical-lovelace.md`.

## Filosofia

Cada sprint entrega **UMA peça completa**:

- **Onda U** (4 sprints): peça estruturante universal — toca shell global, impacta todas as 29 telas. Devem ser primeiras.
- **Onda T** (29 sprints): UMA tela inteira por sprint — layout 1:1 com mockup + funcional + dados reais + validação humana.
- **Onda Q** (3 sprints): quality gates finais.

Quando uma sprint fecha, sua peça está **100% pronta** e não precisa voltar.

## Garantias de qualidade (em cada sprint)

1. **Captura side-by-side mockup × dashboard** automática em `docs/auditorias/redesign-2026-05-06/<sprint>.png`.
2. **Validação humana obrigatória** entre sprints — dono inspeciona antes de mover para `concluidos/`.
3. **Validador integrador (Opus interativo)** revisa output antes de declarar concluída.
4. **Gauntlet rigoroso**: lint + smoke + pytest baseline + deep-link da rota afetada + smoke específico da página.
5. **Reversibilidade**: cada sprint em commit isolado, mensagem `feat(ux-<u|t|q>-NN): <slug>`.
6. **Quality gates por onda**: U bloqueia T; T bloqueia Q.

## DAG de dependências

```
Onda U (sequencial, todas bloqueiam Onda T)
  U-01 (sidebar)            -- independente
    |
  U-02 (topbar)              -- independente
    |
  U-03 (page-header)         -- depende U-02 (topbar é onde page-header se ancora)
    |
  U-04 (filtros página)      -- depende U-01 (sidebar precisa ficar shell-only)

Onda T (depende U-01..U-04 mergeadas; sequencial entre si)
  T-01 (Visão Geral)         -- precisa shell + filtros prontos
  T-02 .. T-29               -- na ordem da tabela

Onda Q (depende todas T-* mergeadas)
  Q-01 (auditoria visual)
  Q-02 (regressão funcional)
  Q-03 (fechamento)
```

## Tabela completa das 36 sprints

### Onda U — Estruturantes universais (4 sprints, ~3-4 dias)

| ID | Tema | Esforço | Mockup-fonte | Toca |
|---|---|--:|---|---|
| **U-01** | Sidebar canônica (8 clusters scroll, brand glyph, busca, badges, **zero widgets antigos**) | 1 dia | `00-shell-navegacao.html` (bloco sidebar) | `componentes/shell.py`, `tema_css.py` (.sidebar overflow-y:auto) |
| **U-02** | Topbar canônica (breadcrumb clicável + slot `topbar-actions` por página) | 0.5 dia | `00-shell-navegacao.html` (bloco topbar) | `componentes/shell.py:renderizar_topbar`, `app.py:_renderizar_topbar_para` |
| **U-03** | Page-header canônico (helper `componentes/page_header.py`, h1 40px UPPERCASE gradient + page-subtitle + page-meta) | 1 dia | `_shared/components.css` `.page-header`/`.page-title` | NOVO `componentes/page_header.py`; refactor 29 `paginas/*.py` |
| **U-04** | Filtros por página (helper `componentes/filtros_pagina.py`; refactor `_sidebar()` para shell-only) | 1.5 dia | filtros visíveis em mockups específicos (ex.: 02-extrato, 11-categorias, 22-eventos) | `app.py:_sidebar` (corte radical), 29 `paginas/*.py`, NOVO `componentes/filtros_pagina.py` |

### Onda T — Telas (29 sprints, ~29 dias, 1 sprint/dia média)

Ordem estratégica do mais visível ao mais nicho:

| Ordem | ID | Tela | Mockup-fonte | Esforço |
|--:|---|---|---|--:|
| 1 | **T-01** | Visão Geral | `01-visao-geral.html` | 1d |
| 2 | **T-02** | Extrato | `02-extrato.html` | 1.5d |
| 3 | **T-03** | Contas | `03-contas.html` | 1d |
| 4 | **T-04** | Pagamentos (calendário 14d) | `04-pagamentos.html` | 1.5d |
| 5 | **T-05** | Projeções (3 cenários) | `05-projecoes.html` | 1d |
| 6 | **T-06** | Busca Global | `06-busca-global.html` | 1d |
| 7 | **T-07** | Catalogação | `07-catalogacao.html` | 1d |
| 8 | **T-08** | Completude (heatmap) | `08-completude.html` | 1d |
| 9 | **T-09** | Revisor (4-way ETL×Opus×Grafo×Humano) | `09-revisor.html` | 1.5d |
| 10 | **T-10** | Validação por Arquivo (Extração Tripla) | `10-validacao-arquivos.html` | 1.5d |
| 11 | **T-11** | Categorias (treemap+árvore) | `11-categorias.html` | 1d |
| 12 | **T-12** | Análise (sankey+heatmap) | `12-analise.html` | 1.5d |
| 13 | **T-13** | Metas (donuts+gauges) | `13-metas.html` | 1.5d |
| 14 | **T-14** | Skills D7 | `14-skills-d7.html` | 1d |
| 15 | **T-15** | IRPF | `15-irpf.html` | 1d |
| 16 | **T-16** | Inbox | `16-inbox.html` | 1d |
| 17 | **T-17** | Bem-estar Hoje | `17-bem-estar-hoje.html` | 1d |
| 18 | **T-18** | Humor heatmap | `18-humor-heatmap.html` | 1d |
| 19 | **T-19** | Diário emocional | `19-diario-emocional.html` | 1d |
| 20 | **T-20** | Rotina | `20-rotina.html` | 1d |
| 21 | **T-21** | Recap | `21-recap.html` | 1d |
| 22 | **T-22** | Eventos | `22-eventos.html` | 1d |
| 23 | **T-23** | Memórias | `23-memorias.html` | 1d |
| 24 | **T-24** | Medidas | `24-medidas.html` | 1d |
| 25 | **T-25** | Ciclo | `25-ciclo.html` | 1d |
| 26 | **T-26** | Cruzamentos | `26-cruzamentos.html` | 1d |
| 27 | **T-27** | Privacidade A↔B | `27-privacidade.html` | 0.5d |
| 28 | **T-28** | Editor TOML | `28-rotina-toml.html` | 0.5d |
| 29 | **T-29** | Shell index revalidação | `00-shell-navegacao.html` | 0.5d |

### Onda Q — Quality Gates (3 sprints, ~2 dias)

| ID | Tema | Esforço |
|---|---|--:|
| **Q-01** | Auditoria visual completa 29/29 com tabela fidelidade ≥90% por dimensão | 0.5d |
| **Q-02** | Regressão funcional integradora (`./run.sh --tudo` + smoke 10/10 + pytest baseline + deep-link 8 clusters) | 0.5d |
| **Q-03** | Fechamento (mover specs para concluidos/, atualizar docs, gerar `AUDITORIA_REDESIGN_FINAL_2026-XX.md`, commit + tag) | 1d |

## Anatomia de cada spec T-NN (template)

Toda spec da Onda T segue este formato:

```yaml
sprint:
  id: UX-T-NN
  title: "<Nome da tela>"
  prioridade: P0
  estimativa: <Xh>
  onda: T
  mockup_fonte: novo-mockup/mockups/NN-slug.html
  depende_de: [U-01, U-02, U-03, U-04]
  bloqueia: []
  touches:
    - path: src/dashboard/paginas/<X>.py
      reason: "Reescrita 1:1 com mockup"
    - path: tests/test_<X>_redesign.py
      reason: "NOVO -- testes de comportamento da nova página"
  forbidden:
    - "Reaproveitar layout antigo da página (reescreve do zero baseado no mockup)"
    - "Adicionar widgets na sidebar (já é shell-only após U-04)"
  hipotese:
    - "Estado atual da página diverge do mockup em N pontos. Captura BEFORE confirma antes de codar."
  acceptance_criteria:
    - "Layout 1:1 com mockup canônico (estrutura + tipografia + paleta + densidade)"
    - "Botões topbar mockup presentes via slot topbar-actions (U-02)"
    - "Filtros inline mockup presentes via componentes/filtros_pagina (U-04)"
    - "Gráficos mockup com biblioteca correta (SVG inline custom OU Plotly Dracula via tema_plotly)"
    - "Dados reais integrados (sem mock); empty state quando vault/XLSX vazio"
    - "Validação humana: dono confirma visualmente comparando mockup × dashboard ao vivo"
  proof_of_work:
    - "PNG side-by-side em docs/auditorias/redesign-2026-05-06/T-NN.png"
    - "Gauntlet completo verde"
```

Cada spec terá 7-10 seções (Contexto, Hipótese, Layout canônico, Funcionalidades, Dados, Tarefas, Validação, Gauntlet, Anti-débito, Citação).

## Critério global de pronto (após Q-03)

- 29 telas com fidelidade ≥90% por dimensão (estrutura, tipografia, paleta, conteúdo, animação, interação)
- Sidebar com 8 clusters totalmente visíveis em viewport >= 768x600, scroll interno, sem widgets antigos
- Topbar com breadcrumb clicável + slot ações por página
- Page-title canônico em 100% das páginas (UPPERCASE 40px gradient)
- Filtros inline em cada página (sem globais na sidebar)
- `make lint` exit 0; `make smoke` 10/10; `pytest tests/ -q` >= 2530
- Pipeline ETL `./run.sh --tudo` sem regressão
- Deep-link 8 clusters × abas declaradas funcionais
- Zero TODO/FIXME inline
- Cobertura WCAG 2.1 AA (skip-link + aria-current + role=tablist + foco visível)

## Cronograma realista

| Onda | Sprints | Duração |
|---|--:|--:|
| U | 4 | 3-4 dias |
| T | 29 | ~29 dias |
| Q | 3 | 2 dias |
| **Total** | **36** | **5-6 semanas** |

## Estado atual (2026-05-06)

| Status | Contagem |
|---|--:|
| Onda U specs em `backlog/` | 4 (a escrever após este roteiro) |
| Onda T specs em `backlog/` | 0 (escritas em batch após Onda U mergeada) |
| Onda Q specs em `backlog/` | 0 (escritas após Onda T mergeada) |
| Concluídas | 0 |
| Total previsto | 36 |

---

*"Cada peça encaixa em seu tempo; quem tenta encaixar todas ao mesmo tempo, encaixa nenhuma." -- adaptado de provérbio chinês*
