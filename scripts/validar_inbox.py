"""CLI -- iterar arquivos pendentes do CSV de validação (batch fino).

Sprint VALIDAR-BATCH-01.

Wrapper sobre ``scripts/validar_arquivo.py`` que pré-filtra pendências e
agrupa por sha8 (1 arquivo = N campos pendentes), facilitando que EU
(Opus interativo, supervisor ADR-13) leia em sequência via Read
multimodal e marque cada campo via ``validar_arquivo.py --marcar``.

Variante implementada: **A (interativo)** -- imprime metadata por arquivo
e aguarda Opus chamar ``/validar-arquivo --sha8 X`` para cada um. Não
processa arquivos automaticamente. ADR-13: supervisor é EU, manual.

NÃO é cron, NÃO é chamada Anthropic API.

Modos:

  --tipo X
      Filtra por tipo_arquivo (ex: nfce_modelo_65, holerite_g4f).

  --mes YYYY-MM
      Filtra por ts_processado iniciando com YYYY-MM.

  --apenas-divergentes
      Filtra onde valor_etl != valor_humano (humano já preenchido). Usado
      para revisar discrepâncias após validação humana.

  --limite N
      Primeiros N arquivos (default 50). Reporta progresso a cada 5.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ_REPO))

from src.load.validacao_csv import (  # noqa: E402
    LinhaValidacao,
    filtrar_pendentes_opus,
    ler_csv,
)

PROGRESSO_CADA_N: int = 5


def _agrupar_por_sha8(
    linhas: list[LinhaValidacao],
) -> dict[str, list[LinhaValidacao]]:
    """Agrupa linhas pendentes por sha8_arquivo (1 arquivo -> N campos)."""
    indice: dict[str, list[LinhaValidacao]] = defaultdict(list)
    for linha in linhas:
        indice[linha.sha8_arquivo].append(linha)
    return indice


def _aplicar_filtros(
    pendentes: list[LinhaValidacao],
    tipo: str | None,
    mes: str | None,
    apenas_divergentes: bool,
    todas: list[LinhaValidacao],
) -> list[LinhaValidacao]:
    """Aplica filtros opcionais à lista de pendências."""
    if tipo:
        pendentes = [linha for linha in pendentes if linha.tipo_arquivo == tipo]
    if mes:
        pendentes = [linha for linha in pendentes if linha.ts_processado.startswith(mes)]
    if apenas_divergentes:
        # apenas-divergentes requer linha onde humano JÁ preencheu valor
        # diferente do ETL. Pendentes do Opus que também são divergentes
        # do humano são prioridade máxima de revisão.
        sha8s_divergentes = {
            linha.sha8_arquivo
            for linha in todas
            if linha.valor_humano and linha.valor_etl and linha.valor_humano != linha.valor_etl
        }
        pendentes = [linha for linha in pendentes if linha.sha8_arquivo in sha8s_divergentes]
    return pendentes


def comando_principal(args: argparse.Namespace) -> int:
    todas = ler_csv()
    pendentes = filtrar_pendentes_opus(todas)
    if not pendentes:
        print("[VAL-BATCH] sem pendencias para Opus no CSV")
        return 0

    pendentes = _aplicar_filtros(
        pendentes,
        tipo=args.tipo,
        mes=args.mes,
        apenas_divergentes=args.apenas_divergentes,
        todas=todas,
    )
    if not pendentes:
        print("[VAL-BATCH] filtros eliminaram todas as pendencias")
        return 0

    grupos = _agrupar_por_sha8(pendentes)
    arquivos_ordenados = sorted(grupos.keys())[: args.limite]
    total = len(arquivos_ordenados)

    filtro_resumo = []
    if args.tipo:
        filtro_resumo.append(f"tipo={args.tipo}")
    if args.mes:
        filtro_resumo.append(f"mes={args.mes}")
    if args.apenas_divergentes:
        filtro_resumo.append("apenas-divergentes")
    descritor_filtro = f" (filtro: {', '.join(filtro_resumo)})" if filtro_resumo else ""

    print(f"[VAL-BATCH] {total} arquivo(s) pendente(s){descritor_filtro}")

    for indice, sha8 in enumerate(arquivos_ordenados, start=1):
        linhas_arquivo = grupos[sha8]
        primeira = linhas_arquivo[0]
        campos_pendentes = ", ".join(linha.campo for linha in linhas_arquivo)
        print()
        print(
            f"[VAL-BATCH] arquivo {indice}/{total}: "
            f"{Path(primeira.caminho_relativo).name} (sha8={sha8})"
        )
        print(f"[VAL-BATCH] tipo: {primeira.tipo_arquivo}")
        print(f"[VAL-BATCH] caminho: {primeira.caminho_relativo}")
        print(f"[VAL-BATCH] campos pendentes ({len(linhas_arquivo)}): {campos_pendentes}")
        print(f"[VAL-BATCH] aguardando Opus -- chame /validar-arquivo --sha8 {sha8}")
        if indice % PROGRESSO_CADA_N == 0 and indice < total:
            print(f"[VAL-BATCH] === progresso: {indice}/{total} ===")

    print()
    print(f"[VAL-BATCH] fim da listagem ({total} arquivo(s))")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument("--tipo", help="filtra por tipo_arquivo")
    parser.add_argument("--mes", help="filtra por ts_processado iniciando com YYYY-MM")
    parser.add_argument(
        "--apenas-divergentes",
        action="store_true",
        help="filtra arquivos onde humano preencheu valor diferente do ETL",
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=50,
        help="máximo de arquivos a listar (default 50)",
    )
    args = parser.parse_args()
    return comando_principal(args)


if __name__ == "__main__":
    sys.exit(main())


# "Lote a lote, arquivo a arquivo. Sem fila invisivel."
#  -- princípio operacional do Protocolo Ouroboros
