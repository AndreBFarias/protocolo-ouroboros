"""Carregador do schema canônico de Extração Tripla.

Sprint INFRA-EXTRACAO-TRIPLA-SCHEMA. Lê
``data/output/extracao_tripla.json`` produzido por
``scripts/popular_extracao_tripla.py`` e devolve uma lista de registros
parseados, prontos para consumo pela aba Validação Tripla
(``src/dashboard/paginas/extracao_tripla.py``) e pelo Revisor 4-way.

Schema esperado (v1):

.. code-block:: json

    {
      "$schema": "https://ouroboros/schemas/extracao_tripla/v1.json",
      "registros": [
        {
          "sha256": "54d49747",
          "filename": "nfce_americanas_supermercado.pdf",
          "tipo": "nfce_modelo_65",
          "etl": {
            "extractor_versao": "nfce_modelo_65 v1.0.0",
            "campos": {"<campo>": ["<valor>", <confianca>]}
          },
          "opus": {
            "versao": "opus_v1_supervisor_artesanal",
            "campos": {"<campo>": ["<valor>", <confianca>]}
          },
          "humano": {
            "validado_em": null,
            "campos": {"<campo>": "<valor>"}
          }
        }
      ]
    }

Princípios:

  - Graceful fallback: se o JSON não existe ou está corrompido, devolve
    lista vazia em vez de levantar exceção (ADR-10 Resiliência Graciosa).
  - Não modifica o arquivo: leitura pura.
  - Tuplas de ``(valor, confiança)`` são devolvidas como ``list`` (JSON
    nativo) -- o consumidor que normalize se quiser tupla.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Caminho canônico do JSON, relativo à raiz do repo.
CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "data" / "output" / "extracao_tripla.json"


def carregar_extracoes_triplas(
    caminho: Path | None = None,
) -> list[dict[str, Any]]:
    """Lê o JSON canônico e devolve a lista de registros.

    Args:
        caminho: caminho alternativo para o JSON (default
            ``data/output/extracao_tripla.json``).

    Returns:
        Lista de registros parseados conforme o schema v1. Lista vazia se
        o arquivo não existe, está corrompido ou tem schema inválido.
    """
    alvo = caminho or CAMINHO_PADRAO
    if not alvo.exists():
        return []
    try:
        bruto = alvo.read_text(encoding="utf-8")
        documento = json.loads(bruto)
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(documento, dict):
        return []
    registros = documento.get("registros")
    if not isinstance(registros, list):
        return []
    return [r for r in registros if isinstance(r, dict)]


def contar_divergencias(registro: dict[str, Any]) -> int:
    """Conta campos onde ETL e Opus discordam para um registro.

    Considera apenas campos presentes em ambos com valores não-vazios.
    Usado pelo dashboard para exibir badge DIVERGENTE no header.
    """
    etl_campos = registro.get("etl", {}).get("campos", {}) or {}
    opus_campos = registro.get("opus", {}).get("campos", {}) or {}
    chaves_comuns = set(etl_campos.keys()) & set(opus_campos.keys())
    div = 0
    for k in chaves_comuns:
        v_etl = etl_campos[k][0] if etl_campos[k] else ""
        v_opus = opus_campos[k][0] if opus_campos[k] else ""
        if v_etl and v_opus and v_etl != v_opus:
            div += 1
    return div


def calcular_paridade(registro: dict[str, Any]) -> float:
    """Devolve % de campos onde ETL e Opus concordam (ambos não-vazios).

    Range 0.0 a 100.0. Retorna 0.0 quando não há comparação possível.
    """
    etl_campos = registro.get("etl", {}).get("campos", {}) or {}
    opus_campos = registro.get("opus", {}).get("campos", {}) or {}
    chaves_comuns = set(etl_campos.keys()) & set(opus_campos.keys())
    if not chaves_comuns:
        return 0.0
    iguais = 0
    avaliados = 0
    for k in chaves_comuns:
        v_etl = etl_campos[k][0] if etl_campos[k] else ""
        v_opus = opus_campos[k][0] if opus_campos[k] else ""
        if not v_etl and not v_opus:
            # campos vazios em ambos não contam como comparação
            continue
        avaliados += 1
        if v_etl == v_opus:
            iguais += 1
    if avaliados == 0:
        return 0.0
    return iguais / avaliados * 100.0


# "Sem schema, não há comparação. Sem comparação, não há validação."
#  -- princípio INFRA-EXTRACAO-TRIPLA
