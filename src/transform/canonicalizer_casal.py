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
    """Retorna True se a descrição casa com identidade dos titulares do casal.

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


def variantes_curtas(
    descricao: str,
    banco_origem: str,
    caminho_yaml: Optional[str] = None,
) -> bool:
    """Nível 2 do matcher: variantes curtas sob contexto bancário obrigatório.

    Sprint 82: cobre descrições abreviadas que o matcher rigoroso
    `e_transferencia_do_casal` deliberadamente recusa (para não gerar
    falso-positivo com homônimos). Esta função só retorna True se a
    descrição satisfizer TODAS as condições de uma regra declarada em
    `mappings/contas_casal.yaml` na chave `nomes_variantes`:

        * banco_origem está na whitelist `bancos` da regra;
        * pelo menos `min_matches` tokens da regra aparecem no texto;
        * se a regra tem `marcadores`, pelo menos 1 marcador aparece;
        * se a regra tem `data_no_texto: true`, a descrição contém
          um padrão `DD/MM` (dois dígitos + barra + dois dígitos).

    Contrato de composição com `e_transferencia_do_casal`:
        - O chamador tipicamente tenta PRIMEIRO `e_transferencia_do_casal`.
          Se ele retornar True, encerra. Só se retornar False é que se
          testa `variantes_curtas`. Nunca chame os dois em paralelo sem
          essa precedência, senão a métrica de falso-positivo mistura
          contribuição de ambos os níveis.

    Fail-closed: se o YAML estiver ausente ou inválido, retorna False.
    """
    if not descricao or not banco_origem:
        return False

    config = _carregar_config(caminho_yaml)
    if not config:
        return False

    desc_upper_sem_acento = _remover_acentos(descricao.upper())

    for pessoa, perfil in config.items():
        if not isinstance(perfil, dict):
            continue

        regras = perfil.get("nomes_variantes", []) or []
        for regra in regras:
            if not isinstance(regra, dict):
                continue

            bancos_aceitos = regra.get("bancos", []) or []
            if banco_origem not in bancos_aceitos:
                continue

            tokens = regra.get("tokens", []) or []
            min_matches = int(regra.get("min_matches", 1))
            acertos = 0
            for token in tokens:
                token_norm = _remover_acentos(str(token).upper().strip())
                if not token_norm:
                    continue
                # Início de palavra é obrigatório (evita casar "VITORIA"
                # dentro de "MERCAVITORIA"), mas o FIM aceita limite de
                # palavra OU dígito aderente (cobre nome+data colados, onde
                # a data vem colada ao nome em extrato Itaú).
                padrao = rf"(?<!\w){re.escape(token_norm)}(?=\W|\d|$)"
                if re.search(padrao, desc_upper_sem_acento):
                    acertos += 1
            if acertos < min_matches:
                continue

            marcadores = regra.get("marcadores", []) or []
            if marcadores:
                marcador_ok = any(
                    _remover_acentos(str(m).upper()) in desc_upper_sem_acento for m in marcadores
                )
                if not marcador_ok:
                    continue

            if regra.get("data_no_texto") and not re.search(r"\d{2}/\d{2}", descricao):
                continue

            logger.debug(
                "Match por variante curta: pessoa=%s banco=%s tokens=%s",
                pessoa,
                banco_origem,
                tokens,
            )
            return True

    return False


# "Conhecer é reconhecer." -- Heráclito
