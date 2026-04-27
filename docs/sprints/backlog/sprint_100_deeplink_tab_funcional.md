## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 100
  title: "Deep-link ?tab=X funcional dentro de cluster Streamlit"
  prioridade: P1
  estimativa: 2h
  origem: "auditoria 2026-04-26 -- ?tab=Busca+Global em ?cluster=Documentos abre Catalogacao"
  touches:
    - path: src/dashboard/app.py
      reason: "ler ?tab=X ao trocar cluster e injetar st.session_state['active_tab']"
    - path: src/dashboard/componentes/drilldown.py
      reason: "atualizar query_params quando usuario troca tab"
    - path: tests/test_dashboard_deeplink_tab.py
      reason: "regressao: ?tab=X dentro de cluster certo abre tab certa"
  forbidden:
    - "Quebrar drill-down existente (Sprint 73)"
    - "Adicionar deps externas (manter pure-Streamlit)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_deeplink_tab.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "?cluster=Documentos&tab=Busca+Global abre cluster Documentos com tab Busca Global ativa"
    - "?tab=Categorias sem cluster infere cluster=Analise via MAPA_ABA_PARA_CLUSTER (ja existe)"
    - "Trocar tab manualmente atualiza ?tab=X na URL (browser back funciona)"
    - "5 testes: cada cluster com 1 tab não-default deep-linkavel"
  proof_of_work_esperado: |
    # Antes
    curl -s "http://localhost:8520/?cluster=Documentos&tab=Busca+Global" | grep -i "Busca Global"
    # = nada (renderiza Catalogacao)
    
    # Depois
    [mesmo curl]
    # = match em "Busca Global" como aba ativa
```

---

# Sprint 100 -- Deep-link tab funcional

**Status:** BACKLOG (P1, criada 2026-04-26)

Streamlit `st.tabs(...)` não expoe API para ativar tab por nome. Sprint usa truque: `st.session_state['_active_tab_<cluster>']` lido do query_params na inicializacao + `st.tabs(...)` retorna lista; injeta JavaScript via `st.components.v1.html()` que clica na tab correspondente apos render.

Padrao ja documentado em `docs/ARMADILHAS.md #11`. Esta sprint formaliza solução reusavel.

---

*"URL eh contrato. Quem clicou em link tem direito a chegar onde queria." -- principio do deep-link honesto*
