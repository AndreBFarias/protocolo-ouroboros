# Sprint UX-07 -- Snapshot histórico com timestamp dinâmico em Inventário/Prazos/Dívidas Ativas

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 6
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 17 da auditoria

## Problema

Aviso 'snapshot 2023' hardcoded sem data dinâmica.

## Hipótese

Ler mtime do XLSX + exibir em rodapé.

## Implementação proposta

Edit em paginas/contas.py + estender para Inventário/Prazos/Dívidas Ativas.

## Proof-of-work (runtime real)

UI mostra 'Snapshot atualizado em <data>'.

## Acceptance criteria

- Timestamp em 4 abas.

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
