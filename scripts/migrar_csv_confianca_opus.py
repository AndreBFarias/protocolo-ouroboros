#!/usr/bin/env python3
"""Migração idempotente do CSV de validação por arquivo (Sprint UX-RD-11).

Adiciona a coluna ``confianca_opus`` (float, default ``0.0``) imediatamente
após ``valor_opus`` em ``data/output/validacao_arquivos.csv``.

Idempotente: se a coluna já existe, é no-op (apenas reporta).

Uso:

    python scripts/migrar_csv_confianca_opus.py --dry-run
    python scripts/migrar_csv_confianca_opus.py --executar
    python scripts/migrar_csv_confianca_opus.py --executar --csv <path>

Saída:

    [DRY-RUN] schema atual: 12 colunas
    [DRY-RUN] coluna 'confianca_opus' AUSENTE -- migração necessária
    [EXECUTAR] migração concluída: 12 -> 13 colunas
    [EXECUTAR] coluna já presente -- no-op
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

NOVA_COLUNA: str = "confianca_opus"
ANCORA: str = "valor_opus"
VALOR_DEFAULT: str = "0.0"

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_PATH_PADRAO: Path = _RAIZ_REPO / "data" / "output" / "validacao_arquivos.csv"


def _ler_header(caminho: Path) -> list[str]:
    """Lê apenas a primeira linha do CSV e devolve a lista de cabeçalhos."""
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            return next(reader)
        except StopIteration:
            return []


def _inserir_coluna(
    cabecalho_atual: list[str], nova: str, ancora: str
) -> list[str]:
    """Devolve novo cabeçalho com ``nova`` logo após ``ancora``.

    Se ``ancora`` ausente, anexa ao final. Se ``nova`` já presente, devolve
    inalterado.
    """
    if nova in cabecalho_atual:
        return list(cabecalho_atual)
    if ancora not in cabecalho_atual:
        return [*cabecalho_atual, nova]
    saida: list[str] = []
    for col in cabecalho_atual:
        saida.append(col)
        if col == ancora:
            saida.append(nova)
    return saida


def _migrar_arquivo(
    caminho: Path, novo_cabecalho: list[str], antigo_cabecalho: list[str]
) -> None:
    """Reescreve o CSV com a nova coluna preenchida com VALOR_DEFAULT.

    Atômico via .tmp + rename. Backup ``.bak`` mantido por segurança.
    """
    backup = caminho.with_suffix(caminho.suffix + ".bak")
    shutil.copy2(caminho, backup)

    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    with caminho.open("r", encoding="utf-8", newline="") as fin, tmp.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin, fieldnames=antigo_cabecalho)
        # Pula header original
        next(reader, None)
        writer = csv.DictWriter(fout, fieldnames=novo_cabecalho)
        writer.writeheader()
        for row in reader:
            row[NOVA_COLUNA] = row.get(NOVA_COLUNA) or VALOR_DEFAULT
            writer.writerow(row)
    tmp.replace(caminho)


def migrar(caminho: Path, executar: bool) -> int:
    """Executa o fluxo de migração. Retorna exit code (0 = ok)."""
    if not caminho.exists():
        print(f"[ERRO] CSV não encontrado: {caminho}", file=sys.stderr)
        return 1

    cabecalho_atual = _ler_header(caminho)
    if not cabecalho_atual:
        print(f"[ERRO] CSV vazio ou sem header: {caminho}", file=sys.stderr)
        return 1

    prefixo = "[EXECUTAR]" if executar else "[DRY-RUN]"
    print(f"{prefixo} schema atual: {len(cabecalho_atual)} colunas")

    if NOVA_COLUNA in cabecalho_atual:
        print(f"{prefixo} coluna '{NOVA_COLUNA}' PRESENTE -- no-op idempotente")
        return 0

    print(f"{prefixo} coluna '{NOVA_COLUNA}' AUSENTE -- migração necessária")

    if not executar:
        return 0

    novo = _inserir_coluna(cabecalho_atual, NOVA_COLUNA, ANCORA)
    _migrar_arquivo(caminho, novo, cabecalho_atual)
    print(
        f"{prefixo} migração concluída: "
        f"{len(cabecalho_atual)} -> {len(novo)} colunas"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--dry-run", action="store_true", help="apenas reporta")
    grupo.add_argument("--executar", action="store_true", help="aplica a migração")
    parser.add_argument(
        "--csv",
        type=Path,
        default=_PATH_PADRAO,
        help="caminho do CSV (default: data/output/validacao_arquivos.csv)",
    )
    args = parser.parse_args(argv)
    return migrar(args.csv, executar=args.executar)


if __name__ == "__main__":
    sys.exit(main())


# "O método é a alma da ciência." -- William Whewell
