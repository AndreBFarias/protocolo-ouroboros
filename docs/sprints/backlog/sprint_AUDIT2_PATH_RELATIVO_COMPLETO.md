# Sprint AUDIT2-PATH-RELATIVO-COMPLETO -- Aplicar to_relativo em todos ingestores

**Origem**: Auditoria self-driven 2026-04-29, achado B1.
**Prioridade**: P1.
**Estimado**: 1h.

## Problema

Sprint AUDIT-PATH-RELATIVO ligou `src/graph/path_canonico.py::to_relativo()`
em `src/graph/ingestor_documento.py` para holerites. Mas DAS PARCSN, boletos
e envelopes seguem outros caminhos de ingestao e gravam path absoluto.

Estado atual no grafo (45 documentos):
- ~24 holerites: path relativo `data/raw/andre/holerites/...`
- ~21 DAS+boletos+envelopes: path absoluto `/home/andrefarias/.../data/raw/...`

Impacto: querys via `idx_node_arquivo_origem` (Sprint AUDIT-INDEX-JSON)
não casam por match exato; consumidores precisam fallback LIKE.
`scripts/popular_valor_grafo_real.py` ja aplica esse fallback, mas e um
band-aid.

## Implementação sugerida

1. Identificar todos os pontos onde `metadata.arquivo_origem` e gravado
   (grep por `arquivo_origem` em `src/`).
2. Garantir que TODOS chamem `to_relativo()` antes de gravar.
3. Criar teste regressivo: assert `arquivo_origem` nunca comeca com `/`.
4. Backfill: rodar `scripts/backfill_arquivo_origem.py --tudo` (ou criar
   variante).

## Proof-of-work esperado

```sql
SELECT COUNT(*) FROM node
WHERE tipo='documento'
  AND json_extract(metadata, '$.arquivo_origem') LIKE '/%';
```

Esperado: 0.

## Acceptance

- 0 nodes com path absoluto em `arquivo_origem`.
- `popular_valor_grafo_real.py` pode remover o fallback LIKE (cleanup).
- Teste invariante adicionado.
