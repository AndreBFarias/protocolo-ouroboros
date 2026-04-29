---
concluida_em: 2026-04-21
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 61
  title: "Projeções com contexto explícito: explicar média histórica vs mês atual"
  touches:
    - path: src/dashboard/paginas/projecoes.py
      reason: "exibe 'ritmo atual R$ 92,53' sem explicar que é média histórica"
    - path: src/projections/scenarios.py
      reason: "calcular também janelas (últimos 3/6/12 meses) para dar contexto"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_projecoes.py -v"
      timeout: 60
  acceptance_criteria:
    - "Página Projeções mostra 3 ritmos: (a) média histórica completa, (b) últimos 12 meses, (c) últimos 3 meses"
    - "Texto explicativo: 'Ritmo = saldo médio mensal; 12m mostra tendência recente; 3m mostra tendência imediata'"
    - "Quando mês atual aparece na sidebar com saldo R$ X, Projeções tem callout 'Mês atual R$ X (não incluído na projeção, é snapshot incompleto se não é último dia)'"
    - "Gráfico 12 meses mostra linhas separadas dos 3 cenários"
    - "Acentuação PT-BR correta em todos os textos novos"
  proof_of_work_esperado: |
    # Abrir dashboard, aba Projeções:
    # 1. Confirmar 3 cartões de ritmo
    # 2. Callout do mês atual
    # Screenshot via skill validacao-visual
```

---

# Sprint 61 — Projeções com contexto

**Status:** BACKLOG
**Prioridade:** P2
**Issue:** AUDIT-2026-04-21-UX-5

## Problema

Auditoria: aba Projeções mostra "Ritmo Atual R$ 92,53/mês, Reserva em 292 meses" enquanto sidebar mostra saldo R$ 6.969,23 do mês corrente. Usuário fica confuso: se ritmo é R$ 92, como o mês atual tem 6969?

Raiz: "ritmo atual" é média histórica (inclui meses de receita baixa). Mês atual é saldo de abril/2026 parcial. Sem explicar, parece contraditório.

## Implementação

`src/projections/scenarios.py`:

```python
def calcular_ritmos(transacoes: list[dict]) -> dict:
    return {
        "historico": media_saldo_mensal(transacoes, janela=None),
        "12_meses": media_saldo_mensal(transacoes, janela=12),
        "3_meses": media_saldo_mensal(transacoes, janela=3),
    }
```

`src/dashboard/paginas/projecoes.py`:

```python
ritmos = calcular_ritmos(dados)
col1, col2, col3 = st.columns(3)
col1.metric("Ritmo histórico", f"R$ {ritmos['historico']:,.2f}")
col2.metric("Ritmo 12 meses", f"R$ {ritmos['12_meses']:,.2f}")
col3.metric("Ritmo 3 meses", f"R$ {ritmos['3_meses']:,.2f}")

st.info(
    "Ritmo = saldo médio mensal observado. "
    "12m e 3m mostram tendências mais recentes. "
    "Mês corrente não é incluído na projeção (pode estar incompleto)."
)
```

## Evidências Obrigatórias

- [ ] Screenshot com 3 cartões
- [ ] Callout explicativo visível

---

*"Contexto transforma número em informação." — princípio estatístico*
