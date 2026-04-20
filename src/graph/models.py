"""Dataclasses Node e Edge + helpers de serialização JSON.

Sprint 42. Schema canônico em src/graph/schema.sql.

Convenções de uso:
- `nome_canonico` é a chave natural por (tipo, nome). Sempre normalizado
  via `normalizar_nome_canonico` antes de upsert -- evita "NEOENERGIA"
  e "neoenergia" virarem nodes diferentes.
- `aliases` armazena variantes de string que apontam para o mesmo
  conceito. Lista vazia por padrão.
- `metadata` é dict livre por tipo de nó. Não validado em runtime;
  responsabilidade dos callers (extratores) seguir convenção do ADR-14.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Node:
    """Nó do grafo. id é None até persistir."""

    tipo: str
    nome_canonico: str
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class Edge:
    """Aresta direcional do grafo. id é None até persistir."""

    src_id: int
    dst_id: int
    tipo: str
    peso: float = 1.0
    evidencia: dict[str, Any] = field(default_factory=dict)
    id: int | None = None
    created_at: str | None = None


# ============================================================================
# Helpers de normalização
# ============================================================================


def normalizar_nome_canonico(nome: str) -> str:
    """Normaliza para upper().strip() -- evita case-sensitivity da UNIQUE.

    Regra mínima: maiúsculas, sem espaços nas pontas. Remoção de sufixos
    societários (S/A, LTDA, ME) é responsabilidade do entity_resolution
    (não desta camada baixa)."""
    return nome.strip().upper()


def serializar_aliases(aliases: list[str]) -> str:
    """list[str] -> JSON string ordenada (estabilidade entre rodadas)."""
    return json.dumps(sorted(set(aliases)), ensure_ascii=False)


def serializar_metadata(metadata: dict[str, Any]) -> str:
    """dict -> JSON string com sort_keys (estabilidade entre rodadas)."""
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str)


def deserializar_aliases(raw: str | None) -> list[str]:
    """JSON string -> list[str]. None ou inválido -> [] (defensivo)."""
    if not raw:
        return []
    try:
        valor = json.loads(raw)
        if isinstance(valor, list):
            return [str(v) for v in valor]
    except json.JSONDecodeError:
        pass
    return []


def deserializar_metadata(raw: str | None) -> dict[str, Any]:
    """JSON string -> dict. None ou inválido -> {} (defensivo)."""
    if not raw:
        return {}
    try:
        valor = json.loads(raw)
        if isinstance(valor, dict):
            return valor
    except json.JSONDecodeError:
        pass
    return {}


def node_de_row(row: tuple) -> Node:
    """Constrói Node a partir de tupla SELECT.

    Esperado: (id, tipo, nome_canonico, aliases, metadata, created_at, updated_at).
    """
    return Node(
        id=row[0],
        tipo=row[1],
        nome_canonico=row[2],
        aliases=deserializar_aliases(row[3]),
        metadata=deserializar_metadata(row[4]),
        created_at=row[5],
        updated_at=row[6],
    )


def edge_de_row(row: tuple) -> Edge:
    """Constrói Edge a partir de tupla SELECT.

    Esperado: (id, src_id, dst_id, tipo, peso, evidencia, created_at).
    """
    return Edge(
        id=row[0],
        src_id=row[1],
        dst_id=row[2],
        tipo=row[3],
        peso=row[4],
        evidencia=deserializar_metadata(row[5]),
        created_at=row[6],
    )


# "O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo
