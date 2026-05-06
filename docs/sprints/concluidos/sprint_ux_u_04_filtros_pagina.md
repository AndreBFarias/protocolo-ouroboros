---
concluida_em: 2026-05-06
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: UX-U-04
  title: "Filtros por página: eliminar widgets antigos da sidebar; criar filtros_pagina.py"
  prioridade: P0
  estimativa: 1.5 dia
  onda: U
  mockup_fonte: "29 mockups (cada tela tem seus próprios filtros visíveis no header da página)"
  depende_de: [UX-U-01]
  bloqueia: [UX-T-01..UX-T-29]
  touches:
    - path: src/dashboard/app.py
      reason: "linhas 206-364: _sidebar() injeta selectbox Granularidade/Mês/Pessoa/Forma_Pagamento + text_input Busca Global + logo escudo + caption Dados de. CORTAR: deixar APENAS o shell HTML novo (renderizar_sidebar). Filtros viram inline em cada página."
    - path: src/dashboard/componentes/filtros_pagina.py
      reason: "NOVO -- helpers renderizar_filtro_periodo(dados, granularidade_padrao='Mês') -> str + renderizar_filtro_pessoa() -> str + renderizar_filtro_forma_pagamento() -> str + renderizar_filtros_grid(filtros: list) -> str. Cada página chama os filtros que precisa, alinhado ao mockup."
    - path: 29 paginas/*.py
      reason: "Refactor cada página para ter filtros inline (no header, abaixo do page-header) em vez de receber via tupla. Páginas continuam recebendo dados completo + ctx; LÊEM filtros via st.session_state (compat com filtro_forma_ativo() existente)."
    - path: src/dashboard/dados.py
      reason: "Helpers filtrar_por_periodo, filtrar_por_pessoa, filtrar_por_forma_pagamento, filtro_forma_ativo, obter_meses_disponiveis, obter_anos_disponiveis JÁ EXISTEM. Reutilizar."
    - path: src/dashboard/tema.py
      reason: "logo_sidebar_html() vira deprecated (não chamada); manter por backward-compat até Onda Q."
    - path: tests/test_filtros_pagina.py
      reason: "NOVO -- 6+ testes: helper renderiza HTML correto; sidebar não tem widgets antigos após refactor; 3 páginas amostra (Extrato, Categorias, Análise) ainda mostram filtros equivalentes mas inline."
  forbidden:
    - "Quebrar comportamento de filtros existente (forma_pagamento via session_state, pessoa, mes_ref) — apenas mudar onde é renderizado."
    - "Remover helpers de dados.py — apenas refatorar quem chama."
    - "Remover busca global ainda — Sprint UX-114 já implementou; mantém aparecendo onde mockup pede (sidebar busca placeholder + topbar busca real)."
  hipotese:
    - "_sidebar() retorna tupla (periodo, pessoa, granularidade, cluster_ativo) que 29 páginas consomem. Os filtros granularidade/mês/pessoa/forma_pagamento aparecem como widgets na sidebar abaixo do shell HTML, gerando a mistura visual antiga+nova reportada pelo dono."
  tests:
    - cmd: ".venv/bin/pytest tests/test_filtros_pagina.py -v"
      esperado: "8+ PASSED (helpers + sidebar limpa + 3 páginas integração)"
    - cmd: "make smoke"
      esperado: "10/10"
  acceptance_criteria:
    - "src/dashboard/componentes/filtros_pagina.py exporta 4+ helpers: renderizar_filtro_periodo, renderizar_filtro_pessoa, renderizar_filtro_forma_pagamento, renderizar_filtros_grid."
    - "Cada helper retorna o valor selecionado (não emite HTML diretamente; usa st.selectbox internamente, mas em colunas dentro da página, não na sidebar)."
    - "_sidebar() em app.py:206 não tem mais selectbox/text_input/logo escudo/caption. Emite apenas o shell HTML via renderizar_sidebar()."
    - "Tupla retornada por _sidebar passa de (periodo, pessoa, granularidade, cluster) para apenas (cluster,) — outras 3 saem da sidebar e migram para session_state populadas pelos helpers de filtros_pagina."
    - "Páginas que precisam de periodo/pessoa/granularidade lêem via st.session_state.get('seletor_periodo', 'Mês corrente'), etc.; OU recebem via ctx atualizado."
    - "Páginas Extrato, Categorias, Análise renderizam seus filtros inline (st.columns no header, abaixo do page-header)."
    - "Sidebar tem ZERO selectbox e ZERO text_input após refactor (validação playwright)."
    - "Validação humana: dono compara sidebar dashboard com mockup 00-shell-navegacao.html; aceita que sidebar é puramente shell HTML novo."
  proof_of_work_esperado: |
    nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
    sleep 8
    .venv/bin/python -c "
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_context(viewport={'width':1440,'height':900}).new_page()
        page.goto('http://127.0.0.1:8765/'); page.wait_for_timeout(5000)
        info = page.evaluate('''() => {
            const sb = document.querySelector('[data-testid=\"stSidebar\"]');
            return {
                n_selectbox: sb?.querySelectorAll('[data-testid=\"stSelectbox\"]').length || 0,
                n_textinput: sb?.querySelectorAll('[data-testid=\"stTextInput\"]').length || 0,
                tem_shell_novo: !!sb?.querySelector('aside.sidebar.ouroboros-sidebar-redesign'),
                cluster_count: sb?.querySelectorAll('.sidebar-cluster-header').length || 0
            };
        }''')
        print(info)
        assert info['n_selectbox'] == 0, f'esperado 0 selectbox na sidebar, achou {info[\"n_selectbox\"]}'
        assert info['n_textinput'] == 0, f'esperado 0 text_input na sidebar (busca movida), achou {info[\"n_textinput\"]}'
        assert info['tem_shell_novo']
        assert info['cluster_count'] == 8
        print('OK contratos U-04 sidebar limpa')
        b.close()
    "
```

---

# Sprint UX-U-04 — Filtros por página

**Status:** BACKLOG — Onda U (estruturante).

## 1. Contexto

Diagnóstico Phase 1 da auditoria 2026-05-06 (Explore agent confirmou):

- `_sidebar()` em `app.py:206-364` faz **dois shells na mesma sidebar**:
  1. Shell HTML novo (linha 231): `renderizar_sidebar()` — 8 clusters, busca placeholder, brand glyph.
  2. Widgets Streamlit antigos (linhas 243-358):
     - `logo_sidebar_html()` — escudo PNG "PROTOCOLO OUROBOROS"
     - Caption "Dados de DD/MM/YYYY — HH:MM —"
     - `renderizar_input_busca()` — text_input Busca Global
     - `st.selectbox` Granularidade (Dia/Semana/Mês/Ano)
     - `st.selectbox` Mês ou Período (depende de granularidade)
     - `st.selectbox` Pessoa (Todos/André/Vitória)
     - `st.selectbox` Forma de pagamento (Todas/Pix/Débito/Crédito/Boleto/Transferência)
- Tupla retornada `(periodo, pessoa, granularidade, cluster_ativo)` é passada para 29 páginas.

**Decisão arquitetural** (mockup canônico): cada tela tem seus próprios filtros relevantes inline no header. Sidebar é **navegação pura**.

Esta sprint corta os widgets antigos da sidebar e cria infraestrutura `filtros_pagina.py` para que cada página renderize seus filtros relevantes.

## 2. Hipótese verificável (Fase ANTES)

```bash
# 1. confirmar widgets atuais na sidebar
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
sleep 8
.venv/bin/python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_context().new_page()
    page.goto('http://127.0.0.1:8765/'); page.wait_for_timeout(5000)
    info = page.evaluate('''() => {
        const sb = document.querySelector('[data-testid=\"stSidebar\"]');
        return {
            selectbox: sb?.querySelectorAll('[data-testid=\"stSelectbox\"]').length || 0,
            textinput: sb?.querySelectorAll('[data-testid=\"stTextInput\"]').length || 0,
            stMarkdown: sb?.querySelectorAll('[data-testid=\"stMarkdown\"]').length || 0
        };
    }''')
    print(info)
"
pkill -f 'streamlit.*8765'

# 2. confirmar quem chama os filtros (consumidores da tupla)
grep -rnE '\(periodo, pessoa,|periodo, pessoa, granularidade' src/dashboard/ | head -10

# 3. confirmar helpers existentes em dados.py
grep -nE '^def filtrar_por|^def filtro_forma|^def obter_meses' src/dashboard/dados.py
```

## 3. Tarefas

1. Rodar hipótese.

2. Criar `src/dashboard/componentes/filtros_pagina.py`:

   ```python
   """Filtros inline por página (substitui filtros globais da sidebar).

   Antes (UX-RD-03): _sidebar() retornava (periodo, pessoa, granularidade, cluster)
   como tupla. Agora cada página renderiza seus próprios filtros via helpers
   deste módulo, e o estado é compartilhado via st.session_state.

   Mockup-fonte: cada tela tem filtros relevantes no header (ex.: 02-extrato.html
   tem dropdowns de período + categoria + busca por local; 22-eventos.html tem
   Modo + Período + Categoria + Pessoa).

   Reutiliza helpers de src/dashboard/dados.py:
   - obter_meses_disponiveis(dados) -> list[str]
   - obter_anos_disponiveis(dados) -> list[str]
   - filtrar_por_periodo(df, granularidade, periodo) -> DataFrame
   - filtrar_por_pessoa(df, pessoa) -> DataFrame
   - filtrar_por_forma_pagamento(df, forma) -> DataFrame
   - filtro_forma_ativo() -> str | None
   """
   from __future__ import annotations
   import streamlit as st
   from src.dashboard.dados import (
       obter_meses_disponiveis,
       obter_anos_disponiveis,
       obter_dias_do_mes,
       obter_semanas_do_mes,
   )

   FORMAS_PAGAMENTO = ["Todas", "Pix", "Débito", "Crédito", "Boleto", "Transferência"]
   PESSOAS_PADRAO = ["Todos", "pessoa_a", "pessoa_b", "casal"]

   def renderizar_filtro_periodo(
       dados: dict,
       granularidade_padrao: str = "Mês",
       key_prefix: str = "filtro",
   ) -> tuple[str, str]:
       """Renderiza dropdown de granularidade + período.

       Returns:
           (granularidade, periodo) -- (str, str). Atualiza st.session_state[f'{key_prefix}_granularidade'] e [f'{key_prefix}_periodo'].
       """
       granularidade = st.selectbox(
           "Granularidade",
           ["Dia", "Semana", "Mês", "Ano"],
           index=["Dia", "Semana", "Mês", "Ano"].index(granularidade_padrao),
           key=f"{key_prefix}_granularidade",
           label_visibility="collapsed",
       )
       if granularidade == "Ano":
           opcoes = obter_anos_disponiveis(dados) or ["2026"]
       elif granularidade == "Mês":
           opcoes = obter_meses_disponiveis(dados) or ["2026-04"]
       elif granularidade == "Semana":
           mes = st.session_state.get(f"{key_prefix}_mes_base", "2026-04")
           opcoes = obter_semanas_do_mes(dados, mes) or ["S1"]
       else:  # Dia
           mes = st.session_state.get(f"{key_prefix}_mes_base", "2026-04")
           opcoes = obter_dias_do_mes(dados, mes) or ["2026-04-01"]

       periodo = st.selectbox(
           "Período",
           opcoes,
           index=0,
           key=f"{key_prefix}_periodo",
           label_visibility="collapsed",
       )
       return granularidade, periodo

   def renderizar_filtro_pessoa(
       opcoes: list[str] | None = None,
       key: str = "filtro_pessoa",
   ) -> str:
       """Renderiza selectbox Pessoa. Returns: pessoa selecionada."""
       opcoes = opcoes or PESSOAS_PADRAO
       return st.selectbox(
           "Pessoa",
           opcoes,
           index=0,
           key=key,
           label_visibility="collapsed",
       )

   def renderizar_filtro_forma_pagamento(key: str = "filtro_forma") -> str:
       """Renderiza selectbox Forma de pagamento. Atualiza session_state['filtro_forma']."""
       forma = st.selectbox(
           "Forma de pagamento",
           FORMAS_PAGAMENTO,
           index=0,
           key=key,
           label_visibility="collapsed",
       )
       return forma

   def renderizar_grid_filtros(
       dados: dict,
       *,
       periodo: bool = True,
       pessoa: bool = True,
       forma_pagamento: bool = False,
       granularidade_padrao: str = "Mês",
       key_prefix: str = "filtro",
   ) -> dict:
       """Renderiza grid de filtros em colunas. Returns dict com chaves selecionadas.

       Combina os filtros pedidos em st.columns. Cada página chama com os filtros
       que precisa (ex.: Visão Geral só pessoa; Extrato pessoa+forma_pagamento+período;
       Eventos pessoa+período).
       """
       filtros_ativos = []
       if periodo:
           filtros_ativos.append("periodo")
       if pessoa:
           filtros_ativos.append("pessoa")
       if forma_pagamento:
           filtros_ativos.append("forma")
       if not filtros_ativos:
           return {}

       resultado = {}
       cols = st.columns(len(filtros_ativos) + (1 if periodo else 0))
       i = 0
       if periodo:
           with cols[i]:
               st.caption("Granularidade")
               g, p = renderizar_filtro_periodo(dados, granularidade_padrao, key_prefix)
               resultado["granularidade"] = g
           i += 1
           with cols[i]:
               st.caption("Período")
               resultado["periodo"] = p
           i += 1
       if pessoa:
           with cols[i]:
               st.caption("Pessoa")
               resultado["pessoa"] = renderizar_filtro_pessoa(key=f"{key_prefix}_pessoa")
           i += 1
       if forma_pagamento:
           with cols[i]:
               st.caption("Forma pagamento")
               resultado["forma"] = renderizar_filtro_forma_pagamento(key=f"{key_prefix}_forma")
           i += 1
       return resultado

   # "Cada lugar tem suas próprias regras." -- Heráclito (paráfrase)
   ```

3. Refatorar `_sidebar()` em `src/dashboard/app.py`:

   ```python
   # ANTES (linhas 206-364): mistura shell + widgets antigos
   def _sidebar(dados: dict, aba_ativa: str = "") -> tuple[str, str, str, str]:
       cluster_ativo = _selecionar_cluster()
       with st.sidebar:
           st.markdown(renderizar_sidebar(...), unsafe_allow_html=True)
           # logo escudo (REMOVER)
           # caption Dados de (REMOVER)
           # text_input Busca (REMOVER, vai para topbar via U-02 slot)
           # selectbox Granularidade/Mês/Pessoa/Forma (REMOVER, vai para inline)
       return periodo, pessoa, granularidade, cluster_ativo

   # DEPOIS: shell-only
   def _sidebar(aba_ativa: str = "") -> str:
       """Renderiza sidebar canônica (shell HTML puro). Returns cluster_ativo."""
       cluster_ativo = _selecionar_cluster()
       with st.sidebar:
           st.markdown(
               renderizar_sidebar(cluster_ativo=cluster_ativo, aba_ativa=aba_ativa),
               unsafe_allow_html=True,
           )
       return cluster_ativo
   ```

4. Refatorar consumidores da tupla em `app.py:main()`:

   ```python
   # ANTES
   periodo, pessoa, granularidade, cluster = _sidebar(dados, aba_ativa=...)

   # DEPOIS
   cluster = _sidebar(aba_ativa=...)
   # periodo/pessoa/granularidade vêm de cada página via filtros_pagina helper
   # ctx é dict opcional preenchido pela página
   ```

5. Para cada uma das 29 páginas em `paginas/*.py`, ajustar assinatura de `renderizar()` para usar `ctx` em vez de tupla:

   ```python
   def renderizar(dados: dict, ctx: dict | None = None) -> None:
       # filtros inline (Visão Geral só pessoa; Extrato pessoa+período+forma_pgto)
       from src.dashboard.componentes.filtros_pagina import renderizar_grid_filtros
       filtros = renderizar_grid_filtros(dados, periodo=True, pessoa=True, forma_pagamento=True)
       periodo = filtros.get("periodo", "")
       pessoa = filtros.get("pessoa", "Todos")
       granularidade = filtros.get("granularidade", "Mês")
       # ... resto da página
   ```

   ATENÇÃO: refactor cuidadoso preserva comportamento (filtros funcionam como antes) mas muda LOCAL de renderização (sidebar -> inline).

6. Criar `tests/test_filtros_pagina.py` com 8+ testes (helpers unitários + sidebar limpa + 3 páginas amostra).

7. Rodar gauntlet (§7).

## 4. Anti-débito

- **Refactor pode quebrar muitos testes** (29 páginas mudam assinatura). Aceitar e atualizar testes em batch como parte desta sprint, OU dividir em U-04.A (helper + sidebar) e U-04.B (refactor 29 páginas).
- Se decidir dividir: U-04.A entrega helper + sidebar shell-only; U-04.B refatora 29 páginas em sequência (cada uma toca 1 arquivo). Mas todas T-* dependem de U-04.B.
- **Recomendo NÃO dividir**: risco de drift entre A e B. Fazer tudo numa sprint pesada (1.5 dia).

## 5. Validação visual humana

```bash
# Dashboard ao vivo + verificar sidebar limpa
nohup .venv/bin/streamlit run src/dashboard/app.py --server.port 8765 --server.headless true &
sleep 8
# Dono abre 3 telas:
# - http://127.0.0.1:8765/                                       (Visão Geral, sidebar shell-only)
# - http://127.0.0.1:8765/?cluster=Finan%C3%A7as&tab=Extrato     (Extrato, filtros inline no header)
# - http://127.0.0.1:8765/?cluster=An%C3%A1lise&tab=Categorias   (Categorias, filtros inline)
```

Critério visual: sidebar tem APENAS o shell novo (8 clusters, brand, busca placeholder, footer "D7 cobertura observável"). Filtros aparecem na própria página, abaixo do page-header.

## 6. Gauntlet

```bash
make lint                                              # exit 0
make smoke                                             # 10/10
.venv/bin/pytest tests/test_filtros_pagina.py -v       # 8+/8+
.venv/bin/pytest tests/ -q --tb=no                     # baseline mantida
```

---

*"Cada lugar tem suas próprias regras." -- Heráclito (paráfrase)*
