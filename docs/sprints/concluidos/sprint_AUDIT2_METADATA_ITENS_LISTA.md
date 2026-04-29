---
concluida_em: 2026-04-28
---

# Sprint AUDIT2-METADATA-ITENS-LISTA -- Persistir itens granulares em metadata

**Origem**: Auditoria self-driven 2026-04-29, achado B2.
**Prioridade**: P3 (impacta dimensao itens da auditoria 4-way).
**Estimado**: 4h (varios extratores).

## CONCLUÍDA em 2026-04-29

**Implementação**:
- `src/graph/ingestor_documento.py::ingerir_documento_fiscal`: agora popula
  `metadata.itens` automaticamente. Caller pode pré-preencher
  `documento["itens"]` (caminho holerite, sem `upsert_item` por não ter
  código de produto) ou deixar que o ingestor monte a lista a partir do
  argumento `itens` (caminho NFC-e/DANFE que também cria nodes `item`).
- `src/extractors/contracheque_pdf.py`:
  - `_parse_g4f`: agora preenche `itens: [{descricao, valor, tipo}]` com
    proventos+descontos individuais extraídos pelos regex.
  - `_parse_infobase`: preenche `itens` com pseudo-itens agregados
    (SALARIO BRUTO / ADIANTAMENTO 13 / INSS / IRRF) quando os valores são
    > 0. OCR INFOBASE não dá lista granular completa de proventos.
  - `_ingerir_holerite_no_grafo`: passa `documento["itens"]` para o
    ingestor (com `valor_total` ao invés de `valor`, alinhando com schema
    de NFC-e).
- `tests/test_metadata_itens_lista.py` (NOVO, 4 testes): cobre ingestão
  via argumento, ingestão via documento pre-preenchido, parse_g4f e
  parse_infobase.

**Runtime real (após `python -m scripts.reprocessar_documentos --forcar-reextracao`)**:
- 24 holerites com `metadata.itens` populada (era 0).
- 2 NFC-e (recém-ingeridos pela reextração) com `metadata.itens`
  granular (era 0).
- DAS PARCSN (19) e boletos (2) seguem sem itens (esperado — não há
  itens granulares nesses documentos).
- pytest: 2.014 → 2.018 passed (+4).

Verificação:
```sql
SELECT json_extract(metadata, '$.tipo_documento') AS tipo,
  SUM(CASE WHEN json_array_length(json_extract(metadata, '$.itens')) > 0 THEN 1 ELSE 0 END) AS com_itens,
  COUNT(*) FROM node WHERE tipo='documento' GROUP BY 1;
-- holerite|24|24
-- nfce_modelo_65|2|2
-- das_parcsn_andre|0|19
-- boleto_servico|0|2
```

---

## Spec original (preservada para histórico)

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
