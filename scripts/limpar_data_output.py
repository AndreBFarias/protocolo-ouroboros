"""Limpeza periódica de diretórios obsoletos em `data/output/`.

Sprint CLEANUP-DATA-OUTPUT-DIRETORIOS (2026-05-17). Auditoria revelou
acúmulo de diretórios pós-sprint sem política de retenção:

| Diretório | Origem | Política |
|---|---|---|
| `opus_ocr_pendentes_lixo_*` | pytest residual | DELETE |
| `opus_ocr_cache_sintetico_backup` | Sprint Fase A | MOVE |
| `_backup_pre_migracao_quem` | Sprint META-NORMALIZAR | MOVE |

Destino dos MOVE: `data/_arquivo_historico/<YYYY-MM-DD>/`.

Idempotente: rodar 2× consecutivas não duplica trabalho.

Uso CLI::

    python scripts/limpar_data_output.py             # dry-run (lista)
    python scripts/limpar_data_output.py --apply     # executa
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
DIR_OUTPUT = _RAIZ / "data" / "output"
DIR_ARQUIVO = _RAIZ / "data" / "_arquivo_historico"


# (padrão_glob, ação, comentário) — ações: "DELETE" ou "MOVE"
POLITICAS: list[tuple[str, str, str]] = [
    (
        "opus_ocr_pendentes_lixo_*",
        "DELETE",
        "Resíduos pytest temp; sem valor histórico",
    ),
    (
        "opus_ocr_cache_sintetico_backup",
        "MOVE",
        "Backup pré-substituição caches Opus (Sprint Fase A)",
    ),
    (
        "_backup_pre_migracao_quem",
        "MOVE",
        "Backup pré-migração tipo_documento (sprint META-NORMALIZAR-TIPO-DOCUMENTO-ETL)",
    ),
]


def _coletar_alvos() -> list[tuple[Path, str, str]]:
    """Devolve lista (path, acao, comentario) dos alvos atuais."""
    out: list[tuple[Path, str, str]] = []
    if not DIR_OUTPUT.exists():
        return out
    for padrao, acao, comentario in POLITICAS:
        for alvo in sorted(DIR_OUTPUT.glob(padrao)):
            if alvo.is_dir() or alvo.is_file():
                out.append((alvo, acao, comentario))
    return out


def _formatar_tamanho(path: Path) -> str:
    """Retorna tamanho legível do diretório/arquivo."""
    try:
        if path.is_file():
            return f"{path.stat().st_size:,} bytes"
        total = sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
        return f"{total:,} bytes"
    except OSError:
        return "?"


def _executar(alvo: Path, acao: str, data_iso: str) -> tuple[str, Path | None]:
    """Aplica ação. Retorna (status, destino) para log."""
    if acao == "DELETE":
        try:
            if alvo.is_dir():
                shutil.rmtree(alvo)
            else:
                alvo.unlink()
            return ("removido", None)
        except OSError as exc:
            return (f"erro:{exc}", None)
    if acao == "MOVE":
        DIR_ARQUIVO.mkdir(parents=True, exist_ok=True)
        destino_dia = DIR_ARQUIVO / data_iso
        destino_dia.mkdir(parents=True, exist_ok=True)
        destino = destino_dia / alvo.name
        try:
            shutil.move(str(alvo), str(destino))
            return ("movido", destino)
        except OSError as exc:
            return (f"erro:{exc}", None)
    return ("acao_invalida", None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Limpa diretorios obsoletos em data/output/"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa (default: dry-run lista alvos sem mover/deletar)",
    )
    args = parser.parse_args(argv)

    alvos = _coletar_alvos()
    if not alvos:
        sys.stdout.write("Sem alvos para limpeza. data/output/ limpo.\n")
        return 0

    data_iso = datetime.now().strftime("%Y-%m-%d")
    sys.stdout.write(f"Modo: {'apply' if args.apply else 'dry-run'}\n")
    sys.stdout.write(f"Alvos detectados ({len(alvos)}):\n")
    for alvo, acao, comentario in alvos:
        tamanho = _formatar_tamanho(alvo)
        sys.stdout.write(f"  [{acao}] {alvo.name} ({tamanho}) -- {comentario}\n")

    if not args.apply:
        sys.stdout.write("\nDry-run: nada foi modificado. Use --apply para executar.\n")
        return 0

    sys.stdout.write("\nExecutando...\n")
    sucessos = 0
    falhas = 0
    for alvo, acao, _ in alvos:
        status, destino = _executar(alvo, acao, data_iso)
        if status.startswith("erro"):
            falhas += 1
            sys.stdout.write(f"  FALHA {alvo.name}: {status}\n")
        elif destino:
            sucessos += 1
            sys.stdout.write(f"  OK {alvo.name} → {destino}\n")
        else:
            sucessos += 1
            sys.stdout.write(f"  OK {alvo.name} ({status})\n")

    sys.stdout.write(f"\nResultado: {sucessos} sucesso(s), {falhas} falha(s).\n")
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())


# "Diretório morto é hospede silencioso." -- princípio da casa arrumada
