# Sprint DOC-19 -- Holerite cria edge contem-item mesmo sem código de produto

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P3
**Onda**: 3
**Esforço estimado**: 1h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 27 da auditoria

## Problema

ingestor_documento.py:563 pula entrada se faltar o campo de código do produto. Holerite tem verbas sem código → drill-down item-a-item impossível.

## Hipótese

Gerar código sintético `holerite_<slug_descricao>` quando ausente.

## Implementação proposta

Edit cirúrgico em ingestor_documento.py.

## Proof-of-work (runtime real)

Holerite real → 3+ edges contem_item criadas.

## Acceptance criteria

- Patch.
- Teste regressivo.

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
