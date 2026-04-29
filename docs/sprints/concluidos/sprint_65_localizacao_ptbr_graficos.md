---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 65
  title: "Localização PT-BR dos gráficos Plotly (meses, moeda, separador decimal)"
  touches:
    - path: src/dashboard/theme.py
      reason: "helper aplicar_locale_ptbr em todos os gráficos"
    - path: src/dashboard/paginas/visao_geral.py
      reason: "gráfico Receita vs Despesa mostra 'Nov 2025', 'Apr 2026' em inglês"
    - path: src/dashboard/paginas/categorias.py
      reason: "gráfico de evolução também"
    - path: src/dashboard/paginas/projecoes.py
      reason: "eixo x em inglês"
    - path: src/dashboard/paginas/grafo_obsidian.py
      reason: "bar charts com locale"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_locale.py -v"
      timeout: 30
  acceptance_criteria:
    - "Meses em português: 'Nov 2025' → 'Nov 2025' (abreviado PT-BR) ou 'Nov/25'"
    - "Meses completos quando aplicável: 'Abril 2026' em vez de 'April 2026'"
    - "Separador decimal vírgula (R$ 1.463,35), não ponto"
    - "Moeda formatada 'R$ ' com espaço"
    - "Helper aplicar_locale_ptbr(fig) único reutilizado"
  proof_of_work_esperado: |
    # Screenshot Visão Geral com eixo x em PT-BR
```

---

# Sprint 65 — Localização PT-BR

**Status:** BACKLOG
**Prioridade:** P3
**Issue:** AUDIT-2026-04-21-UX-10

## Problema

Gráficos Plotly usam locale padrão en-US: "Nov 2025", "Apr 2026" (abreviação em inglês). Casal é brasileiro, dashboard é PT-BR — inconsistência.

## Implementação

`src/dashboard/theme.py`:

```python
def aplicar_locale_ptbr(fig):
    fig.update_layout(
        xaxis=dict(
            tickformat="%b %Y",
            tickvals=None,  # força re-render
        ),
        separators=",.",  # vírgula decimal, ponto milhar
    )
    fig.update_xaxes(tickfont=dict(family="monospace"))
    # Plotly não tem locale PT-BR nativo; usar tickmode="array" com ticktext PT-BR
    ...
    return fig
```

Ou: passar `ticktext=["Nov/25","Dez/25","Jan/26","Fev/26","Mar/26","Abr/26"]` explicitamente.

## Evidências Obrigatórias

- [ ] Screenshot gráfico com meses PT-BR
- [ ] Separador decimal correto

---

*"Idioma é parte da experiência." — princípio de UX local*
