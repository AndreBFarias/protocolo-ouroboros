---
concluida_em: 2026-04-28
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: AUDIT-INDEX-JSON
  title: "Indice SQLite em json_extract(metadata, $.arquivo_origem) para queries O(N) em vez de O(N^2)"
  prioridade: P3
  estimativa: ~30min
  origem: "auditoria externa 2026-04-28 P2-06 -- _atualizar_grafo em migrar_pessoa_via_cpf eh O(arquivos x nodes_documento)"
  touches:
    - path: src/graph/db.py
      reason: "criar_schema adiciona CREATE INDEX IF NOT EXISTS em json_extract"
    - path: scripts/migrar_pessoa_via_cpf.py
      reason: "trocar SELECT WHERE tipo='documento' + iteracao por SELECT WHERE arquivo_origem=?"
  forbidden:
    - "Mudar schema canônico do node (apenas índice expressao)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
  acceptance_criteria:
    - "CREATE INDEX idx_node_arquivo_origem ON node(json_extract(metadata, '\$.arquivo_origem')) declarado em criar_schema"
    - "Query em _atualizar_grafo usa json_extract na clausula WHERE em vez de iterar fetchall()"
    - "Performance: 10 arquivos migrados em grafo de 1000 docs em < 100ms (vs 5s atual)"
```

---

# Sprint AUDIT-INDEX-JSON

**Status:** BACKLOG (P3, criada 2026-04-28 pela auditoria externa)

## Motivação

`scripts/migrar_pessoa_via_cpf.py::_atualizar_grafo` faz:

```python
cur = grafo._conn.execute("SELECT id, ... FROM node WHERE tipo='documento'")
for row in cur.fetchall():
    meta = json.loads(row[3] or "{}")
    if meta.get("arquivo_origem") == str(arquivo_antigo):
        ...
```

Para cada arquivo movido, varre TODOS os nodes documento. O(N x M). Trivial hoje (50 docs, 6 arquivos = 300 ops), mas escala mal para 760 arquivos x 1000 docs = 760k ops.

## Implementação

### `src/graph/db.py::criar_schema`

```sql
CREATE INDEX IF NOT EXISTS idx_node_arquivo_origem
ON node(json_extract(metadata, '$.arquivo_origem'))
WHERE tipo = 'documento';
```

### `migrar_pessoa_via_cpf.py::_atualizar_grafo`

```python
cur = grafo._conn.execute(
    """
    SELECT id, tipo, nome_canonico, metadata, aliases
    FROM node
    WHERE tipo='documento'
      AND json_extract(metadata, '$.arquivo_origem') = ?
    """,
    (str(arquivo_antigo),),
)
```

## Testes regressivos

- Criar grafo com 100 nodes documento + 100 nodes outros tipos.
- Migrar 1 arquivo -> query usa índice (verificar via `EXPLAIN QUERY PLAN`).
- Resultado funcional identico ao código antigo.
