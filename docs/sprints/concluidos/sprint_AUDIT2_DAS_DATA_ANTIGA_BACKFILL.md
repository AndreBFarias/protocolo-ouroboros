---
concluida_em: 2026-04-28
---

# Sprint AUDIT2-DAS-DATA-ANTIGA-BACKFILL -- Recompor data_emissao em DAS pre-90b

**Origem**: Auditoria self-driven 2026-04-29, achado A2.
**Prioridade**: P2.
**Estimado**: 2h.

## RESOLVIDA INDIRETAMENTE em 2026-04-29 -- via Sprint AUDIT2-B4

**Status**: NÃO-APLICÁVEL. O achado A2 (node_7432 com data divergente) era
artefato de marcações em `revisao_humana.sqlite` apontando para nodes ja
deletados pela reextração 2026-04-28 (mesmo padrão (y) da A1).

Verificação em runtime real (2026-04-29):
- `node_7432` não existe no grafo atual (todos os 19 DAS PARCSN atuais
  estão entre ids 7490+, já com extractor pós-Sprint 90b aplicado).
- DAS com `periodo_apuracao = 'diversos'` usam `data_emissao = vencimento`
  como melhor proxy quando o PDF não traz data de emissão explícita —
  comportamento correto da Sprint 90b.

Após Sprint AUDIT2-B4 ter limpado as marcações órfãs, restam 0 marcações
no Revisor com data divergente para nodes existentes. Não requer fix de
código nem backfill adicional.

---

## Spec original (preservada para histórico)

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
