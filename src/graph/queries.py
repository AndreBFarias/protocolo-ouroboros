"""Biblioteca de consultas canônicas sobre o grafo. Sprint 42.

Cada função recebe `db: GrafoDB` ou caminho do SQLite e devolve
estrutura serializável (list[dict] ou dict). NÃO faz pretty-print --
isso é responsabilidade do caller (CLI, dashboard, scripts de auditoria).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB, caminho_padrao
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.queries")


def estatisticas(db: GrafoDB | None = None) -> dict[str, Any]:
    """Devolve contagens por tipo de node e edge.

    Aceita GrafoDB já aberto (testes) ou abre/fecha automaticamente
    no caminho padrão (uso CLI).
    """
    if db is not None:
        return db.estatisticas()
    with GrafoDB(caminho_padrao()) as db_local:
        return db_local.estatisticas()


def vida_de_transacao(db: GrafoDB, transacao_id: int) -> list[dict[str, Any]]:
    """Devolve as arestas que SAEM da transação (categoria, periodo, etc.).

    Usado pra responder "que rastros este lançamento bancário tem?"
    """
    arestas = db.listar_edges(src_id=transacao_id)
    resultado: list[dict[str, Any]] = []
    for aresta in arestas:
        dst = db.buscar_node_por_id(aresta.dst_id)
        if dst is None:
            continue
        resultado.append(
            {
                "edge_tipo": aresta.tipo,
                "dst_tipo": dst.tipo,
                "dst_nome": dst.nome_canonico,
                "evidencia": aresta.evidencia,
            }
        )
    return resultado


def listar_por_tipo(db: GrafoDB, tipo: str) -> list[dict[str, Any]]:
    """Devolve nodes de um tipo como dicts com (id, nome_canonico, metadata)."""
    return [
        {
            "id": n.id,
            "nome_canonico": n.nome_canonico,
            "aliases": n.aliases,
            "metadata": n.metadata,
        }
        for n in db.listar_nodes(tipo=tipo)
    ]


def fornecedores_recorrentes(
    db: GrafoDB, edge_tipo: str = "fornecido_por", minimo: int = 3
) -> list[dict[str, Any]]:
    """Top fornecedores por quantidade de arestas `fornecido_por` recebidas.

    Útil pra dashboard/auditoria: quem aparece mais no grafo merece atenção.
    """
    cursor = db._conn.execute(
        """
        SELECT n.id, n.nome_canonico, COUNT(e.id) AS qtd
        FROM node n
        JOIN edge e ON e.dst_id = n.id
        WHERE n.tipo = 'fornecedor' AND e.tipo = ?
        GROUP BY n.id
        HAVING qtd >= ?
        ORDER BY qtd DESC
        """,
        (edge_tipo, minimo),
    )
    return [{"id": r[0], "nome_canonico": r[1], "ocorrencias": r[2]} for r in cursor.fetchall()]


def cli_imprimir_estatisticas(caminho: Path | None = None) -> None:
    """Helper para `python -m src.graph.queries` -- imprime estatísticas."""
    db_path = caminho or caminho_padrao()
    if not db_path.exists():
        logger.warning("grafo não existe em %s -- rode src.graph.migracao_inicial", db_path)
        return
    with GrafoDB(db_path) as db:
        stats = estatisticas(db)
    logger.info("Estatísticas do grafo (%s):", db_path)
    logger.info("  nodes: %d total", stats["nodes_total"])
    for tipo, qtd in sorted(stats["nodes_por_tipo"].items(), key=lambda x: -x[1]):
        logger.info("    %-20s %d", tipo, qtd)
    logger.info("  edges: %d total", stats["edges_total"])
    for tipo, qtd in sorted(stats["edges_por_tipo"].items(), key=lambda x: -x[1]):
        logger.info("    %-20s %d", tipo, qtd)


if __name__ == "__main__":
    cli_imprimir_estatisticas()


# "Saber é dispor: quem tem o índice tem o livro." -- princípio da consulta
