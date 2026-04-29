# Sprint LLM-04 -- Supervisor Modo 2 (Auditor) — audita N% das classificações

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 2
**Esforço estimado**: 6h
**Depende de**: LLM-01
**Fecha itens da auditoria**: nenhum

## Problema

Pipeline determinístico (regex + YAML) classifica 100%, mas pode ter erros sistemáticos não detectáveis sem amostragem externa.

## Hipótese

Auditor lê amostra estratificada (10% por categoria, mín 5 por mês) e produz relatório de divergências. Gera PR de correção quando encontra padrão sistemático.

## Implementação proposta

1. supervisor.auditor(amostra, regras_atuais) → AuditoriaClassificacao.
2. CLI `python -m src.llm.auditor --mes 2026-04`.
3. Relatório data/output/auditoria_classificacao_<mes>.md.

## Proof-of-work (runtime real)

Rodar auditor em mês com erro conhecido (ex: bug Sprint 55 reproduzido) → reporta divergência.

## Acceptance criteria

- CLI funcional.
- Relatório gerado.
- Schema versionado.

## Gate anti-migué

Para mover esta spec para `docs/sprints/concluidos/`:

1. Hipótese declarada validada com `grep` antes de codar.
2. Proof-of-work runtime real capturado em log.
3. `make conformance-<tipo>` exit 0 quando aplicável (>=3 amostras 4-way).
4. `make lint` exit 0.
5. `make smoke` 10/10 contratos.
6. `pytest` baseline mantida ou crescida.
7. Achados colaterais viraram sprint-ID OU Edit-pronto. Zero TODO solto.
8. Validador (humano ou subagent) APROVOU.
9. Frontmatter `concluida_em: YYYY-MM-DD` adicionado.
