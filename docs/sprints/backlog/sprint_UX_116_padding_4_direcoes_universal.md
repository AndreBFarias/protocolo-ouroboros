## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-116
  title: "Padding 4 direcoes (esq/sup/dir/inf) universal em todas as abas"
  prioridade: P1
  estimativa: 1h
  origem: "feedback dono 2026-04-27 -- 'temos que ter um padding a esquerda, superior, a direita, inferior. Em todas as abas.' UX-112 cobriu inputs/expanders mas paginas inteiras ainda colam texto na borda em algumas viewports."
  pre_requisito_de: [UX-114]
  touches:
    - path: src/dashboard/tema.py
      reason: "css_global() emite regra explicita padding-{top,bottom,left,right} = PADDING_INTERNO em .main .block-container; sidebar interna ganha padding-{top,bottom,left,right} = PADDING_CHIP via [data-testid='stSidebar'] > div:first-child"
    - path: tests/test_dashboard_tema.py
      reason: "regressao: 4 propriedades padding-{top,right,bottom,left} presentes em css_global em ambos os seletores"
  forbidden:
    - "Tocar em tokens existentes (PADDING_INTERNO=24, PADDING_CHIP=16 ja existem da UX-112)"
    - "Hardcode em paginas individuais -- toda regra global em css_global()"
    - "Quebrar drill-down Sprint 73 (filtros sidebar continuam funcionais)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - ".main .block-container declara as 4 propriedades padding-{top,right,bottom,left} com valor PADDING_INTERNO (24px)"
    - "Sidebar interna [data-testid='stSidebar'] > div:first-child declara as 4 padding com valor PADDING_CHIP (16px)"
    - "Validacao visual humana: nenhum texto, controle ou heading colado em qualquer borda em qualquer aba (Hoje/Dinheiro/Documentos/Analise/Metas)"
    - "Regressao: testes da Sprint 76 (PADDING_PAGINA_PADRAO_PX presente) continuam verdes"
    - "Pelo menos 4 testes regressivos: 4 padding na main, 4 padding na sidebar, valores derivados de tokens (nao hardcoded), regra nao quebra Sprint 76"
  proof_of_work_esperado: |
    # Confirmacao tecnica
    .venv/bin/python -c "
    from src.dashboard.tema import css_global
    css = css_global()
    assert 'padding-top: 24px' in css and 'padding-bottom: 24px' in css
    assert 'padding-left: 24px' in css and 'padding-right: 24px' in css
    print('OK 4 paddings em .main')
    "

    # Validacao visual via Playwright em 5 abas (uma por cluster)
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # Capturar screenshots http://localhost:8520/?cluster={Hoje,Dinheiro,Documentos,Analise,Metas}
    # Confirmar margem visual em todos os 4 lados
```

---

# Sprint UX-116 -- Padding 4 direcoes universal

**Status:** BACKLOG (P1, criada 2026-04-27, complementa UX-112)

UX-112 estabeleceu tokens `PADDING_INTERNO=24px` e `PADDING_CHIP=16px` mas aplicou apenas em inputs e expanders. Ainda existem viewports (especialmente apos navegacao) onde texto e controles ficam colados nas bordas do `.main .block-container` ou da sidebar. Sprint emite regras universais explicitas para 4 direcoes em ambos os retangulos.

Escopo cirurgico: nenhum token novo, nenhum touch em paginas individuais. Apenas extensao do `css_global()`.

---

*"Padding em tres direcoes e descuido; padding em quatro direcoes e respeito." -- principio do retangulo respiravel*
