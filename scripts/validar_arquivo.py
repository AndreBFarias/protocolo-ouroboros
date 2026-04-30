"""CLI -- abrir arquivo no Opus interativo e marcar valor_opus no CSV.

Sprint VALIDAÇÃO-CSV-01.

Este script é o ponto de entrada para que EU (Opus principal da sessão
Claude Code interativa, conforme ADR-13 / docs/SUPERVISOR_OPUS.md) leia
um arquivo via Read multimodal e atualize a coluna ``valor_opus`` do CSV
``data/output/validacao_arquivos.csv``.

NÃO é cron, NÃO é chamada Anthropic API. O script apenas (1) lista
linhas pendentes e (2) recebe atualização explicita por chave (sha8,
campo). A leitura do arquivo é feita pelo Opus dentro da sessão
interativa via Read tool sobre o caminho retornado, e a marcação volta
via flag ``--marcar``.

Modos:

  --listar [--tipo X]
      Imprime linhas com status_opus=pendente (filtra por tipo se passado).

  --sha8 <X>
      Imprime metadata do arquivo + linhas associadas (uso preparatório
      antes do Opus abrir o arquivo).

  --marcar --sha8 X --campo Y --valor "Z" [--status ok|erro|lacuna]
      Atualiza valor_opus + status_opus para a linha (sha8=X, campo=Y).

  --resumo
      Imprime totais: pendente_etl/opus/humano + concordancia 3-way.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ_REPO))

from src.load.validacao_csv import (  # noqa: E402
    STATUS_VALIDOS,
    atualizar_validacao_opus,
    filtrar_pendentes_opus,
    ler_csv,
)


def comando_listar(args: argparse.Namespace) -> int:
    pendentes = filtrar_pendentes_opus()
    if args.tipo:
        pendentes = [linha for linha in pendentes if linha.tipo_arquivo == args.tipo]
    if not pendentes:
        print("[VAL] sem pendencias para Opus")
        return 0
    print(f"[VAL] {len(pendentes)} linha(s) pendente(s) para Opus:")
    for linha in pendentes[: args.limite]:
        print(
            f"  {linha.sha8_arquivo}  {linha.tipo_arquivo:20s}  "
            f"{linha.campo:25s}  etl='{linha.valor_etl}'"
        )
    if len(pendentes) > args.limite:
        print(f"  ... e mais {len(pendentes) - args.limite}.")
    return 0


def comando_sha8(args: argparse.Namespace) -> int:
    linhas = [linha for linha in ler_csv() if linha.sha8_arquivo == args.sha8]
    if not linhas:
        print(f"[VAL] sha8={args.sha8} não encontrado no CSV")
        return 1
    primeira = linhas[0]
    print(f"[VAL] arquivo sha8={args.sha8}")
    print(f"  tipo: {primeira.tipo_arquivo}")
    print(f"  caminho: {primeira.caminho_relativo}")
    print(f"  ts_processado: {primeira.ts_processado}")
    print(f"  campos no CSV: {len(linhas)}")
    for linha in linhas:
        print(
            f"    {linha.campo:25s}  etl='{linha.valor_etl}'  "
            f"opus='{linha.valor_opus}'  humano='{linha.valor_humano}'  "
            f"status={linha.status_etl}/{linha.status_opus}/{linha.status_humano}"
        )
    return 0


def comando_marcar(args: argparse.Namespace) -> int:
    if args.status not in STATUS_VALIDOS:
        print(f"[VAL] status inválido: {args.status} (validos: {sorted(STATUS_VALIDOS)})")
        return 2
    if not args.sha8 or not args.campo:
        print("[VAL] --marcar requer --sha8 e --campo")
        return 2
    valor = args.valor or ""
    ok = atualizar_validacao_opus(args.sha8, args.campo, valor, args.status)
    if not ok:
        print(
            f"[VAL] linha (sha8={args.sha8}, campo={args.campo}) não encontrada -- "
            f"ETL deve registrar primeiro via registrar_extracao()."
        )
        return 1
    print(f"[VAL] marcado sha8={args.sha8} campo={args.campo} status={args.status}")
    return 0


def comando_resumo(_args: argparse.Namespace) -> int:
    linhas = ler_csv()
    if not linhas:
        print("[VAL] CSV vazio ou ausente")
        return 0
    total = len(linhas)
    contador_etl: Counter[str] = Counter(linha.status_etl for linha in linhas)
    contador_opus: Counter[str] = Counter(linha.status_opus for linha in linhas)
    contador_humano: Counter[str] = Counter(linha.status_humano for linha in linhas)
    concordantes_3way = sum(
        1
        for linha in linhas
        if linha.status_etl == linha.status_opus == linha.status_humano == "ok"
    )
    print(f"[VAL] total de linhas: {total}")
    print(f"  status_etl:    {dict(contador_etl)}")
    print(f"  status_opus:   {dict(contador_opus)}")
    print(f"  status_humano: {dict(contador_humano)}")
    print(f"  concordancia 3-way (ok x 3): {concordantes_3way}/{total}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument("--listar", action="store_true")
    parser.add_argument("--marcar", action="store_true")
    parser.add_argument("--resumo", action="store_true")
    parser.add_argument("--tipo", help="filtra por tipo_arquivo no --listar")
    parser.add_argument(
        "--limite", type=int, default=20, help="máximo de linhas a imprimir em --listar"
    )
    parser.add_argument("--sha8", help="sha8 do arquivo para --sha8 ou --marcar")
    parser.add_argument("--campo", help="campo canônico para --marcar")
    parser.add_argument("--valor", help="valor lido pelo Opus para --marcar")
    parser.add_argument(
        "--status",
        default="ok",
        help=f"status_opus para --marcar (validos: {sorted(STATUS_VALIDOS)})",
    )
    args = parser.parse_args()

    if args.marcar:
        return comando_marcar(args)
    if args.resumo:
        return comando_resumo(args)
    if args.listar:
        return comando_listar(args)
    if args.sha8:
        return comando_sha8(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Validar é o segundo ato da extração. Sem ele, o primeiro é só promessa."
#  -- princípio operacional do Protocolo Ouroboros
