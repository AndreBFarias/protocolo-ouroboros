---
id: UX-V-2.17-FIX
titulo: Recap — comparativo 30D estruturado + 5 destaques + bloco narrativa manual
status: backlog
prioridade: media
data_criacao: 2026-05-08
fase: PARIDADE_VISUAL
depende_de: []
esforco_estimado_horas: 3
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-08.md (página 21)
mockup: novo-mockup/mockups/21-recap.html
---

# Sprint UX-V-2.17-FIX — Recap com comparativo + destaques + narrativa manual

## Contexto

UX-V-2.17 entregou KPIs (Humor médio, Eventos, Treinos, Peso variação) e gráfico comparativo de humor (barras simples), respeitando ADR-13 (sem LLM API). Mockup `21-recap.html` mostra:

- Comparativo · vs 30D anteriores: tabela com humor médio +0.42, ansiedade -1.10, foco +0.28, crises -3, aderência medicação 93% +12pp, tarefas concluídas 82% +6pp, noites <6h sono 5 -4, treinos 14 +2, rolezinhos casal 3 (= mesmo).
- Destaques do mês: 5 cards coloridos (47 dias sem fumar, Viagem Trancoso, Padrão descoberto, Streak 12 dias).
- Narrativa: dashboard NÃO faz LLM API; auditoria 2026-05-07 propôs adicionar bloco "narrativa do mês (gerada manualmente via /gerar-recap)".

## Objetivo

1. Substituir gráfico de barras "Comparativo de humor" por tabela estruturada `vs 30D anteriores` com 9 métricas e deltas coloridos.
2. Adicionar seção "DESTAQUES DO MÊS" com 5 cards canônicos (gerados deterministicamente a partir do cache: streaks, marcos, padrões temporais).
3. Adicionar bloco "NARRATIVA DO MÊS" que lê `docs/recaps/<mes>.md` se existe, senão mostra CTA "rode `/gerar-recap` para criar narrativa via Opus interativo".

## Validação ANTES (grep)

```bash
wc -l src/dashboard/paginas/be_recap.py
grep -n "comparativo\|destaques\|narrativa\|recaps" src/dashboard/paginas/be_recap.py | head
ls docs/recaps/ 2>&1 | head
```

## Não-objetivos

- NÃO chamar Anthropic API automaticamente.
- NÃO mexer nos 4 KPIs do topo.

## Proof-of-work

```bash
make lint && make smoke
.venv/bin/pytest tests/ -k be_recap -q
```

Captura visual: 4 KPIs + tabela comparativo + 5 destaques + bloco narrativa (CTA ou texto).

## Critério de aceitação

1. Tabela comparativo vs 30D com >=9 métricas.
2. 5 cards destaques renderizados deterministicamente.
3. Bloco narrativa funcional (CTA ou markdown).
4. Lint + smoke + baseline pytest.

## Referência

- Mockup: `21-recap.html`.
- ADR-13 (supervisor artesanal).

*"Recap sem comparativo é só foto do mês." — princípio V-2.17-FIX*
