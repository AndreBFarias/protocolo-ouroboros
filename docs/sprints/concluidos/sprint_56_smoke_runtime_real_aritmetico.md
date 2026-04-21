## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 56
  title: "Smoke runtime-real aritmético: contrato global de receita/despesa"
  touches:
    - path: scripts/smoke_aritmetico.py
      reason: "novo script que valida contratos globais do XLSX após pipeline"
    - path: Makefile
      reason: "target 'make smoke' inclui scripts/smoke_aritmetico.py"
    - path: scripts/finish_sprint.sh
      reason: "gauntlet invoca smoke_aritmetico no final"
    - path: tests/test_smoke_aritmetico.py
      reason: "teste que roda o próprio smoke e valida exit code"
  n_to_n_pairs:
    - ["Makefile:smoke", "scripts/smoke_aritmetico.py"]
    - ["scripts/finish_sprint.sh", "scripts/smoke_aritmetico.py"]
  forbidden:
    - "Trocar o smoke existente (./run.sh --check) — eles são complementares"
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/python scripts/smoke_aritmetico.py"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_smoke_aritmetico.py -v"
      timeout: 60
  acceptance_criteria:
    - "scripts/smoke_aritmetico.py existe e aceita flag --strict"
    - "Smoke valida 8 contratos: receita por mês não exagera salário, despesa não negativa, transferências internas batem origem/destino, nenhum IOF/Juros/Multa como Receita, soma classificações = despesa total, categoria nunca nula, tipo sempre em conjunto válido, banco_origem válido"
    - "Exit 0 quando XLSX está saudável; exit 1 com descrição literal do contrato violado"
    - "make smoke invoca scripts/smoke_aritmetico.py depois de ./run.sh --check"
    - "scripts/finish_sprint.sh invoca smoke_aritmetico antes de declarar sprint concluída"
  proof_of_work_esperado: |
    make smoke
    # Esperado: "[SMOKE-ARIT] 8/8 contratos OK"
    .venv/bin/python scripts/smoke_aritmetico.py --strict
    echo "exit=$?"
```

---

# Sprint 56 — Smoke runtime-real aritmético

**Status:** CONCLUÍDA
**Prioridade:** P0
**Dependências:** Sprint 55 (precisa do fix aplicado para smoke passar)
**Issue:** AUDIT-2026-04-21-2

## Problema

VALIDATOR_BRIEF.md check #1 ("Runtime real") só referencia `./run.sh --check` (23 checagens de dependências). Não valida **contratos aritméticos** do output. Por isso o BUG #1 (classificador de tipo, Sprint 55) sobreviveu 6 meses sem ser detectado.

## Implementação

`scripts/smoke_aritmetico.py` (novo, ~180 linhas):

```python
"""Smoke aritmético: valida contratos globais do ouroboros_2026.xlsx."""
from __future__ import annotations
import sys
import argparse
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
XLSX = RAIZ / "data" / "output" / "ouroboros_2026.xlsx"

def contrato_receita_nao_exagera_salario(df: pd.DataFrame) -> str | None:
    """Receita de cada mês não pode exceder salário bruto + 40% (reembolso + rendimento)."""
    ...

def contrato_despesa_nao_negativa(df: pd.DataFrame) -> str | None: ...
def contrato_juros_iof_multa_nunca_receita(df: pd.DataFrame) -> str | None: ...
def contrato_transferencias_internas_batem(df: pd.DataFrame) -> str | None: ...
def contrato_classificacao_soma_despesa(df: pd.DataFrame) -> str | None: ...
def contrato_categoria_nunca_nula_em_despesa(df: pd.DataFrame) -> str | None: ...
def contrato_tipo_em_conjunto_valido(df: pd.DataFrame) -> str | None: ...
def contrato_banco_origem_valido(df: pd.DataFrame) -> str | None: ...

CONTRATOS = [
    contrato_receita_nao_exagera_salario,
    contrato_despesa_nao_negativa,
    contrato_juros_iof_multa_nunca_receita,
    contrato_transferencias_internas_batem,
    contrato_classificacao_soma_despesa,
    contrato_categoria_nunca_nula_em_despesa,
    contrato_tipo_em_conjunto_valido,
    contrato_banco_origem_valido,
]

def main() -> int:
    ...
```

### Makefile target

```makefile
smoke: install
	@./run.sh --check
	@.venv/bin/python scripts/smoke_aritmetico.py --strict
```

### finish_sprint.sh

Adicionar antes do `echo "Sprint X concluída"`:

```bash
.venv/bin/python scripts/smoke_aritmetico.py --strict || {
    echo "REPROVADO: smoke aritmético falhou"
    exit 1
}
```

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A56-1 | Contratos rígidos quebram em meses legítimos com bônus/13º | Usar limiar salário × 1.8 no mês de dezembro |
| A56-2 | Smoke falha em repo recém-clonado sem XLSX | Exit 0 com warning se arquivo não existe |
| A56-3 | Executar smoke antes do fix Sprint 55 vai falhar | Documentar que smoke depende de Sprint 55 |

## Evidências Obrigatórias

- [ ] Scripts/smoke_aritmetico.py com 8 contratos e `--strict`
- [ ] `make smoke` exit 0 após Sprint 55 aplicada
- [ ] `scripts/finish_sprint.sh` invoca smoke
- [ ] Teste unitário roda o smoke como subprocess
- [ ] Documentação em VALIDATOR_BRIEF.md check #1 atualizada

---

*"Medir duas vezes, cortar uma." — oficio antigo*
