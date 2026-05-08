---
id: UX-V-2.7-FIX
titulo: Visão Geral — corrigir KPI Metas, Atividade Recente, acentuação, modularizar 996L
status: concluída
concluida_em: 2026-05-08
commit: 28f88fc
prioridade: alta
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md A2 + M3
mockup: novo-mockup/mockups/01-visao-geral.html
---

# Sprint UX-V-2.7-FIX — Visão Geral com 5 defeitos endereçados

## Contexto

UX-V-2.7 declarou paridade mas inspeção 2026-05-08 revelou:
1. `src/dashboard/paginas/visao_geral.py = 996 linhas` — viola limite `(h)` 800L.
2. Card "Metas" mostra `1.1k fornecedores · 82 períodos` (semântica errada — vem de Análise).
3. Atividade Recente: 2 linhas vs 6 do mockup, sem ícones tipados, timestamps idênticos `07/05 10:03`.
4. Texto sem acento: `Sprint UX V 2 6 ANALISE concluída` deveria ser `ANÁLISE`.
5. Sprint atual mostra `V-2.2.B - Modularizar pagamentos.py` (sub-sprint backlog) como "EM EXECUÇÃO" — semântica errada.

## Objetivo

1. **Modularizar** `visao_geral.py` quebrando em:
   - `src/dashboard/componentes/atividade_recente.py` (nova).
   - `src/dashboard/componentes/cards_clusters.py` (nova).
   - `visao_geral.py` mantém só orquestração + KPIs row + hero.
2. Corrigir KPI Metas: lê do contador real (`6 financeiras · 4 operacionais` quando dado existe) — não cair em fornecedores.
3. Atividade Recente: ler de fonte canônica de eventos (sprints concluídas + commits + ADRs novos), exibir 6 linhas com ícones diferenciados por tipo (sprint / divergência / catálogo / regressão / ADR).
4. Acentuação canônica em todos textos PT-BR ("ANÁLISE", "EVENTOS", "PRIVACIDADE").
5. Sprint atual: filtrar por `status: em_execucao` real, não pegar primeiro item do backlog.

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/visao_geral.py
grep -nE "ANALISE|ANALISE|EVENTOS|atividade_recente|sprint_atual|fornecedores" src/dashboard/paginas/visao_geral.py | head -20
```

## Não-objetivos

- NÃO mudar layout dos 6 cards de cluster.
- NÃO mexer no hero "OUROBOROS PROTOCOLO".

## Proof-of-work

```bash
wc -l src/dashboard/paginas/visao_geral.py  # esperado <=800
test -f src/dashboard/componentes/atividade_recente.py
test -f src/dashboard/componentes/cards_clusters.py
make lint && make smoke
.venv/bin/pytest tests/ -k "visao_geral" -q
```

Validação visual: card Metas mostra contadores corretos; Atividade Recente com 6 linhas e ícones; texto "ANÁLISE concluída" correto.

## Critério de aceitação

1. `visao_geral.py <= 800 linhas`.
2. 2 componentes novos exportam funções públicas.
3. Card Metas com contadores corretos (6 financeiras / 4 operacionais).
4. Atividade Recente com >=4 linhas distintas (timestamps reais), ícones tipados.
5. Acentuação OK no painel renderizado.
6. Lint + smoke 10/10 + baseline pytest.

## Referência

- Spec original: `sprint_ux_v_2_7_visao_geral.md`.
- Mockup: `01-visao-geral.html`.
- VALIDATOR_BRIEF: `(b)/(h)`.

*"O painel diz quem somos hoje. Se mente, mente sobre nós." — princípio V-2.7-FIX*
