# Sprint DOC-15 -- parse_data_br() em src/utils/parse_br.py + remover regex local de 22 extratores

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 3
**Esforço estimado**: 4h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 26 da auditoria

## Problema

22 extratores fazem regex próprio para data DD/MM/YYYY. Inconsistente.

## Hipótese

parse_data_br(s: str, formatos: tuple = ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d')) -> date | None com fallback. Substituir em todos os 22.

## Implementação proposta

Adicionar função + grep+sed substitui em cada extrator.

## Proof-of-work (runtime real)

grep para regex de data deve voltar 0 fora de parse_br.py.

## Acceptance criteria

- Função coberta.
- Migração completa.
- Pytest baseline mantido.

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
