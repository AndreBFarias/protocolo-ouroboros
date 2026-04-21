"""Migração inicial do XLSX consolidado para o grafo SQLite. Sprint 42.

Lê `data/output/ouroboros_*.xlsx` aba `extrato`, popula:

  Nodes:
    - transacao  (1 por linha; nome_canonico = hash data+valor+local+banco)  # noqa: accent
    - fornecedor (contraparte, com entity resolution via rapidfuzz)
    - categoria  (1 por categoria distinta)
    - periodo    (1 por YYYY-MM distinto)
    - conta      (1 por banco_origem distinto)
    - tag_irpf   (1 por tag distinta)

  Edges:
    - origem      transacao -> conta   (sempre)  # noqa: accent
    - ocorre_em   transacao -> periodo (sempre)  # noqa: accent
    - categoria_de transacao -> categoria (sempre)  # noqa: accent
    - contraparte transacao -> fornecedor (quando local != banco/transferência)  # noqa: accent
    - irpf        transacao -> tag_irpf (quando tag_irpf não-nulo)  # noqa: accent

Idempotente: rodar duas vezes não duplica (UNIQUE em node e edge).

Uso:
    python -m src.graph.migracao_inicial
    python -m src.graph.migracao_inicial --limpar  # apaga e re-popula (dev)
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from src.graph.db import GrafoDB, caminho_padrao
from src.graph.entity_resolution import normalizar_fornecedor, resolver_fornecedor
from src.utils.logger import configurar_logger

logger = configurar_logger("graph.migracao")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_OUTPUT: Path = _RAIZ_REPO / "data" / "output"


# ============================================================================
# Helpers
# ============================================================================


def _hash_transacao(data: Any, valor: float, local: str, banco: str) -> str:
    """Identificador canônico determinístico para uma transação."""
    chave = f"{data}|{valor:.2f}|{local}|{banco}"
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()[:16]


def _localizar_xlsx_mais_recente() -> Path:
    """Devolve o XLSX ouroboros_*.xlsx mais recente em data/output/."""
    candidatos = sorted(_PATH_OUTPUT.glob("ouroboros_*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(f"nenhum ouroboros_*.xlsx em {_PATH_OUTPUT}")
    return candidatos[-1]


def _str_normalizada(valor: Any, default: str = "") -> str:
    """Converte None/NaN para `default`; trim e str."""
    if valor is None:
        return default
    if isinstance(valor, float) and pd.isna(valor):
        return default
    return str(valor).strip() or default


# ============================================================================
# Migração
# ============================================================================


def executar(
    db_path: Path | None = None, xlsx_path: Path | None = None, limpar: bool = False
) -> dict[str, Any]:
    """Executa migração completa. Idempotente.

    Args:
        db_path: caminho do SQLite. Default = data/output/grafo.sqlite.
        xlsx_path: XLSX fonte. Default = ouroboros_*.xlsx mais recente.
        limpar: se True, limpa o grafo antes de migrar (DEV).

    Returns:
        Dict com estatísticas pós-migração.
    """
    db_path = db_path or caminho_padrao()
    xlsx_path = xlsx_path or _localizar_xlsx_mais_recente()
    logger.info("migração inicial: db=%s, xlsx=%s", db_path, xlsx_path)

    df = pd.read_excel(xlsx_path, sheet_name="extrato")
    logger.info("xlsx carregado: %d linhas", len(df))

    with GrafoDB(db_path) as db:
        db.criar_schema()
        if limpar:
            db.limpar()

        # Pass 1: cria todos os nodes auxiliares (categorias, periodos, contas,
        # tag_irpf, fornecedores). Necessário antes das transações para obter
        # os ids e criar arestas.
        ids_categorias = _migrar_categorias(db, df)
        ids_periodos = _migrar_periodos(db, df)
        ids_contas = _migrar_contas(db, df)
        ids_tags_irpf = _migrar_tags_irpf(db, df)
        ids_fornecedores = _migrar_fornecedores(db, df)

        # Pass 2: transações + arestas (uma por linha).
        n_transacoes, n_arestas = _migrar_transacoes_e_arestas(
            db,
            df,
            ids_categorias=ids_categorias,
            ids_periodos=ids_periodos,
            ids_contas=ids_contas,
            ids_tags_irpf=ids_tags_irpf,
            ids_fornecedores=ids_fornecedores,
        )

        stats = db.estatisticas()
        logger.info(
            "migração concluída: %d transações, %d arestas, total nodes=%d edges=%d",
            n_transacoes,
            n_arestas,
            stats["nodes_total"],
            stats["edges_total"],
        )
        return stats


def _migrar_categorias(db: GrafoDB, df: pd.DataFrame) -> dict[str, int]:
    ids: dict[str, int] = {}
    for cat in df["categoria"].dropna().unique():
        nome = _str_normalizada(cat)
        if not nome:
            continue
        ids[nome] = db.upsert_node("categoria", nome)
    logger.info("categorias migradas: %d distintas", len(ids))
    return ids


def _migrar_periodos(db: GrafoDB, df: pd.DataFrame) -> dict[str, int]:
    ids: dict[str, int] = {}
    for periodo in df["mes_ref"].dropna().unique():
        nome = _str_normalizada(periodo)
        if not nome:
            continue
        ids[nome] = db.upsert_node("periodo", nome)
    logger.info("periodos migrados: %d distintos", len(ids))
    return ids


def _migrar_contas(db: GrafoDB, df: pd.DataFrame) -> dict[str, int]:
    ids: dict[str, int] = {}
    for banco in df["banco_origem"].dropna().unique():
        nome = _str_normalizada(banco)
        if not nome:
            continue
        ids[nome] = db.upsert_node("conta", nome)
    logger.info("contas migradas: %d distintas", len(ids))
    return ids


def _migrar_tags_irpf(db: GrafoDB, df: pd.DataFrame) -> dict[str, int]:
    ids: dict[str, int] = {}
    for tag in df["tag_irpf"].dropna().unique():
        nome = _str_normalizada(tag)
        if not nome:
            continue
        ids[nome] = db.upsert_node("tag_irpf", nome)
    logger.info("tags_irpf migradas: %d distintas", len(ids))
    return ids


def _migrar_fornecedores(db: GrafoDB, df: pd.DataFrame) -> dict[str, int]:
    """Cria 1 node por contraparte distinta, aplicando entity resolution.

    `local` contém variantes ("NEOENERGIA", "Neoenergia S/A", "neoenergia").
    Normalização determinística + fuzzy decide qual canônico usar; nomes
    variantes viram aliases.
    """
    locais = [str(local) for local in df["local"].dropna().unique() if str(local).strip()]
    canonicos: list[str] = []
    aliases_por_canonico: dict[str, set[str]] = {}
    raw_para_canonico: dict[str, str] = {}

    for nome_bruto in locais:
        resultado = resolver_fornecedor(nome_bruto, canonicos)
        canonico = resultado.nome_canonico
        if resultado.decisao == "novo" or resultado.fonte == "novo":
            canonicos.append(canonico)
            aliases_por_canonico.setdefault(canonico, set())
        # Adiciona o nome bruto como alias (exceto se for igual ao canônico)
        if normalizar_fornecedor(nome_bruto) != canonico:
            aliases_por_canonico.setdefault(canonico, set()).add(nome_bruto)
        raw_para_canonico[nome_bruto] = canonico

    ids: dict[str, int] = {}
    for canonico in canonicos:
        aliases = sorted(aliases_por_canonico.get(canonico, set()))
        ids[canonico] = db.upsert_node("fornecedor", canonico, aliases=aliases)

    # Mapeia também os nomes brutos para o id do canônico
    for nome_bruto, canonico in raw_para_canonico.items():
        ids[nome_bruto] = ids[canonico]

    logger.info(
        "fornecedores migrados: %d canônicos a partir de %d locais distintos",
        len(canonicos),
        len(locais),
    )
    return ids


def _migrar_transacoes_e_arestas(
    db: GrafoDB,
    df: pd.DataFrame,
    *,
    ids_categorias: dict[str, int],
    ids_periodos: dict[str, int],
    ids_contas: dict[str, int],
    ids_tags_irpf: dict[str, int],
    ids_fornecedores: dict[str, int],
) -> tuple[int, int]:
    n_transacoes = 0
    n_arestas = 0
    for row in df.itertuples(index=False):
        data = getattr(row, "data", None)
        valor = float(getattr(row, "valor", 0.0) or 0.0)
        local = _str_normalizada(getattr(row, "local", ""))
        banco = _str_normalizada(getattr(row, "banco_origem", ""))
        categoria = _str_normalizada(getattr(row, "categoria", ""))
        periodo = _str_normalizada(getattr(row, "mes_ref", ""))
        tag_irpf = _str_normalizada(getattr(row, "tag_irpf", ""))
        tipo_transacao = _str_normalizada(getattr(row, "tipo", "Despesa"))

        if not local or not banco:
            continue  # linhas inválidas (sem local ou banco) -- pulam

        hash_t = _hash_transacao(data, valor, local, banco)
        metadata: dict[str, Any] = {
            "data": str(data),
            "valor": valor,
            "local": local,
            "banco": banco,
            "tipo": tipo_transacao,
            "forma_pagamento": _str_normalizada(getattr(row, "forma_pagamento", "")),
            "quem": _str_normalizada(getattr(row, "quem", "")),
            "classificacao": _str_normalizada(getattr(row, "classificacao", "")),
        }
        id_transacao = db.upsert_node("transacao", hash_t, metadata=metadata)
        n_transacoes += 1

        # Edge: categoria_de
        if categoria and categoria in ids_categorias:
            db.adicionar_edge(id_transacao, ids_categorias[categoria], "categoria_de")
            n_arestas += 1

        # Edge: ocorre_em
        if periodo and periodo in ids_periodos:
            db.adicionar_edge(id_transacao, ids_periodos[periodo], "ocorre_em")
            n_arestas += 1

        # Edge: origem
        if banco and banco in ids_contas:
            db.adicionar_edge(id_transacao, ids_contas[banco], "origem")
            n_arestas += 1

        # Edge: contraparte (se temos fornecedor mapeado)
        if local in ids_fornecedores:
            db.adicionar_edge(id_transacao, ids_fornecedores[local], "contraparte")
            n_arestas += 1

        # Edge: irpf
        if tag_irpf and tag_irpf in ids_tags_irpf:
            db.adicionar_edge(id_transacao, ids_tags_irpf[tag_irpf], "irpf")
            n_arestas += 1

    return n_transacoes, n_arestas


# ============================================================================
# CLI
# ============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limpar", action="store_true", help="apaga grafo antes de migrar")
    parser.add_argument("--xlsx", type=Path, default=None, help="caminho do XLSX fonte")
    parser.add_argument("--db", type=Path, default=None, help="caminho do SQLite alvo")
    args = parser.parse_args()

    stats = executar(db_path=args.db, xlsx_path=args.xlsx, limpar=args.limpar)
    logger.info("estatísticas finais: %s", stats)


if __name__ == "__main__":
    main()


# "Quem migra leva o que importa; quem se muda perde o que esquece." -- princípio do arquivista
