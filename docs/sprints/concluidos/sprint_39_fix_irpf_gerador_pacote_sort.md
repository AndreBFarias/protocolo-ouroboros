## 0. SPEC (machine-readable)

```yaml
sprint:
  id: 39
  title: "Fix: IRPF gerador_pacote crash em sorted() com tag_irpf mista str/NaN"
  touches:
    - path: src/irpf/gerador_pacote.py
      reason: "filtrar tag_irpf para isinstance(str) antes de agrupar; previne comparação str < float NaN em sorted()"
  n_to_n_pairs: []
  forbidden: []
  tests:
    - cmd: "make lint"
      timeout: 60
    - cmd: "python -m src.irpf --ano 2026"
      timeout: 30
  acceptance_criteria:
    - "python -m src.irpf --ano 2026 roda sem TypeError em sorted()"
    - "CSVs gerados: dedutivel_medico.csv, imposto_pago.csv, rendimento_isento.csv, rendimento_tributavel.csv"
    - "resumo_irpf.csv com totais por tag"
    - "Acentuação PT-BR correta"
```

> Executar antes de começar: `make lint && ./run.sh --check`

---

# Sprint 39 -- Fix: IRPF gerador_pacote crash em sorted() com tag_irpf mista

**Status:** CONCLUÍDA
**Data:** 2026-04-18
**Prioridade:** ALTA
**Tipo:** Bugfix
**Dependências:** Sprint 22 (criação do `src/irpf/__main__.py`)
**Desbloqueia:** IRPF funcional ponta-a-ponta
**Issue:** --
**ADR:** --

---

## Como Executar

**Comandos principais:**
- `python -m src.irpf --ano 2026`
- `.venv/bin/pytest tests/` -- regressão
- `make lint`

### O que NÃO fazer

- NÃO trocar `sorted(por_tipo.items())` por `sorted(por_tipo)` -- ambos dão o mesmo TypeError
- NÃO silenciar o erro com try/except cego -- filtrar a entrada é a correção correta

---

## Problema

Após criar `src/irpf/__main__.py` na Sprint 22, `python -m src.irpf --ano 2026` passou a carregar corretamente mas crashava downstream:

```
Traceback (most recent call last):
  File "src/irpf/__init__.py", line 52, in executar
    csvs = gerar_csvs_por_tipo(transacoes_ano, saida)
  File "src/irpf/gerador_pacote.py", line 22, in gerar_csvs_por_tipo
    for tipo, registros in sorted(por_tipo.items()):
                           ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: '<' not supported between instances of 'str' and 'float'
```

Diagnóstico: quando `pandas.read_excel` carrega a aba `extrato`, transações sem `tag_irpf` vêm com valor `NaN` (float). A checagem `if tag:` aceita NaN como truthy (pois `bool(math.nan) == True` em Python). NaN entrava como chave no dict `por_tipo`, junto com tags-string reais. `sorted()` falha ao comparar `str < float`.

Mesmo erro reaparecia em `gerar_resumo()` (linha 70 original) — padrão idêntico `for tipo in sorted(totais.keys())`.

Impacto: IRPF inteiramente quebrado em ambos os comandos (`python -m src.irpf`, `./run.sh --irpf`).

---

## O que já existe (NÃO duplicar)

| Sistema | Arquivo | O que faz |
|---------|---------|-----------|
| IRPF executor | `src/irpf/__init__.py:31-95` | Orquestra gerador de CSVs, resumo, simulador, checklist |
| Gerador de pacote | `src/irpf/gerador_pacote.py` | Escreve CSVs por tipo + resumo consolidado |
| Tagger IRPF | `src/transform/irpf_tagger.py` | Define tags (rendimento_tributavel, dedutivel_medico, inss_retido, imposto_pago, rendimento_isento) |

---

## Implementação

### Fase 1: guard na agregação por tipo

**Arquivo:** `src/irpf/gerador_pacote.py` (`gerar_csvs_por_tipo`, linhas 15-19)

```python
for t in transacoes:
    tag = t.get("tag_irpf")
    if isinstance(tag, str) and tag:
        por_tipo.setdefault(tag, []).append(t)
```

Condição dupla: `isinstance(tag, str)` filtra NaN/None/numéricos, e `and tag` filtra strings vazias.

### Fase 2: mesmo guard no gerador de resumo

**Arquivo:** `src/irpf/gerador_pacote.py` (`gerar_resumo`, linhas 61-65)

```python
for t in transacoes:
    tag = t.get("tag_irpf")
    if isinstance(tag, str) and tag:
        totais[tag] = totais.get(tag, 0) + t.get("valor", 0)
        contagens[tag] = contagens.get(tag, 0) + 1
```

### Fase 3: validação

```bash
python -m src.irpf --ano 2026
```

Output esperado:
```
CSV gerado: dedutivel_medico.csv (4 registros)
CSV gerado: imposto_pago.csv (6 registros)
CSV gerado: rendimento_isento.csv (7 registros)
CSV gerado: rendimento_tributavel.csv (3 registros)
Resumo IRPF gerado: data/output/irpf_2026/resumo_irpf.csv
```

---

## Armadilhas Conhecidas

| Ref | Armadilha | Como evitar |
|-----|-----------|-------------|
| A39-1 | `bool(math.nan) == True` -- `if tag:` passa NaN como tag válida | Usar `isinstance(tag, str) and tag` ao consumir coluna que pode vir do pandas |
| A39-2 | `sorted()` em lista com tipos mistos falha em Python 3.3+ | Garantir homogeneidade de tipos ANTES de ordenar |
| A39-3 | Coluna opcional de XLSX vem como NaN, não como None | Assumir `pd.NA`/`math.nan` em qualquer coluna não-obrigatória |

Referência: `docs/ARMADILHAS.md`

---

## Evidências Obrigatórias

- [x] `make lint` passa
- [x] `python -m src.irpf --ano 2026` roda sem crash
- [x] 4 CSVs gerados em `data/output/irpf_2026/`
- [x] `resumo_irpf.csv` contém totais por tag
- [x] Simulador IRPF e checklist executam sem erro

---

## Verificação end-to-end

```bash
python -m src.irpf --ano 2026 2>&1 | grep -E "CSV gerado|Resumo IRPF|Saldo"
# Esperado: 4 linhas "CSV gerado" + 1 "Resumo IRPF gerado" + linhas de saldo
ls data/output/irpf_2026/
# Esperado: 4 .csv de tipo + resumo_irpf.csv
```

---

*"O erro é humano, mas persistir nele é diabólico." -- Sêneca*
