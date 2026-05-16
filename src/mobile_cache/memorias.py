"""Leitor e validador do cache ``memorias.json`` consumido pelo dashboard.

Diferente de geradores como :mod:`src.mobile_cache.humor_heatmap`, este
módulo NÃO produz o cache — quem grava é o app Mobile
(``Protocolo-Mob-Ouroboros``, sprints ``I-FOTO`` / ``I-AUDIO`` /
``I-VIDEO``). Aqui apenas:

* :func:`carregar` lê ``<vault_root>/.ouroboros/cache/memorias.json``;
* :func:`validar` confere o payload contra
  ``mappings/schema_memorias.json`` (JSON Schema 2020-12, ADR-25);
* :func:`carregar_validado` combina os dois e devolve
  ``(items, gerado_em)`` para a UI consumir direto.

Espelha o padrão de :mod:`src.mobile_cache.humor_heatmap` em:

* docstring de topo + citação de filósofo no rodapé (padrão ``(g)``);
* logger via :func:`src.utils.logger.configurar_logger`;
* constantes ``SCHEMA_VERSION`` e ``CACHE_FILENAME`` no topo;
* tolerância a vault ausente (retorna lista vazia, não levanta).

Schema canônico em :doc:`docs/adr/ADR-25-memorias-schema.md`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from src.utils.logger import configurar_logger

logger = configurar_logger("mobile_cache.memorias")

SCHEMA_VERSION: int = 1
CACHE_FILENAME: str = "memorias.json"
TIPOS_VALIDOS: tuple[str, ...] = ("foto", "audio", "texto", "video")

# Caminho do JSON Schema relativo à raiz do repositório.
# Resolvido em runtime para casar com a localização real do projeto.
_SCHEMA_PATH_RELATIVA = Path("mappings") / "schema_memorias.json"


def _raiz_repo() -> Path:
    """Localiza a raiz do repositório procurando ``pyproject.toml``."""
    aqui = Path(__file__).resolve()
    for ancestre in aqui.parents:
        if (ancestre / "pyproject.toml").exists():
            return ancestre
    return aqui.parents[2]


@lru_cache(maxsize=1)
def _carregar_schema() -> dict[str, Any]:
    """Carrega o JSON Schema oficial uma única vez por processo."""
    caminho = _raiz_repo() / _SCHEMA_PATH_RELATIVA
    if not caminho.exists():
        raise FileNotFoundError(f"schema_memorias.json não encontrado em {caminho}")
    return json.loads(caminho.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validador() -> Draft202012Validator:
    """Devolve o validador compilado uma única vez."""
    schema = _carregar_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validar(payload: dict[str, Any]) -> list[str]:
    """Valida o payload contra o schema. Devolve lista de erros legíveis.

    Retorna lista vazia quando o payload é válido. Mensagens são
    formatadas com o caminho dentro do documento (``items[3].tipo``)
    seguido da causa, prontas para log/UI.
    """
    erros: list[str] = []
    for err in sorted(_validador().iter_errors(payload), key=lambda e: e.path):
        caminho = ".".join(str(parte) for parte in err.absolute_path) or "<raiz>"
        erros.append(f"{caminho}: {err.message}")
    return erros


def carregar(vault_root: Path | None) -> dict[str, Any] | None:
    """Lê o cache ``memorias.json`` do vault.

    Retorna o payload completo (dict) quando existe e é JSON válido.
    Retorna ``None`` quando vault ausente, arquivo ausente ou JSON
    malformado — nunca levanta para a UI.
    """
    if vault_root is None:
        return None
    arquivo = Path(vault_root) / ".ouroboros" / "cache" / CACHE_FILENAME
    if not arquivo.exists():
        return None
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("falha ao ler %s: %s", arquivo, exc)
        return None
    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        logger.warning("memorias.json malformado em %s: %s", arquivo, exc)
        return None


def carregar_validado(
    vault_root: Path | None,
    *,
    estrito: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """Lê e valida o cache. Retorna ``(items, gerado_em)``.

    Quando o JSON está ausente, devolve ``([], None)`` sem ruído.

    Quando o JSON existe mas viola o schema:

    * em modo padrão (``estrito=False``): loga warning, devolve
      ``([], gerado_em_se_disponivel)`` para a UI cair em skeleton;
    * em modo ``estrito=True``: levanta :class:`ValidationError`
      com o resumo dos erros (uso em testes/validação CI).
    """
    payload = carregar(vault_root)
    if payload is None:
        return [], None

    erros = validar(payload)
    if erros:
        resumo = "; ".join(erros[:5])
        if estrito:
            raise ValidationError(f"memorias.json inválido ({len(erros)} erro(s)): {resumo}")
        logger.warning("memorias.json inválido (%d erro(s)): %s", len(erros), resumo)
        gerado_em = payload.get("gerado_em") if isinstance(payload, dict) else None
        return [], gerado_em if isinstance(gerado_em, str) else None

    items = payload.get("items") or []
    if not isinstance(items, list):
        return [], payload.get("gerado_em")
    gerado_em = payload.get("gerado_em")
    return items, gerado_em if isinstance(gerado_em, str) else None


# "A memória é o diário que carregamos conosco." -- Oscar Wilde
