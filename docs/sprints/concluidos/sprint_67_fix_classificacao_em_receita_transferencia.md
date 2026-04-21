## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 67
  title: "Fix: classificacao (Obrigatório/Supérfluo/Questionável) não deve popular em Receita/Transferência Interna"
  touches:
    - path: src/transform/categorizer.py
      reason: "popula classificacao em linhas que não são Despesa/Imposto"
    - path: src/transform/normalizer.py
      reason: "eventual sink de classificacao residual"
    - path: tests/test_categorizer.py
      reason: "testes regressivos"
  n_to_n_pairs: []
  forbidden:
    - "Remover coluna classificacao do XLSX"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_categorizer.py -v"
      timeout: 60
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py --strict"
      timeout: 30
  acceptance_criteria:
    - "Zero linhas com tipo=Receita ou tipo=Transferência Interna têm classificacao preenchida (classificacao deve ser NaN/None nessas)"
    - "classificacao continua preenchida para 100% das linhas tipo=Despesa ou tipo=Imposto"
    - "Contrato smoke 'classificacao_soma_despesa' passa (soma classificações por mês == soma despesa+imposto do mês)"
    - "Sprint 55 + 67 aplicadas: Receitas do XLSX tem classificacao NaN em 100% das linhas"
  proof_of_work_esperado: |
    .venv/bin/python <<'EOF'
    import pandas as pd
    df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
    bad = df[(df['tipo'].isin(['Receita','Transferência Interna'])) & (df['classificacao'].notna())]
    assert len(bad) == 0, f"{len(bad)} linhas com classificacao em Receita/TI"
    despesas_sem_class = df[(df['tipo'].isin(['Despesa','Imposto'])) & (df['classificacao'].isna())]
    assert len(despesas_sem_class) == 0, f"{len(despesas_sem_class)} Despesas sem classificacao"
    print(f"OK: Receita/TI com classif={len(bad)}, Despesas sem classif={len(despesas_sem_class)}")
    EOF
    .venv/bin/python scripts/smoke_aritmetico.py --strict
    echo "exit=$?"
```

---

# Sprint 67 — Fix classificação só em Despesa/Imposto

**Status:** BACKLOG
**Prioridade:** P0
**Dependências:** Sprint 55 (fix tipo) e 56 (smoke) aplicadas
**Issue:** SMOKE-M56-2

## Problema

Sprint 56 (smoke aritmético) detectou: 128 linhas com `tipo=Receita` têm `classificacao` preenchida (Obrigatório/Questionável/Supérfluo). 44 linhas com `tipo=Transferência Interna` idem. Schema do projeto (CLAUDE.md §Schema) declara `N/A` ou null para não-despesas.

Evidência do smoke em observador:
```
classificacao_soma_despesa: 2019-10: despesa R$ 117.26 ≠ classificação R$ 4,730.35
```

Raiz provável: `src/transform/categorizer.py` aplica regras de classificação sem checar `tipo` da transação antes.

## Implementação

### Fase 1 — Guardar clausura por tipo

`src/transform/categorizer.py`:

```python
def categorizar(transacao: dict, categorias: dict, overrides: dict) -> dict:
    # ... regras de categoria (sempre aplicar)
    
    # Classificação: só aplicar para Despesa/Imposto
    if transacao.get("tipo") in ("Despesa", "Imposto"):
        transacao["classificacao"] = _inferir_classificacao(...)
    else:
        transacao["classificacao"] = None  # explicit
```

### Fase 2 — Reprocessar XLSX

`./run.sh --tudo`

### Fase 3 — Testes

```python
def test_receita_nao_recebe_classificacao():
    tx = {"tipo": "Receita", "local": "SALARIO", "valor": 7000}
    categorizado = categorizar(tx, {}, {})
    assert categorizado["classificacao"] is None

def test_transferencia_interna_nao_recebe_classificacao():
    tx = {"tipo": "Transferência Interna", "local": "Pagamento fatura Nubank", "valor": 500}
    categorizado = categorizar(tx, {}, {})
    assert categorizado["classificacao"] is None

def test_despesa_recebe_classificacao():
    tx = {"tipo": "Despesa", "local": "NEOENERGIA", "valor": 400}
    categorizado = categorizar(tx, {}, {})
    assert categorizado["classificacao"] in ("Obrigatório", "Questionável", "Supérfluo")
```

## Armadilhas Conhecidas

| A67-1 | Overrides em `mappings/overrides.yaml` podem forçar classificação | Respeitar override se explícito, mas log warning se tipo != Despesa |
| A67-2 | Pipeline roda categorizer antes do fix do tipo (Sprint 55) | Ordem: normalizar (tipo) → categorizar (categoria + classificação condicional) |

## Evidências Obrigatórias

- [ ] Smoke `--strict` passa contrato `classificacao_soma_despesa`
- [ ] Zero linhas Receita/TI com classificação
- [ ] Testes regressivos verdes

---

*"Schema claro é rigor técnico." — meta-regra 1*
