## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-119
  title: "Polish combo v2: 11 micro-ajustes UX (sidebar agrupada + cor unificada + chips/cards uniformes + status bar)"
  prioridade: P1
  estimativa: 2h
  origem: "feedback dono 2026-04-27 segunda parte (imagens 10-18) -- 11 achados de polish em tema.py e sidebar"
  pre_requisito_de: [Sprint 100, UX-122, UX-123]
  touches:
    - path: src/dashboard/tema.py
      reason: "css_global() ganha 9 regras novas; helpers logo/card preservados; literal #444659 (UX-115/UX-118) trocado por var(--color-card-fundo)"
    - path: src/dashboard/app.py
      reason: "_sidebar() remove st.markdown('---') entre Buscar/Area/Granularidade/Mes/Pessoa/Forma; label_visibility='collapsed' no input Buscar"
    - path: tests/test_dashboard_tema.py
      reason: "9-11 testes regressivos novos cobrindo cada AC"
    - path: tests/test_dashboard_sidebar.py
      reason: "atualiza testes de ordem (separadores '---' removidos)"
  forbidden:
    - "Tocar em paginas individuais (so tema.py + app.py)"
    - "Mudar logica de filtros ou drill-down Sprint 73"
    - "Adicionar tokens novos (CORES e DRACULA permanecem intocados)"
    - "Mudar contrato de hero_titulo_html (UX-122 trata isso)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: label Buscar duplicado removido
    - "st.text_input('Buscar', ...) em busca_global_sidebar.py usa label_visibility='collapsed'; placeholder permanece 'Buscar (documento, fornecedor...)'"
    # AC2: status bar Streamlit em card_fundo
    - "css_global() emite regra para [data-testid='stStatusWidget'] e [data-testid='stToast'] com background var(--color-card-fundo)"
    # AC3: selectboxes altura aumentada + glyph integro
    - ".stSelectbox div[role='combobox'] OU [data-testid='stSelectbox'] > div > div ganha min-height: 44px + white-space: nowrap + overflow: hidden em valor selecionado"
    # AC4: sidebar agrupada
    - "_sidebar() em app.py NAO contem st.markdown('---') entre os 6 filtros (Buscar/Area/Granularidade/Mes/Pessoa/Forma); ordem mantida; gap controlado por margin-bottom uniforme"
    # AC5: NAO APLICA -- absorvida em AC6/AC10/AC11/AC13
    # AC6: separador vertical roxo entre sidebar e content
    - "[data-testid='stSidebar'] recebe border-right: 2px solid var(--color-destaque) em css_global()"
    # AC7: padding-top header de cada pagina
    - "[data-testid='stMainBlockContainer'] ganha padding-top adicional ou margin-bottom em h1/h2 (espelha o '/n /n /n' pedido pelo dono)"
    # AC10: chips uniformes (Tipos rapidos)
    - "Container dos chips abaixo do input em paginas/busca.py recebe display: flex + flex-wrap: wrap + gap; cada button ganha flex: 0 0 auto + min-width consistente; white-space: nowrap impede quebra de palavra; se nao couber, linha inteira vai para baixo"
    # AC11: sugestoes uniformes
    - "Mesma tecnica do AC10 aplicada ao container de sugestoes (autocomplete) -- todos com mesma min-width derivada do maior label"
    # AC13: padronizacao de stButton globais (cards Catalogacao + outros)
    - "[data-testid='stButton'] > button ganha min-height: 44px + min-width: 140px + white-space: nowrap; com queda para flex-wrap quando container apertado"
    # AC14: cor unificada (UX-115 e UX-118 substituidos)
    - "Toda ocorrencia de literal '#444659' em tema.py trocada por 'var(--color-card-fundo)' (UX-115 stMain + UX-118 stApp)"
    # AC15: residuais #282A36 cobertos
    - "Investigar elementos visiveis ainda em #282A36 e cobrir via [data-testid] correspondente; documentar no commit message quais foram"
    # Regressivos
    - "Pelo menos 11 testes regressivos em test_dashboard_tema.py (1+ por AC) + ajuste de 1-2 testes em test_dashboard_sidebar.py para refletir remocao dos separadores"
  proof_of_work_esperado: |
    # AC4: confere que separadores foram removidos
    grep -c "st.markdown(\"---\")" src/dashboard/app.py
    # = espera-se valor menor (so separadores em outros locais)

    # AC14: confere unificacao de cor
    grep -n "#444659" src/dashboard/tema.py
    # = 0 matches (todas trocadas por var())
    grep -c "var(--color-card-fundo)" src/dashboard/tema.py
    # = >=4 matches (stMain, stApp, eventualmente stStatusWidget, residuais)

    # AC10/11/13: confere flex em chips/cards
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert 'flex-wrap: wrap' in css and 'white-space: nowrap' in css
    print('AC10/11/13 OK: flex-wrap + nowrap presentes')
    "

    # AC6: confere border-right na sidebar
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert 'border-right: 2px solid' in css
    assert '[data-testid=\"stSidebar\"]' in css
    print('AC6 OK: separador vertical 2px destaque')
    "

    # Validacao visual via Playwright em http://localhost:8520
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # Capturar 4 estados: cluster Hoje (cor unificada + linha vertical), Documentos/Catalogacao (cards uniformes), Documentos/Busca Global (chips uniformes), sidebar com selectboxes integros
```

---

# Sprint UX-119 -- Polish combo v2 (11 ACs)

**Status:** CONCLUÍDA (commit `a69769a`, 2026-04-27 — 9/11 ACs sólidos + 2/11 parciais (AC10/AC11 cobertas funcionalmente via AC13 global; sub-sprint UX-119a sugerida para refactor st.html). Aguarda validação visual humana.)

11 micro-ajustes de polish identificados pelo dono apos validar UX-115/116/117/118 mergeadas. Agrupados em 1 sprint para evitar overhead de merge -- todos tocam apenas `tema.py` e `app.py`.

Achado mais relevante: cor inconsistente entre sidebar (`#44475A`) e body (`#444659` introduzido como literal pela UX-115). UX-119 unifica via `var(--color-card-fundo)` -- visualmente sidebar e body são idênticos.

Padronizacao de chips/cards/botoes globalmente: nenhum botao pode quebrar palavra; se não couber, joga linha inteira pra baixo.

---

*"Polish não e detalhe -- e respeito ao olho do usuario." -- principio do detalhamento honesto*
