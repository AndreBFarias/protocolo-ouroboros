## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-118
  title: "Polish combo: tabs sticky + cor stApp + logo + saldo overflow"
  prioridade: P1
  estimativa: 1.5h
  origem: "feedback dono 2026-04-27 (apos UX-115/116/117 mergeados) -- 4 micro-ajustes em tema.py"
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/tema.py
      reason: "css_global() ganha 4 regras novas (tabs sticky + linha 2px destaque, stApp background card_fundo, logo dimensoes ajustadas, card_sidebar_html margin-left zero)"
    - path: tests/test_dashboard_tema.py
      reason: "regressao: 4 ACs novos cobertos por testes regex em css_global"
  forbidden:
    - "Tocar em outras paginas (so tema.py)"
    - "Mudar tokens existentes (PADDING_INTERNO, BORDA_RAIO, BORDA_ATIVA_PX, CORES, DRACULA)"
    - "Adicionar deps externas"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    # AC1: Tabs sticky com separador 2px roxo
    - "Barra de tabs (.stTabs [data-baseweb='tab-list']) ganha position: sticky; top: 0; z-index: 10; background: card_fundo"
    - "Separador 2px na cor destaque (#BD93F9) abaixo de toda a barra de tabs (border-bottom: 2px solid)"
    - "Tabs nao cobrem o conteudo ao rolar (z-index alto + sticky)"
    # AC2: stApp background trocado de #282A36 para #44475A
    - "[data-testid='stApp'] recebe background var(--color-card-fundo) ou #44475A diretamente"
    - "Faixas vazias residuais que pareciam #282A36 desaparecem (TODA area visivel sem dados sai em #44475A)"
    - "Token CORES['fundo'] continua intocado (#282A36 ainda eh DRACULA['background']); apenas o seletor stApp muda"
    # AC3: Logo dimensoes ajustadas
    - "logo_sidebar_html() emite <img> com width=120 OU height-auto explicito; CSS adicional .ouroboros-logo-img garante max-width: 120px e altura proporcional via aspect-ratio"
    - "Validacao visual: logo aparece em ~120px largura e altura proporcional (imagem original eh 724x733, quase quadrada)"
    # AC4: Saldo card -- borda colorida nao transborda padding-left da sidebar
    - "card_sidebar_html() injeta margin-left: 0 e box-sizing: border-box no <div> wrapper para evitar que a borda colorida 3px (border-left) escape do padding interno da sidebar"
    - "Validacao visual: cards Receita/Despesa/Saldo na sidebar ficam dentro do retangulo de PADDING_CHIP=16px da UX-116"
    - "Pelo menos 6 testes regressivos em test_dashboard_tema.py (1-2 por AC)"
  proof_of_work_esperado: |
    # Confirmacao tecnica AC1
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert 'position: sticky' in css and 'tab-list' in css
    assert 'border-bottom: 2px solid' in css
    print('AC1 OK: tabs sticky + linha 2px')
    "

    # Confirmacao tecnica AC2
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert '[data-testid=\"stApp\"]' in css
    # Pode usar var() ou hex literal
    assert '#44475A' in css.lower() or 'var(--color-card-fundo)' in css.lower() or '#44475a' in css.lower()
    print('AC2 OK: stApp em #44475A')
    "

    # Validacao visual via Playwright em http://localhost:8520
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. Abrir cluster=Hoje, conferir logo ~120px largura e altura proporcional
    # 2. Rolar a sidebar e conferir que cards Saldo nao transbordam padding
    # 3. Conferir que toda area de fundo aparece em #44475A
    # 4. Rolar conteudo e conferir que tabs ficam visiveis no topo (sticky)
```

---

# Sprint UX-118 -- Polish combo 2026-04-27

**Status:** EM PRODUÇÃO (P1, criada e despachada 2026-04-27)

Quatro micro-ajustes identificados pelo dono apos validar UX-115/116/117 mergeados. Agrupados em uma sprint para evitar overhead de merge (todos tocam apenas `tema.py`):

1. **Tabs sticky + separador 2px**: barra de tabs deve ficar fixa no topo durante scroll, com linha 2px na cor destaque (#BD93F9) abaixo dela.
2. **Cor `#282A36` global → `#44475A`**: sumir com qualquer faixa escura residual aplicando `#44475A` no `[data-testid='stApp']`. Não tocar tokens.
3. **Logo dimensoes**: imagem natural 724x733 renderiza como 64x65 hoje — visualmente desproporcional. Aumentar para ~120px com aspect-ratio mantido.
4. **Saldo card overflow**: bordas coloridas dos cards Receita/Despesa/Saldo na sidebar transbordam o padding-left de 16px da UX-116. Corrigir via `margin-left: 0` + `box-sizing: border-box`.

Escopo deliberadamente cirurgico: nenhum token novo, nenhuma pagina alterada. Apenas extensao de `css_global()` e ajuste em `card_sidebar_html()`.

---

*"Quatro pequenas correcoes em um arquivo valem mais do que quatro sprints fragmentadas." -- principio do agrupamento honesto*
