"""Biblioteca de consultas canônicas sobre o grafo. Sprint 42.

Cada função recebe `db: GrafoDB` ou caminho do SQLite e devolve
estrutura serializável (list[dict] ou dict). NÃO faz pretty-print --
isso é responsabilidade do caller (CLI, dashboard, scripts de auditoria).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB, caminho_padrao
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.queries")

# Comprimento máximo do fallback de nome_canonico antes de truncar (Sprint 60).
_LIMITE_LABEL_FALLBACK = 40


def label_humano(node: dict[str, Any]) -> str:
    """Devolve o rótulo mais legível possível para um node do grafo.

    Ordem de preferência (Sprint 60):
    1. Primeiro elemento de `aliases` (JSON string ou lista já decodificada).
    2. `metadata.razao_social` quando presente.
    3. `nome_canonico` truncado em 40 caracteres com reticências se maior.

    Aceita `aliases` e `metadata` como string JSON (formato de `GrafoDB`) ou
    como estruturas Python já deserializadas (formato usado pelo dashboard
    após `json.loads`). Assim pode ser chamado em qualquer camada.
    """
    aliases_raw = node.get("aliases")
    aliases: list[Any] = []
    if isinstance(aliases_raw, list):
        aliases = aliases_raw
    elif isinstance(aliases_raw, str) and aliases_raw.strip():
        try:
            decodificado = json.loads(aliases_raw)
            if isinstance(decodificado, list):
                aliases = decodificado
        except (json.JSONDecodeError, TypeError):
            aliases = []

    if aliases:
        primeiro = aliases[0]
        if primeiro is not None and str(primeiro).strip():
            return str(primeiro)

    metadata_raw = node.get("metadata")
    metadata: dict[str, Any] = {}
    if isinstance(metadata_raw, dict):
        metadata = metadata_raw
    elif isinstance(metadata_raw, str) and metadata_raw.strip():
        try:
            decodificado = json.loads(metadata_raw)
            if isinstance(decodificado, dict):
                metadata = decodificado
        except (json.JSONDecodeError, TypeError):
            metadata = {}

    razao_social = metadata.get("razao_social")
    if razao_social and str(razao_social).strip():
        return str(razao_social)

    canonico = str(node.get("nome_canonico") or "")
    if len(canonico) > _LIMITE_LABEL_FALLBACK:
        return canonico[:_LIMITE_LABEL_FALLBACK] + "..."
    return canonico


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


def obter_documentos_por_tipo_e_periodo(
    db: GrafoDB,
    tipos_documento: list[str] | None = None,
    mes_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Devolve documentos filtrados por `metadata.tipo_documento` e por período.

    `tipos_documento=None` traz todos os tipos. `mes_ref=None` traz todos os
    meses. Itera sobre o retorno de `listar_nodes('documento')` filtrando em
    memória -- volumes de documentos no grafo são baixos (dezenas, não milhares)
    e não justificam índice dedicado em metadata.
    """
    resultado: list[dict[str, Any]] = []
    for nd in db.listar_nodes(tipo="documento"):
        tipo_doc = nd.metadata.get("tipo_documento")
        if tipos_documento is not None and tipo_doc not in tipos_documento:
            continue
        if mes_ref is not None:
            data_emissao = nd.metadata.get("data_emissao") or ""
            if not str(data_emissao).startswith(mes_ref):
                continue
        resultado.append(
            {
                "id": nd.id,
                "tipo_documento": tipo_doc,
                "nome_canonico": nd.nome_canonico,
                "metadata": nd.metadata,
            }
        )
    return resultado


def obter_transacoes_candidatas_para_documento(
    db: GrafoDB,
    data_iso: str,
    total: float,
    janela_dias: int,
    diff_valor_percentual: float,
) -> list[dict[str, Any]]:
    """Lista transações em (data ± janela_dias) cujo valor bate com `total`.

    Critério de match de valor: `|valor - total| <= max(total * diff_pct, 0.01)`.
    O centavo fixo absorve arredondamentos quando `diff_pct=0` e evita excluir
    casos exatos por ruído binário.

    Resultado: lista de dict {id, nome_canonico, metadata} ordenada por
    proximidade da data (ascendente).
    """
    from datetime import date, timedelta

    try:
        data_ref = date.fromisoformat(str(data_iso)[:10])
    except ValueError:
        return []

    tolerancia = max(abs(total) * diff_valor_percentual, 0.01)
    datas_alvo = {
        (data_ref + timedelta(days=delta)).isoformat()
        for delta in range(-janela_dias, janela_dias + 1)
    }

    candidatas: list[tuple[int, dict[str, Any], int]] = []
    for nd in db.listar_nodes(tipo="transacao"):
        meta = nd.metadata
        data_t = str(meta.get("data") or "")[:10]
        if data_t not in datas_alvo:
            continue
        try:
            valor_t = float(meta.get("valor") or 0.0)
        except (TypeError, ValueError):
            continue
        if abs(abs(valor_t) - abs(total)) > tolerancia:
            continue
        try:
            delta_dias = abs((date.fromisoformat(data_t) - data_ref).days)
        except ValueError:
            delta_dias = janela_dias
        candidatas.append(
            (
                nd.id,  # type: ignore[arg-type]
                {
                    "id": nd.id,
                    "nome_canonico": nd.nome_canonico,
                    "metadata": meta,
                    "delta_dias": delta_dias,
                },
                delta_dias,
            )
        )

    candidatas.sort(key=lambda t: t[2])
    return [c[1] for c in candidatas]


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
