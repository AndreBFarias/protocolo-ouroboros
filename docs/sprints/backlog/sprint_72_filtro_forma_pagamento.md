## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 72
  title: "Filtro Forma de Pagamento no sidebar (Pix/Débito/Crédito/Boleto/Transferência)"
  touches:
    - path: src/dashboard/app.py
      reason: "sidebar: adicionar selectbox embaixo de Granularidade/Mês/Pessoa"
    - path: src/dashboard/dados.py
      reason: "aplicar filtro em carregar_extrato/metricas_mes"
    - path: src/dashboard/paginas/*.py
      reason: "cada página respeita filtro ativo"
    - path: tests/test_dashboard_filtro_forma.py
      reason: "testes regressivos"
  n_to_n_pairs:
    - ["selectbox forma_pagamento", "coluna forma_pagamento do XLSX"]
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_filtro_forma.py -v"
      timeout: 60
  acceptance_criteria:
    - "Sidebar mostra selectbox 'Forma de pagamento' com opções: Todas, Pix, Débito, Crédito, Boleto, Transferência"
    - "Default: Todas"
    - "Ao selecionar 'Crédito', todas as páginas filtram o DataFrame por forma_pagamento=='Crédito'"
    - "Cards KPI (Receita/Despesa/Saldo) da sidebar refletem filtro"
    - "Teste regressivo: total despesa com filtro Crédito <= total despesa sem filtro"
    - "Filtro é combinável com granularidade/mês/pessoa"
  proof_of_work_esperado: |
    # Screenshot sidebar com novo selectbox
    # Screenshot aba Extrato mostrando só transações Crédito após seleção
    # SHA256 dos PNGs
```

---

# Sprint 72 — Filtro forma de pagamento

**Status:** BACKLOG
**Prioridade:** P1
**Dependências:** nenhuma
**Issue:** UX-ANDRE-01

## Problema

Andre pediu: "falta um filtro assim pode ser em baixo da granularidade" — para ver só Pix, só Crédito, só Boleto. Coluna `forma_pagamento` já existe no schema do XLSX.

## Implementação

`src/dashboard/app.py` sidebar:

```python
with st.sidebar:
    # ... filtros existentes (granularidade, mês, pessoa)
    forma_sel = st.selectbox(
        "Forma de pagamento",
        options=["Todas", "Pix", "Débito", "Crédito", "Boleto", "Transferência"],
        key="filtro_forma_pagamento",
    )
    st.session_state["filtro_forma"] = None if forma_sel == "Todas" else forma_sel
```

`src/dashboard/dados.py`:

```python
def carregar_extrato(..., filtro_forma: Optional[str] = None) -> pd.DataFrame:
    df = ...
    if filtro_forma:
        df = df[df["forma_pagamento"] == filtro_forma]
    return df
```

Cada página consome via `st.session_state.get("filtro_forma")`.

## Armadilhas

| A72-1 | Filtro cacheado entre abas via session_state | Usar key única por filtro para cache invalidation |
| A72-2 | Valores do XLSX podem variar (ex: "TED" vs "Transferência") | Canonicalizar via dict normalizacao no carregar_extrato |

## Evidências

- [ ] Filtro funciona em todas as abas
- [ ] KPIs da sidebar refletem filtro
- [ ] Screenshot com sidebar + filtro ativo

---

*"Filtros são lupas sobre os dados." — princípio"*
