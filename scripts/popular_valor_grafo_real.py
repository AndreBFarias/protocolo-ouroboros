"""Popula coluna `valor_grafo_real` em `revisao_humana.sqlite` (auditoria 4-way).

Para cada (item_id, dimensão) na tabela `revisão`, busca o node documento
correspondente em `data/output/grafo.sqlite` e extrai o valor canonico
persistido apos normalizacao do pipeline. Permite comparar:

  - ETL (extracao bruta antes do grafo)
  - Opus (decisão Opus apos ler arquivo)
  - Grafo (estado canonico apos sintetico Sprint 107 + normalizacao)
  - Humano (radio OK/Erro/N-A)

Idempotente: rodar 2x produz mesmo resultado. Falha-soft: erro ao buscar
node não aborta o run, deixa NULL na coluna.

Resolução item_id -> arquivo no grafo:
  - `node_<id>`: busca direto pelo id.
  - paths relativos (`raw/_classificar/...`): casa com metadata.arquivo_origem
    (relativo) OU constroi absoluto e casa com metadata.arquivo_origem (absoluto).

Mapeamento dimensão -> fonte canonica:
  - data        : metadata.data_emissao
  - valor       : metadata.total (ou metadata.bruto)
  - itens       : metadata.itens (lista) ou string vazia (sem itens granulares)
  - fornecedor  : razao_social do node fornecedor via aresta `fornecido_por`
                  (fallback: metadata.razao_social)
  - pessoa      : inferida de metadata.contribuinte (ANDRE/VITORIA) ou path

Sessão 2026-04-29 (auditoria 4-way pos-Sprint 108).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

_RAIZ = Path(__file__).resolve().parents[1]
_GRAFO_DB = _RAIZ / "data" / "output" / "grafo.sqlite"
_REVISAO_DB = _RAIZ / "data" / "output" / "revisao_humana.sqlite"

# Dimensoes canonicas (mesma ordem da Sprint 103 / DIMENSOES_CANONICAS).
_DIMENSOES: tuple[str, ...] = ("data", "valor", "itens", "fornecedor", "pessoa")


def _buscar_node_id(conn: sqlite3.Connection, item_id: str) -> int | None:
    """Resolve item_id -> node.id no grafo. Retorna None se não encontrado.

    Estrategia (todas tentadas em ordem):
    1. node_<id> direto.
    2. Match exato em arquivo_origem (relativo OU absoluto).
    3. LIKE com sufixo do path (lida com inconsistencia AUDIT-PATH-RELATIVO:
       holerites usam path relativo `data/raw/...` enquanto DAS/boletos
       usam path absoluto `/home/.../data/raw/...`).
    """
    if item_id.startswith("node_"):
        try:
            return int(item_id.split("_", 1)[1])
        except ValueError:
            return None

    # Match exato em variantes conhecidas
    candidatos_exatos: list[str] = [item_id]
    abs_a = str((_RAIZ / item_id).resolve())
    if abs_a not in candidatos_exatos:
        candidatos_exatos.append(abs_a)
    if item_id.startswith("raw/"):
        abs_b = str((_RAIZ / "data" / item_id).resolve())
        if abs_b not in candidatos_exatos:
            candidatos_exatos.append(abs_b)
        rel_b = "data/" + item_id  # holerites no grafo usam esse formato
        if rel_b not in candidatos_exatos:
            candidatos_exatos.append(rel_b)
    for cand in candidatos_exatos:
        cur = conn.execute(
            "SELECT id FROM node WHERE tipo='documento' "
            "AND json_extract(metadata, '$.arquivo_origem') = ? LIMIT 1",
            (cand,),
        )
        row = cur.fetchone()
        if row:
            return int(row[0])

    # Fallback LIKE %item_id (sufixo). Tipicamente robusto contra prefixos
    # divergentes; risco baixo de colisão porque hashes nos nomes são unicos.
    cur = conn.execute(
        "SELECT id FROM node WHERE tipo='documento' "
        "AND json_extract(metadata, '$.arquivo_origem') LIKE ? LIMIT 1",
        (f"%{item_id}",),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    return None


def _carregar_node(conn: sqlite3.Connection, node_id: int) -> dict | None:
    """Carrega metadata + tipo + nome_canonico de um node."""
    cur = conn.execute(
        "SELECT id, tipo, nome_canonico, metadata FROM node WHERE id = ?",
        (node_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    try:
        meta = json.loads(row[3] or "{}")
    except json.JSONDecodeError:
        meta = {}
    return {
        "id": row[0],
        "tipo": row[1],
        "nome_canonico": row[2],
        "metadata": meta,
    }


def _fornecedor_via_aresta(conn: sqlite3.Connection, doc_id: int) -> str:
    """Busca razao_social do node fornecedor ligado via `fornecido_por`."""
    cur = conn.execute(
        "SELECT n.metadata FROM edge e JOIN node n ON n.id=e.dst_id "
        "WHERE e.src_id=? AND e.tipo='fornecido_por' LIMIT 1",
        (doc_id,),
    )
    row = cur.fetchone()
    if not row:
        return ""
    try:
        meta = json.loads(row[0] or "{}")
    except json.JSONDecodeError:
        return ""
    return str(meta.get("razao_social", "") or "")


def _inferir_pessoa(metadata: dict[str, Any], item_id: str) -> str:
    """Infere pessoa canonica (andre/vitoria/casal) a partir do metadata.

    Sprint AUDIT2-METADATA-PESSOA-CANONICA: ingestor agora grava
    `metadata.pessoa` direto. Quando presente e valida, usa direto.
    Fallbacks preservados para nodes pre-AUDIT2 ou onde o backfill
    ainda não rodou.
    """
    pessoa_explicita = metadata.get("pessoa")
    if pessoa_explicita in {"andre", "vitoria", "casal"}:
        return str(pessoa_explicita)
    contribuinte = str(metadata.get("contribuinte", "") or "").upper()
    if "ANDRE" in contribuinte:
        return "andre"
    if "VITORIA" in contribuinte or "VITÓRIA" in contribuinte:
        return "vitoria"
    item_id_lower = item_id.lower()
    if "/andre/" in item_id_lower:
        return "andre"
    if "/vitoria/" in item_id_lower:
        return "vitoria"
    if "/casal/" in item_id_lower:
        return "casal"
    return ""


def _extrair_valor_grafo(
    conn: sqlite3.Connection,
    node: dict,
    dimensão: str,
) -> str:
    """Extrai o valor canonico da `dimensão` a partir do node documento."""
    meta = node["metadata"]
    if dimensão == "data":
        return str(meta.get("data_emissao", "") or "")
    if dimensão == "valor":
        total = meta.get("total")
        if total in (None, ""):
            total = meta.get("bruto")
        if total in (None, ""):
            return ""
        try:
            return f"{float(total):.2f}"
        except (TypeError, ValueError):
            return str(total)
    if dimensão == "itens":
        itens = meta.get("itens")
        if isinstance(itens, list):
            return f"{len(itens)} item(ns)"
        return ""
    if dimensão == "fornecedor":
        razao = _fornecedor_via_aresta(conn, int(node["id"]))
        if razao:
            return razao
        return str(meta.get("razao_social", "") or "")
    if dimensão == "pessoa":
        return _inferir_pessoa(meta, node.get("nome_canonico", ""))
    return ""


def popular(
    grafo_db: Path = _GRAFO_DB,
    revisao_db: Path = _REVISAO_DB,
    sobrescrever: bool = False,
) -> dict[str, int]:
    """Atualiza coluna `valor_grafo_real` em todas as marcacoes da `revisão`.

    Args:
        grafo_db: SQLite do grafo (read-only).
        revisao_db: SQLite de revisão_humana (read-write).
        sobrescrever: se True, atualiza mesmo quando ja existe valor; se False
            (default) so atualiza onde valor_grafo_real eh NULL (idempotencia).

    Retorna {atualizadas, ja_preenchidas, sem_node, total}.
    """
    if not grafo_db.exists():
        print(f"[ERRO] {grafo_db} não existe.", file=sys.stderr)
        return {"atualizadas": 0, "ja_preenchidas": 0, "sem_node": 0, "total": 0}

    contagens = {"atualizadas": 0, "ja_preenchidas": 0, "sem_node": 0, "total": 0}

    conn_grafo = sqlite3.connect(f"file:{grafo_db}?mode=ro", uri=True)
    conn_rev = sqlite3.connect(revisao_db)
    try:
        cur_rev = conn_rev.execute("SELECT item_id, dimensao, valor_grafo_real FROM revisao")
        marcacoes = cur_rev.fetchall()
        contagens["total"] = len(marcacoes)

        # Cache node_id por item_id (varias dimensoes do mesmo item).
        cache_node_id: dict[str, int | None] = {}
        cache_node: dict[int, dict | None] = {}

        for item_id, dimensão, valor_atual in marcacoes:
            if not sobrescrever and valor_atual not in (None, ""):
                contagens["ja_preenchidas"] += 1
                continue

            if item_id not in cache_node_id:
                try:
                    cache_node_id[item_id] = _buscar_node_id(conn_grafo, item_id)
                except sqlite3.Error:
                    cache_node_id[item_id] = None
            node_id = cache_node_id[item_id]
            if node_id is None:
                contagens["sem_node"] += 1
                continue

            if node_id not in cache_node:
                try:
                    cache_node[node_id] = _carregar_node(conn_grafo, node_id)
                except sqlite3.Error:
                    cache_node[node_id] = None
            node = cache_node[node_id]
            if node is None:
                contagens["sem_node"] += 1
                continue

            try:
                valor_grafo = _extrair_valor_grafo(conn_grafo, node, dimensão)
            except (sqlite3.Error, KeyError, TypeError, ValueError):
                # Falha-soft: log e segue.
                continue

            conn_rev.execute(
                "UPDATE revisao SET valor_grafo_real = ? WHERE item_id = ? AND dimensao = ?",
                (valor_grafo, item_id, dimensão),
            )
            contagens["atualizadas"] += 1

        conn_rev.commit()
    finally:
        conn_grafo.close()
        conn_rev.close()
    return contagens


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Popula coluna valor_grafo_real em revisao_humana.sqlite a partir "
            "do grafo.sqlite. Permite comparacao 4-way (ETL/Opus/Grafo/Humano) "
            "no Revisor Visual."
        )
    )
    parser.add_argument(
        "--grafo-db",
        type=Path,
        default=_GRAFO_DB,
        help="Caminho do SQLite do grafo (default: data/output/grafo.sqlite).",
    )
    parser.add_argument(
        "--revisao-db",
        type=Path,
        default=_REVISAO_DB,
        help="Caminho do SQLite de revisão_humana (default: data/output/revisao_humana.sqlite).",
    )
    parser.add_argument(
        "--sobrescrever",
        action="store_true",
        help="Atualiza valor_grafo_real mesmo quando ja preenchido (perde idempotencia).",
    )
    args = parser.parse_args(argv)

    contagens = popular(
        grafo_db=args.grafo_db,
        revisao_db=args.revisao_db,
        sobrescrever=args.sobrescrever,
    )
    print(
        f"Total: {contagens['total']} marcacoes\n"
        f"Atualizadas: {contagens['atualizadas']}\n"
        f"Ja preenchidas (skip idempotente): {contagens['ja_preenchidas']}\n"
        f"Sem node correspondente no grafo: {contagens['sem_node']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
