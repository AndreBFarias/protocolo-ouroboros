## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 62
  title: "Responsividade: cards e gráficos não quebram em viewport <1200px"
  touches:
    - path: src/dashboard/paginas/visao_geral.py
      reason: "cards 'Maior gasto R$ 1.463,35' cortados em 900px"
    - path: src/dashboard/components/card.py
      reason: "reutilizável com breakpoints"
    - path: src/dashboard/theme.py
      reason: "tokens de tipografia que encolhem em <1200px"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_components.py -v"
      timeout: 60
  acceptance_criteria:
    - "Em viewport 900×700, cards de KPI quebram linha em grid 2×2 (não 3×1)"
    - "Valores monetários nunca são truncados — fonte diminui via clamp(14px, 2vw, 20px)"
    - "Legendas de gráficos não sobrepõem título do gráfico"
    - "Scroll horizontal de tabs com botões visíveis em qualquer viewport"
    - "Proof via Playwright screenshot em 3 viewports: 1600, 1200, 900"
  proof_of_work_esperado: |
    # Playwright em 3 larguras:
    # 1600x1000, 1200x800, 900x700
    # cada uma: screenshot Visão Geral
    # esperado: valor R$ 1.463,35 legível nas 3
```

---

# Sprint 62 — Responsividade dos cards

**Status:** BACKLOG
**Prioridade:** P2
**Issue:** AUDIT-2026-04-21-UX-6

## Problema

Em viewport 900×700, auditoria encontrou:
- Card "Maior gasto: Impostos" cortado: mostra "R$ 1.463" (falta ",35")
- Legenda "Receita Despesa Saldo" sobrepõe título "Receita vs Despesa"
- Tabs "Catalogação" e "Busca Global" somem sem scroll visível

## Implementação

### Fase 1 — Grid adaptativo

`src/dashboard/paginas/visao_geral.py`:

```python
# Antes:
col1, col2, col3 = st.columns(3)

# Depois:
viewport = st.session_state.get("viewport_width", 1600)
if viewport < 1000:
    row1 = st.columns(2)
    row2 = st.columns(2)  # 2x2
else:
    row1 = st.columns(3)  # 3x1
```

Ou usar CSS via `st.markdown("<style>...</style>", unsafe_allow_html=True)` com `@media` queries nas classes custom dos cards.

### Fase 2 — Tipografia fluida

`src/dashboard/theme.py`:

```python
TOKEN_TIPO_KPI_VALOR = "clamp(14px, 2vw, 22px)"
TOKEN_TIPO_KPI_LABEL = "clamp(10px, 1.2vw, 14px)"
```

### Fase 3 — Testes visuais

Playwright + validacao-visual em 3 larguras. <!-- noqa: accent -->


## Evidências Obrigatórias

- [ ] Screenshot 1600×1000: cards grid 3×1
- [ ] Screenshot 1200×800: grid 2×2 ou 3×1 sem truncamento
- [ ] Screenshot 900×700: grid 2×2 com valores legíveis

---

*"Responsivo é respeito ao usuário móvel." — princípio web*
