---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 50b
  title: "item_categorizer remove arestas categoria_de antigas ao mutar regra YAML"
  touches:
    - path: src/transform/item_categorizer.py
      reason: "antes de adicionar nova aresta categoria_de, remover arestas categoria_de preexistentes do mesmo item"
    - path: src/graph/db.py
      reason: "expor deletar_edges(src_id, tipo) ou equivalente se ainda não existir"
    - path: tests/test_item_categorizer.py
      reason: "teste de mutação: categorizar → editar YAML → categorizar de novo → exatamente 1 aresta categoria_de"
  n_to_n_pairs:
    - ["categorizar_todos_items_no_grafo (fluxo normal)", "mutação de regra YAML entre rodadas"]
  forbidden:
    - "Alterar contrato de adicionar_edge (INSERT OR IGNORE continua)"
    - "Deletar arestas de outros tipos (fornecido_por, contem_item, ocorre_em)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Após mutação de regra em categorias_item.yaml que mudaria a categoria de um item existente, categorizar_todos_items_no_grafo DELETA a aresta categoria_de antiga antes de criar a nova"
    - "Teste test_mutar_regra_yaml_nao_acumula_arestas_categoria_de: cria item, categoriza com regra A, muda regra para B, re-categoriza → exatamente 1 aresta categoria_de apontando para categoria B"
    - "Zero regressão: test_idempotente_nao_duplica_aresta continua passando (INSERT OR IGNORE preservado para re-execução com regra idêntica)"
    - "Baseline de testes cresce ou mantém"
```

---

# Sprint 50b — item_categorizer: remover arestas antigas ao mutar YAML

**Status:** BACKLOG
**Prioridade:** P3 (minúcia M50-1 registrada no BRIEF; não bloqueia, afeta apenas cenário "editar regra e re-categorizar")
**Dependências:** Sprint 50 (entregue); Sprint 57 (reprocessamento de volume — garante que há arestas categoria_de no grafo real)
**Origem:** achado MINÚCIA M50-1 do validador da Sprint 50 (VALIDATOR_BRIEF.md §121)

## Problema

`src/transform/item_categorizer.py::categorizar_todos_items_no_grafo` usa `db.adicionar_edge(item_id, categoria_id, "categoria_de")` que por trás tem `INSERT OR IGNORE` no schema (`src/graph/db.py:200-205`). Isso garante idempotência SOB RE-EXECUÇÃO COM A MESMA REGRA, mas NÃO cobre mutação de regra entre rodadas:

1. Rodada 1: regra YAML mapeia "PAO FRANCES" → categoria `Padaria`. Item ganha aresta `categoria_de → Padaria`.
2. Operador edita `mappings/categorias_item.yaml`: regex de Padaria agora casa só "BAGUETE"; "PAO FRANCES" passa a casar `Alimentação`.
3. Rodada 2: item ganha aresta nova `categoria_de → Alimentação`. **Aresta antiga → Padaria permanece.** Item acumula 2 arestas conflitantes.

O teste existente `test_cada_item_tem_exatamente_uma_categoria` só valida em grafo vazio (rodada 1), não cobre mutação.

## Escopo

### 50b.1 — Helper de deleção de arestas por (src_id, tipo)

Confirmar se `src/graph/db.py` já expõe `deletar_edges(src_id=?, tipo=?)`. Se não, acrescentar:

```python
def deletar_edges(self, src_id: int, tipo: str) -> int:
    """Remove todas as arestas (src_id, *, tipo). Retorna contagem."""
    cur = self._conn.execute(
        "DELETE FROM edge WHERE src_id=? AND tipo=?", (src_id, tipo),
    )
    self._conn.commit()
    return cur.rowcount
```

Justificativa: `item -> categoria_de -> categoria` tem UNIQUE(src,dst,tipo); precisa deletar por (src,tipo) para pegar tanto a categoria antiga quanto a atual antes de re-inserir.

### 50b.2 — item_categorizer: delete-before-insert

Em `categorizar_todos_items_no_grafo`, antes do `adicionar_edge(item_id, categoria_id, "categoria_de")`, chamar `deletar_edges(src_id=item_id, tipo="categoria_de")`. Opcionalmente: só deletar se a categoria antiga for DIFERENTE da nova, para economizar writes (mas DELETE em 0 linhas é barato; simplicidade vence).

### 50b.3 — Teste regressivo

`tests/test_item_categorizer.py::test_mutar_regra_yaml_nao_acumula_arestas_categoria_de`:

```python
def test_mutar_regra_yaml_nao_acumula_arestas_categoria_de(tmp_path):
    # rodada 1: YAML A mapeia "PAO FRANCES" → Padaria
    yaml_a = tmp_path / "cat_a.yaml"
    yaml_a.write_text("categorias:\n  Padaria:\n    - PAO FRANCES\n")
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    item_id = db.upsert_node("item", "pao-frances-xxx", metadata={"descricao": "PAO FRANCES"})
    categorizar_todos_items_no_grafo(db, yaml_a)
    assert len(db.listar_edges(src_id=item_id, tipo="categoria_de")) == 1

    # rodada 2: YAML B mapeia "PAO FRANCES" → Alimentação
    yaml_b = tmp_path / "cat_b.yaml"
    yaml_b.write_text("categorias:\n  Alimentação:\n    - PAO FRANCES\n")
    categorizar_todos_items_no_grafo(db, yaml_b)
    arestas = db.listar_edges(src_id=item_id, tipo="categoria_de")
    assert len(arestas) == 1  # não acumula; antiga foi deletada
    # confirma que aponta para a nova categoria
    dst = db.buscar_node_por_id(arestas[0].dst_id)
    assert dst.nome_canonico.startswith("Alimenta")
```

## Armadilhas

- `INSERT OR IGNORE` em `adicionar_edge` NÃO basta — ele impede duplicata da mesma (src,dst,tipo) mas não mata (src,dst_antigo,tipo).
- Cuidado com `listar_edges` — verificar se existe com parâmetro `src_id` ou só `dst_id`. Sprint 87.6 descobriu que `dst_id` pode não estar exposto; ajustar API se necessário (neste caso, `src_id` é o que precisamos — item é sempre src).
- Idempotência de `adicionar_edge` é preservada (INSERT OR IGNORE); a nova lógica é delete-before-insert, que em re-execução com regra idêntica faz `DELETE ...` (0 linhas) + `INSERT OR IGNORE` (0 novas). Custo trivial.

## Evidência obrigatória

- [ ] `db.deletar_edges(src_id, tipo)` existe e tem docstring explicando uso
- [ ] Teste `test_mutar_regra_yaml_nao_acumula_arestas_categoria_de` PASSA
- [ ] `test_idempotente_nao_duplica_aresta` existente continua PASSANDO
- [ ] Gauntlet verde (lint + pytest + smoke)

---

*"Regra que muda não deve deixar resíduo." — princípio pós-mutação do YAML*
