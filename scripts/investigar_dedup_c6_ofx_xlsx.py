#!/usr/bin/env python3
"""Investigação INFRA-DEDUP-LANCAMENTO-DUPLICADO-G4F.

Cruza lançamentos do C6/pessoa_a no XLSX final, agrupa por (data, valor) e
relata pares com `forma_pagamento`/`local` divergentes -- padrão típico de
ingestão paralela OFX + XLSX da mesma instituição.

Não modifica dados: apenas relata. Saída CSV em
`/tmp/dedup_c6_ofx_xlsx_<timestamp>.csv` + sumário no stdout.

Uso:
    .venv/bin/python scripts/investigar_dedup_c6_ofx_xlsx.py \\
        --xlsx data/output/ouroboros_2026.xlsx --quem pessoa_a --banco C6
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


def investigar(xlsx_path: Path, quem: str, banco: str) -> dict:
    df = pd.read_excel(xlsx_path, sheet_name="extrato")
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%Y-%m-%d")

    alvo = df[(df["banco_origem"] == banco) & (df["quem"] == quem)].copy()
    alvo["valor_abs"] = alvo["valor"].abs()

    grupos = alvo.groupby(["data", "valor_abs"])
    pares_suspeitos: list[dict] = []

    for (data, valor), bloco in grupos:
        if len(bloco) < 2:
            continue
        formas = set(bloco["forma_pagamento"].astype(str).tolist())
        locais = bloco["local"].astype(str).tolist()
        # Sufixo após " - " (padrão OFX) versus sem prefixo (padrão XLSX C6).
        normalizados = {loc.split(" - ", 1)[-1].strip().upper() for loc in locais}
        casam_normalizados = len(normalizados) == 1
        pares_suspeitos.append(
            {
                "data": data,
                "valor": valor,
                "n": len(bloco),
                "formas_pagamento": "|".join(sorted(formas)),
                "locais": "  ##  ".join(locais),
                "casa_apos_normalizar": casam_normalizados,
                "identificadores": "|".join(bloco["identificador"].astype(str).tolist()),
            }
        )

    return {
        "total_linhas_alvo": len(alvo),
        "total_grupos": grupos.ngroups,
        "pares_suspeitos": pares_suspeitos,
        "pares_que_casam_normalizado": sum(1 for p in pares_suspeitos if p["casa_apos_normalizar"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, default=Path("data/output/ouroboros_2026.xlsx"))
    parser.add_argument("--quem", default="pessoa_a")
    parser.add_argument("--banco", default="C6")
    args = parser.parse_args()

    if not args.xlsx.exists():
        print(f"ERRO: XLSX não encontrado: {args.xlsx}", file=sys.stderr)
        return 2

    rel = investigar(args.xlsx, args.quem, args.banco)

    saida = Path(f"/tmp/dedup_c6_ofx_xlsx_{int(time.time())}.csv")
    pd.DataFrame(rel["pares_suspeitos"]).to_csv(saida, index=False)

    print(f"Linhas alvo ({args.banco}/{args.quem}): {rel['total_linhas_alvo']}")
    print(f"Grupos unicos (data, valor): {rel['total_grupos']}")
    print(f"Pares suspeitos (n>=2):       {len(rel['pares_suspeitos'])}")
    print(f"Casam apos normalizar local:  {rel['pares_que_casam_normalizado']}")
    print(f"CSV: {saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Onde ha excesso de zelo, ha desconfianca de duplicidade." -- Tacito
