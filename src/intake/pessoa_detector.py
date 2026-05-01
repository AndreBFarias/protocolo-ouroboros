"""Auto-detect de pessoa para arquivos da inbox.

Decisao ortogonal a classificação de tipo: cada arquivo e roteado para
``data/raw/<bucket>/...``, e essa pessoa precisa vir de algum lugar.

Schema do retorno (Sprint MOB-bridge-1):

    Compatibilidade preservada com a estrutura fisica de
    ``data/raw/`` (não alterada nesta sprint). O detector retorna
    rotulos legacy (``andre``/``vitoria``/``casal``), que são
    aliases bijetivos de ``pessoa_a``/``pessoa_b``/``casal``. A
    traducao para identidade generica ocorre em
    ``src.utils.pessoas.pessoa_id_de_legacy`` no momento em que o
    valor e persistido no XLSX (coluna ``quem``).

Detecao em camadas (curta-circuito no primeiro hit):

    1. CPF do preview cadastrado em ``mappings/cpfs_pessoas.yaml``.
    2. CPF / CNPJ / razao social / alias casados via
       ``mappings/pessoas.yaml`` (identidade rica, fonte canonica).
    3. Pasta-pai do arquivo casa com bucket conhecido.
    4. Fallback ``casal`` -- nunca chuta sem evidencia.

API:

    pessoa, fonte = detectar_pessoa(caminho_arquivo, preview_texto)

Devolve uma tupla ``(pessoa, fonte_da_decisao)``. ``fonte`` e string
humano-legivel para auditoria (nunca contem PII em claro).

LGPD: ``mappings/cpfs_pessoas.yaml`` e ``mappings/pessoas.yaml`` ficam
no ``.gitignore``. Repo carrega so o ``.example``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml

from src.intake.glyph_tolerant import extrair_cpf
from src.utils.logger import configurar_logger, hash_curto_pii
from src.utils.pessoas import pessoa_id_de_pasta

logger = configurar_logger("intake.pessoa")

Pessoa = Literal["andre", "vitoria", "casal", "_indefinida"]

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_MAPPING: Path = _RAIZ_REPO / "mappings" / "cpfs_pessoas.yaml"
_PATH_PESSOAS: Path = _RAIZ_REPO / "mappings" / "pessoas.yaml"

_PESSOAS_VALIDAS: frozenset[str] = frozenset({"andre", "vitoria", "casal"})

# Schema canonico (yaml + XLSX coluna quem) e bijetivo aos rotulos
# fisicos (pasta em data/raw/). O detector retorna rotulo fisico e
# normaliza chaves de yaml na entrada via este mapa.
_GENERICO_PARA_FISICO: dict[str, str] = {
    "pessoa_a": "andre",
    "pessoa_b": "vitoria",
    "casal": "casal",
    "andre": "andre",
    "vitoria": "vitoria",
}

# Cache do mapping carregado uma vez no primeiro uso.
_CACHE_CPFS: dict[str, str] | None = None
# Identidade completa (CPFs + CNPJs + razao social + aliases).
_CACHE_PESSOAS: dict | None = None


# ============================================================================
# API publica
# ============================================================================


def detectar_pessoa(
    caminho_arquivo: Path,
    preview_texto: str | None,
) -> tuple[Pessoa, str]:
    """Devolve ``(pessoa, fonte_da_decisao)``.

    Ordem (curta-circuito no primeiro hit):
      1. CPF do preview cadastrado em ``mappings/cpfs_pessoas.yaml``
      2. Casamento rico via ``mappings/pessoas.yaml``
      3. Pasta-pai do arquivo casa com bucket conhecido
      4. Fallback ``casal``

    Nunca levanta. Mapping ausente -> camada respectiva pulada.
    """
    if preview_texto:
        cpf = extrair_cpf(preview_texto)
        if cpf:
            mapeamento = _carregar_mapeamento_se_preciso()
            cpf_chave = _normalizar_cpf_chave(cpf)
            pessoa = mapeamento.get(cpf_chave)
            if pessoa in _PESSOAS_VALIDAS:
                return pessoa, f"CPF {cpf}"  # type: ignore[return-value]

        pessoa_rica, fonte_rica = _casar_via_pessoas_yaml(preview_texto)
        if pessoa_rica:
            return pessoa_rica, fonte_rica  # type: ignore[return-value]

    pessoa_pasta_generica = pessoa_id_de_pasta(caminho_arquivo)
    if pessoa_pasta_generica:
        pessoa_pasta = _GENERICO_PARA_FISICO.get(pessoa_pasta_generica, "casal")
        if pessoa_pasta in _PESSOAS_VALIDAS:
            return pessoa_pasta, f"path '{caminho_arquivo.parent.name}/'"  # type: ignore[return-value]

    return "casal", "fallback (sem CPF/CNPJ/razao social mapeados + pasta-pai não-bucket)"


def recarregar_mapeamento(path: Path | None = None) -> dict[str, str]:
    """Recarrega ``mappings/cpfs_pessoas.yaml``.

    Schema aceito (valores ``pessoa_a/pessoa_b/casal`` ou aliases
    historicos ``andre/vitoria/casal`` -- ambos são normalizados):

        cpfs:
          "00000000000": pessoa_a
          "11111111111": pessoa_b
          "22222222222": casal

    Mapping ausente e OK -- detector simplesmente nunca casa pela camada 1.
    Mapping com schema inválido levanta ``ValueError`` (falha-cedo).
    """
    global _CACHE_CPFS
    arquivo = path or _PATH_MAPPING

    if not arquivo.exists():
        logger.debug(
            "mappings/cpfs_pessoas.yaml ausente -- camada 1 inativa, pessoas.yaml "
            "cobre CPF/CNPJ/razao/alias via _casar_via_pessoas_yaml."
        )
        _CACHE_CPFS = {}
        return _CACHE_CPFS

    with arquivo.open(encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}

    if not isinstance(dados, dict):
        raise ValueError(f"YAML em {arquivo} não é dict raiz -- esperado chave 'cpfs' no topo")
    cpfs_raw = dados.get("cpfs", {})
    if not isinstance(cpfs_raw, dict):
        raise ValueError(f"YAML em {arquivo}: chave 'cpfs' deve ser dict")

    mapeamento: dict[str, str] = {}
    for chave_bruta, valor in cpfs_raw.items():
        chave = _normalizar_cpf_chave(str(chave_bruta))
        if len(chave) != 11 or not chave.isdigit():
            logger.warning(
                "CPF inválido em mappings/cpfs_pessoas.yaml: %r (esperado 11 digitos)",
                chave_bruta,
            )
            continue
        valor_normalizado = _GENERICO_PARA_FISICO.get(str(valor).lower())
        if valor_normalizado is None:
            logger.warning(
                "valor inválido para CPF %r em mappings/cpfs_pessoas.yaml: %r "
                "(esperado pessoa_a|pessoa_b|casal ou alias andre/vitoria/casal)",
                chave_bruta,
                valor,
            )
            continue
        mapeamento[chave] = valor_normalizado

    _CACHE_CPFS = mapeamento
    logger.info("cpfs_pessoas.yaml carregado: %d CPF(s) registrado(s)", len(_CACHE_CPFS))
    return _CACHE_CPFS


# ============================================================================
# Internals
# ============================================================================


def _carregar_mapeamento_se_preciso() -> dict[str, str]:
    if _CACHE_CPFS is None:
        recarregar_mapeamento()
    return _CACHE_CPFS or {}


def _normalizar_cpf_chave(cpf: str) -> str:
    """Remove pontuacao e espacos, devolve so digitos."""
    return re.sub(r"\D", "", cpf)


def _carregar_pessoas_se_preciso() -> dict:
    """Carrega mappings/pessoas.yaml (identidade rica)."""
    global _CACHE_PESSOAS
    if _CACHE_PESSOAS is not None:
        return _CACHE_PESSOAS
    if not _PATH_PESSOAS.exists():
        _CACHE_PESSOAS = {}
        return _CACHE_PESSOAS
    try:
        with _PATH_PESSOAS.open(encoding="utf-8") as f:
            _CACHE_PESSOAS = yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as exc:
        logger.warning("falha ao ler mappings/pessoas.yaml: %s", exc)
        _CACHE_PESSOAS = {}
    return _CACHE_PESSOAS


def recarregar_pessoas(path: Path | None = None) -> dict:
    """Recarrega mappings/pessoas.yaml (use em testes)."""
    global _CACHE_PESSOAS
    _CACHE_PESSOAS = None
    if path:
        global _PATH_PESSOAS
        _PATH_PESSOAS = path
    return _carregar_pessoas_se_preciso()


def _casar_via_pessoas_yaml(texto: str) -> tuple[Pessoa | None, str]:
    """Casa texto contra CPF, CNPJ, razao social e alias de pessoas.yaml.

    Aceita chaves de topo genericas (``pessoa_a``/``pessoa_b``/``casal``)
    ou aliases historicos (``andre``/``vitoria``/``casal``); SEMPRE
    retorna identificador generico.

    Ordem: CPF > CNPJ (raiz 8 digitos) > razao social > alias.
    """
    dados = _carregar_pessoas_se_preciso()
    pessoas = dados.get("pessoas") or {}
    if not pessoas:
        return None, ""

    texto_upper = texto.upper()
    digitos_texto = re.sub(r"\D", "", texto)

    # 1. CPF -- 11 digitos limpos
    for pessoa, ids in pessoas.items():
        pessoa_gen = _GENERICO_PARA_FISICO.get(str(pessoa).lower())
        if pessoa_gen not in _PESSOAS_VALIDAS:
            continue
        for cpf in ids.get("cpfs", []) or []:
            digitos_cpf = re.sub(r"\D", "", str(cpf))
            if len(digitos_cpf) == 11 and digitos_cpf in digitos_texto:
                return pessoa_gen, f"CPF hash={hash_curto_pii(digitos_cpf)}"  # type: ignore[return-value]

    # 2. CNPJ (raiz 8 digitos)
    for pessoa, ids in pessoas.items():
        pessoa_gen = _GENERICO_PARA_FISICO.get(str(pessoa).lower())
        if pessoa_gen not in _PESSOAS_VALIDAS:
            continue
        for cnpj in ids.get("cnpjs", []) or []:
            raiz = re.sub(r"\D", "", str(cnpj).split("/")[0])
            if len(raiz) >= 8 and raiz[:8] in digitos_texto:
                return pessoa_gen, f"CNPJ {cnpj}"  # type: ignore[return-value]

    # 3. Razao social literal
    for pessoa, ids in pessoas.items():
        pessoa_gen = _GENERICO_PARA_FISICO.get(str(pessoa).lower())
        if pessoa_gen not in _PESSOAS_VALIDAS:
            continue
        for razao in ids.get("razao_social", []) or []:
            if str(razao).upper() in texto_upper:
                return pessoa_gen, f"razao social hash={hash_curto_pii(str(razao))}"  # type: ignore[return-value]

    # 4. Alias curto
    for pessoa, ids in pessoas.items():
        pessoa_gen = _GENERICO_PARA_FISICO.get(str(pessoa).lower())
        if pessoa_gen not in _PESSOAS_VALIDAS:
            continue
        for alias in ids.get("aliases", []) or []:
            if str(alias).upper() in texto_upper:
                return pessoa_gen, f"alias hash={hash_curto_pii(str(alias))}"  # type: ignore[return-value]

    return None, ""


# "Onde não ha prova, não ha acusacao." -- principio do direito civilizado
