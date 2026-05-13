---
id: LLM-07-V2-METRICAS-AUTOSSUFICIENCIA
titulo: Sprint LLM-07-V2 — Métricas de autossuficiência (ADR-09)
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint LLM-07-V2 — Métricas de autossuficiência (ADR-09)

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_07_metricas_autossuficiencia (arquivada).
**Prioridade**: P3
**Onda**: 2
**Esforço estimado**: 2h
**Depende de**: LLM-01-V2

## Problema

ADR-09 (Autossuficiência Progressiva) define métrica = % determinístico. Sem medição, não sabemos se o sistema está convergindo para 100%.

## Hipótese

Métrica derivada do grafo:
- "% determinístico" = nodes cuja categoria veio de regex YAML (`metadata.fonte: yaml`).
- "% via supervisor" = nodes cuja categoria veio de proposta aprovada (`metadata.fonte: supervisor`).
- Meta: `% determinístico → 100%` ao longo do tempo (cada proposta aprovada vira regra YAML, então o "via supervisor" decai).

## Implementação proposta

1. Coluna `metadata.fonte` populada em todo node novo (já existe em alguns extratores; padronizar).
2. Aba "Autossuficiência" no dashboard com gráfico de série temporal.
3. Smoke contract novo (smoke 11/11): "% determinístico mensal nunca decresce monotonicamente".

## Acceptance criteria

- Coluna padronizada.
- Aba funcional.
- 3+ testes.

## Gate anti-migué

9 checks padrão.
