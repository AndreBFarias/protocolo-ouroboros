## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-127
  title: "4 fixes finais na Busca Global: botao cortado + remover Tipo de busca + bug contagem + sem novas abas"
  prioridade: P1
  estimativa: 1.5h
  origem: "feedback dono 2026-04-27 (image 22) -- 4 achados finais apos validar cluster v2 + iteracao 3"
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/paginas/busca.py
      reason: "remover dropdown 'Tipo de busca'; corrigir contagem 'Documentos (N)'; garantir resultado inline (UX-124 ja entregou base)"
    - path: src/dashboard/componentes/busca_global_sidebar.py
      reason: "botao de busca da sidebar nao corta em viewport estreito; layout responsivo"
    - path: src/dashboard/tema.py
      reason: "css_global() ganha media query para input de busca da sidebar nao cortar em viewport estreito"
    - path: tests/test_busca_fixes_127.py
      reason: "NOVO -- 6 testes regressivos (1-2 por AC)"
  forbidden:
    - "Mudar logica do roteador UX-114 (so a UI da busca global em paginas/busca.py)"
    - "Quebrar autocomplete + chips (UX-114/UX-126 entregaram)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_busca_fixes_127.py -v"
    - cmd: ".venv/bin/pytest tests/test_busca*.py tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: botao busca sidebar nao corta
    - "Em viewport estreito (320-700px), o input de busca da sidebar (label='Busca Global') renderiza completamente sem corte horizontal"
    - "css_global() emite media query @media (max-width: 700px) com regra que garante width: 100% e overflow: visible no input + container"
    # AC2: remover dropdown 'Tipo de busca'
    - "Bloco st.selectbox('Tipo de busca', ...) eh REMOVIDO de paginas/busca.py"
    - "Filtragem por tipo passa a vir SOMENTE dos chips clicaveis abaixo do input + auto-deteccao por substring (ja funciona via UX-114 roteador)"
    - "Mensagem 'Tipo de busca' nao aparece mais em runtime"
    # AC3: contagem 'Documentos (N)' correta
    - "Quando filtro casa fornecedor com 1+ documentos vinculados, contagem mostra valor real (nao 0)"
    - "Investigar query ou filter no busca.py que esta zerando -- comparar com construir_dataframe_fornecedor() (UX-124) que ja funciona"
    - "Pelo menos 1 teste regressivo com fixture conhecida (boleto -> >=1 documento) provando contagem correta"
    # AC4: busca nao abre nova aba
    - "grep '\\bst.button.*Ir para\\|st.link_button' em paginas/busca.py: 0 matches em runtime de fornecedor (UX-124 ja removeu para Catalogacao filtrada; cobrir outros casos: aba, livre)"
    - "Resultados de tipo='aba' renderizam mensagem inline 'Sua busca casa o nome da aba X' SEM botao de navegacao automatica"
    - "Resultados de tipo='livre' renderizam tabela inline (mesmo padrao da UX-124 para fornecedor)"
    - "Pelo menos 6 testes regressivos cobrindo cada AC"
  proof_of_work_esperado: |
    # AC2
    grep -c "Tipo de busca" src/dashboard/paginas/busca.py
    # = 0

    # AC4
    grep -c "Ir para Catalogacao\|Ir para aba\|st.link_button" src/dashboard/paginas/busca.py
    # = 0

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # http://localhost:8520/?cluster=Documentos&tab=Busca+Global
    # 1. Conferir que NAO ha dropdown 'Tipo de busca' acima do input
    # 2. Clicar chip 'Boleto' -> tabela inline aparece, contagem 'N transacoes' correta
    # 3. Em viewport mobile (320px), input de busca da sidebar visivel inteiro
```

---

# Sprint UX-127 -- 4 fixes finais na Busca Global

**Status:** CONCLUÍDA (commit `ae02904`, 2026-04-27 — 10 testes novos, dropdown removido, contagem fixada, sem novas abas)

4 achados finais identificados pelo dono apos validar UX-126:

1. **Botao de busca da sidebar cortado** em viewport estreito.
2. **Dropdown "Tipo de busca" redundante** -- chips + autocomplete ja cobrem.
3. **Bug contagem "Documentos (0)" sempre** -- investigar query e corrigir.
4. **Busca nao deve abrir nova aba** -- UX-124 cobriu fornecedor; precisa cobrir aba e livre tambem.

Sprint cirurgica: nao toca o roteador UX-114, apenas a UI em busca.py + responsividade da sidebar.

---

*"Filtro que nao filtra e mockup. Botao cortado e amador." -- principio do funcional honesto*
