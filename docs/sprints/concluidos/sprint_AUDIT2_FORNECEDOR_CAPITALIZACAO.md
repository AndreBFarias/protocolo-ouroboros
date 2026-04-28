# Sprint AUDIT2-FORNECEDOR-CAPITALIZACAO -- Normalizar caixa de razao_social em cupons

**Origem**: Auditoria self-driven 2026-04-29, achado A3.
**Prioridade**: P2.
**Estimado**: 30min.

## RESOLVIDA INDIRETAMENTE em 2026-04-29 -- via Sprint AUDIT2-B4

**Status**: NÃO-APLICÁVEL no estado atual do grafo. Os nodes 7383, 7386,
7464, 7466 mencionados no achado A3 já não existem (deletados pela
reextração 2026-04-28). Padrão (y) "fantasma de cache histórico".

Verificação em runtime real (2026-04-29):
```sql
SELECT COUNT(*) FROM node WHERE tipo='documento'
  AND json_extract(metadata, '$.razao_social') GLOB '*[a-z]*americanas*';
-- Resultado: 0
```

**Ressalva preservada (causa raiz não tocada)**: os extractors
`src/extractors/cupom_termico_foto.py` e
`src/extractors/cupom_garantia_estendida_pdf.py` continuam sem
`.upper().strip()` antes de gravar `razao_social`. Se uma nova ingestão
de cupom Americanas em lowercase aparecer, o problema reaparece. Risco
baixo (4 ocorrências históricas em 86 itens). Pode reabrir esta sprint
ou tratar como follow-up se reincidir.

---

## Spec original (preservada para histórico)

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
