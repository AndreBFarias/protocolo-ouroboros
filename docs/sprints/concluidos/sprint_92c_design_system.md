---
concluida_em: 2026-04-24
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 92c
  title: "Design system: CSS vars + componentes canônicos + Feather icons"
  depends_on:
    - sprint_id: 92a
    - sprint_id: 92b
  touches:
    - path: src/dashboard/tema.py
      reason: "CSS vars; novos helpers callout_html/progress_inline_html/metric_semantic_html/icon_html/chip_html/breadcrumb_drilldown_html"
    - path: src/dashboard/componentes/icons.py
      reason: "novo módulo com 11 SVGs Feather inline"
    - path: src/dashboard/paginas/*.py
      reason: "migrar chamadas ad-hoc para helpers canônicos (grep <div style= deve cair de ~50 para <=10)"
    - path: tests/test_dashboard_tema.py
      reason: "teste helpers novos: contraste, render HTML, SVG"
    - path: docs/ux/design_tokens.md
      reason: "atualizar com CSS vars publicadas"
  forbidden:
    - "Adicionar dependências runtime novas (Feather é SVG inline, sem CDN)"
    - "Mudar semântica de cores da paleta Dracula"
    - "Tocar schema do grafo (N-para-N inviolável)"
  tests:
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "make lint"
    - cmd: "make smoke"
  acceptance_criteria:
    - "callout_html substitui 100% dos st.warning/st.info/st.success"
    - "hero_titulo_html aplicado em 100% das 13 abas (um por cluster + um por aba)"
    - "progress_inline_html substitui st.progress em Metas"
    - "metric_semantic_html substitui st.metric em Projeções e Pagamentos"
    - "icon_html('search', 16) no input da Busca Global; 'check-circle' e 'alert-triangle' no Extrato coluna Doc?"
    - "CSS vars publicadas em tema.py::css_global: --color-*, --spacing-*, --font-*"
    - "grep -rn '<div style=' src/dashboard/paginas/ retorna <=10 matches (hoje ~50)"
    - "Screenshots antes/depois do Extrato (lupa, check-circle), Metas (progress inline), Projeções (metric colorido) em docs/screenshots/sprint_92c_*"
```

---

# Sprint 92c — design system implementado

**Status:** BACKLOG (criada pela Sprint 92 audit)
**Prioridade:** P1 (consolidação estrutural, baixo risco técnico)
**Dependências:** Sprint 92a + 92b concluídas
**Origem:** `docs/ux/audit_2026-04-23.md` §8 (Sprint 92c)

## Entregas

### C.1 CSS vars em `tema.py::css_global`

```css
:root {
    --color-fundo: #282a36;
    --color-card-fundo: #44475a;
    --color-texto: #f8f8f2;
    --color-texto-sec: #6272a4;
    --color-positivo: #50fa7b;
    --color-negativo: #ff5555;
    --color-alerta: #ffb86c;
    --color-destaque: #bd93f9;
    --color-neutro: #8be9fd;
    --color-info: #f1fa8c;
    --color-superfluo: #ff79c6;
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    --spacing-xxl: 48px;
    --font-min: 13px;
    --font-label: 13px;
    --font-corpo: 15px;
    --font-subtitulo: 18px;
    --font-titulo: 22px;
    --font-hero: 28px;
}
```

Todos os helpers HTML passam a usar `var(--...)` em vez de f-string com hex.

### C.2 Componentes canônicos novos (em `tema.py`)

```python
def callout_html(tipo: Literal["info","warning","error","success"], mensagem: str, titulo: str | None = None) -> str:
    ...

def progress_inline_html(pct: float, cor: str | None = None, label: str | None = None) -> str:
    ...

def metric_semantic_html(label: str, valor: str, delta: float | None = None, cor: str | None = None) -> str:
    ...

def icon_html(nome_feather: str, tamanho: int = 16, cor: str | None = None) -> str:
    ...

def chip_html(texto: str, cor: str | None = None, clicavel: bool = True) -> str:
    ...

def breadcrumb_drilldown_html(filtros: dict[str, str]) -> str:
    ...
```

### C.3 Ícones Feather SVG inline em `src/dashboard/componentes/icons.py`

11 SVGs listados no `docs/ux/design_tokens.md` §4. Cada um como string template com placeholder para cor (`currentColor` default).

Exemplo:
```python
SEARCH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/>'
    '</svg>'
)
```

### C.4 Migração das páginas

- `busca.py`: input com `icon_html("search", 16)` à esquerda.
- `extrato.py`: coluna "Doc?" com `icon_html("check-circle")` / `icon_html("alert-triangle")`.
- `completude.py`, `contas.py`, `pagamentos.py`: `st.warning(...)` -> `st.markdown(callout_html("warning", ...))`.
- `visao_geral.py`: Saúde financeira usa `progress_inline_html`.
- `metas.py`: progress no card (já iniciado em 92a.9, aqui consolida).
- `projecoes.py`, `pagamentos.py`: `st.metric` -> `metric_semantic_html`.
- `analise_avancada.py`: inalterado (usa Plotly nativo).
- `grafo_obsidian.py`: `chip_html(tipo, cor)` para os tipos do multiselect.
- `extrato.py`: `breadcrumb_drilldown_html(filtros)` em vez de loop manual.

### C.5 Remoção de hex hardcoded

- Grep `'#[0-9a-fA-F]{6}'` em `src/dashboard/paginas/` deve retornar apenas em comentários ou em strings de `customdata`/`hovertemplate` do Plotly (quando CSS var não funciona em JSON).
- Alvo: <= 5 ocorrências (hoje ~30).

## Proof-of-work

- 4 screenshots antes/depois (Extrato com ícones, Metas com progress, Projeções com metric colorido, Completude com callout).
- `grep -rn "st.warning\|st.info\|st.success" src/dashboard/paginas/ | wc -l` retorna 0 (ou apenas em fallbacks de graceful degradation que são aceitos).
- `grep -rn '<div style=' src/dashboard/paginas/ | wc -l` <= 10.
- Testes unitários de cada helper novo (callout, progress, metric, icon, chip, breadcrumb).

## Armadilhas

- **CSS vars não funcionam em JSON inline do Plotly.** Mantém hex dentro de `LAYOUT_PLOTLY["font"]["color"]`. CSS vars são apenas para HTML renderizado pelo Streamlit.
- **`st.markdown(unsafe_allow_html=True)` com SVG pode ser bloqueado por configurações strict de sanitização.** Streamlit default permite SVG inline — testar em ambiente de CI.
- **Icons Feather licença MIT** — adicionar NOTICE em `docs/licenses/feather.md` com URL do repo e SHA da versão usada.

---

*"O design system não é invisível quando funciona; é consistente." -- princípio de coerência de produto*
