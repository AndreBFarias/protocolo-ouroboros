---
concluida_em: 2026-04-28
---

# Sprint AUDIT2-METADATA-PESSOA-CANONICA -- Gravar pessoa canonica no node documento

**Origem**: Auditoria self-driven 2026-04-29, achado B3.
**Prioridade**: P2.
**Estimado**: 1.5h.

## CONCLUÍDA em 2026-04-29

**Implementação**:
- `src/graph/ingestor_documento.py`: novo helper `_inferir_pessoa_canonica`
  (heurística leve: contribuinte ANDRE/VITORIA → andre/vitoria; senão path
  partes; fallback `casal`). Aplicado nos 4 pontos de gravação de
  `metadata.arquivo_origem` (linhas 274, 522, 655, 864).
- `scripts/backfill_metadata_pessoa.py` (NOVO): backfill idempotente em
  nodes existentes (documento, apolice, prescricao, garantia). Modo
  --dry-run honesto (open SQLite read-only) + --executar.
- `scripts/popular_valor_grafo_real.py`: `_inferir_pessoa` agora prefere
  `metadata.pessoa` direto quando válida (fallback preservado para nodes
  sem o campo).
- `run.sh --reextrair-tudo`: encadeia `backfill_metadata_pessoa --executar`
  como passo final (Sprint 108).
- `tests/test_backfill_metadata_pessoa.py` (NOVO, 10 testes): cobre
  inferência por contribuinte, path, fallback, e backfill com idempotência
  e modo sobrescrever.

**Runtime real**:
- Antes: 19/45 documentos com pessoa populada (22%).
- Depois: 45/45 documentos (100%) — todos `andre` (todos os documentos
  atuais são do supervisor; casal/vitória ainda sem ingestão).
- 47 nodes atualizados no total (45 documento + 2 apolice).
- pytest: 1.997 → 2.007 passed (+10).

Verificação:
```sql
SELECT json_extract(metadata, '$.pessoa'), COUNT(*) FROM node
  WHERE tipo='documento' GROUP BY 1;
-- andre|45
```

---

## Spec original (preservada para histórico)

## Problema

Apenas 19/86 itens (22%) tem `pessoa` populada no Grafo. A inferencia
atual (`popular_valor_grafo_real::_inferir_pessoa`) depende de
`metadata.contribuinte` (so DAS PARCSN tem) ou inferencia de path
(falha quando arquivo esta em `_envelopes/`).

Sprint 90 introduziu `pessoa_detector` mas o resultado não chega ao node
documento. Pessoa fica como invariante implicito no path/banco_origem.

## Implementação sugerida

1. Em `ingestor_documento.py`, ao criar node documento, chamar
   `pessoa_detector.detectar(...)` e gravar `metadata.pessoa = "andre" |
   "vitoria" | "casal"`.
2. Backfill nodes existentes via SQL UPDATE (consultando contribuinte +
   path como fallback).
3. `_inferir_pessoa` em popular_valor_grafo_real lê direto de
   `metadata.pessoa` (sem fallback).

## Proof-of-work esperado

```sql
SELECT COUNT(*) FROM node WHERE tipo='documento'
  AND json_extract(metadata, '$.pessoa') IS NOT NULL;
```

Esperado: 45/45 (todos os documentos atuais).

## Acceptance

- 100% dos nodes documento tem `metadata.pessoa`.
- Coluna `valor_grafo_real` para dimensao pessoa no Revisor sobe de 19 -> 86.
