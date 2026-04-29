# Sprint DOC-16 -- DANFE valida ingestão antes de retornar []

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P0
**Onda**: 3
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 21 da auditoria

## Problema

danfe_pdf.py:224 retorna [] sem checar se db.adicionar_edge funcionou.

## Hipótese

Trocar por try/except + log.error em falha + raise se modo strict.

## Implementação proposta

Edit cirúrgico em danfe_pdf.py.

## Proof-of-work (runtime real)

Forçar erro SQL em fixture → log.error registrado, não silêncio.

## Acceptance criteria

- Patch aplicado.
- Teste regressivo.
- Log estruturado em falhas.

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
