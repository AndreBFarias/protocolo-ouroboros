---
concluida_em: 2026-04-28
---

# Sprint LLM-02-V2 — Proposição de extrator via Edit em docs/propostas/

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_02_supervisor_propor_extractor (arquivada).
**Prioridade**: P1
**Onda**: 2
**Esforço estimado**: 1.5h
**Depende de**: LLM-01-V2 (template), ANTI-MIGUE-01 (gate 4-way)

## Problema

Quando classifier retorna `tipo=None` para um arquivo novo, o sistema precisa de um caminho para o supervisor (Opus principal interativo) propor um extrator dedicado.

## Hipótese

`make conformance-<tipo>` exit 1 + `tipo` ausente do classifier → o Opus principal abre `docs/propostas/extracao_<tipo>_<data>.md` via Edit tool com hipótese de regex/layout + sub-spec sugerida em `backlog/sprint_doc_<X>_*.md`.

## Implementação proposta

1. Documentar workflow em CLAUDE.md §workflow obrigatório.
2. Skill `/propor-extrator <tipo> <amostra>` que pré-popula o template.
3. Sub-spec gerada inclui referência cruzada à proposta.

## Acceptance criteria

- Workflow documentado.
- Skill funcional.
- Pelo menos 1 proposta de extrator gerada como exemplo (ex: para `pix_foto_comprovante`).

## Gate anti-migué

9 checks padrão.
