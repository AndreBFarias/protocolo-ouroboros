---
id: INFRA-SPLIT-RECAP
titulo: Modularizar be_recap.py (825L) em be_recap.py + recap_comparativo.py
status: backlog
prioridade: baixa
data_criacao: 2026-05-08
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 2
---

# Sprint INFRA-SPLIT-RECAP — split do comparativo + destaques

## Contexto

`src/dashboard/paginas/be_recap.py = 825L` excede limite `(h)` 800L. Origem: 9 métricas comparativas + 5 destaques + narrativa MD adicionados em UX-V-2.17-FIX.

## Objetivo

Extrair para `src/dashboard/componentes/recap_comparativo.py`:
- `_COMPARATIVO_CONFIG` (9 métricas com formatadores).
- `_comparativo_html(janela_atual, janela_anterior)`.
- `_gerar_destaques(dados)` (5 heurísticas: streak humor, viagens, padrões, etc).

`be_recap.py` mantém: 4 KPIs + tabs Período + delegação.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/be_recap.py
grep -n "_COMPARATIVO_CONFIG\|_comparativo_html\|_gerar_destaques" src/dashboard/paginas/be_recap.py | head
```

## Não-objetivos

- NÃO chamar Anthropic API (ADR-13 vence).
- NÃO mexer no formato de `docs/recaps/<mes>.md`.

## Proof-of-work

```bash
wc -l src/dashboard/paginas/be_recap.py        # esperado <=800
make lint && make smoke
.venv/bin/pytest tests/ -k be_recap -q
```

## Critério de aceitação

1. `be_recap.py <= 800L`.
2. `recap_comparativo.py` exporta `comparativo_html` e `gerar_destaques`.
3. Lint + smoke + pytest baseline.

*"Modularizar é desentupir." — princípio INFRA-SPLIT-RECAP*
