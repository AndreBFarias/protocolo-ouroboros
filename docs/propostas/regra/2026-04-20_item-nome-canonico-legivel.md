---
id: 2026-04-20_item-nome-canonico-legivel
tipo: regra
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 44b
---

# Proposta: view SQL com descrição legível para nós `item`

## Contexto

Após a Sprint 44b, os 33 nós `item` no grafo têm `nome_canonico` composto
`<cnpj_varejo>|<data>|<codigo>` -- ótimo para chavear, ruim para leitura:

```sql
SELECT nome_canonico FROM node WHERE tipo='item' LIMIT 3;
-- 00.776.574/0160-79|2026-04-19|000004300823
-- 00.776.574/0160-79|2026-04-19|000004298119
-- 00.776.574/0160-79|2026-04-19|000004328964
```

Descrição real (ex.: `CONTROLE P55 DUALSENSE`) está em `metadata.descricao`
e `aliases[0]`, mas listagens default não a expõem.

## Diff proposto

NÃO alterar `nome_canonico` (quebraria idempotência). Criar view SQL
legível + helper Python:

```diff
# src/graph/schema.sql
+
+CREATE VIEW IF NOT EXISTS v_item_legivel AS
+  SELECT id,
+         json_extract(metadata, '$.descricao')      AS descricao,
+         json_extract(metadata, '$.cnpj_varejo')    AS cnpj_varejo,
+         json_extract(metadata, '$.data_compra')    AS data_compra,
+         json_extract(metadata, '$.codigo_produto') AS codigo,
+         json_extract(metadata, '$.valor_total')    AS valor
+  FROM node WHERE tipo='item';
```

E helper em `src/graph/queries.py` com função `listar_itens_legivel(db, limite)`.

## Justificativa

- **Impacto:** queries de inspeção/dashboard ficam 10x mais legíveis.
- **Risco:** zero. View é read-only, não altera schema dos nós nem
  ingestão.
- **Alternativa descartada:** mudar `nome_canonico` para incluir
  descrição. Rejeitada: descrição tem variação de espaços/acentos que
  quebra unicidade e idempotência retroativa.

## Teste de regressão

```bash
.venv/bin/pytest tests/test_graph.py -k "listar_itens_legivel" -v
sqlite3 data/output/grafo.sqlite "SELECT * FROM v_item_legivel LIMIT 3;"
# esperado: linhas com descrição legível
```

## Decisão humana

**Aprovada em:** (preencher ao aprovar)
**Rejeitada em:** (preencher ao rejeitar)
**Motivo:** (preencher se rejeitada)

---

*"A chave técnica une; o alias humano revela." -- princípio de camada de apresentação*
