#!/usr/bin/env python3
"""Dedup retroativo de NFCe duplicadas por ruído de OCR no grafo SQLite.

Sprint INFRA-NFCE-DEDUP-OCR-DUPLICATAS (2026-05-12).

Origem: auditoria artesanal detectou 4 nodes ``documento`` (tipo NFCe modelo 65)
para apenas 2 NFCe físicas. Cada nota real virou 2 nodes com chave_44 divergente
em 9-10 dígitos (zona OCR ruim), mas com total, data e CNPJ idênticos. Spec
original supôs diff <= 4; auditoria empírica mediu 9 e 10 -- limite padrão
deste script é portanto 10, calibrado pelos dados reais.

O que faz:

1. Backup do grafo SQLite em ``/tmp/grafo_backup_nfce_dedup_<ts>.sqlite``.
2. Lista nodes NFCe agrupados por (cnpj_emitente, data_emissao, total).
3. Para cada grupo com >1 node, identifica pares irmãos via ``_eh_mesma_nfce``.
4. Mantém o node com mais itens (qtde > 0); aresta do perdedor é re-apontada
   ao vencedor (alias preserva a chave_44 do perdedor). Perdedor é removido.
5. Idempotente: rodar 2x devolve 0 fusões na segunda.

Uso:

    python -m scripts.dedup_nfce_grafo                     # dry-run
    python -m scripts.dedup_nfce_grafo --apply             # aplica mudanças
    python -m scripts.dedup_nfce_grafo --max-diff-chave 6  # limite custom

Achado importante: chave_44 contém DV calculado sobre os dígitos. Quando OCR
troca dígitos no meio, o DV "valida" porque o erro acumula só em 1 posição
final. Isso explica como duas chaves OCR-distintas passam pelo
``valida_digito_verificador`` -- nenhum dos dois é a chave real impressa.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

# Permite execução direta via ``python scripts/dedup_nfce_grafo.py``.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.graph.db import GrafoDB, caminho_padrao  # noqa: E402
from src.graph.ingestor_documento import (  # noqa: E402
    _completude_nfce,
    _eh_mesma_nfce,
)
from src.utils.logger import configurar_logger  # noqa: E402

logger = configurar_logger("scripts.dedup_nfce_grafo")


#: Limite calibrado pelos 4 nodes auditados em 2026-05-12 (distâncias 9 e 10).
#: Spec original sugeria 4; padrão deste script é 10 para casar dados reais.
LIMITE_DIFF_RETROATIVO_PADRAO: int = 10


def _listar_nfce(db: GrafoDB) -> list[tuple[int, dict[str, Any]]]:
    cursor = db._conn.execute(  # noqa: SLF001
        """
        SELECT id, metadata FROM node
        WHERE tipo = 'documento'
          AND json_extract(metadata, '$.tipo_documento') = 'nfce_modelo_65'
        ORDER BY id ASC
        """
    )
    nfces: list[tuple[int, dict[str, Any]]] = []
    for node_id, meta_raw in cursor.fetchall():
        try:
            meta = json.loads(meta_raw) if meta_raw else {}
        except json.JSONDecodeError:
            continue
        nfces.append((int(node_id), meta))
    return nfces


def _fundir_par(
    db: GrafoDB,
    vencedor_id: int,
    perdedor_id: int,
    perdedor_meta: dict[str, Any],
) -> int:
    """Re-aponta arestas do perdedor para o vencedor e apaga o perdedor.

    Idempotente: arestas já existentes no vencedor são ignoradas (UNIQUE
    constraint do schema). Devolve número de arestas re-apontadas.
    """
    conn = db._conn  # noqa: SLF001

    # Coleta as arestas do perdedor antes de mexer
    rows_out = conn.execute(
        "SELECT dst_id, tipo, peso, evidencia FROM edge WHERE src_id = ?",
        (perdedor_id,),
    ).fetchall()
    rows_in = conn.execute(
        "SELECT src_id, tipo, peso, evidencia FROM edge WHERE dst_id = ?",
        (perdedor_id,),
    ).fetchall()

    redirecionadas = 0
    for dst_id, tipo, peso, evidencia in rows_out:
        conn.execute(
            "INSERT OR IGNORE INTO edge (src_id, dst_id, tipo, peso, evidencia) "
            "VALUES (?, ?, ?, ?, ?)",
            (vencedor_id, dst_id, tipo, peso, evidencia),
        )
        redirecionadas += 1
    for src_id, tipo, peso, evidencia in rows_in:
        conn.execute(
            "INSERT OR IGNORE INTO edge (src_id, dst_id, tipo, peso, evidencia) "
            "VALUES (?, ?, ?, ?, ?)",
            (src_id, vencedor_id, tipo, peso, evidencia),
        )
        redirecionadas += 1

    # Anexa chave_44 do perdedor como alias do vencedor (preserva histórico).
    chave_perdedor = perdedor_meta.get("chave_44") or ""
    if chave_perdedor:
        node_v = db.buscar_node_por_id(vencedor_id)
        aliases_existentes = list(node_v.aliases) if node_v else []
        if chave_perdedor not in aliases_existentes:
            db.upsert_node(
                "documento",
                node_v.nome_canonico if node_v else chave_perdedor,
                metadata={"chave_44_alternativa": chave_perdedor},
                aliases=[chave_perdedor],
            )

    # Remove o perdedor (CASCADE elimina arestas residuais)
    conn.execute("DELETE FROM node WHERE id = ?", (perdedor_id,))
    conn.commit()
    return redirecionadas


def dedup_grafo(
    db: GrafoDB,
    *,
    limite_diff_chave: int = LIMITE_DIFF_RETROATIVO_PADRAO,
    apply: bool = False,
) -> dict[str, Any]:
    """Identifica e (opcionalmente) funde NFCe duplicadas no grafo.

    Devolve dict com::

        {
          "antes": <N nodes NFCe>,
          "depois": <N nodes NFCe pós-dedup>,
          "fusoes": [(vencedor_id, perdedor_id, motivo), ...],
          "arestas_redirecionadas": <int>,
        }
    """
    nfces = _listar_nfce(db)
    antes = len(nfces)
    fusoes: list[tuple[int, int, str]] = []
    arestas_redirecionadas = 0

    ja_perdedores: set[int] = set()
    for i, (id_a, meta_a) in enumerate(nfces):
        if id_a in ja_perdedores:
            continue
        for id_b, meta_b in nfces[i + 1 :]:
            if id_b in ja_perdedores or id_a in ja_perdedores:
                continue
            if _eh_mesma_nfce(
                str(meta_a.get("chave_44") or ""),
                str(meta_b.get("chave_44") or ""),
                meta_a.get("total"),
                meta_b.get("total"),
                str(meta_a.get("data_emissao") or "")[:10],
                str(meta_b.get("data_emissao") or "")[:10],
                str(meta_a.get("cnpj_emitente") or ""),
                str(meta_b.get("cnpj_emitente") or ""),
                limite_diff_chave=limite_diff_chave,
            ):
                comp_a = _completude_nfce(meta_a)
                comp_b = _completude_nfce(meta_b)
                if comp_a >= comp_b:
                    vencedor, perdedor, perdedor_meta = id_a, id_b, meta_b
                else:
                    vencedor, perdedor, perdedor_meta = id_b, id_a, meta_a
                motivo = f"completude vencedor={max(comp_a, comp_b)} perdedor={min(comp_a, comp_b)}"
                fusoes.append((vencedor, perdedor, motivo))
                if apply:
                    arestas_redirecionadas += _fundir_par(db, vencedor, perdedor, perdedor_meta)
                ja_perdedores.add(perdedor)

    depois = antes - len(fusoes) if apply else antes
    return {
        "antes": antes,
        "depois": depois,
        "fusoes": fusoes,
        "arestas_redirecionadas": arestas_redirecionadas,
    }


def _backup_grafo(caminho: Path) -> Path:
    destino = Path(f"/tmp/grafo_backup_nfce_dedup_{int(time.time())}.sqlite")
    shutil.copy2(caminho, destino)
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica fusões. Sem esta flag, apenas relata (dry-run).",
    )
    parser.add_argument(
        "--max-diff-chave",
        type=int,
        default=LIMITE_DIFF_RETROATIVO_PADRAO,
        help=(
            "Limite Levenshtein entre chave_44 (padrão %(default)d, "
            "calibrado pela auditoria 2026-05-12)."
        ),
    )
    parser.add_argument(
        "--grafo",
        type=Path,
        default=None,
        help="Caminho do grafo SQLite. Default: caminho_padrao().",
    )
    args = parser.parse_args()

    caminho = args.grafo or caminho_padrao()
    if not caminho.exists():
        logger.error("grafo não encontrado: %s", caminho)
        return 2

    backup = _backup_grafo(caminho) if args.apply else None
    if backup:
        logger.info("backup criado em %s", backup)

    db = GrafoDB(caminho)
    try:
        resultado = dedup_grafo(db, limite_diff_chave=args.max_diff_chave, apply=args.apply)
    finally:
        db._conn.close()  # noqa: SLF001

    print(f"NFCe antes:  {resultado['antes']}")
    print(f"NFCe depois: {resultado['depois']}")
    print(f"Fusões: {len(resultado['fusoes'])}")
    for vencedor, perdedor, motivo in resultado["fusoes"]:
        print(f"  vencedor={vencedor}  perdedor={perdedor}  {motivo}")
    print(f"Arestas redirecionadas: {resultado['arestas_redirecionadas']}")
    if not args.apply:
        print("(dry-run -- rode novamente com --apply para aplicar)")
    if backup:
        print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "O grafo é um espelho; espelho que duplica perde a verdade." -- princípio do dedup
