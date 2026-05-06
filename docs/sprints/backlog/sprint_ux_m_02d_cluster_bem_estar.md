---
id: UX-M-02.D
titulo: Migração cluster Bem-estar para ui.py canônico
status: backlog
prioridade: alta
data_criacao: 2026-05-06
fase: MODULARIZAÇÃO
depende_de: [UX-M-02, UX-M-03]
co_executavel_com: [UX-M-02.A, UX-M-02.B, UX-M-02.C]
esforco_estimado_horas: 6
---

# Sprint UX-M-02.D — Migração cluster Bem-estar

## Contexto

Sub-sprint para migrar 12 páginas do cluster **Bem-estar** (be_*) para `ui.py` + `components.css` canônico. Cluster mais volumoso: 12 páginas, 4 com CSS local explícito, todas com layouts próprios (heatmap humor, timeline diária, ciclo, eventos, etc.).

## Páginas afetadas (12 páginas)

| Arquivo | Tem CSS local? | Ação |
|---|---|---|
| `be_hoje.py` | SIM | Migrar |
| `be_humor.py` | SIM | Migrar |
| `be_diario.py` | SIM | Migrar |
| `be_eventos.py` | SIM | Migrar |
| `be_ciclo.py` | NÃO | Validar imports |
| `be_marcos.py` | NÃO | Validar imports |
| `be_alarmes.py` | NÃO | Validar imports |
| `be_treinos.py` | NÃO | Validar imports |
| `be_tarefas.py` | NÃO | Validar imports |
| `be_recap.py` | NÃO | Validar imports |
| `be_cruzamentos.py` | NÃO | Validar imports |
| `be_memorias.py` | NÃO | Validar imports |
| `be_rotina.py` | NÃO | Validar imports |
| `be_medidas.py` | NÃO | Validar imports |
| `be_contadores.py` | NÃO | Validar imports |
| `be_privacidade.py` | NÃO | Validar imports |
| `be_editor_toml.py` | NÃO | Validar imports |

(Total real do cluster pode variar — verificar ANTES.)

**Foco principal: 4 páginas com CSS local.**

## Objetivo

1. Remover `_CSS_LOCAL_*` das 4 páginas com CSS embutido.
2. Trocar imports em todas as 12+ páginas do cluster (`tema` → `ui`).
3. Reduzir linhas das 4 páginas com CSS local em ≥30% cada.

## Validação ANTES

```bash
# Listar páginas do cluster
ls src/dashboard/paginas/be_*.py | wc -l
# Esperado: ~12-17

# Páginas com CSS local
grep -lE "_CSS_LOCAL_|<style>" src/dashboard/paginas/be_*.py
# Esperado: 4 (be_hoje, be_humor, be_diario, be_eventos)

wc -l src/dashboard/paginas/be_hoje.py src/dashboard/paginas/be_humor.py \
       src/dashboard/paginas/be_diario.py src/dashboard/paginas/be_eventos.py
# Baseline

test -f src/dashboard/componentes/ui.py && echo "M-02 OK"
test -f src/dashboard/css/components.css && echo "M-03 OK"
```

## Spec de implementação

Aplicar regra geral da spec UX-M-02.A:

### Páginas-chave do cluster Bem-estar

- **`be_hoje.py`**: dashboard pessoal do dia (eventos, humor, tarefas). Mockup canônico: `mockups/be-hoje.html` (verificar se existe). Componentes que devem usar canônicos: `kpi_card`, `data_row`, `callout_html`.

- **`be_humor.py`**: heatmap humor + overlay pessoa A/B. Heatmap é específico — manter classe própria como override em CSS de página. Migrar resto.

- **`be_diario.py`**: timeline emocional. Componentes timeline são específicos — manter. Migrar header, KPIs, callouts.

- **`be_eventos.py`**: timeline de eventos + bairros agregados. Mesma lógica do diário.

### Outras 8-13 páginas (sem CSS local)

Apenas trocar imports:

```python
# ANTES
from src.dashboard.tema import callout_html, chip_html

# DEPOIS
from src.dashboard.componentes.ui import callout_html, chip_html
```

## Validação DEPOIS

```bash
# Sem CSS local nas 4 páginas migradas
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/{be_hoje,be_humor,be_diario,be_eventos}.py
# Esperado: 0 cada (ou ≤1 com override mínimo justificado)

# Imports trocados
grep -c "from src.dashboard.componentes.ui import" src/dashboard/paginas/be_*.py | grep -v ":0"
# Esperado: ≥10 hits

# Tamanhos reduzidos
wc -l src/dashboard/paginas/be_hoje.py
# Esperado: ≥30% menor que baseline

make lint && make smoke && pytest tests/test_be*.py -q
```

## Proof-of-work

```bash
# Validação visual playwright batch 12+ páginas:
# - Bem-estar / Hoje
# - Bem-estar / Humor
# - Bem-estar / Diário
# - Bem-estar / Eventos
# - Bem-estar / (resto)

# Mockups (se existirem):
# - novo-mockup/mockups/be-*.html
```

## Critério de aceitação

1. `_CSS_LOCAL_*` removidos das 4 páginas com CSS local (ou reduzidos ao mínimo justificado).
2. Todas as 12+ páginas do cluster importam de `ui.py`.
3. 4 páginas com CSS reduzidas ≥30% em linhas.
4. Lint OK + smoke 10/10 + testes regressivos verdes.
5. Validação visual: páginas idênticas aos mockups (onde houver).

## Não-objetivos

- NÃO migrar páginas de outros clusters (A/B/C fazem).
- NÃO mudar lógica de heatmap, timeline ou cálculos de bem-estar.
- NÃO unificar componentes específicos do bem-estar (heatmap, timeline) com componentes universais — manter como classes locais.

## Referência

- UX-M-02 + UX-M-03 (dependem).
- `novo-mockup/mockups/be-*.html` (se existirem).
- Sprints concluídas anteriormente: ux_rd_17, ux_rd_18, ux_rd_19 (Onda 6 do Bem-estar).

*"Cluster volumoso exige paciência: cada página é uma checagem visual." — princípio M-02.D*
