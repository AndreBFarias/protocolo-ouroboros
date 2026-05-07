---
id: UX-M-02.C
titulo: Migração clusters Análise + Metas + Inbox + Sistema para ui.py
status: concluida
prioridade: alta
data_criacao: 2026-05-06
concluida_em: 2026-05-06
commit: 6d36249
fase: MODULARIZAÇÃO
depende_de: [UX-M-02, UX-M-03]
co_executavel_com: [UX-M-02.A, UX-M-02.B, UX-M-02.D]
esforco_estimado_horas: 3
---

# Sprint UX-M-02.C — Migração Análise + Metas + Inbox + Sistema

## Contexto

Sub-sprint para migrar páginas dos 4 clusters menores (Análise, Metas, Inbox, Sistema) para `ui.py` + `components.css` canônico. Páginas heterogêneas: tabelas, gráficos plotly, treemap, lista densa.

## Páginas afetadas

| Cluster | Arquivo | Tem CSS local? | Ação |
|---|---|---|---|
| Análise | `categorias.py` | SIM | Migrar |
| Análise | `analise_avancada.py` | NÃO | Validar imports |
| Análise | `irpf.py` | NÃO | Validar imports |
| Metas | `metas.py` | NÃO | Validar imports |
| Inbox | `inbox.py` | SIM | Migrar |
| Sistema | `skills_d7.py` | SIM | Migrar |

**Foco principal: 3 páginas com CSS local (`categorias.py`, `inbox.py`, `skills_d7.py`).**

## Objetivo

1. Remover `_CSS_LOCAL_*` das 3 páginas.
2. Trocar imports em 6 páginas (`tema` → `ui` quando aplicável).
3. Reduzir linhas das 3 páginas com CSS local em ≥30%.

## Validação ANTES

```bash
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/{categorias,inbox,skills_d7}.py
# Esperado: ≥1 cada

wc -l src/dashboard/paginas/{categorias,inbox,skills_d7,analise_avancada,irpf,metas}.py
# Baseline

test -f src/dashboard/componentes/ui.py && echo "M-02 OK"
test -f src/dashboard/css/components.css && echo "M-03 OK"
```

## Spec de implementação

Aplicar regra geral da spec UX-M-02.A:

- **`categorias.py`**: tem treemap com classes próprias. Migrar imports + CSS comum, manter classes específicas de treemap como override em CSS de página (`<style>` mínimo).
- **`inbox.py`**: tem dropzone + fila densa + drawer sidecar. Mockup `15-inbox.html` é referência. Trocar classes `_CSS_LOCAL_INBOX` por canônicas (`.dropzone`, `.queue-row`, `.drawer`).
- **`skills_d7.py`**: tem cards de skill com pílulas D7 (graduado/calibracao/regredindo). Substituir `_CSS_LOCAL_SKILLS` por classes canônicas de `components.css` (`.skill-instr`, `.pill-d7-*`).

## Validação DEPOIS

```bash
grep -c "_CSS_LOCAL\|<style>" src/dashboard/paginas/{categorias,inbox,skills_d7}.py
# Esperado: 0 cada (ou ≤1 se mantiver override mínimo)

wc -l src/dashboard/paginas/{categorias,inbox,skills_d7}.py
# Esperado: ≥30% menor que baseline

make lint && make smoke && pytest tests/test_categorias*.py tests/test_inbox*.py tests/test_skills*.py -q
```

## Proof-of-work

```bash
# Validação visual playwright batch 6 páginas:
# - Categorias (cluster=Análise&tab=Categorias)
# - Análise (cluster=Análise&tab=Análise)
# - IRPF (cluster=Análise&tab=IRPF)
# - Metas (cluster=Metas&tab=Metas)
# - Inbox (cluster=Inbox&tab=Inbox)
# - Skills D7 (cluster=Sistema&tab=Skills+D7)

# Mockups:
# - 11-categorias.html
# - 12-analise.html
# - 13-irpf.html
# - 14-metas.html
# - 15-inbox.html
# - 16-skills.html
```

## Critério de aceitação

1. `_CSS_LOCAL_*` removidos das 3 páginas (ou reduzidos ao mínimo essencial).
2. 6 páginas importam de `ui.py`.
3. 3 páginas com CSS local reduzidas ≥30% em linhas.
4. Lint OK + smoke 10/10 + testes regressivos verdes.
5. Validação visual: 6 páginas idênticas aos mockups.

## Não-objetivos

- NÃO migrar Bem-estar (sub-sprint D faz).
- NÃO mudar lógica das páginas.
- NÃO unificar treemap de categorias com outros componentes — específico, manter.

## Referência

- UX-M-02 + UX-M-03 (dependem).
- `novo-mockup/mockups/11-categorias.html` ... `16-skills.html`.

*"Páginas heterogêneas exigem julgamento sobre o que é específico." — princípio M-02.C*
