"""Humanização de tipos canônicos de documento -- Sprint UX-126 (AC1).

Mapping `{tipo_canonico_slug -> nome_humano}` carregado de
`mappings/tipos_documento_humanizado.yaml`. Usado pela página Catalogação
(`src/dashboard/paginas/catalogacao.py`) para substituir slugs crus
(ex: `das_parcsn_andre`) por rótulos legíveis (ex: `DAS Parcelado André`).

Princípios:
- Cache em módulo (mapping é estável durante a vida do processo).
- Fallback determinístico: `slug.replace('_', ' ').title()` quando ausente.
- Sem dependência de Streamlit (testável em puro pytest).
- Tolerante a YAML ausente (devolve dict vazio + fallback continua a funcionar).
"""

from __future__ import annotations

from pathlib import Path

import yaml

_MAPPING_PATH: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "tipos_documento_humanizado.yaml"
)

_CACHE: dict[str, str] | None = None


def carregar_mapping() -> dict[str, str]:
    """Lê o YAML e devolve dict {slug: nome_humano}. Cacheia no módulo.

    Devolve dict vazio quando o arquivo não existe -- caller continua
    funcionando via fallback `humanizar()`.
    """
    global _CACHE
    if _CACHE is None:
        if not _MAPPING_PATH.exists():
            _CACHE = {}
        else:
            with _MAPPING_PATH.open("r", encoding="utf-8") as f:
                conteudo = yaml.safe_load(f) or {}
            # `yaml.safe_load` devolve dict; valida tipos.
            _CACHE = {
                str(k): str(v)
                for k, v in conteudo.items()
                if isinstance(k, str) and isinstance(v, str)
            }
    return _CACHE


def humanizar(tipo_canonico: str) -> str:
    """Devolve nome humano para um slug canônico.

    Fallback (slug não mapeado): `slug.replace('_', ' ').title()`.
    Slug vazio ou ``None`` devolve string vazia (defensivo).
    """
    if not tipo_canonico:
        return ""
    mapping = carregar_mapping()
    if tipo_canonico in mapping:
        return mapping[tipo_canonico]
    # Fallback determinístico: snake_case -> Title Case.
    return tipo_canonico.replace("_", " ").title()


def _resetar_cache_para_teste() -> None:
    """Helper para testes que mexem no YAML em runtime. Não usar em produção."""
    global _CACHE
    _CACHE = None


# "Dar nome ao que existe é o início de toda inteligência." -- inspirado em Carl Linnaeus
