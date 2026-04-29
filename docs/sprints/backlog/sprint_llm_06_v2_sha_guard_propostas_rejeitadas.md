# Sprint LLM-06-V2 — SHA-guard de propostas rejeitadas

**Origem**: REVISAO-LLM-ONDA-01 (reescrita sob ADR-13).
**Substitui**: sprint_llm_06_proposicao_sha_guard (arquivada).
**Prioridade**: P3
**Onda**: 2
**Esforço estimado**: 1h
**Depende de**: LLM-05-V2

## Problema

Sem guard, sessão futura pode regenerar uma proposta cujo conteúdo já foi rejeitado (mesma hipótese, vinda de outro contexto). Resultado: humano revisa o mesmo lixo várias vezes.

## Hipótese

`scripts/check_propostas_rejeitadas.py`: para cada arquivo em `docs/propostas/_rejeitadas/`, calcula sha256 da hipótese normalizada (lower + trim + strip pontuação). Antes de criar proposta nova, supervisor consulta o registro. Match → aborta + mostra motivo da rejeição original.

## Implementação proposta

1. Tabela SQLite `propostas_rejeitadas(sha, motivo, ts, arquivo_original)`.
2. Script standalone `check_propostas_rejeitadas.py`.
3. Hook no fluxo de geração de proposta (skills de LLM-02-V2 e LLM-03-V2).

## Acceptance criteria

- Script funcional.
- Hook integrado.
- 3+ testes regressivos.

## Gate anti-migué

9 checks padrão.
