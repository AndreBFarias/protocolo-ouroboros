# Sprint AUDIT2-METADATA-PESSOA-CANONICA -- Gravar pessoa canonica no node documento

**Origem**: Auditoria self-driven 2026-04-29, achado B3.
**Prioridade**: P2.
**Estimado**: 1.5h.

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
