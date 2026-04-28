# Sprint AUDIT2-FORNECEDOR-CAPITALIZACAO -- Normalizar caixa de razao_social em cupons

**Origem**: Auditoria self-driven 2026-04-29, achado A3.
**Prioridade**: P2.
**Estimado**: 30min.

## Problema

Extractor de cupom termico foto (`src/extractors/cupom_termico_foto.py`) e
de cupom garantia estendida (`cupom_garantia_estendida_pdf.py`) gravam
`razao_social = "americanas sa - 0337"` (lowercase, exatamente como vem do
OCR do cupom). Outros extratores usam UPPERCASE para razao_social.

Inconsistencia gera divergencia ETL ≠ Opus desnecessaria (ambos referem ao
mesmo fornecedor).

## Implementação sugerida

1. Adicionar `razao_social = razao_social.upper().strip()` antes de gravar
   metadata em ambos os extratores.
2. Backfill: UPDATE direto em nodes existentes (1 query SQL).
3. Teste cobrindo `"americanas sa"` -> `"AMERICANAS SA"`.

## Proof-of-work esperado

```sql
SELECT json_extract(metadata, '$.razao_social') FROM node
WHERE tipo='documento'
  AND json_extract(metadata, '$.razao_social') LIKE '%americanas%';
```

Todos retornam UPPERCASE.

## Acceptance

- 0 razao_social com mix case no grafo.
- Teste regressivo em test_cupom_termico_foto.py.
