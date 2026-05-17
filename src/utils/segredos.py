"""Carregamento de credenciais via `.env` (Sprint SEC-SENHAS-PARA-ENV).

Fronteira canônica para credenciais (senhas de PDFs bancários, tokens
opcionais, paths sensíveis). Substitui ``mappings/senhas.yaml`` como
fonte primária — YAML continua suportado como fallback durante migração.

Princípios:
- ``.env`` é o padrão. Não trackeado pelo git (já em .gitignore).
- ``.env.example`` é template trackeado, sem PII real.
- Falha-soft: ausência de credencial retorna string vazia ou lista vazia,
  nunca crasha.
- PII never in INFO log (padrão ``e``): apenas chave do segredo, nunca valor.

API canônica::

    from src.utils.segredos import senhas_pdf, segredo

    todas_senhas = senhas_pdf()           # lista[str]
    token = segredo("API_TOKEN", "")      # str
"""

from __future__ import annotations

import os
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger("segredos")

_RAIZ_REPO = Path(__file__).resolve().parents[2]
_PATH_ENV = _RAIZ_REPO / ".env"
_ENV_CARREGADO: bool = False


def _carregar_env_uma_vez() -> None:
    """Lê ``.env`` na raiz do repo e popula ``os.environ`` (idempotente).

    Não substitui variáveis já definidas no ambiente (export tem
    precedência sobre arquivo). Suporta linhas `KEY=value` e comentários
    `# ...`. Aspas em valor são removidas.
    """
    global _ENV_CARREGADO
    if _ENV_CARREGADO:
        return
    _ENV_CARREGADO = True

    if not _PATH_ENV.exists():
        logger.debug("Arquivo .env ausente em %s; usando apenas os.environ.", _PATH_ENV)
        return

    try:
        for linha in _PATH_ENV.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            chave = chave.strip()
            valor = valor.strip()
            # Remove aspas duplas/simples envolventes:
            if valor and valor[0] == valor[-1] and valor[0] in ('"', "'"):
                valor = valor[1:-1]
            os.environ.setdefault(chave, valor)
    except OSError as exc:
        logger.warning("Falha ao ler .env: %s", exc)


def segredo(chave: str, default: str = "") -> str:
    """Retorna valor de variável de ambiente (com fallback)."""
    _carregar_env_uma_vez()
    return os.environ.get(chave, default)


def senhas_pdf() -> list[str]:
    """Retorna lista de senhas de PDFs bancários do `.env`.

    Chaves esperadas:
    - ``PDF_SENHA_PRIMARIA``
    - ``PDF_SENHA_SECUNDARIA``
    - ``PDF_SENHA_CPF``
    - Adicionais: ``PDF_SENHA_<NOME>`` qualquer.

    Devolve apenas senhas não-vazias. Ordem: PRIMARIA → SECUNDARIA →
    CPF → outras (alfabético).
    """
    _carregar_env_uma_vez()
    canonicas = ["PDF_SENHA_PRIMARIA", "PDF_SENHA_SECUNDARIA", "PDF_SENHA_CPF"]
    out: list[str] = []
    vistas: set[str] = set()
    for chave in canonicas:
        valor = os.environ.get(chave, "")
        if valor and valor not in vistas:
            out.append(valor)
            vistas.add(valor)
    # Senhas adicionais (PDF_SENHA_* fora das canônicas):
    extras = []
    for chave, valor in os.environ.items():
        if (
            chave.startswith("PDF_SENHA_")
            and chave not in canonicas
            and valor
            and valor not in vistas
        ):
            extras.append((chave, valor))
            vistas.add(valor)
    for chave, valor in sorted(extras):
        out.append(valor)
    if not out:
        logger.warning(
            "Nenhuma senha PDF encontrada no .env. "
            "Defina PDF_SENHA_PRIMARIA, PDF_SENHA_SECUNDARIA, PDF_SENHA_CPF."
        )
    return out


# "Segredo guardado em arquivo é segredo confiado a quem o lê." -- princípio do .env
