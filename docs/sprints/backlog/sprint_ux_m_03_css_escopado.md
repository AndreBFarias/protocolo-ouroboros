---
id: UX-M-03
titulo: CSS escopado por componente em css/components/
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-01, UX-M-02]
bloqueia: []
---

# Sprint UX-M-03 — CSS escopado por componente

## Contexto

Após UX-M-02 entregar componentes universais (`ui_canonico.py`), cada componente precisa de seu CSS canônico. Hoje o CSS de elementos repetidos vive espalhado em 17 `_CSS_LOCAL_*` nas páginas, com ~50-300 linhas cada.

## Objetivo

Criar pasta `src/dashboard/css/components/` com **um CSS por componente**. `ui_canonico.py` carrega o CSS automaticamente quando a função correspondente é chamada (cache em sessão para não duplicar). Páginas existentes têm seus `_CSS_LOCAL_*` removidos.

## Hipótese

Cada componente em `ui_canonico.py` (UX-M-02) precisa de ~30-80 linhas CSS estáveis. Centralizar em arquivo dedicado simplifica:
- 1 lugar para mexer em estilo de KPI cards
- 1 lugar para mexer em search bar
- etc.

## Validação ANTES

```bash
# Volume atual de CSS local
wc -l src/dashboard/paginas/*.py | tail -1
# Esperado: linhas totais

grep -rn "_CSS_LOCAL\|<style>" src/dashboard/paginas/ | wc -l
# Esperado: ~17+ ocorrências

# Tokens já centralizados (UX-M-01)?
test -f src/dashboard/css/tokens.css && echo OK || echo FALTA-M01
```

## Spec de implementação

### 1. Criar estrutura `src/dashboard/css/components/`

```
src/dashboard/css/
├── tokens.css                    # criado em UX-M-01
└── components/
    ├── page_header.css
    ├── kpi_card.css
    ├── section_header.css
    ├── group_card.css
    ├── data_row.css
    ├── search_bar.css
    ├── chip_group.css
    └── toolbar.css
```

### 2. Cada CSS de componente — exemplo `kpi_card.css`

```css
.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--sp-4) var(--sp-5);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.kpi-card--purple { border-left: 3px solid var(--accent-purple); }
.kpi-card--cyan { border-left: 3px solid var(--accent-cyan); }
.kpi-card--green { border-left: 3px solid var(--accent-green); }
.kpi-card--yellow { border-left: 3px solid var(--accent-yellow); }
.kpi-card--red { border-left: 3px solid var(--accent-red); }
.kpi-card--orange { border-left: 3px solid var(--accent-orange); }
.kpi-card--pink { border-left: 3px solid var(--accent-pink); }

.kpi-label {
  font-family: var(--ff-mono);
  font-size: var(--fs-label);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.kpi-valor {
  font-family: var(--ff-mono);
  font-size: 28px;
  color: var(--text-primary);
  font-weight: 600;
}

.kpi-sub {
  font-family: var(--ff-mono);
  font-size: var(--fs-mono);
  color: var(--text-muted);
}
```

### 3. Auto-load em `ui_canonico.py`

```python
import streamlit as st
from pathlib import Path
from functools import lru_cache

_CSS_DIR = Path(__file__).resolve().parent.parent / "css" / "components"

@lru_cache(maxsize=None)
def _carregar_css(nome: str) -> str:
    caminho = _CSS_DIR / f"{nome}.css"
    return f"<style>{caminho.read_text(encoding='utf-8')}</style>"


def _emitir_css(nome: str) -> None:
    """Emite CSS do componente uma vez por sessão Streamlit."""
    chave = f"_css_emitido_{nome}"
    if chave not in st.session_state:
        st.markdown(_carregar_css(nome), unsafe_allow_html=True)
        st.session_state[chave] = True


def page_header(titulo, ...):
    _emitir_css("page_header")
    return minificar(...)


def kpi_card(label, ...):
    _emitir_css("kpi_card")
    return minificar(...)
```

### 4. Remover `_CSS_LOCAL_*` das páginas migradas

Para cada página migrada para usar `ui_canonico` (sub-sprints UX-M-02.A..D):
- Remover blocos `_CSS_LOCAL_*` que duplicavam CSS dos componentes.
- Manter CSS específico DA PÁGINA (raros: gráficos plotly, layouts únicos não-genéricos).

## Proof-of-work

```bash
# Após criar todos os CSS:
ls src/dashboard/css/components/ | wc -l
# Esperado: 8 arquivos

# Após remover _CSS_LOCAL_* de N páginas migradas:
grep -rn "_CSS_LOCAL" src/dashboard/paginas/ | wc -l
# Esperado: < 5 (só páginas com layouts realmente únicos)

# Validação visual: 5 páginas-amostra sem regressão
make dashboard
# Comparar antes/depois das 5 páginas piloto.
```

## Critério de aceitação

1. `src/dashboard/css/components/` existe com ≥8 arquivos.
2. `ui_canonico.py` carrega CSS via `_emitir_css(nome)` com cache de sessão.
3. Cada CSS de componente referencia tokens via `var(--xxx)` (sem fallback).
4. ≥10 páginas têm `_CSS_LOCAL_*` REMOVIDO após migração para `ui_canonico`.
5. Lint, smoke, tests verdes.
6. Validação visual: 5 páginas-amostra sem regressão visual.

## Não-objetivos

- NÃO migrar todas as 17 páginas que têm `_CSS_LOCAL_*` — restantes ficam em backlog.
- NÃO mexer em `instalar_fix_sidebar_padding` (isso é UX-M-04).

## Referência

- UX-M-01 (depende de) — tokens CSS.
- UX-M-02 (depende de) — componentes universais.

*"O CSS do botão vive perto do botão." — princípio da Onda M*
