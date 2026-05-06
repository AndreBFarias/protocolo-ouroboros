# Relatório Consolidado — Onda U (estruturantes universais)

**Data:** 2026-05-06
**Branch:** `ux/redesign-v1`
**Sprints concluídas:** UX-U-01, UX-U-02, UX-U-03, UX-U-04 (4/4)
**Status:** AGUARDA APROVAÇÃO HUMANA antes de iniciar Onda T (29 telas)

---

## Resumo executivo

A Onda U entregou as 4 peças estruturantes universais que servem de base para as 29 sprints da Onda T (uma por mockup). Todas as peças tocam o shell global e estavam misturadas com widgets antigos do dashboard pré-redesign, gerando o "horrível" reportado pelo dono em 2026-05-06.

Após Onda U:

- Sidebar é **shell HTML puro** — zero widgets antigos.
- Topbar tem **slot de ações** programável por página.
- Helper canônico de **page-header** disponível, 13 páginas migradas.
- Filtros globais saíram da sidebar, viraram **expander compacto no main**.
- Helper `componentes/filtros_pagina.py` disponível para Onda T usar opt-in.

Métricas:

| Métrica | Antes | Depois |
|---|--:|--:|
| Selectbox na sidebar | 4 | **0** |
| TextInput na sidebar | 1 | **0** |
| Cluster nav links | 8 (mas misturado) | **8 limpos** |
| Páginas com `<h1 class="page-title">` | 22 | **35** |
| Helper canônico de page-header | ausente | `componentes/page_header.py` |
| Helper canônico de filtros inline | ausente | `componentes/filtros_pagina.py` |
| Topbar com slot de ações | só breadcrumb | **+ slot dinâmico** |
| Pytest baseline | 2.530 passed | **2.558 passed** (+28) |
| Lint | 0 erros | 0 erros |
| Smoke aritmético | 10/10 | 10/10 |

---

## UX-U-01 — Sidebar canônica com scroll interno

**Concluída:** 2026-05-06
**Commit alvo:** próximo `feat(ux-u-01): sidebar canônica scroll interno`

### Entregue

- Scrollbar canônica via `::-webkit-scrollbar` em `tema_css.py` para `[data-testid="stSidebar"]` — track e thumb seguindo tokens Dracula (`--bg-base`, `--border-subtle`, `--border-strong`).
- 8 clusters (Inbox, Home, Finanças, Documentos, Análise, Metas, Bem-estar, Sistema) acessíveis via scroll interno em qualquer viewport ≥ 768x600.
- Cluster Inbox ganhou `<span class="badge">` no header (placeholder `...` até UX-RD-15 popular contagem real).
- Brand do shell continua sendo o glyph SVG ouroboros (fix-07), busca placeholder com kbd `/`.

### Testes

- `tests/test_sidebar_canonica.py` — 6/6 PASSED:
  - `test_sidebar_renderiza_oito_clusters`
  - `test_sidebar_tem_overflow_auto`
  - `test_sidebar_brand_eh_svg_ouroboros`
  - `test_sidebar_busca_placeholder_tem_kbd`
  - `test_sidebar_inbox_tem_badge`
  - `test_sidebar_scrollbar_canonica_aplicada`

### Captura

- `docs/auditorias/redesign-2026-05-06/U-01_AFTER_dashboard_sidebar.png` (260×900px)
- `docs/auditorias/redesign-2026-05-06/U-04_AFTER_sidebar.png` (estado final consolidado)

---

## UX-U-02 — Topbar canônica com slot de ações

**Concluída:** 2026-05-06

### Entregue

- Novo módulo `src/dashboard/componentes/topbar_actions.py` com helpers:
  - `Acao` (TypedDict): `{label, href?, primary?, glyph?, kbd?, title?}`
  - `renderizar_grupo_acoes(acoes: Iterable[Acao])` — popula `st.session_state['topbar_acoes_html']`.
  - `consumir_acoes_html()` — leitura.
  - `resetar_slot()` — usado por `app.py:_renderizar_topbar_para`.
- `componentes/shell.py:renderizar_topbar` agora lê `st.session_state['topbar_acoes_html']` e injeta no slot `<div class="topbar-actions">`.
- `app.py:main()` cria placeholder `st.empty()` para o topbar e preenche **após** o dispatcher (assim cada página pode chamar `renderizar_grupo_acoes` antes do topbar ser renderizado).
- Reset do slot a cada run anti-leak entre páginas.

### Testes

- `tests/test_topbar_canonica.py` — 5/5 PASSED:
  - `test_topbar_tem_slot_actions`
  - `test_topbar_breadcrumb_clicavel`
  - `test_helper_renderizar_grupo_acoes_grava_session_state`
  - `test_main_reseta_slot_topbar_em_cada_run`
  - `test_topbar_actions_helper_existe`

### Implicação Onda T

Cada sprint T-NN da Onda T pode chamar:

```python
from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
renderizar_grupo_acoes([
    {"label": "Atualizar", "glyph": "refresh", "kbd": "r"},
    {"label": "Ir para Validação", "primary": True,
     "href": "?cluster=Documentos&tab=Revisor"},
])
```

E o resultado aparece automaticamente na topbar, alinhado à direita do breadcrumb.

---

## UX-U-03 — Page-header canônico (helper único)

**Concluída:** 2026-05-06

### Entregue

- Novo módulo `src/dashboard/componentes/page_header.py`:
  - `Pill` (TypedDict): `{texto, tipo}`.
  - `renderizar_page_header(titulo, subtitulo='', sprint_tag='', pills=())` retorna HTML canônico:

    ```html
    <header class="page-header">
      <div>
        <h1 class="page-title">EXTRATO</h1>
        <p class="page-subtitle">…</p>
      </div>
      <div class="page-meta">
        <span class="sprint-tag">UX-RD-06</span>
        <span class="pill pill-d7-graduado">…</span>
      </div>
    </header>
    ```
- 13 páginas migradas para o helper:
  - 8 Bem-estar (`be_ciclo`, `be_cruzamentos`, `be_editor_toml`, `be_medidas`, `be_memorias`, `be_privacidade`, `be_recap`, `be_rotina`) que usavam `<h1 style="font-size:24px">` customizado.
  - `extrato.py`, `extracao_tripla.py`, `grafo_obsidian.py`, `analise_avancada.py` que usavam `hero_titulo_html` com h1 não-canônico.
- Total no dashboard agora: **35 páginas com `<h1 class="page-title">` canônico** (era 22).

### Testes

- `tests/test_page_header_canonico.py` — 14/14 PASSED:
  - 7 unitários do helper (titulo, subtitulo, sprint_tag, pills, escape HTML, omissões).
  - 2 lint estrutural (`zero_st_title`, `zero_st_markdown_h1`).
  - 5 integração ao vivo (Extrato, Revisor, Categorias, Bem-estar/Hoje, Skills D7) — todos com `text-transform: uppercase` confirmado.

### Implicação Onda T

Cada T-NN usa:

```python
from src.dashboard.componentes.page_header import renderizar_page_header
st.markdown(
    renderizar_page_header(
        titulo="EXTRATO",
        subtitulo="Tabela densa com transações do período…",
        sprint_tag="UX-T-02",
        pills=[{"texto": "78 transações", "tipo": "d7-graduado"}],
    ),
    unsafe_allow_html=True,
)
```

Resultado: page-title homogêneo cross-páginas (UPPERCASE 40px gradient).

---

## UX-U-04 — Filtros por página + sidebar shell-only

**Concluída:** 2026-05-06

### Entregue

- **`_sidebar()` em `app.py:201-238`**: cortado radicalmente. Antes 158 linhas de widgets misturados; agora emite **apenas** `renderizar_sidebar()` HTML.
  - Removido: `logo_sidebar_html` (logo escudo PNG), caption "Dados de DD/MM — HH:MM —", `renderizar_input_busca`, `selectbox` Granularidade/Mês/Pessoa/Forma_Pagamento, `_cards_sidebar` (cards de saldo).
  - Mantido: assinatura `tuple[str, str, str, str]` para retrocompat com 29 páginas que consomem `(periodo, pessoa, granularidade, cluster_ativo)`.
- **`_filtros_globais_main(dados)` nova função em `app.py:240-299`**: renderiza `st.expander("Filtros globais", expanded=False)` no main, abaixo da topbar, com 4 selectbox em 4 colunas. Mantém comportamento existente (`session_state["filtro_forma"]`, `seletor_*` etc.).
- **Novo módulo `src/dashboard/componentes/filtros_pagina.py`** com helpers:
  - `renderizar_filtro_periodo(dados, granularidade_padrao, key_prefix)` → `(granularidade, periodo)`.
  - `renderizar_filtro_pessoa(opcoes, key)` → string.
  - `renderizar_filtro_forma_pagamento(key)` → `str | None` (None se "Todas") + atualiza `filtro_forma`.
  - `renderizar_grid_filtros(dados, *, periodo, pessoa, forma_pagamento, granularidade_padrao, key_prefix)` → dict.
- 4 testes legados foram atualizados/skip:
  - `test_ac5_app_chama_logo_com_120px` → @pytest.mark.skip (UX-U-04 removeu).
  - `test_ac6_caption_sidebar_em_duas_linhas_centralizadas` → @pytest.mark.skip (UX-U-04 removeu).
  - `test_app_importavel_sem_streamlit_real_no_path` → ajustado (valida `_filtros_globais_main`).
  - `test_ac4_apenas_dois_separadores_intermediarios_removidos` → ajustado (espera 0, era 2).

### Testes

- `tests/test_filtros_pagina.py` — 7/7 PASSED:
  - `test_sidebar_zero_selectbox`
  - `test_sidebar_zero_text_input`
  - `test_sidebar_continua_com_8_clusters`
  - `test_filtros_globais_main_tem_expander`
  - `test_helper_filtros_pagina_existe`
  - `test_helper_filtro_pessoa_devolve_string`
  - `test_helper_filtro_forma_atualiza_session_state`

### Captura final

- `docs/auditorias/redesign-2026-05-06/U-04_AFTER_dashboard_full.png` (1440×altura completa)
- `docs/auditorias/redesign-2026-05-06/U-04_AFTER_sidebar.png` (260×900)

### Implicação Onda T

Cada T-NN pode escolher:

1. **Continuar consumindo o expander global** (sem mudança) — assinatura `renderizar(dados, periodo, pessoa, ctx)` da página continua igual.
2. **Renderizar filtros próprios** via `componentes/filtros_pagina` (recomendado quando o mockup pede filtros específicos da tela). Exemplo:

   ```python
   from src.dashboard.componentes.filtros_pagina import renderizar_grid_filtros
   filtros = renderizar_grid_filtros(
       dados,
       periodo=True, pessoa=True, forma_pagamento=True,
       key_prefix=f"extrato_filtro",
   )
   periodo = filtros["periodo"]
   pessoa = filtros["pessoa"]
   ```

---

## Gauntlet final consolidado

```
make lint                     # exit 0
make smoke                    # 10/10
.venv/bin/pytest tests/ -q    # 2.558 passed, 11 skipped, 1 xfailed
```

Verificação proof-of-work runtime:

```python
# Sidebar shell-only (visualmente):
sidebar_selectbox: 0
sidebar_textinput: 0
sidebar_clusters: 8
sidebar_brand_svg: True
sidebar_busca_kbd: True
sidebar_footer: True
sidebar_overflow: auto
# Topbar canônica:
tem_topbar: True
tem_topbar_actions_slot: True
tem_breadcrumb: True
# Filtros migrados:
tem_expander_filtros: True (Filtros globais)
```

---

## Pontos de atenção

1. **Visão Geral (`visao_geral.py`) ainda tem hero customizado** — não foi migrada para `renderizar_page_header` porque o hero da Visão Geral é específico (anel ouroboros animado + marca "Sistema agentic-first"). Decisão: manter como está; T-01 (Visão Geral) decide se mantém o hero ou migra.

2. **`hero_titulo_html` ainda é chamado por `contas.py` e `projecoes.py`** — apenas para satisfazer `test_dashboard_titulos.py:test_pagina_chama_hero_titulo_sem_numero`. Migração para `renderizar_page_header` fica para T-03 (Contas) e T-05 (Projeções).

3. **Deep-link `?cluster=X&tab=Y` direciona para tab errada em alguns casos** — observado durante captura de U-03 (Bem-estar/Memórias caiu em "Bem-estar/Hoje", Documentos/Extração Tripla caiu em "Busca Global"). Bug de roteamento pré-existente. Será corrigido nas Q-* (Quality Gates) ou em sprint dedicada.

4. **Testes legados em deprecação progressiva** — `test_dashboard_sidebar.py` e `test_catalogacao_humanizado.py` têm asserts validando comportamento UX-113/UX-126 que UX-U-04 substituiu. Acrescentei `@pytest.mark.skip` com motivo explícito + atualizei dois testes para refletir o novo invariante. Onda Q vai consolidar limpeza desses arquivos.

---

## Próximos passos

1. **Validação humana**: dono abre `nohup streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &` e visita:
   - `http://127.0.0.1:8765/` → sidebar limpa, topbar com breadcrumb, expander Filtros globais visível.
   - `http://127.0.0.1:8765/?cluster=Finan%C3%A7as&tab=Extrato` → page-header EXTRATO em UPPERCASE 40px gradient.
   - `http://127.0.0.1:8765/?cluster=Bem-estar&tab=Recap` → page-header RECAP · MENSAL canônico.
   - Navegação entre clusters via cliques na sidebar funciona; URL atualiza.

2. **Aprovação explícita do dono** (mensagem confirmando que pode prosseguir).

3. **Onda T**: escrever 29 specs T-01..T-29 em batch (template único, conteúdo customizado por mockup) + executar uma sprint por dia com validação humana entre cada.

4. **Onda Q (3 sprints)**: Q-01 auditoria visual completa, Q-02 regressão integradora, Q-03 fechamento documental.

---

*"O caminho longo e o caminho certo às vezes coincidem." — adaptado de Confúcio*
