"""Roteador da Busca Global -- Sprint UX-114.

Decide se a query do usuário casa:

- **Aba** (`kind='aba'`): nome exato (case-insensitive) de uma aba do
  dashboard registrada em `MAPA_ABA_PARA_CLUSTER`. Resultado deve renderizar
  link rápido "Ir para aba <Nome>".
- **Fornecedor** (`kind='fornecedor'`): casa nome de fornecedor no índice
  (substring case-insensitive). Resultado deve renderizar link rápido para
  Catalogação filtrada por aquele fornecedor.
- **Livre** (`kind='livre'`): senão -- vai para busca_global do grafo
  (lista de resultados agrupada por tipo).

O roteador não executa a navegação -- apenas classifica. A página de
busca interpreta o `dict` devolvido e age (`st.query_params` ou
`st.button` com `on_click`).

Padrão (l) subregra retrocompatível: query continua casável pelo
`buscar_global` mesmo quando casa aba/fornecedor; o link rápido é
ALÉM dos resultados, não em vez deles.
"""

from __future__ import annotations

from typing import TypedDict

from src.dashboard.componentes.busca_indice import construir_indice
from src.dashboard.componentes.drilldown import MAPA_ABA_PARA_CLUSTER


class ResultadoRota(TypedDict):
    """Tipo do retorno de `rotear`."""

    kind: str
    destino: str
    tipo: str | None


def _casar_aba(query_norm: str) -> str | None:
    """Retorna o nome canônico da aba se a query casa exatamente, ou None."""
    for nome_aba in MAPA_ABA_PARA_CLUSTER:
        if nome_aba.lower() == query_norm:
            return nome_aba
    return None


def _casar_fornecedor(query_norm: str, indice: dict[str, list[str]]) -> str | None:
    """Retorna o nome canônico do fornecedor que casa, ou None.

    Estratégia: prioriza match exato (case-insensitive); se não houver,
    usa substring com pelo menos 4 caracteres da query e devolve o
    primeiro fornecedor cuja string contém a query inteira.
    """
    fornecedores = indice.get("fornecedores", [])
    # match exato primeiro
    for nome in fornecedores:
        if nome.lower() == query_norm:
            return nome
    # substring -- exige >=4 chars para evitar "a" casar "Banco do Brasil"
    if len(query_norm) >= 4:
        for nome in fornecedores:
            if query_norm in nome.lower():
                return nome
    return None


def rotear(
    query: str,
    indice: dict[str, list[str]] | None = None,
) -> ResultadoRota:
    """Decide o tipo de rota para a query do usuário.

    Args:
        query: termo digitado pelo usuário.
        indice: índice já construído (ver `busca_indice.construir_indice`).
            Se None, constrói um novo (caro em testes; em runtime use
            cached).

    Returns:
        Dict com:
        - `kind`: 'aba' | 'fornecedor' | 'livre'.
        - `destino`: nome canônico (aba ou fornecedor) ou string vazia.
        - `tipo`: classificação auxiliar (ex: 'cluster' p/ aba, 'forn' p/
           fornecedor, None p/ livre).
    """
    q = (query or "").strip().lower()
    if not q:
        return {"kind": "livre", "destino": "", "tipo": None}

    nome_aba = _casar_aba(q)
    if nome_aba:
        cluster = MAPA_ABA_PARA_CLUSTER.get(nome_aba, "")
        return {"kind": "aba", "destino": nome_aba, "tipo": cluster or None}

    idx = indice if indice is not None else construir_indice()
    nome_forn = _casar_fornecedor(q, idx)
    if nome_forn:
        return {"kind": "fornecedor", "destino": nome_forn, "tipo": "fornecedor"}

    return {"kind": "livre", "destino": query.strip(), "tipo": None}


# "Saber para onde se vai é metade do caminho." -- Sêneca
