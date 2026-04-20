"""GrafoDB -- conexão SQLite, schema, upsert idempotente. Sprint 42.

Idempotência crítica:
- `upsert_node` usa INSERT ... ON CONFLICT(tipo, nome_canonico) DO UPDATE.
  Mesmo (tipo, nome_canonico) sempre devolve o MESMO id; aliases/metadata
  são mergeados (aliases: união; metadata: dst sobrescreve src).
- `adicionar_edge` usa INSERT OR IGNORE com UNIQUE(src,dst,tipo). Aresta
  duplicada é silenciosamente ignorada.

Política:
- Foreign keys habilitadas (PRAGMA foreign_keys=ON) -- garante que CASCADE
  no DROP de node remove edges relacionadas.
- Conexão por instância. Não é thread-safe sem locking explícito; intake
  e migração rodam single-thread.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from src.graph.models import (
    Edge,
    Node,
    deserializar_aliases,
    deserializar_metadata,
    edge_de_row,
    node_de_row,
    normalizar_nome_canonico,
    serializar_aliases,
    serializar_metadata,
)
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.db")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_SCHEMA: Path = Path(__file__).parent / "schema.sql"
_PATH_DB_PADRAO: Path = _RAIZ_REPO / "data" / "output" / "grafo.sqlite"


def caminho_padrao() -> Path:
    """Caminho canônico do grafo SQLite em produção."""
    return _PATH_DB_PADRAO


# ============================================================================
# GrafoDB
# ============================================================================


class GrafoDB:
    """Wrapper sobre sqlite3.Connection com API alta-nível para nodes e edges.

    Uso típico:

        db = GrafoDB(caminho_padrao())
        db.criar_schema()
        id_neo = db.upsert_node("fornecedor", "NEOENERGIA", metadata={"cnpj": "..."})
        id_periodo = db.upsert_node("periodo", "2026-04")
        db.adicionar_edge(id_neo, id_periodo, "ocorre_em")
        db.fechar()
    """

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(str(caminho))
        self._conn.execute("PRAGMA foreign_keys = ON")
        # Devolve linhas como tuplas (default); manter explícito por clareza.
        self._conn.row_factory = None

    # ------------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------------

    def criar_schema(self) -> None:
        """Aplica schema.sql. Idempotente (CREATE IF NOT EXISTS)."""
        ddl = _PATH_SCHEMA.read_text(encoding="utf-8")
        self._conn.executescript(ddl)
        self._conn.commit()
        logger.debug("schema aplicado em %s", self.caminho)

    def limpar(self) -> None:
        """Apaga todo o conteúdo das tabelas. USAR SÓ EM DEV/TESTES."""
        self._conn.execute("DELETE FROM edge")
        self._conn.execute("DELETE FROM node")
        self._conn.commit()
        logger.warning("grafo limpo: %s", self.caminho)

    # ------------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------------

    def upsert_node(
        self,
        tipo: str,
        nome_canonico: str,
        metadata: dict[str, Any] | None = None,
        aliases: list[str] | None = None,
    ) -> int:
        """Insere ou atualiza nó por (tipo, nome_canonico).

        Aliases novos são UNIDOS com os existentes (sem perder os antigos).
        Metadata novos SOBRESCREVEM as chaves correspondentes (merge raso).
        Devolve o id do nó (mesmo em update).
        """
        nome_normalizado = normalizar_nome_canonico(nome_canonico)
        meta = metadata or {}
        novos_aliases = list(aliases or [])

        cursor = self._conn.execute(
            "SELECT id, aliases, metadata FROM node WHERE tipo = ? AND nome_canonico = ?",
            (tipo, nome_normalizado),
        )
        row = cursor.fetchone()
        if row is None:
            cursor = self._conn.execute(
                "INSERT INTO node (tipo, nome_canonico, aliases, metadata) VALUES (?, ?, ?, ?)",
                (
                    tipo,
                    nome_normalizado,
                    serializar_aliases(novos_aliases),
                    serializar_metadata(meta),
                ),
            )
            self._conn.commit()
            return int(cursor.lastrowid or 0)

        node_id, aliases_raw, metadata_raw = row
        aliases_existentes = deserializar_aliases(aliases_raw)
        meta_existente = deserializar_metadata(metadata_raw)
        aliases_unificados = sorted(set(aliases_existentes) | set(novos_aliases))
        meta_unificado = {**meta_existente, **meta}
        self._conn.execute(
            """
            UPDATE node
            SET aliases = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                serializar_aliases(aliases_unificados),
                serializar_metadata(meta_unificado),
                node_id,
            ),
        )
        self._conn.commit()
        return int(node_id)

    def buscar_node(self, tipo: str, nome_canonico: str) -> Node | None:
        nome_normalizado = normalizar_nome_canonico(nome_canonico)
        cursor = self._conn.execute(
            """
            SELECT id, tipo, nome_canonico, aliases, metadata, created_at, updated_at
            FROM node WHERE tipo = ? AND nome_canonico = ?
            """,
            (tipo, nome_normalizado),
        )
        row = cursor.fetchone()
        return node_de_row(row) if row else None

    def buscar_node_por_id(self, node_id: int) -> Node | None:
        cursor = self._conn.execute(
            """
            SELECT id, tipo, nome_canonico, aliases, metadata, created_at, updated_at
            FROM node WHERE id = ?
            """,
            (node_id,),
        )
        row = cursor.fetchone()
        return node_de_row(row) if row else None

    def listar_nodes(self, tipo: str | None = None) -> list[Node]:
        sql = "SELECT id, tipo, nome_canonico, aliases, metadata, created_at, updated_at FROM node"
        if tipo:
            cursor = self._conn.execute(sql + " WHERE tipo = ?", (tipo,))
        else:
            cursor = self._conn.execute(sql)
        return [node_de_row(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------------

    def adicionar_edge(
        self,
        src_id: int,
        dst_id: int,
        tipo: str,
        peso: float = 1.0,
        evidencia: dict[str, Any] | None = None,
    ) -> None:
        """Adiciona aresta. INSERT OR IGNORE -- aresta duplicada não duplica.

        Para atualizar evidência de aresta existente, deletar e recriar.
        Aceitável: arestas são fatos; evidência típica não muda."""
        ev = evidencia or {}
        self._conn.execute(
            """
            INSERT OR IGNORE INTO edge (src_id, dst_id, tipo, peso, evidencia)
            VALUES (?, ?, ?, ?, ?)
            """,
            (src_id, dst_id, tipo, peso, serializar_metadata(ev)),
        )
        self._conn.commit()

    def listar_edges(self, src_id: int | None = None, tipo: str | None = None) -> list[Edge]:
        sql = "SELECT id, src_id, dst_id, tipo, peso, evidencia, created_at FROM edge"
        condicoes: list[str] = []
        params: list[Any] = []
        if src_id is not None:
            condicoes.append("src_id = ?")
            params.append(src_id)
        if tipo:
            condicoes.append("tipo = ?")
            params.append(tipo)
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        cursor = self._conn.execute(sql, params)
        return [edge_de_row(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------------
    # Estatísticas + cleanup
    # ------------------------------------------------------------------------

    def estatisticas(self) -> dict[str, Any]:
        """Devolve contagens por tipo de node e edge -- útil pra logs e queries."""
        nodes_por_tipo: dict[str, int] = {}
        for tipo, qtd in self._conn.execute(
            "SELECT tipo, COUNT(*) FROM node GROUP BY tipo"
        ).fetchall():
            nodes_por_tipo[tipo] = qtd
        edges_por_tipo: dict[str, int] = {}
        for tipo, qtd in self._conn.execute(
            "SELECT tipo, COUNT(*) FROM edge GROUP BY tipo"
        ).fetchall():
            edges_por_tipo[tipo] = qtd
        return {
            "nodes_total": sum(nodes_por_tipo.values()),
            "edges_total": sum(edges_por_tipo.values()),
            "nodes_por_tipo": nodes_por_tipo,
            "edges_por_tipo": edges_por_tipo,
        }

    def fechar(self) -> None:
        self._conn.close()

    def __enter__(self) -> GrafoDB:
        return self

    def __exit__(self, *args: object) -> None:
        self.fechar()


# "O grafo é o esqueleto; as arestas são o que lembra." -- princípio de cartógrafo
