---
id: 2026-04-20_apolice-item-heuristica-threshold
tipo: linking
data: 2026-04-20
status: aberta
autor_proposta: claude-code-opus
sprint_contexto: 44b
---

# Proposta de linking: formalizar heurística que casou 2 apólices MAPFRE a 2 itens

## Contexto

Execução end-to-end da Sprint 44b (`./run.sh --tudo` em 2026-04-20) criou
automaticamente 2 arestas `assegura` via `src/graph/ingestor_documento.py:localizar_item`:

- `apolice/781000129322123` → `item/00.776.574/0160-79|2026-04-19|000004300823` (CONTROLE P55)
- `apolice/781000129322124` → `item/00.776.574/0160-79|2026-04-19|000004298119` (BASE P55)

Critérios conjugados:
1. `cnpj_varejo` exato (Americanas)
2. `data_compra` dentro de ±1 dia da `vigencia_inicio`
3. `rapidfuzz.token_set_ratio(descricao)` ≥ 82 (threshold)

Scores reais observados: 100 em ambos (casos fáceis).

## Entidades envolvidas

Arestas JÁ existem. Esta proposta NÃO propõe ligar nada -- propõe:

1. Validar threshold atual contra amostra real (2 pares, score 100).
2. Adicionar teste de regressão bloqueando degradação futura.
3. Comentário em `src/graph/ingestor_documento.py` com case-study real.

## Evidência a favor

- 2 matches perfeitos (score 100) sem intervenção humana.
- Zero falsos positivos.
- Spec 47c aceitava aresta `assegura` opcional -- heurística acertou.

## Evidência contra (cuidados)

- Amostra pequena (2 pares). Threshold 82 pode ser frouxo para variações
  maiores (ex.: apólice "APARELHO SMART TV 55" vs NFC-e "TV LG OLED 55 EVO").
- Janela ±1 dia pode falhar se apólice for emitida horas depois mas corta
  para o dia seguinte.
- `MARGEM_DESEMPATE=5` não foi exercitado (sem ambiguidade).

## Diff proposto

```diff
# src/graph/ingestor_documento.py
 JANELA_MATCH_ITEM_DIAS: int = 1
 THRESHOLD_DESCRICAO: int = 82
 MARGEM_DESEMPATE: int = 5
+
+# Histórico de matches bem-sucedidos (Sprint 44b, 2026-04-20):
+#   descricao_apolice     | descricao_item                         | score
+#   BASE CARREGAMENTO P55 | BASE DE CARREGAMENTO DO CONTROLE P55   | 100
+#   CONTROLE P55          | CONTROLE P55 DUALSENSE GALACTIC PURPLE | 100
+# Ao ajustar threshold, rodar tests/test_graph.py::TestLocalizarItem
+# e conferir que estes 2 casos continuam passando.
```

Teste novo em `tests/test_graph.py`:

```python
def test_localizar_item_casa_apolice_mapfre_p55(grafo_temp):
    """Regressão: case-study real da Sprint 44b."""
    grafo_temp.upsert_node("item", "00.776.574/0160-79|2026-04-19|000004300823",
        metadata={
            "descricao": "CONTROLE P55 DUALSENSE GALACTIC PURPLE",
            "cnpj_varejo": "00.776.574/0160-79",
            "data_compra": "2026-04-19",
        })
    from src.graph.ingestor_documento import localizar_item
    assert localizar_item(grafo_temp,
        descricao="CONTROLE P55",
        cnpj_varejo="00.776.574/0160-79",
        data_iso="2026-04-19") is not None
```

## Teste de regressão

```bash
.venv/bin/pytest tests/test_graph.py -k "localizar_item" -v
```

## Decisão humana

**Aprovada em:** (preencher)
**Ação ao aprovar:** adicionar comentário + teste em `src/` e `tests/`

**Rejeitada em:** (preencher)
**Motivo:** (se rejeitada)

---

*"A heurística que acerta de primeira merece ser imortalizada em teste." -- princípio do regression lock*
