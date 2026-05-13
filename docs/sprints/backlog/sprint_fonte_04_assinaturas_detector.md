---
id: FONTE-04-ASSINATURAS-DETECTOR
titulo: Sprint FONTE-04 -- src/analysis/assinaturas.py — recorrências em cartão
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-28'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint FONTE-04 -- src/analysis/assinaturas.py — recorrências em cartão

**Origem**: plan pure-swinging-mitten (auditoria honesta 2026-04-29).
**Prioridade**: P1
**Onda**: 5
**Esforço estimado**: 3h
**Depende de**: nenhuma
**Fecha itens da auditoria**: nenhum

## Problema

Serviços por assinatura (Spotify, Netflix, iCloud) só aparecem como transação avulsa. Sem visão consolidada.

## Hipótese

Detector: para cada (fornecedor, valor±5%) com ≥3 ocorrências em datas próximas (±3d/mês), marca como assinatura.

## Implementação proposta

Módulo + aba 'Assinaturas' no dashboard.

## Proof-of-work (runtime real)

Corpus real → detecta ≥10 assinaturas conhecidas (Spotify, Amazon, etc.).

## Acceptance criteria

- Detector.
- Aba.
- Tabela com previsão de gasto mensal.

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
