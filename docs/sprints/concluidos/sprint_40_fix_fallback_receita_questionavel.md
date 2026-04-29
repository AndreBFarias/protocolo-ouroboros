---
concluida_em: 2026-04-19
---

## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 40
  title: "Fix: Categorizer fallback não pode classificar Receita/TI/Imposto como Questionável"
  touches:
    - path: src/transform/categorizer.py
      reason: "fallback só marca Questionável se tipo for Despesa (ou indefinido); outros tipos deixam classificação None para _garantir_classificacao resolver"
    - path: tests/test_categorizer.py
      reason: "adicionar cobertura de regressão para Receita/TI/Imposto sem match"
  n_to_n_pairs: []
  forbidden:
    - mappings/categorias.yaml  # não alterar regras para mascarar o bug
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: ".venv/bin/pytest tests/test_categorizer.py -x -q"
      timeout: 60
    - cmd: "./run.sh --tudo"
      timeout: 600
    - cmd: "python -m src.utils.validator"
      timeout: 60
  acceptance_criteria:
    - "Receita sem match NÃO aparece como Questionável no XLSX"
    - "Transferência Interna sem match NÃO aparece como Questionável no XLSX"
    - "Imposto sem match cai em Obrigatório via _garantir_classificacao"
    - "Despesa sem match continua caindo em Questionável (comportamento antigo preservado)"
    - "Testes tests/test_categorizer.py::test_receita_sem_match_cai_em_na passam"
    - "Acentuação PT-BR correta"
    - "Zero emojis"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 40 -- Fix: Categorizer fallback respeita tipo da transação

**Status:** CONCLUÍDA
**Data:** 2026-04-19
**Prioridade:** MEDIA
**Tipo:** Bugfix
**Dependências:** Sprint 30 (testes revelaram o bug)
**Desbloqueia:** Consistência da aba `resumo_mensal` e dos relatórios diagnósticos (Sprint 21)
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `make lint`
- `.venv/bin/pytest tests/test_categorizer.py -v`
- `./run.sh --tudo && python -m src.utils.validator`

### O que NÃO fazer

- NÃO adicionar regex em `categorias.yaml` só pra casar Receita genérica -- mascara o bug
- NÃO remover `_garantir_classificacao` -- continua sendo rede de segurança para todos os tipos
- NÃO mudar o default de Despesa (que deve continuar sendo Questionável)

---

## Problema

Durante a Sprint 30 (escrita de testes mínimos), ficou evidente que o categorizer marcava `Receita` e `Transferência Interna` sem match de regex como classificacao=`"Questionável"` em vez de `"N/A"`.

Reprodução:
```python
from src.transform.categorizer import Categorizer
cat = Categorizer()
t = {"local": "Fonte Obscura XYZ", "tipo": "Receita", "valor": 500, "_descricao_original": "Fonte Obscura XYZ"}
cat.categorizar(t)
assert t["classificacao"] == "N/A"  # falhava antes do fix: vinha "Questionável"
```

Fluxo do bug (pré-fix em `src/transform/categorizer.py:195-199`):

```python
if transacao.get("categoria") is None:
    transacao["categoria"] = "Outros"
    transacao["classificacao"] = "Questionável"   # <-- força Questionável

self._garantir_classificacao(transacao)            # <-- só roda se classificacao é None
```

Como o fallback já setava `"Questionável"`, `_garantir_classificacao` (que corretamente mapeia Receita→N/A, TI→N/A, Imposto→Obrigatório) não era executado.

Impacto: aba `resumo_mensal` contabilizava receitas sem categoria explícita como gastos questionáveis, distorcendo o `total_questionavel`. Impactava também relatórios mensais descritivos.

Na prática o impacto era pequeno porque a maior parte das receitas bate em regras do `categorias.yaml` (SALARIO, PIX RECEBIDO, etc). Mas deixar o bug aberto quebrava a promessa da "verdade nos dados" (Sprint 23).

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| Categorizer | `src/transform/categorizer.py:154-200` | Aplica overrides + regex + fallback |
| Garantir classificação | `src/transform/categorizer.py:202-215` | Rede de segurança por tipo (Receita→N/A, TI→N/A, Imposto→Obrigatório, default→Questionável) |
| Testes do categorizer | `tests/test_categorizer.py` | 6 casos existentes (Sprint 30) |

---

## Implementação

### Fase 1: fallback condicional no tipo

**Arquivo:** `src/transform/categorizer.py:195-198`

Antes:
```python
if transacao.get("categoria") is None:
    transacao["categoria"] = "Outros"
    transacao["classificacao"] = "Questionável"
```

Depois:
```python
if transacao.get("categoria") is None:
    transacao["categoria"] = "Outros"
    if transacao.get("tipo") in ("Despesa", None):
        transacao["classificacao"] = "Questionável"
```

Racional: `"Questionável"` só faz sentido como rótulo de DESPESA. Para Receita/TI/Imposto, deixa `classificacao=None` e `_garantir_classificacao` vai atribuir o valor correto por tipo.

### Fase 2: testes de regressão

**Arquivo:** `tests/test_categorizer.py`

Três testes novos:

```python
def test_imposto_sempre_obrigatorio(transacao):
    cat = Categorizer()
    t = transacao(local="Imposto Desconhecido ZZZ", tipo="Imposto")
    cat.categorizar(t)
    assert t["classificacao"] == "Obrigatório"

def test_receita_sem_match_cai_em_na(transacao):
    cat = Categorizer()
    t = transacao(local="Fonte Obscura ZZQWX", tipo="Receita")
    cat.categorizar(t)
    assert t["classificacao"] == "N/A"

def test_transferencia_interna_sem_match_cai_em_na(transacao):
    cat = Categorizer()
    t = transacao(local="Movimento ZZQWX", tipo="Transferência Interna")
    cat.categorizar(t)
    assert t["classificacao"] == "N/A"
```

Note uso de strings fortemente neutras ("ZZQWX") pra não casar nenhuma das 111 regras em `categorias.yaml`.

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A40-1 | Fallback que força classificação impede `_garantir_classificacao` de rodar | Deixar `classificacao=None` quando tipo não é Despesa; rede de segurança resolve |
| A40-2 | Teste contra texto "genérico" (ex: "Recebimento") casa regex inesperada de `categorias.yaml` | Usar strings improváveis (letras sem vogais, "ZZQWX") em testes de fallback |
| A40-3 | "Questionável" pode parecer default sensato, mas conceitualmente é rótulo de despesa | Manter semântica: Questionável/Supérfluo/Obrigatório só valem pra despesas |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [x] `make lint` passa
- [x] `.venv/bin/pytest tests/test_categorizer.py -v` → 8/8 passam (3 novos)
- [x] `./run.sh --tudo` executa sem erro
- [x] `python -m src.utils.validator` passa (sem regressão em duplicatas ou classificações)
- [x] Dashboard inicia sem erro
- [x] Commit atômico separado da Sprint 30

---

## Verificação end-to-end

```bash
make lint
.venv/bin/pytest tests/test_categorizer.py -v
./run.sh --tudo
python -m src.utils.validator
python -c "
import pandas as pd
df = pd.read_excel('data/output/ouroboros_2026.xlsx', sheet_name='extrato')
receitas_quest = df[(df['tipo'] == 'Receita') & (df['classificacao'] == 'Questionável')]
assert len(receitas_quest) == 0, f'Ainda há {len(receitas_quest)} Receita como Questionável'
print('OK: Nenhuma Receita classificada como Questionável')
"
```

---

*"Classificar é primeiro distinguir; o resto são consequências." -- Aristóteles, sobre as categorias*
