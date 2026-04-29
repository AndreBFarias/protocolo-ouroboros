# Sprint DOC-14 -- Anti-duplicação semântica em data/raw/<pessoa>/<banco>/

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P2
**Onda**: 3
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: item 25 da auditoria

## Problema

dedup_classificar varre só _classificar/. Arquivo duplicado em data/raw/andre/itau_cc/ não é detectado.

## Hipótese

Estender varredura para data/raw/<pessoa>/<banco>/ com chave (tipo, pessoa, data_emissao, valor_total). Variantes de mesmo extrato são detectadas via similaridade.

## Implementação proposta

Generalizar dedup_classificar.py para receber raiz arbitrária.

## Proof-of-work (runtime real)

Subir 2 PDFs do mesmo extrato com nomes diferentes em raw/andre/itau_cc/ → dedup detecta.

## Acceptance criteria

- Função generalizada.
- 5+ testes.

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
