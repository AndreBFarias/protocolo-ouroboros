## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-121
  title: "Rename cluster 'Hoje' para 'Home'"
  prioridade: P1
  estimativa: 30min
  origem: "feedback dono 2026-04-27 (image 12) -- 'Hoje' nao eh ponto de entrada coerente; 'Home' eh termo padrao"
  pre_requisito_de: [UX-123]
  touches:
    - path: src/dashboard/app.py
      reason: "CLUSTERS_VALIDOS: ('Home', 'Dinheiro', 'Documentos', 'Analise', 'Metas')"
    - path: src/dashboard/componentes/drilldown.py
      reason: "MAPA_ABA_PARA_CLUSTER e ABAS_POR_CLUSTER usam 'Home' como chave"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "Strings literais 'Hoje' (se existirem) trocadas por 'Home'"
    - path: tests/test_dashboard_*.py
      reason: "atualizar fixtures/expectativas que mencionam 'Hoje'"
  forbidden:
    - "Renomear arquivos fisicos (so strings)"
    - "Mudar conteudo das outras areas"
    - "Quebrar query_params: ?cluster=Hoje deve continuar resolvendo (alias backward-compat)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "CLUSTERS_VALIDOS em app.py contem 'Home' (nao 'Hoje')"
    - "MAPA_ABA_PARA_CLUSTER e ABAS_POR_CLUSTER usam chave 'Home'"
    - "Sidebar selectbox Area mostra 'Home' como primeiro valor"
    - "Backward-compat: ?cluster=Hoje resolve para 'Home' via alias dict (CLUSTER_ALIASES = {'Hoje': 'Home'}) em ler_filtros_da_url ou no _selecionar_cluster"
    - "Pelo menos 4 testes regressivos: novo nome no selectbox, alias preservado, conteudo da pagina inalterado, drill-down ainda funciona"
  proof_of_work_esperado: |
    grep -rn "\"Hoje\"\|'Hoje'" src/dashboard/ | grep -v "alias\|backward"
    # = 0 matches em codigo de runtime (so em testes de alias)

    grep -c "Home" src/dashboard/app.py
    # = >=1

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    curl -s "http://localhost:8520/?cluster=Hoje" | grep -i "home"  # alias resolveu
    curl -s "http://localhost:8520/?cluster=Home" | grep -i "home"  # canonico
```

---

# Sprint UX-121 -- Rename Hoje -> Home

**Status:** CONCLUÍDA (commit `4caff3d`, 2026-04-27 — alias backward-compat funcionando)

"Hoje" como ponto de entrada e ambiguo (sugere periodo). "Home" e termo padrao em web/apps. Sprint troca string preservando query_params backward-compat por alias.

---

*"Nome do ponto de entrada define mental model. Home eh universal." -- principio do default semantico*
