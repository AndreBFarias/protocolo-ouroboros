"""Carregamento seguro de senhas a partir de `.env` (fonte canônica).

Sprint SEC-SENHAS-PARA-ENV (2026-05-17): fonte primária migrada para
`.env` via `src/utils/segredos.py`. ``mappings/senhas.yaml`` é fallback
durante migração — após auditoria do dono confirmar paridade, a leitura
de YAML será removida em sprint-filha.
"""

from pathlib import Path
from typing import Any

import yaml

from src.utils.logger import configurar_logger
from src.utils.segredos import senhas_pdf as _senhas_pdf_env

logger = configurar_logger("senhas")

_CAMINHO_SENHAS: Path = Path(__file__).resolve().parents[2] / "mappings" / "senhas.yaml"


def carregar_senhas_pdf() -> list[str]:
    """Carrega lista de senhas para PDFs/XLS protegidos.

    Ordem de busca (Sprint SEC-SENHAS-PARA-ENV):
    1. Variáveis de ambiente em ``.env`` (PDF_SENHA_PRIMARIA, etc) — canônico.
    2. ``mappings/senhas.yaml`` (chave ``senhas_pdf``) — fallback legado.

    Retorna lista vazia se nenhum sítio tem senhas configuradas.
    """
    senhas_env = _senhas_pdf_env()
    if senhas_env:
        return senhas_env

    # Fallback: YAML legado (será removido em sprint-filha após auditoria).
    if not _CAMINHO_SENHAS.exists():
        logger.warning(
            "Senhas ausentes: defina PDF_SENHA_PRIMARIA, PDF_SENHA_SECUNDARIA, "
            "PDF_SENHA_CPF no .env (canônico) OU mappings/senhas.yaml (legado).",
        )
        return []

    try:
        with open(_CAMINHO_SENHAS, encoding="utf-8") as f:
            dados: dict[str, Any] = yaml.safe_load(f) or {}
        senhas = dados.get("senhas_pdf", [])
        if senhas:
            logger.info(
                "Senhas carregadas via fallback YAML legado. "
                "Migre para .env (Sprint SEC-SENHAS-PARA-ENV).",
            )
        return [str(s) for s in senhas]
    except (OSError, yaml.YAMLError) as e:
        logger.error("Erro ao carregar senhas YAML legado: %s", e)
        return []


# "O segredo da liberdade esta na coragem." -- Pericles
