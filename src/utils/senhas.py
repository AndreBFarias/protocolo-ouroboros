"""Carregamento seguro de senhas a partir de arquivo externo."""

from pathlib import Path
from typing import Any

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("senhas")

_CAMINHO_SENHAS: Path = Path(__file__).resolve().parents[2] / "mappings" / "senhas.yaml"


def carregar_senhas_pdf() -> list[str]:
    """Carrega lista de senhas para PDFs/XLS protegidos.

    Lê de mappings/senhas.yaml (não rastreado pelo git).
    Retorna lista vazia se o arquivo não existir.
    """
    if not _CAMINHO_SENHAS.exists():
        logger.warning(
            "Arquivo de senhas não encontrado: %s. "
            "Crie mappings/senhas.yaml com a chave 'senhas_pdf'.",
            _CAMINHO_SENHAS,
        )
        return []

    try:
        with open(_CAMINHO_SENHAS, encoding="utf-8") as f:
            dados: dict[str, Any] = yaml.safe_load(f) or {}
        senhas = dados.get("senhas_pdf", [])
        if not senhas:
            logger.warning("Nenhuma senha encontrada em senhas_pdf")
        return [str(s) for s in senhas]
    except Exception as e:
        logger.error("Erro ao carregar senhas: %s", e)
        return []


# "O segredo da liberdade esta na coragem." -- Pericles
