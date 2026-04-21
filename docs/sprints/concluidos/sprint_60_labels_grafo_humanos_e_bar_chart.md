## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 60
  title: "Labels humanos no grafo visual + truncamento correto em bar charts"
  touches:
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "nó central mostra CNPJ bruto; TOP 10 FORNECEDORES trunca do início"
    - path: src/graph/queries.py
      reason: "subgrafo deve expor aliases[0] quando existe"
    - path: tests/test_dashboard_grafo.py
      reason: "teste de rótulo"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_grafo.py -v"
      timeout: 60
  acceptance_criteria:
    - "Nó central do subgrafo mostra 'Americanas Sa - 0337' (aliases[0] ou razao_social) em vez de CNPJ 00.776.574/0160-79"
    - "Fallback quando aliases vazio: razao_social ou truncamento do nome_canonico em 40 chars"
    - "Bar chart TOP 10 FORNECEDORES trunca do FIM da string (não do começo): 'AMERICANAS S A EM RECU...' em vez de 'ICANAS S A EM RECU JUDICIAL'"
    - "Tooltip do bar chart mostra o nome completo ao fazer hover"
    - "Nome de arestas no grafo renderiza com cor/peso visível (pode ser label curto ex: 'fornecido_por' → 'forn')"
  proof_of_work_esperado: |
    # Via skill validacao-visual com dashboard rodando:
    # screenshot da aba Grafo após selecionar fornecedor
    # descrição visual multimodal do validador confirmando rótulos humanos
```

---

# Sprint 60 — Labels humanos no grafo + truncamento correto

**Status:** CONCLUÍDA (2026-04-21)
**Prioridade:** P1
**Issue:** AUDIT-2026-04-21-UX-2 + UX-3

## Problema

Auditoria 2026-04-21:
- Grafo visual mostra `00.776.574/0160-79` como label do nó central — usuário não reconhece "Americanas".
- Bar chart Plotly "TOP 10 FORNECEDORES" trunca texto do INÍCIO: vê-se `ICANAS S A EM RECUPERACAO JUDICIAL` com o "AMER" cortado. Mesmo para `OLETO SESC`, `GENCIA DE RESTAURANTES`.

## Implementação

### Fase 1 — Resolver label humano

Em `src/graph/queries.py:subgrafo_por_entidade`:

```python
def label_humano(node: dict) -> str:
    aliases = json.loads(node.get("aliases") or "[]")
    if aliases:
        return aliases[0]
    metadata = json.loads(node.get("metadata") or "{}")
    if "razao_social" in metadata:
        return metadata["razao_social"]
    canonico = node["nome_canonico"]
    return canonico[:40] + "..." if len(canonico) > 40 else canonico
```

Aplicar em todos os nós antes de renderizar com pyvis/streamlit-agraph.

### Fase 2 — Truncamento correto em bar chart

Plotly `yaxis.tickmode` + `ticktext` com labels já truncados no FIM e tooltip no hover. Ou usar `textposition="outside"` em barras horizontais.

### Fase 3 — Teste

```python
def test_label_humano_prefere_alias():
    node = {"aliases": '["Americanas"]', "metadata": "{}", "nome_canonico": "00.776..."}
    assert label_humano(node) == "Americanas"
```

## Evidências Obrigatórias

- [ ] Screenshot grafo com "Americanas Sa - 0337" no nó central
- [ ] Screenshot bar chart top fornecedores com nomes truncados no fim
- [ ] Tooltip mostra nome completo

---

*"Rótulo é a ponte entre dado e humano." — princípio de visualização*
