---
id: INFRA-SPLIT-PROJECOES
titulo: Modularizar projecoes.py (868L) em projecoes.py + simulacao_personalizada.py
status: backlog
prioridade: baixa
data_criacao: 2026-05-08
fase: MODULARIZACAO
depende_de: []
esforco_estimado_horas: 2
origem: docs/auditorias/INVENTARIO_REAL_VS_MOCKUP_2026-05-08.md (5 splits)
---

# Sprint INFRA-SPLIT-PROJECOES — split do simulador

## Contexto

`src/dashboard/paginas/projecoes.py = 868L` excede limite `(h)` 800L. Origem do excedente: bloco "SIMULAÇÃO PERSONALIZADA" (slider + gráfico de simulação) adicionado em UX-V-2.0.

## Objetivo

Extrair para `src/dashboard/componentes/simulacao_personalizada.py`:
- Função `renderizar_simulacao(transacoes, ...)` que encapsula slider + chamada `projetar_com_economia` + gráfico.
- Helpers internos `_grafico_simulacao`, `_card_simulacao`.

`projecoes.py` mantém: scenarios canônicos (CDI/Carteira/IBOV) + KPIs + marcos + delegação ao módulo de simulação.

## Validação ANTES

```bash
wc -l src/dashboard/paginas/projecoes.py
grep -n "def _grafico_simulacao\|def renderizar_simulacao\|projetar_com_economia" src/dashboard/paginas/projecoes.py | head
```

## Não-objetivos

- NÃO mudar comportamento visual (mesmos KPIs, slider, gráfico).
- NÃO mexer em `src/projections/scenarios.py`.

## Proof-of-work

```bash
wc -l src/dashboard/paginas/projecoes.py        # esperado <=800
wc -l src/dashboard/componentes/simulacao_personalizada.py  # esperado <=300
make lint && make smoke
.venv/bin/pytest tests/ -k projecoes -q
```

## Critério de aceitação

1. `projecoes.py <= 800L`.
2. `simulacao_personalizada.py` exporta `renderizar_simulacao`.
3. Lint + smoke + pytest baseline.

*"Arquivo único é cofre; arquivo modular é vitrine." — princípio INFRA-SPLIT-PROJECOES*
