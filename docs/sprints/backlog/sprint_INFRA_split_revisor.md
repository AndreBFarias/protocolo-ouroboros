---
id: INFRA-SPLIT-REVISOR
titulo: Modularizar revisor.py (1196L) em revisor_4way.py + revisor_legado.py
status: backlog
prioridade: baixa
data_criacao: 2026-05-08
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 4
---

# Sprint INFRA-SPLIT-REVISOR — separar arquitetura 4-way de legado D2

## Contexto

`src/dashboard/paginas/revisor.py = 1196L` excede limite `(h)` 800L em quase 50%. Origem: coexistência da arquitetura 4-way de UX-V-4 (OFX × Rascunho × Opus × Humano) com layout legado da Sprint D2 que ainda é exercido por 79 testes regressivos.

## Objetivo

Refatorar em 3 arquivos:

1. `src/dashboard/paginas/revisor.py` (~200L): orquestração + dispatcher entre 4-way e legado conforme query param ou estado.
2. `src/dashboard/componentes/revisor_4way.py` (~600L): layout 4-pane + cards OFX/Rascunho/Opus/Humano + tabs filtro + trace.
3. `src/dashboard/componentes/revisor_legado.py` (~400L): KPIs + filtros legados + lista pendências (Sprint D2).

Preservar 79 testes existentes sem alteração.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/revisor.py
.venv/bin/pytest tests/ -k revisor -q | tail -3   # baseline atual
```

## Não-objetivos

- NÃO mudar comportamento de nenhuma das duas arquiteturas.
- NÃO mexer em `extracao_tripla.json` schema.

## Proof-of-work

```bash
wc -l src/dashboard/paginas/revisor.py        # esperado <=300
wc -l src/dashboard/componentes/revisor_4way.py
wc -l src/dashboard/componentes/revisor_legado.py
make lint && make smoke
.venv/bin/pytest tests/ -k revisor -q   # esperado: idem baseline (79 passed)
```

## Critério de aceitação

1. `revisor.py <= 300L` (orquestrador).
2. 79 testes regressivos passando sem alteração.
3. Lint + smoke + pytest baseline.

*"Coexistência sem fronteira é dívida arquitetural." — princípio INFRA-SPLIT-REVISOR*
