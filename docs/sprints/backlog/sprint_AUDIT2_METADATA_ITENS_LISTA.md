# Sprint AUDIT2-METADATA-ITENS-LISTA -- Persistir itens granulares em metadata

**Origem**: Auditoria self-driven 2026-04-29, achado B2.
**Prioridade**: P3 (impacta dimensao itens da auditoria 4-way).
**Estimado**: 4h (varios extratores).

## Problema

Nenhum extrator atual grava `metadata.itens` como lista granular. Mesmo
NFC-e (que tem produtos individuais com código+descrição+valor) e holerites
(que tem proventos+descontos discriminados) gravam apenas o `total`
agregado.

Resultado: dimensao "itens" no Revisor 4-way e sempre vazia no Grafo,
impossibilitando comparacao com Opus que infere "2 itens (Controle PS5
+ Base)" do PDF.

## Implementação sugerida

1. Definir schema canonico para `metadata.itens`:
   ```python
   [{"descrição": str, "valor": float, "quantidade": int = 1}]
   ```
2. Adaptar `nfce_pdf.py`, `xml_nfe.py`, `contracheque_pdf.py` para
   popular o array.
3. Backfill rodando extractors em modo `--reextrair` para nodes existentes.
4. Atualizar `extrair_valor_etl_para_dimensao` em revisor.py para usar
   o novo array consistentemente.

## Proof-of-work esperado

```sql
SELECT COUNT(*) FROM node WHERE tipo='documento'
  AND json_array_length(json_extract(metadata, '$.itens')) > 0;
```

Esperado: NFC-e + holerites com itens.

## Acceptance

- Pelo menos 50% dos itens elegiveis (NFC-e + holerites) tem `metadata.itens`
  populada.
- Coluna `valor_grafo_real` da dimensao `itens` no Revisor passa de 0 para
  o número de docs cobertos.
