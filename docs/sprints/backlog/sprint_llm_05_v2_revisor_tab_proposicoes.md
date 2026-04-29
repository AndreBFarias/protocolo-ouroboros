# Sprint LLM-05-V2 — Tab Proposições no Revisor 4-way

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_05_revisor_diff_proposicoes (arquivada).
**Prioridade**: P2
**Onda**: 2
**Esforço estimado**: 3h
**Depende de**: LLM-01-V2, LLM-03-V2

## Problema

Propostas em `docs/propostas/` e `mappings/proposicoes/` precisam de UI para humano aprovar/rejeitar de forma estruturada.

## Hipótese

Adicionar 3ª tab "Proposições" em `src/dashboard/paginas/revisor.py`, listando arquivos `.md` e `.yaml` em ambos diretórios. Cada item tem:
- Diff lado-a-lado.
- Botões: aprovar (move para destino final), rejeitar (move para `_rejeitadas/`).
- Campo livre de motivo na rejeição.

## Implementação proposta

Reusar componentes do Revisor (Sprint D2). Função pura em `revisor_logic.py` (já criado por ANTI-MIGUE-08). Testes em `test_revisor_proposicoes.py`.

## Acceptance criteria

- Tab funcional com >= 5 testes.
- Aprovar/rejeitar gera commit auto-descrito.

## Gate anti-migué

9 checks padrão.
