---
concluida_em: 2026-05-05
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-10
  title: "Completude + Revisor reescritos: matriz tipo×mês + 4 colunas com atalhos j/k/a"
  prioridade: P0
  estimativa: 4h
  onda: 3
  origem: "mockups 08-completude.html + 09-revisor.html"
  depende_de: [UX-RD-03]
  touches:
    - path: src/dashboard/paginas/completude.py
      reason: "REESCRITA -- matriz tipo (linha) × mês (coluna) com cell colorida por D7 (graduado/calibracao/regredindo/pendente) + clique navega para Catalogação filtrada"
    - path: src/dashboard/paginas/revisor.py
      reason: "REESCRITA -- 4 colunas com border-left por origem: OFX original (cyan) | ETL (green) | Opus (purple) | Humano (yellow). Atalhos j (próximo), k (anterior), a (aprovar), r (rejeitar). Preservar Sprint D2 schema sqlite revisao."
    - path: src/dashboard/componentes/atalhos_revisor.py
      reason: "NOVO -- listener JS via st.components.v1.html para j/k/a/r restritos à página revisor"
    - path: tests/test_completude_revisor_redesign.py
      reason: "NOVO -- 10 testes: matriz renderiza com cores corretas, click navega, 4 colunas com border-left, atalhos teclado, sqlite write-back preservado"
  forbidden:
    - "Tocar src/dashboard/dados_revisor.py (Sprint D2 schema preservado)"
    - "Quebrar coluna 'Grafo' atualmente entre Opus e Humano (mockup pede 4 colunas: OFX/ETL/Opus/Humano; verificar com dono se Grafo entra ou sai)"
    - "Tocar revisao_humana.sqlite schema"
  hipotese:
    - "Revisor atual tem 4-way (ETL/Opus/Grafo/Humano) -- mockup mostra 4 colunas mas com OFX no lugar de Grafo. Spec dá flexibilidade: implementar 5 colunas se cabem (OFX original | ETL | Opus | Grafo | Humano) e dono valida visualmente. Caso não caibam, manter 4-way ETL/Opus/Grafo/Humano (mais valioso que OFX visualizável)."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_completude_revisor_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/test_revisor*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Completude: tabela com tipo no eixo Y, mes_ref no X (últimos 12 meses), cell colorida por completude (cor D7)"
    - "Cell hover mostra count e %; click navega para Catalogação filtrada"
    - "Revisor: cards de divergência com 4 ou 5 colunas (decisão visual em runtime), border-left colorida por origem"
    - "Tecla j (próximo) / k (anterior) navega divergências; foco mantém scroll"
    - "Tecla a (aprovar) marca status_humano=aprovado; r (rejeitar) marca rejeitado; gravam em revisao_humana.sqlite (Sprint D2 schema preservado)"
    - "Visual D2 4-way preservado em teste: sqlite tem registro pós-aprovação"
    - "Deep-link preservado"
    - "pytest baseline mantida"
  proof_of_work_esperado: |
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. ?cluster=Documentos&tab=Completude -- matriz colorida visível
    # 2. Click cell -> navega Catalogação
    # 3. ?cluster=Documentos&tab=Revisor -- cards de divergência
    # 4. Pressionar j -> próximo card; a -> aprovar
    # 5. sqlite3 data/output/revisao_humana.sqlite "SELECT * FROM revisao ORDER BY ts DESC LIMIT 3"
    # screenshots
```

---

# Sprint UX-RD-10 — Completude + Revisor

**Status:** BACKLOG

Spec **flexível** num ponto: o mockup `09-revisor.html` mostra 4 colunas
(OFX/ETL/Opus/Humano) mas o Revisor atual entrega 4-way ETL/Opus/Grafo/Humano
(mais valioso que OFX visualizável). Dono decide visualmente em runtime se
mantém 4-way atual ou adota OFX. Spec aceita ambos com proof-of-work.

**Specs absorvidas:** UX-04 (Revisor responsivo) — agora coberto pela
reescrita com .table densa + drawer mobile.

---

*"Validar é mais difícil que produzir; mas é onde a verdade mora." — princípio da auditoria*
