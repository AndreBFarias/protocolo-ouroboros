---
id: <yyyy-mm-dd>_<slug>
tipo: linking
data: <yyyy-mm-dd>
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: none
---

# Proposta de linking: <documento> ↔ <transação|item|apolice>

## Contexto

O ingestor (`src/graph/ingestor_documento.py`) tentou linkar automaticamente
mas a heurística foi ambígua (`localizar_item` devolveu múltiplos candidatos
com score similar; `rapidfuzz` retornou < threshold; ou nenhum candidato
existia no grafo no momento da ingestão).

## Entidades envolvidas

- **Origem:** `<tipo>/<nome_canonico>` (ex.: `apolice/781000129322123`)
- **Destino candidato 1:** `<tipo>/<nome_canonico>` (score rapidfuzz, evidência)
- **Destino candidato 2 (se ambíguo):** idem
- **Tipo de aresta proposta:** `assegura | linked_to | ...`

## Evidência a favor

- Descrição textual: `<string>` bate com `<string>` (similaridade X%)
- CNPJ do varejo: bate exatamente? sim/não
- Janela temporal: compra em `YYYY-MM-DD`, apólice em `YYYY-MM-DD`, delta = N dias
- Valor: compra R$ X, apólice cobre item R$ Y (razão prêmio/limite = Z%)

## Evidência contra (se houver)

- Motivo da ambiguidade ou da heurística ter falhado
- O que seria necessário para resolução automática no futuro

## Diff proposto

```sql
-- Aplicado pelo supervisor via helper, não manualmente:
INSERT INTO edge (src_id, dst_id, tipo, evidencia)
VALUES (
  (SELECT id FROM node WHERE tipo='apolice' AND nome_canonico='781000129322123'),
  (SELECT id FROM node WHERE tipo='item' AND nome_canonico='00.776.574/0160-79|2026-04-19|000004300823'),
  'assegura',
  json('{"match": "descricao+cnpj+janela+aprovacao_humana"}')
);
```

## Decisão humana

**Aprovada em:** (preencher)
**Ação ao aprovar:** executar SQL acima + atualizar heurística se possível
(adicionar caso de regressão em `tests/test_graph.py`)

**Rejeitada em:** (preencher)
**Motivo:** (candidatos errados, documento desatualizado, etc.)

---

*"Quando o dado não se encontra, é o humano que aproxima." -- princípio do elo perdido*
