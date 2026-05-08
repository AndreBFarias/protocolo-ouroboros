---
id: UX-V-2.6-FIX
titulo: Análise — corrigir breadcrumb, tabs duplicadas, KPIs assimétricos, Insights
status: backlog
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 12)
mockup: novo-mockup/mockups/12-analise.html
---

# Sprint UX-V-2.6-FIX — 5 defeitos de Análise

## Contexto

Inspeção 2026-05-08 revelou em UX-V-2.6 (declarada concluída):

1. Breadcrumb mostra "ANÁLISE / VISÃO GERAL" (errado).
2. Tabs duplicadas: 3 tabs no topo + 3 sub-abas idênticas dentro do conteúdo.
3. Layout 4 KPIs assimétrico (3 + 1 quebrado em duas linhas).
4. Investido R$ 0 (cálculo retornando zero indevido — mesmo padrão de Projeções).
5. Insights Derivados parcialmente implementado: aparece "PREVISÃO" cortado no canto inferior; mockup tem 4 cards (POSITIVO / ATENÇÃO / DESCOBERTA / PREVISÃO).

## Objetivo

1. Breadcrumb canônico: `OUROBOROS / ANÁLISE` (sem "VISÃO GERAL").
2. Eliminar uma das duas barras de tabs (manter as 3 superiores; remover sub-abas internas redundantes).
3. Layout 4 KPIs em linha única (grid `1fr 1fr 1fr 1fr`).
4. Investido: revisar `dados.py` cálculo do KPI quando categoria `Investimento` existe.
5. Renderizar 4 Insight Cards (POSITIVO/ATENÇÃO/DESCOBERTA/PREVISÃO) em sidebar direita usando `insight_card_html` já existe em `ui.py`.

## Validação ANTES (grep)

```bash
grep -n "breadcrumb\|st.tabs\|investido\|insight_card_html" src/dashboard/paginas/analise_avancada.py | head
grep -n "VISÃO GERAL" src/dashboard/paginas/analise_avancada.py
```

## Não-objetivos

- NÃO mudar gráfico Sankey.
- NÃO refazer cálculos de KPIs além de Investido.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k analise -q
```

Captura visual: Análise mostra breadcrumb correto, 1 só barra de tabs, 4 KPIs lado-a-lado, Investido com valor real, 4 Insights em sidebar.

## Critério de aceitação

1. Breadcrumb sem "VISÃO GERAL".
2. Apenas 1 barra de tabs principal.
3. 4 KPIs em linha única em viewport >=1280px.
4. Investido != R$ 0 quando dado de Investimento existe.
5. 4 Insight Cards renderizados.
6. Lint + smoke + baseline pytest.

## Referência

- Spec original: `sprint_ux_v_2_6_analise.md`.
- Mockup: `12-analise.html`.

*"Análise duplicada confunde, análise simétrica revela." — princípio V-2.6-FIX*
