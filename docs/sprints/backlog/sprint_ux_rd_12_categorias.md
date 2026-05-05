## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-12
  title: "Categorias reescrita: árvore + treemap + lista de regras YAML"
  prioridade: P1
  estimativa: 3h
  onda: 4
  origem: "mockup 11-categorias.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/categorias.py
      reason: "REESCRITA -- 3 zonas: árvore navegável (categoria > subcategoria) à esquerda, treemap central (cores WCAG-AA), painel direito com regras YAML aplicadas (de mappings/categorias.yaml)"
    - path: tests/test_categorias_redesign.py
      reason: "NOVO -- 6 testes: árvore expande, treemap colore por categoria, regras laterais correspondem à categoria selecionada, drill-down filtra outras páginas"
  forbidden:
    - "Tocar mappings/categorias.yaml"
    - "Hardcodar cores -- usar paleta com contraste WCAG-AA validado"
  hipotese:
    - "Plotly treemap default cores não passam WCAG-AA contra fundo dark. Aplicar palette custom com tokens accent."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_categorias_redesign.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Árvore esquerda: categorias com count, expandir/colapsar"
    - "Treemap central: paleta com >=4.5:1 contraste contra bg #0e0f15 (WCAG-AA)"
    - "Painel direito: regras YAML (regex + override) aplicadas à categoria selecionada"
    - "Click categoria filtra Extrato (drill-down via query params)"
    - "Renderiza em viewport 1200×700 sem corte (UX-115 invariante)"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # ?cluster=Análise&tab=Categorias -- 3 zonas visíveis
    # screenshot
```

---

# Sprint UX-RD-12 — Categorias

**Status:** BACKLOG

**Specs absorvidas:** UX-02 (treemap WCAG ≤1200px) — agora coberto.

---

*"Categorizar é compreender." — princípio da taxonomia*
