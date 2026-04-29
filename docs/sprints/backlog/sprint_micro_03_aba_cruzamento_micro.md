# Sprint MICRO-03 -- Aba Cruzamento Micro no dashboard (drill-down item-a-item)

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 4
**Esforço estimado**: 4h
**Depende de**: MICRO-01, MICRO-02
**Fecha itens da auditoria**: nenhum

## Problema

Sem visualização de fluxo transação → item.

## Hipótese

Aba dedicada: clique numa transação (Vivendas R$ 800) → tabela explode os itens (R$ 40 balinha, R$ 200 mercado, R$ 560 outros).

## Implementação proposta

src/dashboard/paginas/cruzamento_micro.py.

## Proof-of-work (runtime real)

Aba live exibe drill-down em runtime real.

## Acceptance criteria

- Aba.
- Drill-down funcional.
- Validação visual.

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
