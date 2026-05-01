"""Resolver canônico de identidade de pessoa (Sprint MOB-bridge-1).

Módulo único que encapsula toda decisão "este texto/CPF/CNPJ/pasta
pertence a quem?". Substitui as múltiplas cópias espalhadas em
extractors, pipeline, normalizer, detector, dashboard e relatório.

Identificadores canônicos (genéricos, sem nome real):

    pessoa_a   identidade primária (titular do casal)
    pessoa_b   identidade secundária
    casal      compartilhado, indeterminado, fallback

Os nomes reais ficam em ``mappings/pessoas.yaml`` (PII, gitignored)
sob a chave ``display_name``. Só aparecem em runtime via ``nome_de``
para uso em relatórios e UI local-first. NUNCA são persistidos em
código, commits ou artefatos versionados.

API pública (4 funções):

    carregar_pessoas() -> dict
        Lê ``mappings/pessoas.yaml`` e cacheia. Retorna o dict bruto.

    resolver_pessoa(cpf, cnpj, razao_social, alias, fallback) -> str
        Retorna ``pessoa_a`` / ``pessoa_b`` / ``casal`` na ordem CPF
        > CNPJ raiz > razão social > alias > fallback.

    nome_de(pessoa_id) -> str
        Resolve ``display_name`` para uso em prosa de log, XLSX e UI.
        Retorna o próprio identificador se não houver display_name.

    pessoa_id_de_pasta(path) -> str | None
        Camada 2 do detector: lê o nome da pasta-pai e mapeia para
        ``pessoa_a`` / ``pessoa_b`` / ``casal``. Retorna None se a
        pasta não casa com nenhum bucket conhecido.

Helpers auxiliares para coexistência com a estrutura física legada
de ``data/raw/`` (preservada por design nesta sprint, ADR-23):

    pessoa_id_de_legacy(valor) -> str  # anonimato-allow: docstring exemplifica entradas
        Normaliza qualquer rótulo histórico (``"André"``,  # anonimato-allow: exemplo de entrada
        ``"Vitória"``, ``"andre"``, ``"vitoria"``, ``"pessoa_a"``,  # anonimato-allow
        etc.) para identificador genérico.

    pasta_fisica_de(pessoa_id) -> str
        Mapeia identificador genérico para o nome de pasta legacy
        em ``data/raw/<bucket>/``. Garante que arquivos antigos
        continuem em ``data/raw/andre/`` e ``data/raw/vitoria/``.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("utils.pessoas")

PessoaId = Literal["pessoa_a", "pessoa_b", "casal"]

PESSOAS_VALIDAS: frozenset[str] = frozenset({"pessoa_a", "pessoa_b", "casal"})

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_PESSOAS_YAML: Path = _RAIZ_REPO / "mappings" / "pessoas.yaml"

# Buckets aceitos no caminho do arquivo (data/raw/<bucket>/...).
# Aceita tanto a forma genérica nova (``pessoa_a``/``pessoa_b``)
# quanto os aliases históricos (``andre``/``vitoria``) usados pela
# estrutura física legada -- ambos mapeiam para o identificador
# genérico equivalente.
_PASTAS_PARA_PESSOA: dict[str, PessoaId] = {
    "pessoa_a": "pessoa_a",
    "pessoa_b": "pessoa_b",
    "casal": "casal",
    "andre": "pessoa_a",
    "vitoria": "pessoa_b",
}


def _path_yaml() -> Path:
    """Indireto para permitir override em testes via monkeypatch."""
    return _PATH_PESSOAS_YAML


@lru_cache(maxsize=1)
def _carregar_yaml_cacheado(_marcador: int = 0) -> dict:
    """Lê mappings/pessoas.yaml uma vez. ``_marcador`` permite invalidar."""
    arquivo = _path_yaml()
    if not arquivo.exists():
        logger.warning(
            "mappings/pessoas.yaml ausente em %s -- resolver retornará fallback", arquivo
        )
        return {}
    try:
        with arquivo.open(encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
        if not isinstance(dados, dict):
            logger.error("mappings/pessoas.yaml: raiz não é dict")
            return {}
        return dados
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("falha ao ler mappings/pessoas.yaml: %s", exc)
        return {}


_invalidador: int = 0


def carregar_pessoas() -> dict:
    """Retorna o dict carregado de ``mappings/pessoas.yaml``.

    Cache em memória via ``lru_cache``. Use ``recarregar_pessoas``
    para forçar releitura (em testes ou após editar o yaml em runtime).
    """
    return _carregar_yaml_cacheado(_invalidador)


def recarregar_pessoas(path: Path | None = None) -> dict:
    """Invalida cache e recarrega. Aceita path alternativo (testes)."""
    global _invalidador, _PATH_PESSOAS_YAML
    if path is not None:
        _PATH_PESSOAS_YAML = path
    _invalidador += 1
    _carregar_yaml_cacheado.cache_clear()
    return _carregar_yaml_cacheado(_invalidador)


def _so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def resolver_pessoa(
    cpf: str | None = None,
    cnpj: str | None = None,
    razao_social: str | None = None,
    alias: str | None = None,
    fallback: str = "casal",
) -> str:
    """Resolve identidade genérica a partir de qualquer combinação de pistas.

    Ordem de precedência (mais específico vence):

        1. CPF -- 11 dígitos limpos casam com qualquer CPF declarado em
           ``pessoas.<id>.cpfs`` no yaml.
        2. CNPJ -- raiz de 8 dígitos casa com qualquer CNPJ declarado
           em ``pessoas.<id>.cnpjs`` (aceita raiz sem ``/0001-XX``).
        3. Razão social -- comparação case-insensitive contra qualquer
           valor de ``pessoas.<id>.razao_social``.
        4. Alias -- comparação case-insensitive contra qualquer valor
           de ``pessoas.<id>.aliases``.
        5. Fallback -- valor passado pelo chamador (default ``casal``).

    Aceita chaves genéricas (``pessoa_a``/``pessoa_b``/``casal``) ou
    aliases históricos (``andre``/``vitoria``/``casal``) na raiz do
    yaml; sempre devolve identificador genérico canônico.

    Retorna sempre um dos identificadores em ``PESSOAS_VALIDAS``.
    Se algum campo do yaml estiver malformado, é ignorado silenciosamente
    (logs em WARNING para o operador rastrear).
    """
    dados = carregar_pessoas()
    pessoas = dados.get("pessoas") or {}
    if not pessoas:
        return _fallback_seguro(fallback, dados)

    # 1. CPF
    if cpf:
        digitos = _so_digitos(cpf)
        if len(digitos) == 11:
            for chave_pessoa, perfil in pessoas.items():
                pessoa_id = _normalizar_chave_pessoa(chave_pessoa)
                if pessoa_id not in PESSOAS_VALIDAS:
                    continue
                for cpf_yaml in (perfil or {}).get("cpfs") or []:
                    if _so_digitos(str(cpf_yaml)) == digitos:
                        return pessoa_id

    # 2. CNPJ raiz 8 dígitos
    if cnpj:
        raiz = _so_digitos(str(cnpj).split("/")[0])[:8]
        if len(raiz) == 8:
            for chave_pessoa, perfil in pessoas.items():
                pessoa_id = _normalizar_chave_pessoa(chave_pessoa)
                if pessoa_id not in PESSOAS_VALIDAS:
                    continue
                for cnpj_yaml in (perfil or {}).get("cnpjs") or []:
                    raiz_y = _so_digitos(str(cnpj_yaml).split("/")[0])[:8]
                    if raiz_y == raiz:
                        return pessoa_id

    # 3. Razão social literal (case-insensitive, contains)
    if razao_social:
        alvo = razao_social.upper().strip()
        for chave_pessoa, perfil in pessoas.items():
            pessoa_id = _normalizar_chave_pessoa(chave_pessoa)
            if pessoa_id not in PESSOAS_VALIDAS:
                continue
            for rz in (perfil or {}).get("razao_social") or []:
                if str(rz).upper().strip() == alvo or str(rz).upper() in alvo:
                    return pessoa_id

    # 4. Alias
    if alias:
        alvo_a = alias.upper().strip()
        for chave_pessoa, perfil in pessoas.items():
            pessoa_id = _normalizar_chave_pessoa(chave_pessoa)
            if pessoa_id not in PESSOAS_VALIDAS:
                continue
            for ali in (perfil or {}).get("aliases") or []:
                if str(ali).upper().strip() == alvo_a or str(ali).upper() in alvo_a:
                    return pessoa_id

    return _fallback_seguro(fallback, dados)


def _normalizar_chave_pessoa(chave: str) -> str | None:
    """Aceita ``pessoa_a``/``pessoa_b``/``casal`` ou aliases ``andre``/``vitoria``/``casal``."""
    if not chave:
        return None
    valor = str(chave).strip().lower()
    if valor == "pessoa_a" or valor == "andre":
        return "pessoa_a"
    if valor == "pessoa_b" or valor == "vitoria":
        return "pessoa_b"
    if valor == "casal":
        return "casal"
    return None


def _fallback_seguro(fallback: str, dados: dict) -> str:
    """Retorna fallback validado ou ``casal``."""
    if fallback in PESSOAS_VALIDAS:
        return fallback
    yaml_fb = dados.get("fallback_pessoa")
    if isinstance(yaml_fb, str) and yaml_fb in PESSOAS_VALIDAS:
        return yaml_fb
    return "casal"


def nome_de(pessoa_id: str) -> str:
    """Resolve ``display_name`` para uso em UI/relatórios/log.

    Retorna o ``display_name`` declarado em
    ``pessoas.<id>.display_name`` quando existe. Fallback retorna o
    próprio identificador (ex.: ``pessoa_a``), garantindo que o código
    não quebre nem invente nome se o yaml estiver ausente.

    Uso legítimo: prosa em XLSX consolidado, log de auditoria, label
    em dashboard local-first (ADR-24). NUNCA usar para nome de arquivo
    nem persistir em estrutura de dados versionada.

    Aceita também rótulos legados via ``pessoa_id_de_legacy`` antes de
    resolver (ex.: rótulos com nome real ainda vindos de XLSX antigos).
    """
    if not pessoa_id:
        return "Casal"
    canonico = pessoa_id if pessoa_id in PESSOAS_VALIDAS else pessoa_id_de_legacy(pessoa_id)
    if canonico == "casal":
        return "Casal"
    dados = carregar_pessoas()
    pessoas = dados.get("pessoas") or {}
    # Tenta tanto a chave genérica quanto a legacy (yaml pode ainda usar legacy).
    perfis_para_tentar = [canonico]
    if canonico == "pessoa_a":
        perfis_para_tentar.append("andre")
    elif canonico == "pessoa_b":
        perfis_para_tentar.append("vitoria")
    for chave in perfis_para_tentar:
        perfil = pessoas.get(chave) or {}
        display = perfil.get("display_name")
        if isinstance(display, str) and display.strip():
            return display.strip()
    return canonico


def pessoa_id_de_legacy(valor: str | None) -> str:
    """Normaliza qualquer rótulo legado para identificador genérico.

    Aceita ``"André"``/``"Vitória"``/``"Casal"`` (XLSX antigo, com  # anonimato-allow
    acento e Title Case), ``"andre"``/``"vitoria"``/``"casal"`` (pasta
    física, lowercase) ou ``"pessoa_a"``/``"pessoa_b"``/``"casal"``
    (canônico). Retorna sempre identificador genérico.

    Fallback: ``"casal"``.
    """
    if not valor:
        return "casal"
    chave = str(valor).strip().lower()
    chave = "".join(
        c for c in unicodedata.normalize("NFD", chave) if unicodedata.category(c) != "Mn"
    )
    if chave in {"pessoa_a", "andre"}:
        return "pessoa_a"
    if chave in {"pessoa_b", "vitoria"}:
        return "pessoa_b"
    if chave == "casal":
        return "casal"
    return "casal"


def pasta_fisica_de(pessoa_id: str) -> str:
    """Mapeia identificador genérico para nome de pasta no filesystem.

    Decisão arquitetural (ADR-23): a coluna ``quem`` no XLSX e os
    contratos internos são genéricos (``pessoa_a``/``pessoa_b``/``casal``),
    mas a estrutura física em ``data/raw/<bucket>/`` permanece com
    aliases históricos (``andre``/``vitoria``/``casal``) para preservar
    100% dos dados já gravados sem migração destrutiva. Este helper
    faz a tradução em runtime quando router/registry/extratores
    precisam construir paths em disco.

    Tratamento permissivo: se receber um valor já no formato físico
    (``andre``/``vitoria``/``casal``), retorna intacto.
    """
    chave = (pessoa_id or "").lower()
    if chave == "pessoa_a":
        return "andre"
    if chave == "pessoa_b":
        return "vitoria"
    if chave in {"andre", "vitoria", "casal"}:
        return chave
    return "casal"


def pessoa_id_de_pasta(path: str | Path) -> str | None:
    """Mapeia ``data/raw/<bucket>/...`` para ``pessoa_a``/``pessoa_b``/``casal``.

    Usado como fallback layer 2 do detector quando não há pista textual
    no conteúdo do arquivo. Retorna None se a pasta não casa.
    """
    if path is None:
        return None
    p = Path(path)
    for parte in reversed(p.parts):
        chave = parte.lower()
        if chave in _PASTAS_PARA_PESSOA:
            return _PASTAS_PARA_PESSOA[chave]
    return None


# "Toda pessoa tem direito à personalidade jurídica." -- Declaração
# Universal dos Direitos Humanos, Artigo 6.
