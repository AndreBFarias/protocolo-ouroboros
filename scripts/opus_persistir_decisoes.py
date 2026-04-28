"""Sprint 103 -- Fase Opus: persiste decisoes do supervisor no DB de revisao.

Le data/output/transcricoes_opus/decisoes_opus.json (preenchido manualmente
pelo Opus apos análise de cada transcricao) e chama salvar_marcacao(...
valor_opus=<x>) para cada par (item_id, dimensao).

Não marca o estado humano (ok=NULL via valor padrao -- humano ainda não
validou, so o supervisor). Isto deixa o registro em estado 'aguardando humano'
no Revisor Visual.

PII ja vem mascarada das decisoes_opus.json (LGPD-safe).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.dashboard.dados import CAMINHO_REVISAO_HUMANA  # noqa: E402
from src.dashboard.paginas.revisor import (  # noqa: E402
    DIMENSOES_CANONICAS,
    salvar_marcacao,
)

_FONTE_PADRAO = _RAIZ / "data" / "output" / "transcricoes_opus" / "decisoes_opus.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Persiste decisões Opus em revisao_humana.sqlite. "
            "Default lê decisoes_opus.json; passe --arquivo para apontar "
            "para outro JSON (ex: decisoes_opus_v2.json)."
        )
    )
    parser.add_argument(
        "--arquivo",
        type=Path,
        default=_FONTE_PADRAO,
        help="Caminho do JSON de decisões Opus. Default: decisoes_opus.json.",
    )
    args = parser.parse_args(argv)

    fonte = args.arquivo
    if not fonte.exists():
        print(f"[ERRO] {fonte} não existe.", file=sys.stderr)
        print("Rode primeiro scripts/opus_extrair_transcricoes.py", file=sys.stderr)
        return 1

    decisoes = json.loads(fonte.read_text(encoding="utf-8"))
    print(f"Lendo {len(decisoes)} decisoes Opus de {fonte.name}", file=sys.stderr)

    persistidas = 0
    for item in decisoes:
        item_id = item["item_id"]
        observacao = item.get("observacao_opus", "")
        decisoes_dim = item.get("decisoes", {})

        for dim in DIMENSOES_CANONICAS:
            valor_opus = decisoes_dim.get(dim, "")
            # Persiste mesmo quando Opus marcou '?' (sinaliza que Opus tentou
            # mas não conseguiu extrair). Humano vai ver e decidir.
            salvar_marcacao(
                CAMINHO_REVISAO_HUMANA,
                item_id=item_id,
                dimensao=dim,
                ok=None,  # humano ainda não validou
                observacao=f"[Opus] {observacao}" if dim == DIMENSOES_CANONICAS[0] else "",
                valor_opus=str(valor_opus) if valor_opus else "",
            )
            persistidas += 1

    print(
        f"\n[OK] Persistidas {persistidas} marcacoes ({len(decisoes)} itens "
        f"x {len(DIMENSOES_CANONICAS)} dimensoes).",
        file=sys.stderr,
    )
    print(f"DB: {CAMINHO_REVISAO_HUMANA}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
