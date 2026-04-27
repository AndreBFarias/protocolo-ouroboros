## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-113
  title: "Sidebar refactor: campo Buscar primeiro + Area como dropdown"
  prioridade: P1
  estimativa: 3h
  origem: "feedback dono 2026-04-27 -- ponto de entrada cognitivo da sidebar deve ser busca, nao radio de cluster"
  pre_requisito_de: [100]
  depende_de: [UX-114]   # roteador de busca eh implementado em UX-114; UX-113 plugar no input da sidebar
  touches:
    - path: src/dashboard/app.py
      reason: "_sidebar() reordena: Logo -> Campo Buscar -> Area (dropdown) -> Granularidade -> Mes -> Pessoa -> Forma de pagamento"
    - path: src/dashboard/componentes/busca_global_sidebar.py
      reason: "NOVO -- componente do input de busca na sidebar; delega para roteador da Sprint UX-114"
    - path: tests/test_dashboard_sidebar.py
      reason: "regressao: ordem de elementos da sidebar corresponde ao novo design"
  forbidden:
    - "Mudar logica de filtro (Area continua escolhendo cluster; so a UI mudou de radio para selectbox)"
    - "Implementar autocomplete da busca aqui (escopo da UX-114)"
    - "Mudar largura da sidebar (Streamlit nao expoe API estavel)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_sidebar.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Primeiro elemento abaixo do logo na sidebar = st.text_input com placeholder 'Buscar (documento, fornecedor, aba...)'"
    - "Segundo elemento = 'Area' como st.selectbox (dropdown); valores ['Hoje', 'Dinheiro', 'Documentos', 'Analise', 'Metas']; default = primeiro item ou ler de query_params['cluster']"
    - "Demais filtros (Granularidade/Mes/Pessoa/Forma de pagamento) permanecem na ordem atual"
    - "Submeter busca: chama roteador (Sprint UX-114) que decide se navega para aba do dashboard ou abre Busca Global filtrada"
    - "Pelo menos 5 testes regressivos: ordem dos elementos, selectbox da Area, leitura de query_params, navegacao via roteador (mock), preserva drill-down Sprint 73"
  proof_of_work_esperado: |
    # Captura screenshot da sidebar nova vs antiga
    # Antiga: logo + Area (radio 5 opcoes) + Granularidade + Mes + Pessoa + Forma
    # Nova: logo + Campo Buscar (input largo) + Area (selectbox com 5 opcoes) + Granularidade + Mes + Pessoa + Forma

    # Probe runtime (Streamlit + curl):
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6

    # Selectbox Area aparece em vez de radio
    # Submit em "Revisor" no campo Buscar -> URL passa a ser ?cluster=Documentos&tab=Revisor (delegacao para UX-114)
```

---

# Sprint UX-113 -- Sidebar refactor

**Status:** BACKLOG (P1, criada 2026-04-27, pré-requisito da Sprint 100)

Sidebar hoje começa com radio "Área" — força o usuário a navegar antes de poder buscar. Sprint inverte: campo Buscar primeiro (ponto de entrada cognitivo), Área como dropdown abaixo (mantém função de cluster ativo, mas economiza espaço).

A função do **roteador** que decide se a query casa nome de aba (navega) ou conteúdo de documento (abre Busca Global filtrada) é implementada na Sprint UX-114; aqui só plugamos o componente.

---

*"Quem busca primeiro, navega depois. Se navega primeiro, esquece o que buscava." -- princípio do mental model honesto*
