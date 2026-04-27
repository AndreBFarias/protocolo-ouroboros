## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-117
  title: "Filtros contextuais: 'Tipo de pendencia' e 'Pagina' movem para aba Revisor"
  prioridade: P1
  estimativa: 2h
  origem: "feedback dono 2026-04-27 -- 'Tipo de pendencia e Pagina nao sei se fazem sentido' na sidebar global; sao filtros do Revisor; nao deveriam contaminar todas as areas"
  pre_requisito_de: [UX-114]
  depende_de: []
  touches:
    - path: src/dashboard/app.py
      reason: "_sidebar() perde os blocos 'Tipo de pendencia' (multiselect) e 'Pagina' (number_input). Hoje renderizam globais mesmo fora do Revisor."
    - path: src/dashboard/paginas/revisor.py
      reason: "filtros internos: multiselect 'Tipo de pendencia' + number_input 'Pagina' renderizados no topo da pagina via st.columns([2,1]) ou expander 'Filtros'. Mantem session_state keys para retrocompatibilidade."
    - path: tests/test_dashboard_revisor.py
      reason: "regressao: filtros movem; verificar que sidebar nao mostra 'Tipo de pendencia' globalmente"
  forbidden:
    - "Mudar logica de paginacao do Revisor"
    - "Quebrar contrato de listar_pendencias_revisao"
    - "Mover filtros que sao de fato globais (Mes, Pessoa, Forma de pagamento permanecem)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_revisor.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Sidebar global nao tem 'Tipo de pendencia' nem 'Pagina' (verificar grep em app.py)"
    - "Pagina Revisor mostra estes 2 filtros no topo via st.columns([2,1]) -- multiselect a esquerda (largura 2) + number_input a direita (largura 1)"
    - "Comportamento funcional preservado: mesmas pendencias listadas para mesma combinacao de filtros (regressao)"
    - "Session state keys preservadas: revisor_filtro_tipo, revisor_filtro_pagina (atualmente filtro_tipo_pendencia, filtro_pagina_revisor) -- migrar com defesa em camadas se necessario"
    - "Pelo menos 5 testes regressivos: filtros nao aparecem no _sidebar(); aparecem em revisor.py; mesmos resultados antes/depois para fixture conhecida; paginacao funciona; multiselect com 0/1/3 valores produz mesmas listas"
  proof_of_work_esperado: |
    # Antes: grep mostra os filtros em app.py _sidebar()
    grep -n "Tipo de pendencia\|number_input.*Pagina" src/dashboard/app.py
    # = >=2 ocorrencias

    # Depois: filtros nao em app.py _sidebar(), mas em revisor.py topo
    grep -n "Tipo de pendencia\|number_input.*Pagina" src/dashboard/app.py
    # = 0 ocorrencias
    grep -n "Tipo de pendencia\|number_input.*Pagina" src/dashboard/paginas/revisor.py
    # = >=2 ocorrencias

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Hoje -- confirmar sidebar SEM os 2 filtros
    # http://localhost:8520/?cluster=Documentos&tab=Revisor -- confirmar topo COM os 2 filtros
```

---

# Sprint UX-117 -- Filtros contextuais por aba

**Status:** CONCLUÍDA (commit `46d8620`, 2026-04-27)

Hoje a sidebar global mostra 'Tipo de pendência' e 'Página' mesmo quando o usuário está em Hoje/Dinheiro/Análise/Metas. Esses filtros são específicos do **Revisor** e poluem o mental model das outras áreas. Sprint move esses controles para dentro da página Revisor, mantendo lógica funcional intacta.

Padrão (m) branch reversível: se migração quebra session_state existente, manter alias por uma sprint (escrever em ambas keys). Validar via testes regressivos com fixture conhecida antes/depois.

Mês / Pessoa / Forma de pagamento permanecem na sidebar global — filtros transversais válidos para todas as áreas.

---

*"Filtros que so importam em uma area pertencem aquela area. Tudo o mais e ruido cognitivo." -- principio do escopo do filtro*
