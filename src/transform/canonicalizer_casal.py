"""Matcher formal para identidade do casal em descrições bancárias.

Fonte única da verdade sobre "isto é uma transferência interna entre contas
do casal". Consulta `mappings/contas_casal.yaml` e retorna decisão booleana.

Uso:
    from src.transform.canonicalizer_casal import e_transferencia_do_casal
    if e_transferencia_do_casal(descricao):
        tipo = "Transferência Interna"

Contrato:
    - `e_transferencia_do_casal(descricao)` retorna True se a descrição
      casa com nome completo (word boundary, case-insensitive) ou CPF
      explícito (tolerante a pontuação) de alguém da whitelist.
    - Placeholders no YAML (ex: "<CPF_ANDRE>") NUNCA geram match -- são
      filtrados explicitamente para evitar falso-positivo.
    - Nomes curtos genéricos (ex: "ANDRE" sozinho) NÃO devem estar no
      YAML; o matcher não protege contra "ANDRE BARATA" se "ANDRE" for
      aceito. Mantenha nomes compostos e específicos.
"""

import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("canonicalizer_casal")

CAMINHO_YAML: Path = Path(__file__).resolve().parents[2] / "mappings" / "contas_casal.yaml"

REGEX_PLACEHOLDER: re.Pattern[str] = re.compile(r"^<.*>$")


def _remover_acentos(texto: str) -> str:
    """Normaliza texto removendo acentos (NFD + descarta combining marks)."""
    nfd = unicodedata.normalize("NFD", texto)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _so_digitos(texto: str) -> str:
    """Retorna apenas os dígitos de uma string (descarta pontuação)."""
    return re.sub(r"\D", "", texto)


@lru_cache(maxsize=1)
def _carregar_config(caminho: Optional[str] = None) -> dict:
    """Carrega e cacheia o YAML de whitelist do casal.

    Parâmetro `caminho` opcional para permitir override em testes; quando
    omitido, usa o YAML canônico em mappings/contas_casal.yaml.
    """
    alvo = Path(caminho) if caminho else CAMINHO_YAML
    if not alvo.exists():
        logger.warning(
            "contas_casal.yaml não encontrado em %s; matcher sempre retornará False",
            alvo,
        )
        return {}
    try:
        with open(alvo, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as erro:
        logger.error("Falha ao carregar %s: %s", alvo, erro)
        return {}


def resetar_cache() -> None:
    """Limpa o cache do YAML (útil em testes que recarregam configs)."""
    _carregar_config.cache_clear()


def e_transferencia_do_casal(descricao: str, caminho_yaml: Optional[str] = None) -> bool:
    """Retorna True se a descrição casa com identidade de André ou Vitória.

    Regras de matching:
        1. Nome aceito: .upper() + remoção de acentos, busca com \\b word
           boundary. Só casa se a palavra completa do YAML aparece na
           descrição (não casa "ANDRE" dentro de "ANDRE BARATA" quando o
           YAML tem "ANDRE DA SILVA BATISTA").
        2. CPF: compara apenas dígitos (descarta pontos e hífens). Só casa
           se o CPF no YAML tem 11 dígitos (não é placeholder).

    Em caso de config ausente ou inválida, retorna False (fail-closed:
    nunca marca como TI por default).
    """
    if not descricao:
        return False

    config = _carregar_config(caminho_yaml)
    if not config:
        return False

    desc_upper = _remover_acentos(descricao.upper())
    desc_digitos = _so_digitos(descricao)

    for pessoa, perfil in config.items():
        if not isinstance(perfil, dict):
            continue

        for nome in perfil.get("nomes_aceitos", []) or []:
            nome_norm = _remover_acentos(str(nome).upper().strip())
            if not nome_norm:
                continue
            padrao = rf"\b{re.escape(nome_norm)}\b"
            if re.search(padrao, desc_upper):
                logger.debug("Match por nome: pessoa=%s nome=%s", pessoa, nome)
                return True

        cpf_raw = perfil.get("cpf")
        if cpf_raw and not REGEX_PLACEHOLDER.match(str(cpf_raw).strip()):
            cpf_digitos = _so_digitos(str(cpf_raw))
            if len(cpf_digitos) == 11 and cpf_digitos in desc_digitos:
                logger.debug("Match por CPF: pessoa=%s", pessoa)
                return True

    return False


# "Conhecer é reconhecer." -- Heráclito
