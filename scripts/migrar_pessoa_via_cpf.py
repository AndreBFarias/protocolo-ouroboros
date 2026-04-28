"""Sprint 105: migra arquivos em data/raw/casal/ para data/raw/<pessoa>/
quando CPF/CNPJ/razão social no conteúdo identifica pessoa específica.

Resolve achado Opus Sprint 103: 2 NFCes Americanas em casal/ tinham CPF
do Andre no cupom mas o classifier antigo (pré-Sprint 90) não tinha
pessoa_detector via CPF/CNPJ -- caíram em casal/ por fallback.

Estratégia:
  1. Lista todos os arquivos em data/raw/casal/.
  2. Para cada um, extrai texto via pdfplumber/tesseract.
  3. Chama detectar_pessoa() (Sprint 90) com o preview.
  4. Se pessoa retorna 'andre' ou 'vitoria' (não 'casal'):
     - Move arquivo para data/raw/<pessoa>/<resto-do-path>.
     - Atualiza metadata.arquivo_origem do node correspondente.
  5. Caso contrário, mantém em casal/.

Idempotente: rodar 2x não afeta arquivos já migrados (não existem mais
em casal/).

Uso:
    .venv/bin/python scripts/migrar_pessoa_via_cpf.py             # dry-run
    .venv/bin/python scripts/migrar_pessoa_via_cpf.py --executar  # aplica
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.graph.db import GrafoDB, caminho_padrao  # noqa: E402
from src.graph.path_canonico import to_relativo  # noqa: E402
from src.intake.pessoa_detector import detectar_pessoa  # noqa: E402
from src.utils.logger import configurar_logger  # noqa: E402

logger = configurar_logger("scripts.migrar_pessoa_via_cpf")

_RAIZ_RAW_PADRAO: Path = _RAIZ / "data" / "raw"


from src.intake.preview import extrair_preview_completo as _extrair_preview  # noqa: E402,F401


def _calcular_destino(arquivo: Path, raiz_raw: Path, pessoa_nova: str) -> Path:
    """Constrói o destino preservando estrutura de subpastas relativa."""
    raiz_casal = raiz_raw / "casal"
    rel = arquivo.relative_to(raiz_casal)
    return raiz_raw / pessoa_nova / rel


def _atualizar_grafo(
    grafo: GrafoDB | None,
    arquivo_antigo: Path,
    arquivo_novo: Path,
) -> bool:
    r"""Atualiza nodes documento cujo arquivo_origem == arquivo_antigo.

    AUDIT-INDEX-JSON: usa índice expressao em json_extract(metadata,
    '\$.arquivo_origem') para query O(log N) em vez de full scan + iteracao.
    """
    if grafo is None:
        return False
    # Query usa índice expressao quando possivel (Sprint AUDIT-INDEX-JSON).
    # Procura tres formas: relativo (canon novo), absoluto, raw string.
    candidatos = (str(arquivo_antigo), str(arquivo_antigo.resolve()), to_relativo(arquivo_antigo))
    placeholders = ",".join("?" for _ in candidatos)
    cur = grafo._conn.execute(  # noqa: SLF001
        f"SELECT id, tipo, nome_canonico, metadata, aliases FROM node "
        f"WHERE tipo='documento' "
        f"AND json_extract(metadata, '$.arquivo_origem') IN ({placeholders})",
        candidatos,
    )
    atualizados = 0
    for row in cur.fetchall():
        meta = json.loads(row[3] or "{}")
        # AUDIT-PATH-RELATIVO: aceita relativo (Sprint AUDIT-PATH-RELATIVO) ou
        # absoluto (legado pre-sprint) na comparacao.
        ao_atual = meta.get("arquivo_origem", "")
        if ao_atual in (
            str(arquivo_antigo),
            str(arquivo_antigo.resolve()),
            to_relativo(arquivo_antigo),
        ):
            meta["arquivo_origem"] = to_relativo(arquivo_novo)
            if meta.get("arquivo_original"):
                meta["arquivo_original"] = to_relativo(arquivo_novo)
            grafo.upsert_node(
                tipo="documento",
                nome_canonico=row[2],
                metadata=meta,
                aliases=json.loads(row[4] or "[]"),
            )
            atualizados += 1
    return atualizados > 0


def migrar_pessoa_via_cpf(
    raiz_raw: Path | None = None,
    grafo: GrafoDB | None = None,
    dry_run: bool = True,
) -> dict:
    """Itera data/raw/casal/, detecta pessoa via conteúdo e migra."""
    raiz = raiz_raw if raiz_raw is not None else _RAIZ_RAW_PADRAO
    raiz_casal = raiz / "casal"

    stats: dict = {
        "total_em_casal": 0,
        "migrados": 0,
        "preservados": 0,
        "movimentos": [],
    }

    if not raiz_casal.exists():
        return stats

    arquivos = [p for p in raiz_casal.rglob("*") if p.is_file()]
    stats["total_em_casal"] = len(arquivos)

    for arquivo in arquivos:
        preview = _extrair_preview(arquivo)
        pessoa, fonte = detectar_pessoa(arquivo, preview)
        if pessoa not in ("andre", "vitoria"):
            stats["preservados"] += 1
            continue

        destino = _calcular_destino(arquivo, raiz, pessoa)
        stats["movimentos"].append(
            {
                "arquivo": str(arquivo),
                "destino": str(destino),
                "pessoa": pessoa,
                "fonte": fonte,
            }
        )

        if dry_run:
            logger.info(
                "[dry-run] migraria %s -> %s (pessoa=%s via %s)",
                arquivo.name,
                destino,
                pessoa,
                fonte,
            )
            stats["migrados"] += 1
            continue

        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            logger.warning("destino ja existe, pulando: %s", destino)
            stats["preservados"] += 1  # P1-01 fix: invariante total = migrados + preservados
            continue
        try:
            shutil.move(str(arquivo), str(destino))
            logger.info(
                "migrado: %s -> %s (pessoa=%s via %s)",
                arquivo.name,
                destino,
                pessoa,
                fonte,
            )
            _atualizar_grafo(grafo, arquivo, destino)
            stats["migrados"] += 1
        except OSError as exc:
            logger.error("falha ao mover %s -> %s: %s", arquivo, destino, exc)

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Migra arquivos casal->andre/vitoria via CPF/CNPJ no conteúdo.",
    )
    parser.add_argument("--executar", action="store_true", help="Aplica (default: dry-run).")
    parser.add_argument("--grafo", type=Path, default=None, help="Caminho grafo.sqlite.")
    args = parser.parse_args(argv)

    grafo = None
    if args.executar:
        caminho_grafo = args.grafo or caminho_padrao()
        if caminho_grafo.exists():
            grafo = GrafoDB(caminho_grafo)

    rel = migrar_pessoa_via_cpf(grafo=grafo, dry_run=not args.executar)
    modo = "EXECUTAR" if args.executar else "DRY-RUN"
    print(f"\n[Migrar pessoa via CPF -- {modo}]")
    print(f"  Total em casal/:   {rel['total_em_casal']}")
    print(f"  Migrados:          {rel['migrados']}")
    print(f"  Preservados:       {rel['preservados']}")
    if rel["movimentos"][:10]:
        print("  Movimentos (10 primeiros):")
        for m in rel["movimentos"][:10]:
            print(f"    - {Path(m['arquivo']).name} -> {m['pessoa']} (via {m['fonte']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
