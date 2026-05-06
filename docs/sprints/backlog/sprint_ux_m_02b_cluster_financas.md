---
id: UX-M-02.B
titulo: Migração cluster Finanças para ui.py canônico
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-02, UX-M-03]
co_executavel_com: [UX-M-02.A, UX-M-02.C, UX-M-02.D]
esforco_estimado_horas: 3
---

# Sprint UX-M-02.B — Migração cluster Finanças

## Contexto

Sub-sprint para migrar páginas do cluster **Finanças** para usar `ui.py` (M-02) e `components.css` canônico (M-03). Cluster Finanças tem páginas com layouts financeiros pesados (KPIs, cards de banco, gráficos plotly).

## Páginas afetadas

| Arquivo | Tem `_CSS_LOCAL_*`? | Ação |
|---|---|---|
| `src/dashboard/paginas/extrato.py` | SIM (`_CSS_LOCAL_EXTRATO`) | Migrar |
| `src/dashboard/paginas/contas.py` | NÃO (CSS já em tema_css) | Validar imports |
| `src/dashboard/paginas/pagamentos.py` | NÃO | Validar imports |
| `src/dashboard/paginas/projecoes.py` | NÃO | Validar imports |

**Foco principal: 1 página com CSS local (`extrato.py`).**

## Objetivo

1. Substituir `_CSS_LOCAL_EXTRATO` por imports de `ui.py` + classes canônicas.
2. Trocar `from tema import ...` por `from componentes.ui import ...` em 4 páginas.
3. Reduzir linhas de `extrato.py` em ≥30% (página densa, redução menor que outras).

## Validação ANTES

```bash
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/extrato.py
# Esperado: ≥1

grep -E "from src.dashboard.tema import" src/dashboard/paginas/{extrato,contas,pagamentos,projecoes}.py
# Listar imports a trocar

test -f src/dashboard/componentes/ui.py && echo "M-02 OK"
test -f src/dashboard/css/components.css && echo "M-03 OK"

wc -l src/dashboard/paginas/extrato.py
# Baseline para comparar
```

## Spec de implementação

Aplicar regra geral da spec UX-M-02.A:

1. Identificar regras em `_CSS_LOCAL_EXTRATO` que duplicam `components.css` (remover).
2. Trocar `<div class="extrato-...">` por classes canônicas (`.table`, `.row`, `.kpi-card`).
3. Trocar imports.

**Atenção especial em `extrato.py`**:
- Página densa com tabela ≥1000 linhas. Validar performance pós-migração.
- Drawer sidecar pode ter classes específicas — preservar como override em CSS página se necessário.

## Validação DEPOIS

```bash
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/extrato.py
# Esperado: 0

grep -c "from src.dashboard.componentes.ui import" src/dashboard/paginas/extrato.py
# Esperado: ≥1

wc -l src/dashboard/paginas/extrato.py
# Esperado: ≥30% menor que baseline

make lint && make smoke && pytest tests/test_extrato*.py -q
```

## Proof-of-work

```bash
# Validação visual playwright batch 4 páginas:
# - Extrato (cluster=Finanças&tab=Extrato)
# - Contas (cluster=Finanças&tab=Contas)
# - Pagamentos (cluster=Finanças&tab=Pagamentos)
# - Projeções (cluster=Finanças&tab=Projeções)

# Mockups:
# - novo-mockup/mockups/02-extrato.html
# - novo-mockup/mockups/03-contas.html
# - novo-mockup/mockups/04-pagamentos.html
# - novo-mockup/mockups/05-projecoes.html

# Performance: tabela de Extrato continua scroll fluido com 1000+ linhas.
```

## Critério de aceitação

1. `_CSS_LOCAL_EXTRATO` removido.
2. 4 páginas do cluster Finanças importam de `ui.py`.
3. `extrato.py` reduzido ≥30% em linhas.
4. Lint OK + smoke 10/10 + testes regressivos verdes.
5. Validação visual: 4 páginas idênticas ao mockup.
6. Performance Extrato: scroll fluido (subjetivo, validar manualmente).

## Não-objetivos

- NÃO migrar outras páginas (A/C/D fazem).
- NÃO mudar lógica de cálculos financeiros.
- NÃO mexer em `tema_plotly.py` (gráficos têm CSS próprio fora do escopo).

## Referência

- UX-M-02 + UX-M-03 (dependem).
- `novo-mockup/mockups/02-extrato.html` ... `05-projecoes.html`.

*"Tabela densa exige migração cuidadosa." — princípio M-02.B*
