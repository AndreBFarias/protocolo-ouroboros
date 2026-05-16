"""Sprint ANTI-MIGUE-01 -- Gate 4-way conformance >=3 amostras.

Tabela `conformance_amostras` em SQLite registra observações por tipo
de extrator: cada linha é uma amostra real validada nas 4 dimensões
(ETL, Opus, Grafo, Humano). O gate libera o tipo (`exit 0`) quando
houver >=3 linhas com as 4 dimensões verdes.

Uso típico (CLI):

    python -m tests.conformance.gate cnh           # exit 1 se <3 amostras
    python -m tests.conformance.gate cnh --db /tmp/c.sqlite

Uso programático:

    from tests.conformance.gate import inicializar_db, registrar_amostra, validar
    db = Path("data/output/conformance.sqlite")
    inicializar_db(db)
    registrar_amostra(db, tipo="cnh", item_id="doc_42",
                      etl_ok=True, opus_ok=True, grafo_ok=True, humano_ok=True)
    rc = validar(db, tipo="cnh")  # 0 se >=3 amostras 4-way verdes
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[2]
DB_DEFAULT: Path = RAIZ / "data" / "output" / "conformance.sqlite"
LIMIAR_AMOSTRAS_4WAY: int = 3


def inicializar_db(db_path: Path) -> None:
    """Cria a tabela `conformance_amostras` se não existir.

    Schema:
      - id: PK
      - tipo: tipo de documento canônico (ex: 'cnh', 'das_parcsn')
      - item_id: identificador opaco da amostra (sha do arquivo, id de node, etc.)
      - etl_ok / opus_ok / grafo_ok / humano_ok: flags 0/1 para cada dimensão
      - ts: timestamp ISO 8601 da última atualização
      - UNIQUE(tipo, item_id) garante que reinsert atualiza ao invés de duplicar.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conformance_amostras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                item_id TEXT NOT NULL,
                etl_ok INTEGER NOT NULL DEFAULT 0,
                opus_ok INTEGER NOT NULL DEFAULT 0,
                grafo_ok INTEGER NOT NULL DEFAULT 0,
                humano_ok INTEGER NOT NULL DEFAULT 0,
                ts TEXT NOT NULL,
                UNIQUE(tipo, item_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conformance_tipo ON conformance_amostras(tipo)"
        )
        conn.commit()


def registrar_amostra(
    db_path: Path,
    *,
    tipo: str,
    item_id: str,
    etl_ok: bool,
    opus_ok: bool,
    grafo_ok: bool,
    humano_ok: bool,
) -> None:
    """Insere ou atualiza uma amostra. Idempotente via UNIQUE(tipo, item_id)."""
    inicializar_db(db_path)
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO conformance_amostras
                (tipo, item_id, etl_ok, opus_ok, grafo_ok, humano_ok, ts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tipo, item_id) DO UPDATE SET
                etl_ok=excluded.etl_ok,
                opus_ok=excluded.opus_ok,
                grafo_ok=excluded.grafo_ok,
                humano_ok=excluded.humano_ok,
                ts=excluded.ts
            """,
            (tipo, item_id, int(etl_ok), int(opus_ok), int(grafo_ok), int(humano_ok), ts),
        )
        conn.commit()


def contar_amostras_verdes(db_path: Path, tipo: str) -> int:
    """Retorna número de amostras 4-way verdes (todas dimensões = 1) para um tipo."""
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM conformance_amostras
            WHERE tipo = ?
              AND etl_ok = 1
              AND opus_ok = 1
              AND grafo_ok = 1
              AND humano_ok = 1
            """,
            (tipo,),
        ).fetchone()
    return int(row[0]) if row else 0


def validar(db_path: Path, tipo: str, limiar: int = LIMIAR_AMOSTRAS_4WAY) -> int:
    """Retorna 0 se há >= `limiar` amostras 4-way verdes; 1 caso contrário.

    Usado pelo CLI e por scripts/check_anti_migue.sh para bloquear o
    fechamento de sprints de extratores novos sem proof-of-work empírico.
    """
    verdes = contar_amostras_verdes(db_path, tipo)
    if verdes >= limiar:
        print(f"[CONFORMANCE-OK] tipo={tipo}: {verdes} amostras 4-way verdes (limiar={limiar}).")
        return 0
    print(
        f"[CONFORMANCE-FAIL] tipo={tipo}: apenas {verdes} amostras 4-way "
        f"verdes (limiar={limiar}). Marque mais amostras no Revisor."
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate 4-way conformance: >=3 amostras com ETL+Opus+Grafo+Humano OK.",
    )
    parser.add_argument("tipo", help="Tipo de documento canônico (ex: 'cnh', 'das_parcsn').")
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_DEFAULT,
        help=f"Caminho do SQLite (default: {DB_DEFAULT}).",
    )
    parser.add_argument(
        "--limiar",
        type=int,
        default=LIMIAR_AMOSTRAS_4WAY,
        help=f"Mínimo de amostras 4-way verdes (default: {LIMIAR_AMOSTRAS_4WAY}).",
    )
    args = parser.parse_args(argv)
    return validar(args.db, args.tipo, limiar=args.limiar)


if __name__ == "__main__":
    sys.exit(main())


# "Quem mede honestamente, mede com pequena escala muitas vezes." -- princípio empírico
