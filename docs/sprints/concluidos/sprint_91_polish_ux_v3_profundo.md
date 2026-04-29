---
concluida_em: 2026-04-23
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 91
  title: "Polish UX v3 profundo -- legibilidade, hierarquia e densidade"
  touches:
    - path: src/dashboard/paginas/completude.py
      reason: "heatmap textual com rótulos sobrepostos -- remover texto das células, mostrar só no hover"
    - path: src/dashboard/paginas/pagamentos.py
      reason: "coluna vencimento mostra 'YYYY-MM-DD 00:00:00'; formatar para 'YYYY-MM-DD'"
    - path: src/dashboard/paginas/analise.py
      reason: "sankey com labels cortados à direita; ajustar margem"
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "nós do pyvis exibem hash SHA-256 em vez de nome humano (Sprint 60 deveria cobrir)"
    - path: src/dashboard/tema.py
      reason: "alertas em amarelo pálido destoam do tema Dracula; trocar para variante Dracula accent"
    - path: src/dashboard/app.py
      reason: "cabeçalho da sidebar (logo + título) ocupa ~150px; compactar"
    - path: tests/test_dashboard_*.py
      reason: "regression estática (re.findall) dos novos padrões"
  forbidden:
    - "Alterar lógica de dados (Sprint 91 é puro visual)"
    - "Remover funcionalidade existente em troca de estética"
    - "Mudar paleta global sem fallback graceful"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/ -q"
    - cmd: "skill validacao-visual -- recapturar 7 páginas"
  acceptance_criteria:
    - "Heatmap Completude sem texto dentro das células (tooltip hover mostra '0/N com doc')"
    - "Coluna vencimento Pagamentos formatada como date-only (sem hora zerada)"
    - "Sankey Análise com margin_right >= 120px (labels não cortadas)"
    - "Nós pyvis exibem nome humano (razão social para fornecedor, descrição truncada para item, YYYY-MM para período)"
    - "Alertas Completude em card dark-mode (border accent + fundo #282a36 com tipografia clara)"
    - "Sidebar cabeçalho em no máx 100px vertical (logo 64x64 + título inline)"
    - "Re-validação visual via skill confirma 7 páginas limpas (screenshots em docs/screenshots/sprint_91_YYYY-MM-DD/)"
    - "Baseline mantida ou cresce: 1139 passed -> >=1139 passed"
```

---

# Sprint 91 -- Polish UX v3 profundo

**Status:** BACKLOG
**Prioridade:** P2 (não-bloqueante; afeta percepção de qualidade do produto)
**Dependências:** Sprint 76 + 77 (polish v1 + v2 já estabeleceram FONTE_MIN_ABSOLUTA e helpers)
**Origem:** revisão visual 2026-04-24 após validação da Sprint 86.3-86.9 em volume real

## Problemas concretos (evidência nos screenshots)

### 91.1 -- Heatmap Completude ilegível

`docs/screenshots/sprint_86_2026-04-24/07_completude_v2_pos_fix.png` mostra células do heatmap com rótulos textuais do tipo `/.01/02/1 0/10/01/1 0 01/01/` colados uns nos outros. O Plotly está renderizando `text=` em cada célula mas a densidade temporal (meses em eixo X com 7 anos) não cabe.

**Fix:** em `src/dashboard/paginas/completude.py`, remover `text` do `go.Heatmap` e confiar no hover (`hovertemplate="%{y}<br>%{x}: %{z:.0f}%% com doc<extra></extra>"`). Acceptance: cells sem texto visível; tooltip funcional.

### 91.2 -- Coluna vencimento em Pagamentos com hora zerada

`04_pagamentos_v2_pos_fix.png` mostra `2019-11-04 00:00:00` em todas as linhas da coluna vencimento. Após fix do commit f923764 (coerce para datetime), a coluna virou Timestamp; pandas renderiza por default com hora. Estetica ruim.

**Fix:** antes de passar para `st.dataframe`, formatar: `df["vencimento"] = df["vencimento"].dt.strftime("%Y-%m-%d")`.

### 91.3 -- Sankey Análise com labels cortadas

`05_analise_v2_pos_fix.png` mostra "Impostos", "Farmácia", "Juros/Encargos" à direita do Sankey tocando a borda. `margin_right` default do Plotly é pequeno.

**Fix:** `fig.update_layout(margin=dict(l=40, r=140, t=40, b=40))`.

### 91.4 -- Nós pyvis com hash SHA-256

`06_grafo_obsidian_v2_pos_fix.png` mostra nós com labels tipo `5C277BC27E632...`, `8601415F...`. Sprint 60 previu "labels humanos" mas regressão ou incompleta. Conferir `_label_humano` em `src/dashboard/componentes/grafo_pyvis.py`.

**Fix:** validar fallback atual (`aliases[0] -> razao_social -> nome_canonico truncado`). Se nome_canonico truncado ainda mostra hash, ajustar para mostrar tipo + id curto (`transacao#4575`).

### 91.5 -- Alertas em amarelo destoam do Dracula

`07_completude_v2_pos_fix.png` e `05_analise_v2_pos_fix.png` mostram cards de alerta `st.info` com fundo amarelo pálido. Tema Dracula tem `#44475a` (comment), `#50fa7b` (green), `#f1fa8c` (yellow), `#ff79c6` (pink). Cards atuais usam yellow pálido do Streamlit default, não Dracula yellow.

**Fix:** em `src/dashboard/tema.py`, adicionar CSS override:
```css
[data-testid="stAlert"] {
    background-color: #44475a !important;
    color: #f8f8f2 !important;
    border-left: 4px solid #f1fa8c !important;
}
```

### 91.6 -- Sidebar cabeçalho desproporcional

Todas as páginas mostram ~150px vertical para logo+título na sidebar. Logo é 170x170 com padding. Ocupa espaço que poderia ser filtros.

**Fix:** em `src/dashboard/app.py::_sidebar`, reduzir logo para 64x64 inline ao lado do título (usa helper `logo_sidebar_html` Sprint 76; ajustar `largura_px=64`).

## Proof-of-work

Recapturar 7 páginas via skill `validacao-visual` e comparar:
- `docs/screenshots/sprint_86_2026-04-24/*_v2_pos_fix.png` (antes)
- `docs/screenshots/sprint_91_YYYY-MM-DD/*.png` (depois)

Testes estáticos:
- `tests/test_dashboard_completude.py`: grep `text=` ou `texttemplate=` no módulo completude (não deve aparecer após fix).
- `tests/test_dashboard_pagamentos.py`: grep `dt.strftime` no módulo (deve aparecer).
- `tests/test_dashboard_analise.py`: grep `margin` com `r=1[2-9]` no módulo.

## Armadilhas

- Heatmap sem `text` + hover pode perder a informação "0/1" que hoje aparece. Validar com o André se hover é suficiente.
- `dt.strftime` em coluna não-datetime levanta `AttributeError`. Guard: `if pd.api.types.is_datetime64_any_dtype(df["vencimento"])`.
- CSS override em `[data-testid="stAlert"]` afeta **todos** os st.info/st.warning/st.success do app. Validar no app inteiro que cor não fica ilegível em outros contextos.
- Logo 64x64 fica pequeno demais; testar 72x72 ou 80x80 se 64 parecer pobre.

---

*"Conteúdo sem forma é caos legível só para quem o escreveu." -- princípio de dashboard ético*
