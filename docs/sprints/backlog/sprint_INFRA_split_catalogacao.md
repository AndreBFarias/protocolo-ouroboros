---
id: INFRA-SPLIT-CATALOGACAO
titulo: Modularizar catalogacao.py (1052L) em catalogacao.py + catalogacao_grid.py
status: backlog
prioridade: baixa
data_criacao: 2026-05-08
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 3
---

# Sprint INFRA-SPLIT-CATALOGACAO — split do grid de thumbs

## Contexto

`src/dashboard/paginas/catalogacao.py = 1052L` excede limite `(h)` 800L. Origem: grid de thumbs com badges + sidebar 3 facetas (UX-V-3.3-GRID).

## Objetivo

Extrair para `src/dashboard/componentes/catalogacao_grid.py`:
- `EXTENSOES_BADGE` (constante).
- `_extrair_extensao`, `_badge_tipo_arquivo`, `_sha8_doc`, `_fonte_doc`, `_periodo_doc`.
- `_aplicar_filtros_grid`, `_facet_card_html`, `_grid_toolbar_html`, `_grid_cards_html`.
- `renderizar_grid_thumbs(documentos)`.

`catalogacao.py` mantém: KPIs + cards-tipo + delegação ao grid.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/catalogacao.py
grep -nE "def _renderizar_grid_thumbs|def _extrair_extensao|def _facet_card_html" src/dashboard/paginas/catalogacao.py | head
```

## Proof-of-work

```bash
wc -l src/dashboard/paginas/catalogacao.py        # esperado <=800
make lint && make smoke
.venv/bin/pytest tests/ -k catalogacao -q
```

## Critério de aceitação

1. `catalogacao.py <= 800L`.
2. `catalogacao_grid.py` exporta `renderizar_grid_thumbs`.
3. Lint + smoke + pytest baseline.

*"Cada cluster, seu próprio módulo." — princípio INFRA-SPLIT-CATALOGACAO*
