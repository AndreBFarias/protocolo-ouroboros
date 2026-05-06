---
id: UX-M-02
titulo: Componentes universais HTML em ui.py (consolidação)
status: backlog
prioridade: alta
data_criacao: 2026-05-06
data_revisao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01]
bloqueia: [UX-M-03, UX-M-02.A, UX-M-02.B, UX-M-02.C, UX-M-02.D]
esforco_estimado_horas: 8-10
---

# Sprint UX-M-02 — Componentes universais HTML (consolidação)

## Contexto

Cada página do dashboard reinventa seus próprios componentes HTML:
- 4 páginas tinham `_page_header_html()` reescrito (corrigido em commit `2817706`).
- KPI cards têm 5+ classes diferentes (`.vg-t01-kpi`, `.kpi-card`, `.pat-card`, etc.).
- Cards, tabelas, search bars, chips — variantes em N páginas.

**Achado da auditoria 2026-05-06**:

- `src/dashboard/tema.py` exporta **17 funções HTML helpers** (9 são componentes visuais reutilizáveis, 8 são utilitários).
- `src/dashboard/componentes/page_header.py` JÁ implementa `renderizar_page_header()` canônico (usado pela Onda U-03).
- `src/dashboard/componentes/topbar_actions.py` JÁ implementa `renderizar_grupo_acoes()` canônico (usado pela Onda T).
- `src/dashboard/componentes/visao_geral_widgets.py` tem widgets específicos da Visão Geral (não-genéricos).

**Problema real**: NÃO falta criar componentes — falta **consolidar** os existentes em um ponto único de import (`ui.py`) e **migrar** os 9 helpers de `tema.py` que viraram componentes para a mesma fronteira.

## Objetivo

Criar `src/dashboard/componentes/ui.py` como **fronteira pública única** de componentes UI canônicos. Consolida:

1. Re-exports de `page_header.py::renderizar_page_header` e `topbar_actions.py::renderizar_grupo_acoes`.
2. Migração de 9 helpers de `tema.py` (lista exata abaixo).
3. **Adição** de 2-3 funções faltantes que páginas atualmente improvisam (`kpi_card`, `data_row`, `group_card`).

`tema.py` mantém 8 helpers utilitários puros (cor, locale, ícones, etc.) — mas suas 9 funções "componente" viram **alias shim** que importam de `ui.py` (compat 30 páginas que importam de `tema`).

## Hipótese

Uma fronteira `from src.dashboard.componentes.ui import (...)` cobre ≥80% dos componentes HTML usados pelas 30+ páginas. Restante (~20%) são layouts realmente únicos por página (ex: Sankey de categorias, heatmap de humor) — esses ficam no módulo da página.

## Validação ANTES (grep obrigatório)

```bash
# Inventário atual
grep -rn "from src.dashboard.tema import" src/dashboard/paginas/ | wc -l
# Esperado: ~30 imports

grep -rn "renderizar_page_header" src/dashboard/paginas/ | wc -l
# Esperado: ~25 páginas (Onda U-03 trouxe canônico)

grep -rn "hero_titulo_html\|callout_html\|subtitulo_secao_html\|chip_html" src/dashboard/paginas/ | wc -l
# Esperado: dezenas — alvo da consolidação

# Confirmar arquivos canônicos existentes
test -f src/dashboard/componentes/page_header.py && echo "OK page_header.py existe"
test -f src/dashboard/componentes/topbar_actions.py && echo "OK topbar_actions.py existe"

# tokens.css existe (M-01)?
test -f src/dashboard/css/tokens.css && echo "M-01 OK" || echo "BLOQUEADO: M-01 não rodou"
```

## Spec de implementação

### Lista exata: 9 helpers que migram de `tema.py` para `ui.py`

| Função tema.py | Linha tema.py | Ação | Justificativa |
|---|---|---|---|
| `card_html` | 215 | Migrar | KPI/info card genérico — componente visual |
| `card_sidebar_html` | 242 | Migrar | Card específico de sidebar — componente |
| `hero_titulo_html` | 275 | Migrar | Hero legado — componente (mantém compat) |
| `subtitulo_secao_html` | 310 | Migrar | Subtítulo de seção — componente |
| `label_uppercase_html` | 326 | Migrar | Label MAIÚSCULO — componente |
| `callout_html` | 431 | Migrar | Callout info/warning/success — componente |
| `progress_inline_html` | 475 | Migrar | Barra de progresso — componente |
| `metric_semantic_html` | 513 | Migrar | Métrica D7 — componente |
| `chip_html` | 566 | Migrar | Chip estilizado — componente |

### Lista exata: 8 helpers que FICAM em `tema.py`

| Função tema.py | Linha | Justificativa |
|---|---|---|
| `logo_sidebar_html` | 162 | Específico de sidebar — fora do escopo "componentes universais" |
| `rgba_cor_inline` | 338 | Utilitário cor (não emite HTML estruturado) |
| `legenda_abaixo` | 361 | Layout específico de gráfico Plotly |
| `rgba_cor` | 386 | Utilitário cor |
| `icon_html` | 416 | Utilitário Feather icons |
| `breadcrumb_drilldown_html` | 601 | Específico de breadcrumb (Onda U cobre via shell) |
| `formatar_mes_ptbr` | 669 | Utilitário i18n |
| `aplicar_locale_ptbr` | 688 | Utilitário Plotly i18n |

### Estrutura proposta de `ui.py`

```python
"""Componentes universais HTML para o dashboard Ouroboros.

Princípio: ZERO duplicação visual. Toda página usa as mesmas funções.
CSS dos componentes vive em src/dashboard/css/components/ (UX-M-03).

Sprint UX-M-02 — Onda M (modularização).

Fronteira pública. Imports canônicos:

    from src.dashboard.componentes.ui import (
        page_header,        # de page_header.py
        topbar_actions,     # de topbar_actions.py
        card_html,          # de tema.py (migrado)
        callout_html,       # de tema.py (migrado)
        kpi_card,           # NOVO (substitui classes locais)
        data_row,           # NOVO
        group_card,         # NOVO
        # ... etc.
    )
"""
from __future__ import annotations

# Re-exports de componentes já modulares
from src.dashboard.componentes.page_header import (
    renderizar_page_header as page_header,
)
from src.dashboard.componentes.topbar_actions import (
    renderizar_grupo_acoes as topbar_actions,
)

# Componentes migrados de tema.py
# (estas funções FORAM movidas para cá; tema.py mantém aliases shim)
def card_html(titulo: str, valor: str, cor: str) -> str:
    """Card genérico com título + valor + borda colorida.

    Migrado de tema.py em UX-M-02. tema.py mantém alias shim importando daqui.
    """
    # ... implementação igual à de tema.py linha 215
    ...

def callout_html(tipo: str, texto: str) -> str:
    """Callout info/warning/success/error.

    Migrado de tema.py em UX-M-02.
    """
    ...

# (mesmo padrão para os outros 7 helpers)


# NOVO: componentes faltantes que páginas improvisam hoje
def kpi_card(label: str, valor: str, sub_label: str = "", accent: str = "purple") -> str:
    """KPI card canônico: label MAIÚSCULO + valor grande + sub-label.

    Substitui as ~5 classes locais espalhadas (.vg-t01-kpi, .kpi-card,
    .pat-card, etc.). Usar em todas as páginas com KPIs em st.columns.

    Args:
        label: rótulo curto (será UPPERCASE).
        valor: número/texto formatado (ex: "48", "R$ 776.571,59").
        sub_label: contexto secundário (ex: "11 tipos no grafo").
        accent: cor da borda esquerda (purple, cyan, green, yellow, red, orange, pink).
    """
    return f"""<div class="kpi-card kpi-card--{accent}">
      <div class="kpi-label">{label.upper()}</div>
      <div class="kpi-valor">{valor}</div>
      {f'<div class="kpi-sub">{sub_label}</div>' if sub_label else ''}
    </div>"""

def data_row(titulo_html: str, meta_dict: dict[str, str], snippet_html: str = "") -> str:
    """Linha de resultado com título + meta inline + snippet opcional."""
    ...

def group_card(titulo: str, linhas_html: str, contagem: str = "", pill_label: str = "") -> str:
    """Moldura de grupo de resultados (header + linhas)."""
    ...
```

### Estratégia anti-duplicação em `tema.py`

Após mover 9 funções, `tema.py` NÃO mantém implementação dupla. Em vez:

```python
# tema.py — após UX-M-02

# ─────────────────────────────────────────────────────────────────────
# Aliases shim para compat (UX-M-02).
# 9 funções de componentes foram migradas para ui.py. tema.py mantém
# aliases para que páginas que faziam `from tema import callout_html`
# continuem funcionando sem edit.
#
# Sprints futuras (M-02.A..D) migram páginas para imports diretos
# de ui.py, e estes aliases podem ser removidos em sprint UX-M-CLEANUP.
# ─────────────────────────────────────────────────────────────────────

from src.dashboard.componentes.ui import (
    card_html,
    card_sidebar_html,
    hero_titulo_html,
    subtitulo_secao_html,
    label_uppercase_html,
    callout_html,
    progress_inline_html,
    metric_semantic_html,
    chip_html,
)

__all__ = [
    # ... constantes (CORES, SPACING, etc.)
    # ... utilitários puros (rgba_cor, icon_html, etc.)
    # ... aliases shim (re-exports de ui.py)
]
```

**Importante:** zero implementação duplicada. Se uma função existe em `ui.py`, `tema.py` apenas re-exporta. Princípio "Single Source of Truth".

### Migração das páginas — VIRA SUB-SPRINTS

Esta sprint UX-M-02 entrega APENAS `ui.py` + alias shim em `tema.py`. **NÃO migra páginas.**

Migração das 30+ páginas para `from ui import ...` em sub-sprints separadas:

- **UX-M-02.A** — Cluster Documentos (busca, catalogacao, completude, revisor, validacao_arquivos, extracao_tripla, grafo_obsidian).
- **UX-M-02.B** — Cluster Finanças (extrato, contas, pagamentos, projecoes).
- **UX-M-02.C** — Cluster Análise + Metas + Inbox + Sistema (categorias, analise_avancada, irpf, metas, inbox, skills_d7).
- **UX-M-02.D** — Cluster Bem-estar (12 páginas be_*).

## Validação DEPOIS

```bash
# ui.py existe
test -f src/dashboard/componentes/ui.py && echo "OK"

# 9 funções migradas
python -c "from src.dashboard.componentes.ui import (
    page_header, topbar_actions, card_html, callout_html,
    chip_html, hero_titulo_html, subtitulo_secao_html,
    label_uppercase_html, progress_inline_html, metric_semantic_html,
    card_sidebar_html, kpi_card, data_row, group_card
)
print('Imports OK')"

# tema.py compat preservada (páginas existentes não quebram)
python -c "from src.dashboard.tema import (
    callout_html, card_html, hero_titulo_html, chip_html
)
print('Aliases shim OK')"

# Lint, smoke, tests
make lint && make smoke && pytest tests/ -q
```

## Proof-of-work

```bash
# Restart dashboard
pkill -f "streamlit run" 2>/dev/null || true
make dashboard &
sleep 5

# Validar visualmente: 5 páginas-amostra sem regressão
# - Visão Geral, Busca Global, Catalogação, Contas, Projeções
# Esperado: layouts idênticos ao commit 2817706 (baseline pós-revert).

# Página piloto (escolher 1 fácil) migrada para ui.py
# - Edit em UMA página (ex: catalogacao.py): trocar `from tema import card_html`
#   por `from componentes.ui import card_html`. Validar visualmente.
```

## Critério de aceitação

1. `src/dashboard/componentes/ui.py` existe com docstring + lista de imports canônicos.
2. 9 funções migradas (`card_html`, `callout_html`, `chip_html`, `hero_titulo_html`, `subtitulo_secao_html`, `label_uppercase_html`, `progress_inline_html`, `metric_semantic_html`, `card_sidebar_html`).
3. 3 funções novas adicionadas (`kpi_card`, `data_row`, `group_card`) com docstrings + exemplos.
4. 2 re-exports (`page_header`, `topbar_actions`) funcionam.
5. `tema.py` mantém aliases shim — todos os 30+ imports atuais de `tema.py` continuam funcionando.
6. Sub-sprints UX-M-02.A..D existem em `backlog/`.
7. Lint, smoke, tests verdes.
8. Validação visual: 5 páginas-amostra sem regressão.

## Não-objetivos (escopo fechado)

- NÃO migrar páginas (sub-sprints A..D fazem isso).
- NÃO criar CSS dos componentes novos (UX-M-03 faz).
- NÃO mudar assinatura das 9 funções migradas — preservar 100% compat.
- NÃO mexer em `widgets.py` específicos da Visão Geral (são widgets, não componentes universais).
- NÃO mexer em `instalar_fix_sidebar_padding` (UX-M-04).

## Referência

- `src/dashboard/tema.py` linhas 215, 242, 275, 310, 326, 431, 475, 513, 566 — 9 funções a migrar.
- `src/dashboard/componentes/page_header.py` — re-export.
- `src/dashboard/componentes/topbar_actions.py` — re-export.
- UX-M-01 (depende) — tokens CSS centralizados.
- UX-M-03 (bloqueia) — CSS escopado dos componentes.
- UX-M-02.A..D (bloqueia) — sub-sprints de migração.

## Dúvidas que NÃO precisam ser perguntadas

- "Devo recriar `page_header()`?" Não — re-exportar de `page_header.py`.
- "tema.py vai quebrar?" Não — aliases shim mantêm compat 100%.
- "Devo migrar páginas nesta sprint?" Não — sub-sprints A..D fazem.
- "E `visao_geral_widgets.py`?" Fora de escopo (widgets de página, não componentes universais).
- "Renomear `chip_html` para `chip()`?" Não — manter compat com 30 imports atuais.

*"Um botão. Em um lugar. Para todas as páginas." — princípio da Onda M*
