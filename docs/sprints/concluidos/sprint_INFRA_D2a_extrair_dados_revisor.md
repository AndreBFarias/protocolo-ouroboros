---
concluida_em: 2026-04-27
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: INFRA-D2a
  title: "Extrair listar_pendencias_revisao para src/dashboard/dados_revisor.py"
  prioridade: P3
  estimativa: ~30min
  origem: "ressalva da Sprint D2 -- src/dashboard/dados.py cresceu para 976L (limite 800L)"
  touches:
    - path: src/dashboard/dados.py
      reason: "remover listar_pendencias_revisao + helpers privados desta sprint (-140L)"
    - path: src/dashboard/dados_revisor.py
      reason: "novo arquivo com a função extraida"
    - path: src/dashboard/paginas/revisor.py
      reason: "atualizar import"
    - path: tests/test_revisor.py
      reason: "atualizar import nos mocks"
  forbidden:
    - "Mudar comportamento da função -- so mover"
    - "Quebrar test_revisor.py"
  tests:
    - cmd: "make lint"
    - cmd: ".venv/bin/pytest tests/test_revisor.py tests/test_dashboard_app.py -v"
    - cmd: "make smoke"
  acceptance_criteria:
    - "src/dashboard/dados.py volta para <= 836L (estado pre-D2)"
    - "src/dashboard/dados_revisor.py existe com a função listar_pendencias_revisao + helpers privados (~150L)"
    - "Testes da Sprint D2 continuam passando sem mudanca de comportamento"
    - "refactor puro -- zero linhas de lógica nova"
  proof_of_work_esperado: |
    wc -l src/dashboard/dados.py
    # Antes: 976L
    # Depois: 836L (recupera o pre-D2)
    
    .venv/bin/pytest tests/test_revisor.py -v
    # 24 passed
```

---

# Sprint INFRA-D2a -- Extrair dados_revisor

**Status:** CONCLUÍDA (2026-04-27, fechamento pós-INFRA-ACCENT-FIX)

## Resultado

| Métrica | Antes | Depois |
|---|---|---|
| `wc -l src/dashboard/dados.py` | 945L | **830L** (atende `<=836L` do estado pré-D2) |
| `wc -l src/dashboard/dados_revisor.py` | inexistente | **147L** |
| `pytest tests/test_revisor.py tests/test_dashboard_revisor.py tests/test_dashboard_app.py` | 57 passed | **57 passed** |
| Suite full | 1.884 passed | **1.884 passed** (zero regressão) |
| `make lint` | exit 0 (pós-INFRA-ACCENT-FIX) | **exit 0** |
| `make smoke` | 8/8 + 23/23 | **8/8 + 23/23** |

## Refactor aplicado

- **Movido para `dados_revisor.py`**: função `listar_pendencias_revisao` (126L) + constantes `CAMINHO_RAW_CLASSIFICAR` e `CAMINHO_RAW_CONFERIR`.
- **Mantido em `dados.py`**: `CAMINHO_REVISAO_HUMANA` (usado por `revisor.py` e patcheado em `tests/test_dashboard_revisor.py:195` via `d.CAMINHO_REVISAO_HUMANA = ...`).
- **Re-export no fim de `dados.py`**: `from src.dashboard.dados_revisor import (CAMINHO_RAW_CLASSIFICAR, CAMINHO_RAW_CONFERIR, listar_pendencias_revisao)` + `__all__` explícito. Preserva o monkeypatch `setattr(d, "listar_pendencias_revisao", _stub)` em `test_dashboard_revisor.py:223`.

## Armadilha resolvida

`tests/test_dashboard_revisor.py:223` faz `monkeypatch.setattr(d, "listar_pendencias_revisao", _stub)` onde `d` é `dashboard.dados`. Sem o re-export, esse patch quebraria. O re-export torna o atributo presente em ambos os namespaces (`dados` e `dados_revisor`), e como `revisor.py` continua importando de `dados`, o patch externo continua funcionando idêntico ao pré-refactor.

**Origem:** Ressalva conhecida da Sprint D2. `src/dashboard/dados.py` cresceu de 836L para 976L (+140L da nova função `listar_pendencias_revisao` e helpers privados). CLAUDE.md regra 6 limita a 800L por arquivo (exceção: config/, testes/). 836L ja era violacao herdada -- somar 140L piorou.

## Motivação

refactor puro: extrair a lógica de listagem de pendencias para arquivo dedicado, mantendo simetria com outros modulos de dados (`src/dashboard/dados.py` continua hospedando `carregar_documentos_grafo`, `buscar_global` etc -- mas a lógica do revisor merece arquivo próprio). 

Beneficios:
- Limite de 800L respeitado novamente.
- `dados_revisor.py` fica facil de localizar (responsabilidade única).
- Testes do revisor podem importar diretamente sem puxar todo `dados.py`.

## Escopo

### Fase 1 (10min)
Identificar funções a mover:
- `listar_pendencias_revisao` (publica, ~80L)
- helpers privados que so essa função usa (~60L)

### Fase 2 (15min)
Criar `src/dashboard/dados_revisor.py` com as funções movidas. Imports relativos preservados.

### Fase 3 (5min)
Atualizar imports em `src/dashboard/paginas/revisor.py` e `tests/test_revisor.py`.

## Armadilhas

- **Imports circulares:** se `dados_revisor.py` precisar de algo de `dados.py`, importar localmente dentro da função para evitar ciclo.
- **Testes mockam dados:** verificar se `tests/test_revisor.py` patches algum nome de `dados.py` -- pode precisar redirecionar para `dados_revisor`.

## Dependências

- Sprint D2 ja em main (commit `b3026a7`).
- refactor seguro a qualquer momento.

---

*"Casa pequena não cabe tudo; arrume o quintal." -- principio do limite-respeitado*
