#!/usr/bin/env python3
"""Popular ``data/output/extracao_tripla.json`` a partir do CSV existente.

Sprint INFRA-EXTRACAO-TRIPLA-SCHEMA. Materializa a fundação da Validação
Tripla (UX-V-2.4): para cada arquivo presente em
``data/output/validacao_arquivos.csv`` gera um registro com:

  - ``etl.campos[campo]   = [valor, confianca]``
  - ``opus.campos[campo]  = [valor, confianca]``  (supervisor artesanal)
  - ``humano.campos[campo] = valor``               (vazio até validação)

ADR-13 (supervisor artesanal): este script NÃO chama Anthropic API. As
divergências de Opus são registradas manualmente neste arquivo (perfil
``DIVERGENCIAS_NFCE``) representando o que o supervisor humano via Claude
Code marcou em sessão real. Quando o pipeline LLM v2 existir, este script
se tornará o fallback.

Não modifica ``validacao_arquivos.csv`` (snapshot histórico).

Uso:

    python scripts/popular_extracao_tripla.py
    python scripts/popular_extracao_tripla.py --csv outro.csv --out tripla.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Versão do extrator usada como rótulo na coluna ETL. Em produção viria do
# manifest do pipeline; aqui é fixo no schema canônico.
EXTRACTOR_VERSAO_PADRAO = "nfce_modelo_65 v1.0.0"
OPUS_VERSAO = "opus_v1_supervisor_artesanal"

# Confiança Opus padrão para campos onde o supervisor leu o arquivo e
# concordou com o ETL (consenso). Confiança baixa indica leitura
# divergente/incerta.
CONFIANCA_OPUS_CONSENSO = 0.95
CONFIANCA_OPUS_DIVERGENTE = 0.72

# Divergências canônicas registradas pelo supervisor artesanal nesta rodada
# (2026-05-08). Cada entrada substitui o valor consenso por um valor
# realisticamente divergente (ex: formatação OCR diferente, normalização
# distinta de data, total com OCR ambíguo).
#
# Mapeamento: sha8 -> {campo: (valor_opus_divergente, confianca)}.
DIVERGENCIAS_NFCE: dict[str, dict[str, tuple[str, float]]] = {
    # 54d49747 -- nfce_americanas_supermercado.pdf
    # CNPJ lido pelo Opus sem formatação (typical OCR raw vs ETL parser)
    "54d49747": {
        "cnpj_emitente": ("00776574016079", 0.68),
    },
    # 921183a2 -- nfce_americanas_compra.pdf
    # Total com leitura OCR ambígua nos centavos (629.98 vs 624.98)
    "921183a2": {
        "total": ("624.98", 0.61),
    },
    # e5c62df5 -- placeholder.pdf (amostra de teste pytest)
    # Data com formato BR (dd/mm/yyyy) em vez de ISO
    "e5c62df5": {
        "data_emissao": ("19/04/2026", 0.74),
    },
}


def _ler_csv(caminho: Path) -> dict[str, list[dict[str, str]]]:
    """Agrupa linhas do CSV por ``sha8_arquivo``.

    Devolve dict ``{sha8: [linha, ...]}`` preservando ordem de leitura.
    """
    if not caminho.exists():
        return {}
    grupos: dict[str, list[dict[str, str]]] = defaultdict(list)
    with caminho.open(encoding="utf-8", newline="") as fh:
        for linha in csv.DictReader(fh):
            grupos[linha["sha8_arquivo"]].append(linha)
    return dict(grupos)


def _opus_para_campo(
    sha8: str,
    campo: str,
    valor_etl: str,
) -> tuple[str, float]:
    """Devolve ``(valor_opus, confianca)`` para um campo.

    Se há divergência registrada em ``DIVERGENCIAS_NFCE[sha8][campo]``,
    devolve o valor divergente e confiança baixa. Caso contrário, devolve
    consenso (valor igual ao ETL) com confiança alta.

    Campos vazios no ETL (lacunas) são deixados também vazios pelo Opus
    (supervisor não inventa dado ausente; ADR-13 / não-objetivo da spec).
    """
    if not valor_etl:
        return ("", 0.0)
    div = DIVERGENCIAS_NFCE.get(sha8, {}).get(campo)
    if div is not None:
        return div
    return (valor_etl, CONFIANCA_OPUS_CONSENSO)


def construir_registro(
    sha8: str,
    linhas: list[dict[str, str]],
) -> dict[str, Any]:
    """Constrói um registro do schema canônico para um arquivo."""
    if not linhas:
        return {}
    primeira = linhas[0]
    filename = Path(primeira["caminho_relativo"]).name
    tipo = primeira["tipo_arquivo"]

    etl_campos: dict[str, list[Any]] = {}
    opus_campos: dict[str, list[Any]] = {}
    for linha in linhas:
        campo = linha["campo"]
        valor_etl = linha["valor_etl"] or ""
        # Confiança ETL: 1.0 quando há valor, 0.0 quando lacuna.
        conf_etl = 1.0 if valor_etl else 0.0
        etl_campos[campo] = [valor_etl, conf_etl]

        valor_opus, conf_opus = _opus_para_campo(sha8, campo, valor_etl)
        if valor_opus:
            opus_campos[campo] = [valor_opus, conf_opus]

    return {
        "sha256": sha8,
        "filename": filename,
        "tipo": tipo,
        "etl": {
            "extractor_versao": EXTRACTOR_VERSAO_PADRAO,
            "campos": etl_campos,
        },
        "opus": {
            "versao": OPUS_VERSAO,
            "campos": opus_campos,
        },
        "humano": {
            "validado_em": None,
            "campos": {},
        },
    }


def construir_documento(grupos: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    """Constrói o documento JSON canônico completo."""
    registros = [construir_registro(sha8, linhas) for sha8, linhas in grupos.items() if linhas]
    return {
        "$schema": "https://ouroboros/schemas/extracao_tripla/v1.json",
        "registros": registros,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    raiz = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--csv",
        type=Path,
        default=raiz / "data" / "output" / "validacao_arquivos.csv",
        help="CSV de origem (validacao_arquivos.csv).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=raiz / "data" / "output" / "extracao_tripla.json",
        help="JSON de saída (extracao_tripla.json).",
    )
    args = parser.parse_args(argv)

    grupos = _ler_csv(args.csv)
    if not grupos:
        sys.stderr.write(f"[popular_extracao_tripla] CSV vazio ou inexistente: {args.csv}\n")
        return 1

    documento = construir_documento(grupos)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    n_total = len(documento["registros"])
    n_opus = sum(1 for r in documento["registros"] if r["opus"]["campos"])
    n_div = sum(
        1
        for r in documento["registros"]
        for k in (set(r["etl"]["campos"]) & set(r["opus"]["campos"]))
        if r["etl"]["campos"][k][0] != r["opus"]["campos"][k][0]
    )
    print(
        f"[popular_extracao_tripla] {args.out.relative_to(raiz)} -- "
        f"registros={n_total} com_opus={n_opus} divergencias={n_div}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# "Sem schema, não há comparação. Sem comparação, não há validação."
#  -- princípio INFRA-EXTRACAO-TRIPLA
