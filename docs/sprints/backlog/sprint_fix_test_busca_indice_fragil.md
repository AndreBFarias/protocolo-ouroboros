---
id: FIX-TEST-BUSCA-INDICE-FRAGIL
titulo: Sprint FIX-TEST-BUSCA-ÍNDICE-01 — Fix testes frágeis de busca global
status: backlog
concluida_em: null
prioridade: P2
data_criacao: '2026-04-29'
fase: OUTROS
epico: 0
depende_de: []
tipo_documental_alvo: null
---

# Sprint FIX-TEST-BUSCA-ÍNDICE-01 — Fix testes frágeis de busca global

**Origem**: achado colateral durante Sprint ANTI-MIGUE-08 (2026-04-29).
**Prioridade**: P2
**Onda**: 1
**Esforço estimado**: 1.5h
**Depende de**: nenhuma

## Problema

Dois testes de UI da busca global passam **acidentalmente** em main:

- `tests/test_busca_global.py::TestChipDisparaBuscaPontaAPonta::test_injecao_via_session_state_dispara_busca`
- `tests/test_dashboard_busca.py::TestRenderizacaoStreamlit::test_pagina_renderiza_com_termo_que_casa`

A fixture monkeypatcha apenas `src.dashboard.dados.CAMINHO_GRAFO` com um grafo sintético, mas:
1. **`src/dashboard/componentes/busca_indice.py:31`** declara `CAMINHO_GRAFO_DEFAULT` próprio, hardcoded para `RAIZ / "data" / "output" / "grafo.sqlite"` — independe do monkeypatch.
2. `construir_indice()` chama `_ler_grafo(caminho_grafo=CAMINHO_GRAFO_DEFAULT)` por default → sempre lê o grafo de produção.
3. `rotear(termo, indice=indice)` só identifica `kind='fornecedor'` se o termo casar contra o índice carregado de produção. Se o grafo de produção tem "NEOENERGIA", a rota é detectada e o callout `_renderizar_tabela_inline_fornecedor` renderiza um markdown com NEOENERGIA — então o assert `"NEOENERGIA" in markdowns` passa **por sorte**.
4. Em CI fresh, em outro clone ou após `--reextrair-tudo` que limpa o grafo, esses testes falham.

Sprint ANTI-MIGUE-08 fez `dados_grafo._caminho_grafo()` honrar o monkeypatch dinâmico. Isso é correção arquitetural correta, mas REVELOU a fragilidade do teste — o monkeypatch alcança `buscar_global` mas não alcança `construir_indice`.

## Hipótese

Fixar a fixture `grafo_minimo` para também monkeypatchar `busca_indice.CAMINHO_GRAFO_DEFAULT` apontando para o tmp/g.sqlite. Adicionar 1 nó tipo `documento` linkado ao fornecedor para que a rota `kind=fornecedor` seja detectada via construir_indice no fixture.

## Implementação proposta

```python
import src.dashboard.componentes.busca_indice as busca_indice

monkeypatch.setattr(dashboard_dados, "CAMINHO_GRAFO", destino)
monkeypatch.setattr(busca_indice, "CAMINHO_GRAFO_DEFAULT", destino)

# também: dados_grafo.CAMINHO_GRAFO se o teste rodar isolado.
from src.dashboard import dados_grafo
monkeypatch.setattr(dados_grafo, "CAMINHO_GRAFO", destino)
```

## Acceptance criteria

- 2 testes passam em CI fresh (sem grafo de produção).
- Sem regressão em outros 51 testes da mesma suíte.

## Gate anti-migué

9 checks padrão.
