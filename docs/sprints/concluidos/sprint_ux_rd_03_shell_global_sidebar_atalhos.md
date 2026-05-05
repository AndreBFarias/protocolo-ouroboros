---
concluida_em: 2026-05-04
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-RD-03
  title: "Shell global: sidebar 8-clusters + topbar + atalhos teclado + modal ajuda"
  prioridade: P0
  estimativa: 4h
  onda: 0
  origem: "redesign aprovado 2026-05-04 + novo-mockup/_shared/shell.js + 00-shell-navegacao.html"
  bloqueia: [UX-RD-04..UX-RD-19]
  depende_de: [UX-RD-01, UX-RD-02]
  touches:
    - path: src/dashboard/app.py
      reason: "_sidebar() reescrita: 8 clusters (Inbox/Home/Finanças/Documentos/Análise/Metas/Bem-estar/Sistema), busca primeiro, brand+caption, separadores entre clusters; main() dispatcher por cluster atualizado"
    - path: src/dashboard/componentes/shell.py
      reason: "NOVO -- renderizar_sidebar(cluster_ativo, aba_ativa), renderizar_topbar(breadcrumb, acoes), instalar_atalhos_globais(); reusa CLUSTERS_OUROBOROS de novo-mockup/_shared/shell.js mas em Python"
    - path: src/dashboard/componentes/atalhos_teclado.py
      reason: "NOVO -- gerar_html_atalhos() injeta JS via st.components.v1.html(<script>, height=0) com listener: 'g h'/'g i'/'g v'/'g r'/'g f'/'g c' navegam, '/' foca busca, '?' abre modal, 'Esc' fecha"
    - path: src/dashboard/componentes/drilldown.py
      reason: "CLUSTERS_VALIDOS estendido para 8 clusters (Inbox + Bem-estar + Sistema). CLUSTER_ALIASES mantém retrocompat ('Hoje'->'Home', 'Dinheiro'->'Finanças')"
    - path: tests/test_shell_redesign.py
      reason: "NOVO -- 12 testes: 8 clusters expostos, atalhos JS gerados, busca foca via /, modal abre via ?, deep-link ?cluster=Inbox sai válido, retrocompat ?cluster=Hoje resolve para Home"
  forbidden:
    - "Tocar paginas/*.py (cada cluster ganha sprint própria)"
    - "Quebrar deep-link Sprint 100 -- ?cluster=X&tab=Y deve continuar funcionando"
    - "Quebrar ler_filtros_da_url() existente"
    - "Adicionar deps externas"
  hipotese:
    - "CLUSTERS_VALIDOS está em componentes/drilldown.py (já é importado por app.py linha 17). Estender lá."
    - "ler_filtros_da_url() lê query_params via st.query_params -- compatível com qualquer cluster novo se incluído em CLUSTERS_VALIDOS."
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_shell_redesign.py -v"
    - cmd: ".venv/bin/pytest tests/test_dashboard*.py tests/test_drilldown*.py -q"
    - cmd: "make smoke"
  acceptance_criteria:
    - "Sidebar exibe 8 clusters em ordem: Inbox, Home, Finanças, Documentos, Análise, Metas, Bem-estar, Sistema"
    - "Cada cluster tem header (mono, uppercase, tracking 0.10em) + lista de páginas"
    - "Página ativa destacada com border-left 2px var(--accent-purple) e bg gradient"
    - "Brand 'Ouroboros' no topo (mono, 14px, glyph + texto)"
    - "Campo busca abaixo do brand, com kbd '/' à direita; foco com tecla /"
    - "Atalhos g h/g i/g v/g r/g f/g c funcionam de qualquer página"
    - "Tecla ? abre modal com tabela de atalhos"
    - "Tecla Esc fecha modais e overlays"
    - "Topbar com breadcrumb 'Ouroboros / <Cluster> / <Página>' (mono, uppercase, tracking 0.04em)"
    - "?cluster=Inbox renderiza cluster Inbox (mesmo sem páginas implementadas ainda; só fallback graceful)"
    - "?cluster=Hoje continua resolvendo para Home (CLUSTER_ALIASES)"
    - "?cluster=Documentos&tab=Revisor continua abrindo Revisor (deep-link Sprint 100 preservado)"
    - "pytest baseline mantida (atualizar testes deep-link existentes para 8 clusters)"
  proof_of_work_esperado: |
    # Hipótese: drilldown.py centraliza CLUSTERS_VALIDOS
    grep -n "CLUSTERS_VALIDOS\s*=" src/dashboard/componentes/drilldown.py
    # esperado: linha única com tupla/lista

    # AC: 8 clusters
    .venv/bin/python -c "from src.dashboard.componentes.drilldown import CLUSTERS_VALIDOS; assert len(CLUSTERS_VALIDOS) == 8; print(CLUSTERS_VALIDOS)"
    # = ('Inbox', 'Home', 'Finanças', 'Documentos', 'Análise', 'Metas', 'Bem-estar', 'Sistema')

    # AC: deep-link retrocompat
    .venv/bin/python -c "from src.dashboard.componentes.drilldown import CLUSTER_ALIASES; assert CLUSTER_ALIASES.get('Hoje') == 'Home'; assert CLUSTER_ALIASES.get('Dinheiro') == 'Finanças'; print('OK')"

    # Probe runtime
    .venv/bin/streamlit run src/dashboard/app.py --server.port 8520 --server.headless true &
    sleep 6
    # 1. http://localhost:8520/ -- sidebar com 8 clusters visíveis
    # 2. http://localhost:8520/?cluster=Bem-estar -- cluster Bem-estar destacado
    # 3. Pressionar 'g' depois 'i' -> navega para Inbox
    # 4. Pressionar '?' -> modal de atalhos abre
    # 5. Pressionar 'Esc' -> modal fecha
    # 6. Pressionar '/' -> busca foca
    # 7. http://localhost:8520/?cluster=Hoje -- ainda resolve para Home (CLUSTER_ALIASES)
    # screenshots em docs/auditorias/redesign/UX-RD-03_*.png
```

---

# Sprint UX-RD-03 — Shell global

**Status:** BACKLOG

Última sprint da Onda 0. Implementa o "vaso" — sidebar de 8 clusters, topbar
com breadcrumb, atalhos globais. Depois disso, Ondas 1-6 plugam páginas
dentro do shell.

**Por quê isolada:** o shell é compartilhado por todas as 28 telas. Quebrar
shell quebra tudo. Aqui o foco é só shell + atalhos; conteúdo das páginas é
tarefa das ondas seguintes.

**Risco crítico mitigado:** preservar deep-link `?cluster=X&tab=Y` da Sprint 100
e `ler_filtros_da_url()` existente. Specs UX-RD-04..14 vão usar isso para
manter URLs compartilháveis.

**Validação visual do dono:** abrir 8 URLs (uma por cluster). Conferir cada
breadcrumb. Testar 6 atalhos (g h, g i, g v, g r, g f, g c) + / + ? + Esc.

**Specs absorvidas:** UX-08 (deep-link teste 13 abas — agora 16+ páginas em
8 clusters com cobertura nova).

---

*"O todo é maior que a soma das partes — quando bem articulado." — Aristóteles*
