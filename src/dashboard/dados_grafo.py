"""Consultas read-only ao grafo SQLite usadas pelo dashboard.

Extraído de ``src.dashboard.dados`` na Sprint ANTI-MIGUE-08 para manter
``dados.py`` abaixo de 800 linhas. Re-exportado pelo módulo original para
preservar contratos públicos (testes monkeypatcham via ``d.<nome>`` no
namespace de ``dados``).

Funções aqui agrupadas operam exclusivamente sobre ``data/output/grafo.sqlite``
em modo ``mode=ro`` e fazem graceful degradation (ADR-10) quando o grafo está
ausente: retornam estruturas vazias em vez de levantar exceção.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils.logger import configurar_logger

logger = configurar_logger("dashboard.dados_grafo")

CAMINHO_GRAFO: Path = Path(__file__).resolve().parents[2] / "data" / "output" / "grafo.sqlite"
CAMINHO_PROPOSTAS_LINKING: Path = (
    Path(__file__).resolve().parents[2] / "docs" / "propostas" / "linking"
)

def _caminho_grafo() -> Path:
    """Resolve CAMINHO_GRAFO honrando monkeypatch em ``src.dashboard.dados``.

    Testes legados monkeypatcham ``dashboard_dados.CAMINHO_GRAFO``; resolver
    em runtime preserva retrocompat sem ciclo de import (dados.py re-exporta
    deste modulo no fim do arquivo).
    """
    from src.dashboard import dados as _d  # noqa: PLC0415

    valor = getattr(_d, "CAMINHO_GRAFO", None)
    if isinstance(valor, Path):
        return valor
    return CAMINHO_GRAFO


def _caminho_propostas_linking() -> Path:
    """Resolve CAMINHO_PROPOSTAS_LINKING honrando monkeypatch em ``dados``."""
    from src.dashboard import dados as _d  # noqa: PLC0415

    valor = getattr(_d, "CAMINHO_PROPOSTAS_LINKING", None)
    if isinstance(valor, Path):
        return valor
    return CAMINHO_PROPOSTAS_LINKING



@st.cache_data(ttl=300)
def carregar_documentos_grafo() -> pd.DataFrame:
    """Carrega documentos do grafo SQLite como DataFrame read-only.

    Retorna DataFrame com colunas: doc_id, tipo_documento, cnpj_emitente,
    razao_social, data_emissao, total, status_linking, arquivo_origem.

    Status_linking é derivado assim:
      - "Vinculado": existe aresta documento_de saindo do documento
      - "Conflito": existe proposta em docs/propostas/linking/ cujo nome casa
                    com a chave canônica do documento (substring)
      - "Sem transação": caso contrário

    Se o grafo não existe, devolve DataFrame vazio (ADR-10).
    """
    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        logger.warning("grafo não encontrado em %s", cam_grafo)
        return pd.DataFrame(
            columns=[
                "doc_id",
                "tipo_documento",
                "cnpj_emitente",
                "razao_social",
                "data_emissao",
                "total",
                "status_linking",
                "arquivo_origem",
            ]
        )

    import sqlite3

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        docs: list[dict] = []
        for row in conn.execute(
            "SELECT id, nome_canonico, metadata FROM node WHERE tipo = 'documento'"
        ):
            meta_raw = row["metadata"] or "{}"
            try:
                meta = json.loads(meta_raw)
            except (json.JSONDecodeError, TypeError):
                meta = {}
            docs.append(
                {
                    "doc_id": int(row["id"]),
                    "nome_canonico": row["nome_canonico"],
                    "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                    "cnpj_emitente": meta.get("cnpj_emitente", ""),
                    "razao_social": meta.get("razao_social", ""),
                    "data_emissao": meta.get("data_emissao", ""),
                    "total": float(meta.get("total", 0.0) or 0.0),
                    "arquivo_origem": meta.get("arquivo_origem", ""),
                }
            )

        ids_vinculados: set[int] = set()
        for row in conn.execute("SELECT DISTINCT src_id FROM edge WHERE tipo = 'documento_de'"):
            ids_vinculados.add(int(row["src_id"]))
    finally:
        conn.close()

    cam_props = _caminho_propostas_linking()
    chaves_conflito: set[str] = set()
    if cam_props.exists():
        for arquivo in cam_props.glob("*.md"):
            chaves_conflito.add(arquivo.stem)

    for doc in docs:
        if doc["doc_id"] in ids_vinculados:
            doc["status_linking"] = "Vinculado"
        elif any(doc["nome_canonico"][:20] in chave for chave in chaves_conflito):
            doc["status_linking"] = "Conflito"
        else:
            doc["status_linking"] = "Sem transação"

    df = pd.DataFrame(docs)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "doc_id",
                "tipo_documento",
                "cnpj_emitente",
                "razao_social",
                "data_emissao",
                "total",
                "status_linking",
                "arquivo_origem",
            ]
        )
    return df


def contar_propostas_linking() -> int:
    """Conta arquivos .md em docs/propostas/linking/ (não conta subpastas)."""
    cam = _caminho_propostas_linking()
    if not cam.exists():
        return 0
    return sum(1 for _ in cam.glob("*.md"))


@st.cache_data(ttl=60)
def buscar_global(termo: str) -> dict[str, list[dict]]:
    """Busca case-insensitive no grafo SQLite (read-only).

    Executa LIKE contra `nome_canonico`, `aliases` (JSON textual) e
    `metadata` (JSON textual) para os quatro tipos principais:
    fornecedor, documento, transacao e item.                       # noqa: accent

    Returns:
        Dict com 4 chaves: ``fornecedores``, ``documentos``,
        ``transacoes`` e ``itens``. Cada valor é lista de dicts    # noqa: accent
        enxutos (id + campos principais) pronta para renderizar.
        Se o grafo não existe ou termo é vazio, todas as listas vêm
        vazias.
    """
    vazio: dict[str, list[dict]] = {
        "fornecedores": [],
        "documentos": [],
        "transacoes": [],
        "itens": [],
    }

    if not termo or not termo.strip():
        return vazio

    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        logger.warning("grafo não encontrado em %s", cam_grafo)
        return vazio

    import sqlite3

    termo_norm = termo.strip()
    padrao = f"%{termo_norm.lower()}%"

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        fornecedores = _buscar_fornecedores(conn, padrao)
        documentos = _buscar_documentos(conn, padrao)
        transacoes = _buscar_transacoes(conn, padrao)
        itens = _buscar_itens(conn, padrao)
    finally:
        conn.close()

    return {
        "fornecedores": fornecedores,
        "documentos": documentos,
        "transacoes": transacoes,
        "itens": itens,
    }


def _buscar_fornecedores(conn, padrao: str) -> list[dict]:
    """Retorna fornecedores cujo nome/alias/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, aliases, metadata "
        "FROM node "
        "WHERE tipo = 'fornecedor' "
        "  AND (LOWER(nome_canonico) LIKE ? "
        "    OR LOWER(aliases) LIKE ? "
        "    OR LOWER(metadata) LIKE ?) "
        "LIMIT 50"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao, padrao)):
        try:
            aliases = json.loads(row["aliases"] or "[]")
        except (json.JSONDecodeError, TypeError):
            aliases = []
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        fornecedor_id = int(row["id"])
        ndocs, total = _agregados_fornecedor(conn, fornecedor_id)
        resultados.append(
            {
                "id": fornecedor_id,
                "nome_canonico": row["nome_canonico"],
                "aliases": aliases,
                "cnpj": meta.get("cnpj", meta.get("cnpj_emitente", "")),
                "categoria": meta.get("categoria", ""),
                "total_documentos": ndocs,
                "total_gasto": total,
            }
        )
    return resultados


def _agregados_fornecedor(conn, fornecedor_id: int) -> tuple[int, float]:
    """Conta documentos e soma transações ligadas ao fornecedor."""
    ndocs = 0
    total = 0.0
    for row in conn.execute(
        "SELECT src_id FROM edge WHERE dst_id = ? AND tipo = 'fornecido_por'",
        (fornecedor_id,),
    ):
        doc_row = conn.execute("SELECT tipo FROM node WHERE id = ?", (row["src_id"],)).fetchone()
        if doc_row and doc_row["tipo"] == "documento":
            ndocs += 1

    for row in conn.execute(
        "SELECT src_id FROM edge WHERE dst_id = ? AND tipo = 'fornecido_por'",
        (fornecedor_id,),
    ):
        tx_row = conn.execute(
            "SELECT tipo, metadata FROM node WHERE id = ?", (row["src_id"],)
        ).fetchone()
        if tx_row and tx_row["tipo"] == "transacao":
            try:
                meta_tx = json.loads(tx_row["metadata"] or "{}")
                valor = float(meta_tx.get("valor", 0.0) or 0.0)
                total += abs(valor)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return ndocs, total


def _buscar_documentos(conn, padrao: str) -> list[dict]:
    """Retorna documentos cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'documento' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 100"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        resultados.append(
            {
                "id": int(row["id"]),
                "nome_canonico": row["nome_canonico"],
                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                "data": meta.get("data_emissao", ""),
                "razao_social": meta.get("razao_social", ""),
                "total": float(meta.get("total", 0.0) or 0.0),
            }
        )
    return resultados


def _buscar_transacoes(conn, padrao: str) -> list[dict]:
    """Retorna transações cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'transacao' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 200"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        data_raw = meta.get("data", "")
        data_str = str(data_raw)[:10] if data_raw else ""
        resultados.append(
            {
                "id": int(row["id"]),
                "data": data_str,
                "local": meta.get("local", ""),
                "valor": float(meta.get("valor", 0.0) or 0.0),
                "banco": meta.get("banco", ""),
                "tipo_transacao": meta.get("tipo", ""),
            }
        )
    resultados.sort(key=lambda r: r["data"], reverse=True)
    return resultados


def _buscar_itens(conn, padrao: str) -> list[dict]:
    """Retorna itens cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'item' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 100"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        resultados.append(
            {
                "id": int(row["id"]),
                "descricao": meta.get("descricao", row["nome_canonico"]),
                "data": meta.get("data_compra", ""),
                "valor": float(meta.get("valor_total", 0.0) or 0.0),
                "qtde": float(meta.get("qtde", 0.0) or 0.0),
                "cnpj": meta.get("cnpj_varejo", meta.get("cnpj", "")),
            }
        )
    return resultados


@st.cache_data(ttl=60)
def carregar_subgrafo(node_id: int, radius: int = 1) -> dict:
    """Retorna subgrafo a `radius` hops do node alvo (read-only, BFS).

    Graceful degradation (ADR-10): grafo ausente devolve estrutura vazia.
    Retorno:
        {
            "nodes": [{"id", "tipo", "nome_canonico", "metadata"}...],
            "edges": [{"src_id", "dst_id", "tipo"}...],
            "center_id": node_id,
        }
    """
    vazio: dict = {"nodes": [], "edges": [], "center_id": node_id}
    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        logger.warning("grafo não encontrado em %s", cam_grafo)
        return vazio
    if radius < 0:
        return vazio

    import sqlite3

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        visitados: set[int] = {node_id}
        fronteira: set[int] = {node_id}
        arestas_coletadas: list[dict] = []

        for _ in range(max(1, radius)):
            if not fronteira:
                break
            placeholders = ",".join("?" * len(fronteira))
            lista_ids = list(fronteira)
            sql_out = f"SELECT src_id, dst_id, tipo FROM edge WHERE src_id IN ({placeholders})"
            sql_in = f"SELECT src_id, dst_id, tipo FROM edge WHERE dst_id IN ({placeholders})"
            nova_fronteira: set[int] = set()
            for row in conn.execute(sql_out, lista_ids):
                arestas_coletadas.append(
                    {
                        "src_id": int(row["src_id"]),
                        "dst_id": int(row["dst_id"]),
                        "tipo": row["tipo"],
                    }
                )
                if int(row["dst_id"]) not in visitados:
                    nova_fronteira.add(int(row["dst_id"]))
            for row in conn.execute(sql_in, lista_ids):
                arestas_coletadas.append(
                    {
                        "src_id": int(row["src_id"]),
                        "dst_id": int(row["dst_id"]),
                        "tipo": row["tipo"],
                    }
                )
                if int(row["src_id"]) not in visitados:
                    nova_fronteira.add(int(row["src_id"]))
            visitados.update(nova_fronteira)
            fronteira = nova_fronteira

        # dedup de arestas (src,dst,tipo)
        vistos: set[tuple[int, int, str]] = set()
        arestas_unicas: list[dict] = []
        for ar in arestas_coletadas:
            chave = (ar["src_id"], ar["dst_id"], ar["tipo"])
            if chave in vistos:
                continue
            vistos.add(chave)
            arestas_unicas.append(ar)

        # carrega nodes visitados
        if not visitados:
            return vazio
        placeholders_n = ",".join("?" * len(visitados))
        nodes: list[dict] = []
        sql_nodes = (
            "SELECT id, tipo, nome_canonico, aliases, metadata "
            f"FROM node WHERE id IN ({placeholders_n})"
        )
        for row in conn.execute(sql_nodes, list(visitados)):
            try:
                meta = json.loads(row["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            try:
                aliases_list = json.loads(row["aliases"] or "[]")
                if not isinstance(aliases_list, list):
                    aliases_list = []
            except (json.JSONDecodeError, TypeError):
                aliases_list = []
            nodes.append(
                {
                    "id": int(row["id"]),
                    "tipo": row["tipo"],
                    "nome_canonico": row["nome_canonico"],
                    "aliases": aliases_list,
                    "metadata": meta,
                }
            )
    finally:
        conn.close()

    return {"nodes": nodes, "edges": arestas_unicas, "center_id": node_id}


def carregar_drill_down_transacao(transacao_id: int) -> dict:
    """Drill-down item por transação_id (INFRA-DRILL-DOWN-ITEM).

    Walk de 2 saltos no grafo: transação --documento_de--> documento
    --contem_item--> item. Retorna dict pronto para o painel
    ``painel_drill_down`` consumir:

        {
            "documento": {nome_canonico, tipo_documento, data_emissao,
                          razao_social, arquivo_origem} | None,
            "itens": [{codigo, descricao, quantidade,  # noqa: accent
                       valor_unitario, valor_total}, ...],
        }

    Quando ``transacao_id`` não tem aresta ``documento_de``, devolve
    ``{"documento": None, "itens": []}``. Graceful degradation
    (ADR-10) se o grafo está ausente.

    Lê em modo ``mode=ro`` -- não escreve no SQLite.
    """
    vazio: dict = {"documento": None, "itens": []}
    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        return vazio

    import sqlite3

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # 1º salto: transação -> documento (aresta documento_de aponta
        # de documento p/ transação; logo buscar dst_id == transacao_id).
        cur = conn.execute(
            "SELECT n.id, n.nome_canonico, n.metadata "
            "FROM edge e JOIN node n ON n.id = e.src_id "
            "WHERE e.dst_id = ? AND e.tipo = 'documento_de' "
            "  AND n.tipo = 'documento' "
            "LIMIT 1",
            (int(transacao_id),),
        )
        row_doc = cur.fetchone()
        if row_doc is None:
            return vazio
        try:
            meta_doc = json.loads(row_doc["metadata"] or "{}")
            if not isinstance(meta_doc, dict):
                meta_doc = {}
        except (json.JSONDecodeError, TypeError):
            meta_doc = {}
        documento = {
            "id": int(row_doc["id"]),
            "nome_canonico": row_doc["nome_canonico"],
            "tipo_documento": meta_doc.get("tipo_documento", "desconhecido"),
            "data_emissao": meta_doc.get("data_emissao", ""),
            "razao_social": meta_doc.get("razao_social", ""),
            "arquivo_origem": meta_doc.get("arquivo_origem", ""),
        }

        # 2º salto: documento -> item via contem_item.
        itens: list[dict] = []
        for row_item in conn.execute(
            "SELECT n.id, n.nome_canonico, n.metadata "
            "FROM edge e JOIN node n ON n.id = e.dst_id "
            "WHERE e.src_id = ? AND e.tipo = 'contem_item' "
            "  AND n.tipo = 'item'",
            (documento["id"],),
        ):
            try:
                meta_item = json.loads(row_item["metadata"] or "{}")
                if not isinstance(meta_item, dict):
                    meta_item = {}
            except (json.JSONDecodeError, TypeError):
                meta_item = {}
            itens.append(
                {
                    "id": int(row_item["id"]),
                    "codigo": meta_item.get("codigo")
                    or meta_item.get("ean")
                    or row_item["nome_canonico"],
                    "descricao": meta_item.get("descricao")
                    or meta_item.get("nome")
                    or row_item["nome_canonico"],
                    "quantidade": meta_item.get("quantidade")
                    or meta_item.get("qtde")
                    or 0,
                    "valor_unitario": meta_item.get("valor_unitario"),
                    "valor_total": meta_item.get("valor_total"),
                    "produto_canonico": meta_item.get("produto_canonico", ""),
                }
            )
    finally:
        conn.close()

    return {"documento": documento, "itens": itens}


def buscar_transacao_id_por_identificador(identificador: str) -> int | None:
    """Resolve ``transacao_id`` (PK do node) a partir do ``identificador``
    da linha do extrato.

    O extrato XLSX guarda em ``identificador`` o sha256 da transação que
    coincide com ``node.nome_canonico`` quando a transação é do tipo
    ``transacao``. Esta função faz a ponte para o drill-down acionado  # noqa: accent
    via ``?transacao_id=<sha8>`` (sufixo curto) ou sha256 completo.

    Aceita prefixo (sha8 = 8 caracteres). Quando há múltiplos matches,
    retorna o primeiro -- caller deve preferir sha256 completo. Quando
    não encontra, retorna None.
    """
    if not identificador:
        return None
    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        return None

    import sqlite3

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT id FROM node WHERE tipo='transacao' "
            "AND nome_canonico LIKE ? LIMIT 1",
            (f"{identificador}%",),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()


def listar_fornecedores_com_id() -> list[dict]:
    """Lista fornecedores do grafo com id + nome para seleção no selectbox.

    Ordenado alfabeticamente. Read-only. Devolve lista vazia se grafo ausente.
    """
    cam_grafo = _caminho_grafo()
    if not cam_grafo.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(f"file:{cam_grafo}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        resultados: list[dict] = []
        for row in conn.execute(
            "SELECT id, nome_canonico, aliases, metadata FROM node "
            "WHERE tipo = 'fornecedor' ORDER BY nome_canonico LIMIT 500"
        ):
            try:
                aliases_list = json.loads(row["aliases"] or "[]")
                if not isinstance(aliases_list, list):
                    aliases_list = []
            except (json.JSONDecodeError, TypeError):
                aliases_list = []
            try:
                meta = json.loads(row["metadata"] or "{}")
                if not isinstance(meta, dict):
                    meta = {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            resultados.append(
                {
                    "id": int(row["id"]),
                    "nome_canonico": row["nome_canonico"],
                    "aliases": aliases_list,
                    "metadata": meta,
                }
            )
    finally:
        conn.close()
    return resultados


# "A simplicidade é o último grau de sofisticação." -- Leonardo da Vinci
