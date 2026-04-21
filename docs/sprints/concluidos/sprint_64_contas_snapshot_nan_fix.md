## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 64
  title: "Contas: exibir aviso de snapshot histórico e tratar NaN → traço"
  touches:
    - path: src/dashboard/paginas/contas.py
      reason: "tabela mostra 'nan' literal; falta aviso de snapshot 2023"
    - path: src/dashboard/dados.py
      reason: "helper para renderizar DataFrame com NaN → '—'"
    - path: tests/test_dashboard_contas.py
      reason: "teste de renderização"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_dashboard_contas.py -v"
      timeout: 30
  acceptance_criteria:
    - "Aba Contas mostra banner amarelo: 'Dados congelados desde 2023 — snapshot histórico não é atualizado automaticamente'"
    - "Coluna Obs nunca exibe 'nan' — troca por '—' ou string vazia"
    - "Dívidas Ativas, Inventário e Prazos têm banner idêntico (todas marcadas como snapshot)"
    - "Helper renderizar_dataframe aceita kwarg na_rep='—' e é usado em todas as tabelas do dashboard"
  proof_of_work_esperado: |
    # Screenshot aba Contas mostrando banner + sem 'nan' visível
    # validador-sprint via skill validacao-visual
```

---

# Sprint 64 — Contas/snapshot/NaN

**Status:** BACKLOG
**Prioridade:** P2
**Issue:** AUDIT-2026-04-21-UX-8 + UX-9

## Problema

Aba Contas renderiza `nan` literal na coluna Obs (pd.NaN serializado como string). E CLAUDE.md diz que linha 1 do XLSX tem "Snapshot histórico 2023 — dados não são atualizados" mas dashboard não exibe.

## Implementação

### Fase 1 — Helper renderizar_dataframe

`src/dashboard/dados.py`:

```python
def renderizar_dataframe(df: pd.DataFrame, na_rep: str = "—") -> pd.DataFrame:
    """Substitui NaN por na_rep antes de passar pro st.dataframe."""
    return df.fillna(na_rep)
```

Usar em `contas.py`, `extrato.py`, `categorias.py` onde aplicável.

### Fase 2 — Banner

```python
st.warning(
    "Dados congelados desde 2023 — snapshot histórico não é atualizado automaticamente. "
    "Para atualizar, edite manualmente `data/output/controle_bordo_2026.xlsx` "
    "nas abas dividas_ativas, inventario e prazos."
)
```

No topo das 3 seções da aba Contas.

## Evidências Obrigatórias

- [ ] Banner visível nas 3 seções
- [ ] Zero 'nan' literal em qualquer célula
- [ ] Helper reutilizado

---

*"NaN é vazio — mostre vazio ao usuário." — princípio de apresentação*
