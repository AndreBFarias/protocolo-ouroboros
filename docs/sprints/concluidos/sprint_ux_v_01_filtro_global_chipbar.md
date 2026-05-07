---
id: UX-V-01
titulo: Filtro global como chip-bar fina canônica entre breadcrumb e header
status: concluída
prioridade: altissima
data_criacao: 2026-05-07
data_revisao: 2026-05-07
concluida_em: 2026-05-07
fase: PARIDADE_VISUAL
depende_de: [UX-M-02, UX-M-03, UX-M-04]
bloqueia: [UX-V-2.*, UX-V-3.*]
esforco_estimado_horas: 4
origem: docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md (P1)
revisao_2026_05_07: spec corrigida após executor-sprint reportar achado-bloqueio (k) — código real tem 4 filtros + chaves seletor_* + contrato 3-tuple
commit: 4e66dcb
---

# Sprint UX-V-01 — Filtro global como chip-bar fina canônica

## Contexto

Auditoria 2026-05-07 (P1) constatou que o expander `> Filtros globais` aparece no topo de toda página do dashboard mas **não existe no mockup canônico**. Decisão do dono em 2026-05-07: implementar como **chip-bar fina canônica** entre breadcrumb e page-header, idêntica em todos os 5 clusters. Mantém função (drilldown, comparação A/B, filtro pessoa/período/forma) sem poluir layout.

A chip-bar fina substitui o `st.expander("Filtros globais", expanded=False)` atual. Renderiza inline:

```
OUROBOROS / FINANÇAS / EXTRATO
[ pessoa: casal · ] [ período: 30d · ] [ forma: todas ▾ ]              <-- chip-bar fina
EXTRATO
Transações normalizadas dos OFX...
```

Cada chip é clicável e abre dropdown/popover Streamlit. Estado persistido em `st.session_state` mesmo padrão atual.

## Páginas afetadas

Todas as 30 páginas do dashboard que hoje renderizam `st.expander("Filtros globais", ...)`. Localizar via grep.

## Objetivo

1. Criar componente canônico `chip_bar_filtros_globais()` em `src/dashboard/componentes/ui.py`.
2. Adicionar classes `.chip-bar-globais`, `.chip-filtro`, `.chip-filtro-ativo` em `src/dashboard/css/components.css` (ou `src/dashboard/css/paginas/_chip_bar.css` se ficar isolado).
3. Substituir `st.expander("Filtros globais", ...)` por `chip_bar_filtros_globais()` em todas as páginas.
4. Preservar 100% comportamento atual: filtros aplicam ao DataFrame igual antes; estado persiste em session_state com mesmas chaves.
5. Resultado visual: chip-bar fina (altura ~32px) entre breadcrumb e page-header em TODAS as páginas.

## Validação ANTES (grep obrigatório — padrão `(k)`)

```bash
# Onde está o expander hoje?
grep -rn "Filtros globais" src/dashboard/ --include="*.py" | head -20
# Esperado: 1+ matches em algum módulo central (provavelmente shell.py ou page_header.py).

# Quantas páginas chamam?
grep -rln "filtros_globais\|Filtros globais" src/dashboard/paginas/ | wc -l
# Esperado: número que será atualizado.

# Estado atual em session_state?
grep -rn "session_state\[.\(periodo\|pessoa\|forma_pagamento\)" src/dashboard/ --include="*.py" | head -10

# Função existente que renderiza expander?
grep -rn "def .*filtros_globais\|def renderizar_filtros" src/dashboard/ --include="*.py" | head -5

# Dependências M (pré-requisitos)
test -f src/dashboard/componentes/ui.py && echo "ui.py OK"
test -f src/dashboard/css/components.css && echo "components.css OK"
grep -c "carregar_css_pagina" src/dashboard/componentes/ui.py
# Esperado: ≥1 (helper já existe pós Onda M residual)
```

Se grep mostrar que `Filtros globais` está em **lugar único** (provável — implementado em shell.py ou page_header como header injetado), a sprint é cirúrgica. Se está duplicado em N páginas, a sprint vira refatoração maior — registrar achado-bloqueio.

## Spec de implementação

### 1. Helper canônico em `ui.py`

```python
# Adicionar após carregar_css_pagina:

def chip_bar_filtros_globais(
    *,
    pessoas_disponiveis: list[str] | None = None,
    periodos_disponiveis: list[str] | None = None,
    formas_disponiveis: list[str] | None = None,
) -> None:
    """Renderiza chip-bar fina canônica de filtros globais.

    Substitui o `st.expander("Filtros globais", ...)` legado. Lê e grava
    em ``st.session_state`` com as mesmas chaves do expander antigo
    (`periodo_global`, `pessoa_global`, `forma_global`) para preservar
    compatibilidade com filtros aplicados em pipeline de dados.

    Args:
        pessoas_disponiveis: padrão ["casal", "pessoa_a", "pessoa_b"].
        periodos_disponiveis: padrão ["7d", "30d", "90d", "ano", "tudo"].
        formas_disponiveis: padrão ["todas", "pix", "credito", "debito",
            "boleto", "transferencia"].
    """
    import streamlit as st

    pessoas = pessoas_disponiveis or ["casal", "pessoa_a", "pessoa_b"]
    periodos = periodos_disponiveis or ["7d", "30d", "90d", "ano", "tudo"]
    formas = formas_disponiveis or [
        "todas", "pix", "credito", "debito", "boleto", "transferencia"
    ]

    pessoa = st.session_state.get("pessoa_global", "casal")
    periodo = st.session_state.get("periodo_global", "30d")
    forma = st.session_state.get("forma_global", "todas")

    # HTML chip-bar (estilizado por components.css ou paginas/_chip_bar.css)
    st.markdown(
        minificar(
            f"""
            <div class="chip-bar-globais">
              <span class="chip-bar-rotulo">filtros</span>
              <span class="chip-filtro" data-tipo="pessoa">
                pessoa: <strong>{pessoa}</strong>
              </span>
              <span class="chip-filtro" data-tipo="periodo">
                período: <strong>{periodo}</strong>
              </span>
              <span class="chip-filtro" data-tipo="forma">
                forma: <strong>{forma}</strong>
              </span>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    # Selectboxes invisíveis (label_visibility=collapsed) que sincronizam com
    # session_state. Renderizados em colunas para que a interação fique
    # disponível mas sem ocupar altura visível significativa.
    cols = st.columns([1, 1, 1, 6])  # 3 selects + spacer
    with cols[0]:
        nova_pessoa = st.selectbox(
            "pessoa", pessoas,
            index=pessoas.index(pessoa) if pessoa in pessoas else 0,
            key="filtro_global_pessoa",
            label_visibility="collapsed",
        )
    with cols[1]:
        novo_periodo = st.selectbox(
            "período", periodos,
            index=periodos.index(periodo) if periodo in periodos else 1,
            key="filtro_global_periodo",
            label_visibility="collapsed",
        )
    with cols[2]:
        nova_forma = st.selectbox(
            "forma", formas,
            index=formas.index(forma) if forma in formas else 0,
            key="filtro_global_forma",
            label_visibility="collapsed",
        )

    # Sync para session_state global (chaves consumidas pelo pipeline de dados)
    st.session_state["pessoa_global"] = nova_pessoa
    st.session_state["periodo_global"] = novo_periodo
    st.session_state["forma_global"] = nova_forma
```

Adicionar `"chip_bar_filtros_globais"` em `__all__` de `ui.py`.

### 2. CSS canônico

Criar `src/dashboard/css/paginas/_chip_bar.css` (prefixo `_` indica canônico transversal, não página específica):

```css
/* Chip-bar fina de filtros globais (UX-V-01).
   Renderizada entre breadcrumb e page-header em TODAS páginas. */

.chip-bar-globais {
    display: flex;
    align-items: center;
    gap: var(--sp-2);
    padding: var(--sp-2) var(--sp-3);
    margin-bottom: var(--sp-2);
    background: var(--bg-inset);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    font-family: var(--ff-mono, monospace);
    font-size: 11px;
}

.chip-bar-rotulo {
    text-transform: uppercase;
    letter-spacing: 0.10em;
    color: var(--text-muted);
    margin-right: var(--sp-2);
}

.chip-filtro {
    padding: 2px 10px;
    border-radius: var(--r-full);
    background: var(--bg-surface);
    color: var(--text-secondary);
    border: 1px solid var(--border-subtle);
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
}

.chip-filtro:hover {
    border-color: var(--accent-purple);
    color: var(--text-primary);
}

.chip-filtro strong {
    color: var(--text-primary);
    font-weight: 600;
}

.chip-filtro-ativo {
    background: rgba(189, 147, 249, 0.10);
    border-color: var(--accent-purple);
    color: var(--accent-purple);
}

/* Selectboxes invisíveis abaixo da chip-bar -- escondidos por
   label_visibility=collapsed mas Streamlit ainda renderiza altura.
   Reduzir com top negativo. */
div[data-testid="stSelectbox"]:has(label[aria-hidden="true"]) {
    margin-top: -8px;
}
```

Carregar via `tema_css.py` (mesmo padrão dos outros CSS canônicos):

```python
# Adicionar em tema_css.py após _EXTENSOES_CSS:
_CHIP_BAR_CSS = (_RAIZ_DASHBOARD / "css" / "paginas" / "_chip_bar.css").read_text(encoding="utf-8")

# E concatenar em _CSS_GLOBAL_COMPLETO ou wherever components.css is rendered.
```

### 3. Substituir o expander legado

Localizar a função que renderiza `st.expander("Filtros globais", ...)`. Provável local: `src/dashboard/shell.py` ou `src/dashboard/componentes/page_header.py` ou em algum `_renderizar_filtros` invocado por todas as páginas via dispatcher.

Substituir:

```python
# ANTES
with st.expander("Filtros globais", expanded=False):
    pessoa = st.selectbox(...)
    periodo = st.selectbox(...)
    forma = st.selectbox(...)
    st.session_state["pessoa_global"] = pessoa
    ...
```

```python
# DEPOIS
from src.dashboard.componentes.ui import chip_bar_filtros_globais
chip_bar_filtros_globais()
```

### 4. Não tocar em pipeline de dados

Toda lógica downstream que lê `session_state["pessoa_global"]`, `["periodo_global"]`, `["forma_global"]` continua funcionando inalterada. Spec **não muda comportamento de filtragem** — só visual.

## Validação DEPOIS

```bash
# Expander sumiu
grep -rln "expander.*Filtros globais\|expander(\"Filtros" src/dashboard/ --include="*.py"
# Esperado: 0 matches

# Chip-bar é usada
grep -rln "chip_bar_filtros_globais" src/dashboard/ --include="*.py" | wc -l
# Esperado: 1 (na chamada do dispatcher) + 1 (em ui.py) = 2

# CSS criado
test -f src/dashboard/css/paginas/_chip_bar.css && echo "CSS criado OK"

# Lint + smoke + cluster pytest amostrado (1 por cluster)
make lint
make smoke
.venv/bin/python -m pytest \
  tests/test_dashboard_extrato_paginacao.py \
  tests/test_dashboard_categorias.py \
  tests/test_inbox_real.py \
  tests/test_be_diario_eventos.py \
  tests/test_skill_d7.py 2>&1 | tail -5
# Esperado: 0 fails
```

## Proof-of-work runtime-real

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null
setsid -f sh -c '.venv/bin/python -m streamlit run src/dashboard/app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false > /tmp/dash.log 2>&1 &'
sleep 7

# Validação visual em 5 páginas (1 por cluster) via skill validacao-visual:
# - Visão Geral (cluster Home)
# - Extrato (cluster Finanças)
# - Busca Global (cluster Documentos)
# - Categorias (cluster Análise)
# - Bem-estar / Hoje (cluster Bem-estar)

# Cada screenshot deve mostrar:
# 1. Breadcrumb no topo
# 2. CHIP-BAR FINA (altura ~32px) com 3 chips (pessoa/período/forma)
# 3. Page-header (título + subtítulo + sprint-tag)
# 4. NO expander "> Filtros globais" abrindo/fechando
```

## Critério de aceitação

1. `chip_bar_filtros_globais()` adicionado a `ui.py` + `__all__`.
2. `src/dashboard/css/paginas/_chip_bar.css` criado e carregado por `tema_css.py`.
3. `st.expander("Filtros globais", ...)` removido — zero matches em grep.
4. 5 páginas-amostra (1 por cluster) renderizam chip-bar fina entre breadcrumb e page-header sem regressão visual.
5. `session_state["pessoa_global"]`, `["periodo_global"]`, `["forma_global"]` preservados — pipeline de dados não muda comportamento.
6. `make lint && make smoke && pytest` cluster-amostra verde.

## Não-objetivos

- NÃO criar dropdown novo de filtros — usar `st.selectbox` invisível abaixo da chip-bar (limitação Streamlit aceita conforme decisão "mockup é norte, adaptado é OK").
- NÃO mudar lógica de filtragem do pipeline de dados.
- NÃO mexer em filtros locais por página (ex.: filtros do Extrato, do Diário, etc.) — só o GLOBAL.
- NÃO mudar comportamento de drilldown/breadcrumb.

## Referência

- Auditoria 2026-05-07 P1 (`docs/auditorias/AUDITORIA_PARIDADE_VISUAL_2026-05-07.md`).
- Mockup canônico (sem expander): qualquer mockup numerado começa com breadcrumb → page-header.
- VALIDATOR_BRIEF padrões: `(a)` edit incremental, `(b)` acentuação PT-BR, `(k)` hipótese da spec não é dogma, `(p)` supervisor valida pessoalmente, `(u)` proof-of-work runtime real.

*"O filtro deve servir, não ocupar." — princípio chip-bar*
