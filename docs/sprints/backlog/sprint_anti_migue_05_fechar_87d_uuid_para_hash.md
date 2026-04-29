# Sprint ANTI-MIGUE-05 -- Fechar Sprint 87d: UUID → hash determinístico em fallback supervisor cupom

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 1
**Esforço estimado**: 2h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 35 da auditoria honesta

## Problema

Sprint 87d ficou com UUID aleatório no fallback supervisor de cupom (docs/propostas/extracao_cupom/), gerando 6 propostas órfãs por rodada.

## Hipótese

Trocar `uuid4()` por `sha256(arquivo+tipo+data)[:16]` no nome do arquivo de proposta. Idempotência garantida: mesma entrada = mesmo arquivo, em vez de duplicata por execução.

## Implementação proposta

1. Localizar gerador em src/intake/extractors_envelope.py ou módulo correlato.
2. Substituir uuid por hash determinístico.
3. Limpar 6 propostas órfãs antes do merge.
4. Teste regressivo: 2 execuções consecutivas → 1 arquivo, não 2.

## Proof-of-work (runtime real)

ls docs/propostas/extracao_cupom/ | wc -l antes/depois.

## Acceptance criteria

- 0 duplicatas após 2 execuções consecutivas com mesmo input.
- Teste regressivo cobrindo idempotência.
- 6 órfãos pré-existentes removidos.

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
