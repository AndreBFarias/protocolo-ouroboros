---
id: INFRA-SPLIT-EXTRATO
titulo: Modularizar extrato.py (1340L) em extrato.py + extrato_helpers.py
status: backlog
prioridade: baixa
data_criacao: 2026-05-08
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 4
---

# Sprint INFRA-SPLIT-EXTRATO — split filt-bar + lista por dia

## Contexto

`src/dashboard/paginas/extrato.py = 1340L` excede limite `(h)` 800L em mais de 65%. Origem: filt-bar canônica + lista por dia com pílulas tipadas + cards laterais (UX-V-3.1).

## Objetivo

Extrair para `src/dashboard/componentes/extrato_helpers.py`:
- `_pilula_tipo(tipo)`.
- `_filt_bar_canonica(...)`.
- `_aplicar_filt_bar(df, filtros)`.
- `_lista_por_dia_html(df)`.
- `_t02_right_cards_html(...)`, `_saldo_topo_html`, `_breakdown_lateral_html`, `_origens_lateral_html`.

`extrato.py` mantém: orquestração `renderizar(...)` + KPIs + delegação.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/extrato.py
grep -nE "def _pilula_tipo|def _filt_bar_canonica|def _lista_por_dia_html|def _t02_right_cards_html" src/dashboard/paginas/extrato.py | head
```

## Não-objetivos

- NÃO mudar comportamento visual nem filtros.

## Proof-of-work

```bash
wc -l src/dashboard/paginas/extrato.py        # esperado <=800
wc -l src/dashboard/componentes/extrato_helpers.py
make lint && make smoke
.venv/bin/pytest tests/ -k extrato -q
```

## Critério de aceitação

1. `extrato.py <= 800L`.
2. Helpers exportados via `__all__`.
3. Lint + smoke + pytest baseline.

*"Quanto mais largo o arquivo, mais difícil enxergar o todo." — princípio INFRA-SPLIT-EXTRATO*
