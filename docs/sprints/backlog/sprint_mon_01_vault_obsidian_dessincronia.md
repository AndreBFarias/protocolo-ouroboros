# Sprint MON-01 -- Monitor de dessincronia do Vault Obsidian

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 6
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 32 da auditoria

## Problema

sync_rico depende de tag `#sincronizado-automaticamente`. Sem monitor, nota editada manualmente sem tag pode ser sobrescrita.

## Hipótese

Cron diário compara hash de cada nota com último hash conhecido. Divergência sem tag → alerta.

## Implementação proposta

src/obsidian/monitor_dessincronia.py + relatório.

## Proof-of-work (runtime real)

Editar nota sem tag → próximo cron alerta.

## Acceptance criteria

- Cron + relatório.
- Teste.

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
