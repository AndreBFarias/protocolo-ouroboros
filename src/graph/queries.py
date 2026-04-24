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

    Ordem de preferência (Sprint 60 + Sprint 92a):
    1. Primeiro elemento de `aliases` (JSON string ou lista já decodificada).
    2. Label especializado por tipo:
       - `transacao`: `<YYYY-MM-DD> R$ <valor> <local_curto>` lido da  # noqa: accent
         metadata (Sprint 92a item 1: evita mostrar hash sha256 ao usuário).
    3. `metadata.razao_social` quando presente.
    4. `nome_canonico` truncado em 40 caracteres com reticências se maior.

    Aceita `aliases` e `metadata` como string JSON (formato de `GrafoDB`) ou
    como estruturas Python já deserializadas (formato usado pelo dashboard
    após `json.loads`). Assim pode ser chamado em qualquer camada.

    Observação de schema (ADR-14, N-para-N): a chave `tipo` no dict do node
    permanece sem acento (`"transacao"`, `"periodo"`). A acentuação só aparece
    no rótulo exibido ao humano — nunca em chave que participa de contrato.
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

    # Sprint 92a item 1: transações sem alias vêm com nome_canonico = hash
    # sha256 (ver `src/graph/hash_transacao.py`). Montar label humano a partir
    # da metadata melhora drasticamente a leitura do grafo full-page.
    if str(node.get("tipo") or "") == "transacao":
        rotulo_tx = _label_transacao(metadata)
        if rotulo_tx:
            return rotulo_tx

    razao_social = metadata.get("razao_social")
    if razao_social and str(razao_social).strip():
        return str(razao_social)

    canonico = str(node.get("nome_canonico") or "")
    if len(canonico) > _LIMITE_LABEL_FALLBACK:
        return canonico[:_LIMITE_LABEL_FALLBACK] + "..."
    return canonico


def _label_transacao(metadata: dict[str, Any]) -> str:
    """Monta `<data> R$ <valor> <local>` a partir da metadata de uma transação.

    Retorna string vazia se faltar dado essencial (data e valor juntos) --
    assim `label_humano` segue para o próximo fallback (razao_social / nc).
    """
    data_raw = str(metadata.get("data") or "")[:10]
    valor_raw = metadata.get("valor")
    local_raw = str(metadata.get("local") or "").strip()

    try:
        valor_num = float(valor_raw) if valor_raw is not None else None
    except (TypeError, ValueError):
        valor_num = None

    if not data_raw or valor_num is None:
        return ""

    # Formato monetário PT-BR (vírgula decimal, ponto milhar).
    valor_abs = abs(valor_num)
    valor_br = f"{valor_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    if local_raw:
        local_curto = local_raw if len(local_raw) <= 20 else local_raw[:17] + "..."
        return f"{data_raw} R$ {valor_br} {local_curto}"
    return f"{data_raw} R$ {valor_br}"


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


def transacoes_com_documento(db: GrafoDB) -> set[str]:
    """Sprint 87.2 (ADR-20): identificadores de transações com documento vinculado.

    Retorna o conjunto de `nome_canonico` dos nodes `transacao` que possuem ao  # noqa: accent
    menos uma aresta `documento_de` apontando para eles. Usado pela coluna
    "Doc?" do Extrato e pela gap analysis (`calcular_completude`) para marcar
    cobertura documental real sem percorrer o grafo inteiro em cada render.

    A aresta canônica é `documento -> transacao` com `tipo='documento_de'`  # noqa: accent
    (ver `src/graph/linking.py::EDGE_TIPO_DOCUMENTO_DE`). O lado da transação
    é o `dst_id` e o lado do documento é o `src_id`. Idempotência do edge é
    garantida por UNIQUE(src,dst,tipo) no schema.

    Retorna set vazio quando não há arestas `documento_de` no grafo. Não
    levanta exceção se o grafo estiver vazio -- retorno está sempre definido.
    """
    cursor = db._conn.execute(
        """
        SELECT DISTINCT n.nome_canonico
        FROM node n
        JOIN edge e ON e.dst_id = n.id
        WHERE n.tipo = 'transacao' AND e.tipo = 'documento_de'
        """,
    )
    return {str(row[0]) for row in cursor.fetchall() if row[0] is not None}


def total_arestas_por_tipo(db: GrafoDB, tipo_edge: str) -> int:
    """Sprint 87.7: contagem de arestas de um tipo específico no grafo.

    Usado pelo módulo de análise de pagamentos para decidir quando o grafo
    tem cobertura suficiente para ser fonte primária de reconciliação
    boleto-transação. Abaixo do limiar configurado, o caller deve cair na
    heurística textual (`src.analysis.pagamentos.carregar_boletos`).

    Retorna 0 quando o grafo está vazio ou o tipo não existe. Não levanta
    exceção para grafo recém-criado -- o SELECT COUNT sempre responde.
    """
    cursor = db._conn.execute(
        "SELECT COUNT(*) FROM edge WHERE tipo = ?",
        (tipo_edge,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def grafo_filtrado(
    db: GrafoDB,
    tipos: list[str] | None = None,
    incluir_orfaos: bool = False,
    limite: int = 500,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Query da Sprint 78: devolve (nodes, edges) para o grafo visual.

    - Filtra nós por `tipos` (default: fornecedor, documento, categoria, transacao).
    - Ordena por grau decrescente e aplica `limite`.
    - Se `incluir_orfaos=False`, remove nós com grau 0.
    - Edges devolvidos conectam apenas nós do subconjunto retornado.
    """
    # None = default canônico; [] = filtro explícito "nada"
    if tipos is None:
        tipos = ["fornecedor", "documento", "categoria", "transacao"]
    if not tipos:
        return [], []

    placeholders = ",".join("?" * len(tipos))
    query_nodes = f"""
        SELECT n.id, n.tipo, n.nome_canonico, n.aliases, n.metadata,
               (SELECT COUNT(*) FROM edge e
                WHERE e.src_id = n.id OR e.dst_id = n.id) as grau
        FROM node n
        WHERE n.tipo IN ({placeholders})
        ORDER BY grau DESC, n.id ASC
        LIMIT ?
    """
    cursor = db._conn.execute(query_nodes, (*tipos, int(limite)))
    nodes_raw = cursor.fetchall()
    nodes: list[dict[str, Any]] = [
        {
            "id": row[0],
            "tipo": row[1],
            "nome_canonico": row[2],
            "aliases": row[3],
            "metadata": row[4],
            "grau": row[5] or 0,
        }
        for row in nodes_raw
    ]
    if not incluir_orfaos:
        nodes = [n for n in nodes if n["grau"] > 0]

    ids = [n["id"] for n in nodes]
    if not ids:
        return nodes, []

    placeholders_edge = ",".join("?" * len(ids))
    query_edges = f"""
        SELECT src_id, dst_id, tipo, peso
        FROM edge
        WHERE src_id IN ({placeholders_edge}) AND dst_id IN ({placeholders_edge})
    """
    cursor = db._conn.execute(query_edges, (*ids, *ids))
    edges: list[dict[str, Any]] = [
        {"src": row[0], "dst": row[1], "tipo": row[2], "peso": row[3] or 1.0}
        for row in cursor.fetchall()
    ]
    return nodes, edges


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
