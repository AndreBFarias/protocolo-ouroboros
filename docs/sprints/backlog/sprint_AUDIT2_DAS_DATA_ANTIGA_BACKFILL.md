# Sprint AUDIT2-DAS-DATA-ANTIGA-BACKFILL -- Recompor data_emissao em DAS pre-90b

**Origem**: Auditoria self-driven 2026-04-29, achado A2.
**Prioridade**: P2.
**Estimado**: 2h.

## Problema

Sprint 90b corrigiu o regex de periodo "Diversos" no extractor DAS PARCSN
(`src/extractors/das_parcsn_pdf.py`). Mas nodes ingeridos antes da Sprint 90b
gravaram `data_emissao` 1 mes a frente quando o PDF tinha periodo "Diversos".

Evidencia: node_7432 — Opus le no PDF "Setembro/2025 30/09/2025" e decide
data=2025-09-30. ETL gravou data=2025-09-30 mas em outros casos parecidos
(ex: node_7383 etc) gravou a data de **vencimento** em vez de emissao.

Comparativo claro no Revisor: 14 nodes antigos divergem do Opus em ~5
deles (todos com periodo Diversos no PDF original).

## Implementação sugerida

1. Identificar quais nodes antigos tem data divergente: query no grafo
   filtrando por tipo_documento + range de id < 7490.
2. Re-extrair data_emissao desses PDFs com o extractor atual (90b).
3. Atualizar metadata via UPDATE direto (ou rerodar reextracao para esses
   especificos).
4. Teste regressivo: garantir que extractor atual produz data correta para
   1+ exemplo "Diversos".

## Proof-of-work esperado

Ao rodar `popular_valor_grafo_real --sobrescrever`, dimensao=data dos nodes
antigos passa de "data divergente" para "data igual ao Opus".

## Acceptance

- 0 nodes DAS PARCSN com data_emissao divergindo do `Periodo de Apuracao`
  literal do PDF.
- Teste novo em test_das_parcsn_pdf.py cobrindo periodo "Diversos".
