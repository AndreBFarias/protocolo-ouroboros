## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-122
  title: "Remover prefixos numericos dos titulos das paginas"
  prioridade: P1
  estimativa: 30min
  origem: "feedback dono 2026-04-27 (image 13) -- '01 Visao Geral', '13 Completude' poluem header; numeros sao arbitrarios"
  pre_requisito_de: [Sprint 100]
  touches:
    - path: src/dashboard/tema.py
      reason: "hero_titulo_html(numero='', titulo, subtitulo='') -- default vazio + oculta <span> se vazio"
    - path: src/dashboard/paginas/*.py
      reason: "TODAS as chamadas hero_titulo_html('XX', ...) substituidas por hero_titulo_html('', ...) ou hero_titulo_html(titulo='...')"
    - path: tests/test_dashboard_tema.py
      reason: "testes regressivos de hero_titulo_html com e sem numero"
  forbidden:
    - "Quebrar callers existentes (assinatura permanece compativel)"
    - "Mudar layout do hero (so o conteudo do <span> de numero)"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_dashboard_tema.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "hero_titulo_html aceita numero='' como default"
    - "Quando numero == '', o <span> com numero NAO eh renderizado (HTML enxuto)"
    - "TODAS as chamadas em paginas/ trocadas: visao_geral.py, completude.py, extrato.py, contas.py, pagamentos.py, projeções.py, busca.py, catalogacao.py, revisor.py, grafo.py, analise.py, metas.py, etc."
    - "Headers das paginas mostram apenas o titulo (sem '01', '13' etc.)"
    - "Pelo menos 3 testes regressivos: hero com numero (retrocompat), hero sem numero, contagem de chamadas em paginas/"
  proof_of_work_esperado: |
    # ANTES: 'XX Visao Geral' / 'YY Completude'
    grep -rn "hero_titulo_html(['\"]\\d" src/dashboard/paginas/
    # = ate 12 matches

    # DEPOIS: 0 matches com prefixo numerico
    grep -rn "hero_titulo_html(['\"]\\d" src/dashboard/paginas/
    # = 0

    # Renderizacao HTML
    .venv/bin/python -c "
    from src.dashboard.tema import hero_titulo_html
    h1 = hero_titulo_html('', 'Visao Geral')
    h2 = hero_titulo_html('01', 'Visao Geral')
    assert '<span' not in h1.split('Visao Geral')[0] or '01' not in h1
    print('hero sem numero OK / hero com numero retrocompat OK')
    "
```

---

# Sprint UX-122 -- Remover prefixos numericos

**Status:** CONCLUÍDA (commit `c1f9842`, 2026-04-27 — 10 páginas atualizadas)

Numeros nos titulos ('01', '13', etc.) sao arbitrarios e poluem visualmente. Sprint remove em todas as 12+ paginas e atualiza helper `hero_titulo_html` para aceitar `numero=''` como default.

---

*"Numero ordinal so faz sentido quando carrega informacao. Caso contrario, eh ruido." -- principio do header limpo*
