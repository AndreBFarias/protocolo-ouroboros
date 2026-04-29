---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 87c
  title: "Fix _contar_docs_do_fornecedor: listar_edges não aceita dst_id, except engole erro"
  touches:
    - path: src/graph/db.py
      reason: "expor dst_id como parâmetro opcional de listar_edges OU criar helper dedicado contar_edges_para_node(dst_id, tipo)"
    - path: src/obsidian/sync_rico.py
      reason: "substituir try/except silencioso por chamada correta da API"
    - path: tests/test_obsidian_rico_vault.py
      reason: "teste regressivo: 3 documentos do mesmo fornecedor devem produzir qtd_docs=3 na nota do fornecedor"
  forbidden:
    - "Mudar schema de edge"
    - "Alterar contratos existentes de listar_edges usados por outros módulos"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "_contar_docs_do_fornecedor retorna contagem real (não 0 silencioso) quando o fornecedor tem arestas fornecido_por apontando para ele"
    - "listar_edges aceita parâmetro dst_id opcional OU helper contar_edges_para_node existe e está testado"
    - "Teste novo: 3 documentos com mesma aresta fornecido_por → fornecedor ficam contados como qtd_docs=3 na nota Fornecedores/<nome>.md"
    - "Zero regressão: todos os callers atuais de listar_edges continuam funcionando"
```

---

# Sprint 87c — Fix `_contar_docs_do_fornecedor`

**Status:** BACKLOG
**Prioridade:** P3 (descoberto durante execução 87.6; não afeta MOC; causa subestimativa de `qtd_docs` em notas Fornecedores/)
**Dependências:** Sprint 71 (sync_rico existente)
**Origem:** achado colateral registrado pelo executor 87.6 (2026-04-23)

## Problema

`src/obsidian/sync_rico.py::_contar_docs_do_fornecedor` (linha ~365) tenta contar quantos documentos estão vinculados a um fornecedor via aresta `fornecido_por`:

```python
def _contar_docs_do_fornecedor(db: GrafoDB, forn_id: int | None) -> int:
    if forn_id is None:
        return 0
    try:
        edges = db.listar_edges(dst_id=forn_id, tipo="fornecido_por")
        return len(edges)
    except Exception:
        return 0
```

Problema: `db.listar_edges` NÃO aceita parâmetro `dst_id`. A exceção (TypeError ou similar) é silenciosamente engolida e a função devolve `0` SEMPRE. Resultado: notas Fornecedores/<nome>.md sempre mostram `qtd_docs: 0` no frontmatter, mesmo quando há documentos vinculados.

## Causa raiz

`listar_edges` em `src/graph/db.py` foi desenhada com filtros por `src_id` e `tipo`, não `dst_id`. O executor da Sprint 71 pediu um filtro que não existe e não rodou o caminho feliz com dados reais (grafo tinha 0 fornecedores na época; bug só aparece com volume).

## Escopo

### 87c.1 — Expandir `listar_edges` em `src/graph/db.py`

Opção A (preferível, retrocompatível): adicionar `dst_id: int | None = None` à assinatura:

```python
def listar_edges(
    self,
    src_id: int | None = None,
    dst_id: int | None = None,
    tipo: str | None = None,
) -> list[Edge]:
    clausulas = []
    params: list[Any] = []
    if src_id is not None:
        clausulas.append("src_id = ?")
        params.append(src_id)
    if dst_id is not None:
        clausulas.append("dst_id = ?")
        params.append(dst_id)
    if tipo is not None:
        clausulas.append("tipo = ?")
        params.append(tipo)
    where = f"WHERE {' AND '.join(clausulas)}" if clausulas else ""
    rows = self._conn.execute(
        f"SELECT id, src_id, dst_id, tipo, peso, evidencia FROM edge {where}",
        params,
    ).fetchall()
    return [_row_to_edge(r) for r in rows]
```

Opção B: helper dedicado `contar_edges_para_node(dst_id, tipo) -> int` com SQL `SELECT COUNT(*) FROM edge WHERE dst_id=? AND tipo=?`. Mais barato que listar (não materializa objects), mas cria API nova sem reuso.

Recomendo A — é o padrão do projeto e destrava outros call-sites semelhantes no futuro.

### 87c.2 — Corrigir `_contar_docs_do_fornecedor`

Remover o `try/except`:

```python
def _contar_docs_do_fornecedor(db: GrafoDB, forn_id: int | None) -> int:
    if forn_id is None:
        return 0
    return len(db.listar_edges(dst_id=forn_id, tipo="fornecido_por"))
```

Se API nova tiver bug, erro explícito > retorno 0 silencioso.

### 87c.3 — Teste regressivo

```python
def test_contar_docs_do_fornecedor_retorna_contagem_real(tmp_path):
    db = GrafoDB(tmp_path / "grafo.sqlite")
    db.criar_schema()
    forn_id = db.upsert_node("fornecedor", "SESC", metadata={"cnpj": "03288908000130"})
    for i in range(3):
        doc_id = db.upsert_node(
            "documento", f"BOLETO-{i}",
            metadata={"tipo_documento": "boleto_servico", "data_emissao": f"2026-0{i+1}-15"},
        )
        db.adicionar_edge(doc_id, forn_id, "fornecido_por")
    from src.obsidian.sync_rico import _contar_docs_do_fornecedor
    assert _contar_docs_do_fornecedor(db, forn_id) == 3
```

### 87c.4 — Teste de filtros combinados em `listar_edges`

`tests/test_graph_db.py::test_listar_edges_filtra_por_dst_id_tipo` para cobrir a expansão da API.

## Armadilhas

- Outros módulos que usem `listar_edges(src_id=...)` não devem quebrar. A adição de `dst_id` opcional com default None preserva chamadas existentes.
- Edge `fornecido_por` vai de `documento -> fornecedor` (documento=src, fornecedor=dst). Confirme lendo `src/graph/ingestor_documento.py:423` antes de prosseguir.
- O bug está silencioso há várias sprints; após fix, notas de fornecedores passam a mostrar `qtd_docs` diferente de 0. Isso pode surpreender quem abrir o vault — documente no commit message.

## Evidência obrigatória

- [ ] `listar_edges(dst_id=..., tipo=...)` funcional e testado
- [ ] `_contar_docs_do_fornecedor` sem `except` genérico
- [ ] 3 documentos vinculados contam como 3, não 0
- [ ] Gauntlet verde
- [ ] `make lint` aceita a mudança (sem warning I001/etc)

---

*"Silêncio em except é bug que nunca aparece na investigação." — princípio pós-sprint 87.6*
