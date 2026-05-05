## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-09
  title: "Busca Global + Catalogação reescritos: facetas + snippets + banco normalizado"
  prioridade: P0
  estimativa: 4h
  onda: 3
  origem: "mockups 06-busca-global.html + 07-catalogacao.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "REESCRITA -- input grande no topo + facetas laterais (tipo, banco, pessoa, mês, classificação) + cards de resultado com snippet highlight + paginação. Preservar UX-114 router (autocomplete + chips + auto-detecção)."
    - path: src/dashboard/paginas/catalogacao.py
      reason: "REESCRITA -- tabela densa de banco normalizado (sha8, tipo, fornecedor, mês, doc?, valor, pessoa) + filtros laterais + ações export"
    - path: tests/test_busca_catalogacao_redesign.py
      reason: "NOVO -- 8 testes: facetas filtram corretamente, highlight aparece, contagem 'Documentos (N)' fiel a UX-127, sem novas abas (UX-127 invariante), catalogação ordenação por col"
  forbidden:
    - "Quebrar UX-114 router (autocomplete + chips + auto-detecção)"
    - "Quebrar UX-124 inline tables"
    - "Quebrar UX-127 (contagem documentos correta, sem nova aba)"
    - "Tocar src/intake/busca_indice.py"
  hipotese:
    - "busca.py atual (740L) já tem UX-114/124/126/127 acumulados. Reescrita preserva semântica (router, chips, autocomplete) mudando só HTML/CSS."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_busca_catalogacao_redesign.py tests/test_busca*.py -v"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Busca: input grande topo (40px) + chips contextuais abaixo (Boleto/Holerite/NFCe/etc)"
    - "Facetas laterais: 5 grupos (tipo, banco, pessoa, mês, classificação) com checkboxes"
    - "Cards de resultado: thumb + tipo pill + fornecedor + valor + data + snippet com `<mark>` token highlight"
    - "Contagem 'Documentos (N)' correta (UX-127 invariante)"
    - "Resultado de aba: mensagem inline (sem botão de navegação -- UX-127)"
    - "Catalogação: tabela 7 colunas mono, ordenação por click no header"
    - "Filtros laterais Catalogação: tipo, mês, pessoa, doc-vinculado-sim/não"
    - "Deep-link ?cluster=Documentos&tab=Busca+Global e tab=Catalogação preservados"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    grep -c "router_busca\|chips_busca" src/dashboard/paginas/busca.py
    # esperado: >= 1 (router preservado)

    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. ?cluster=Documentos&tab=Busca+Global -- digitar 'boleto', conferir contagem
    # 2. Clicar chip 'Holerite' -- filtra
    # 3. ?cluster=Documentos&tab=Catalogação -- tabela densa, ordenação funcional
    # screenshots
```

---

# Sprint UX-RD-09 — Busca + Catalogação

**Status:** BACKLOG

A página de busca acumula 4 sprints recentes (UX-114/124/126/127). Cada uma
adicionou comportamento que **não pode regredir**: autocomplete, chips,
inline tables, contagem correta, sem nova aba. Reescrita 1:1 mantém todo
esse comportamento; muda só a casca visual (input maior, facetas laterais,
cards com snippet highlight).

**Specs absorvidas:** UX-05 do plano ativo (pyvis fallback) FORA do escopo —
Grafo+Obsidian fica como página separada não-reformada nesta onda.

---

*"Quem busca, acha — se a ferramenta deixar." — adaptado*
