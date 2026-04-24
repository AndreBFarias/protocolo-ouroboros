"""Aplicação automática de tags IRPF em transações financeiras."""

import re
from pathlib import Path
from typing import Optional

import yaml

from src.utils.logger import configurar_logger

logger = configurar_logger("irpf_tagger")

# Sprint 35 / B3 2026-04-23: regras carregadas de mappings/irpf_regras.yaml
# quando disponível. Hardcoded abaixo serve como fallback de retrocompat.
_CAMINHO_YAML_IRPF: Path = (
    Path(__file__).resolve().parents[2] / "mappings" / "irpf_regras.yaml"
)


def _carregar_regras_yaml() -> Optional[list[dict[str, str]]]:
    """Lê mappings/irpf_regras.yaml. None se ausente ou inválido."""
    if not _CAMINHO_YAML_IRPF.exists():
        return None
    try:
        with _CAMINHO_YAML_IRPF.open("r", encoding="utf-8") as f:
            dados = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        logger.warning("falha ao ler irpf_regras.yaml (%s); usando hardcoded", exc)
        return None
    regras = dados.get("regras")
    if not isinstance(regras, list) or not regras:
        return None
    validadas: list[dict[str, str]] = []
    for r in regras:
        if not isinstance(r, dict):
            continue
        if {"regex", "tag", "descricao"}.issubset(r.keys()):
            validadas.append(
                {
                    "regex": str(r["regex"]),
                    "tag": str(r["tag"]),
                    "descricao": str(r["descricao"]),
                }
            )
    return validadas if validadas else None

REGRAS_IRPF: list[dict[str, str]] = [
    # --- Rendimentos tributáveis ---
    {
        "regex": r"G4F",
        "tag": "rendimento_tributavel",
        "descricao": "Salário G4F",
    },
    {
        "regex": r"INFOBASE",
        "tag": "rendimento_tributavel",
        "descricao": "Salário Infobase",
    },
    {
        "regex": r"PAGTO.*SALARIO|CREDITO.*SALARIO",
        "tag": "rendimento_tributavel",
        "descricao": "Salário genérico",
    },
    # --- Rendimentos isentos ---
    {
        "regex": r"NEES|UFAL",
        "tag": "rendimento_isento",
        "descricao": "Bolsa NEES/UFAL",
    },
    {
        "regex": r"FGTS|FUNDO DE GARANTIA",
        "tag": "rendimento_isento",
        "descricao": "FGTS",
    },
    {
        "regex": r"REND PAGO APLIC|RENDIMENTO|JUROS.*POUPANCA|JUROS.*POUPANÇA",
        "tag": "rendimento_isento",
        "descricao": "Rendimento de aplicação/poupança",
    },
    # --- Dedutíveis médicos ---
    {
        "regex": r"CLINICA|CL[IÍ]NICA",
        "tag": "dedutivel_medico",
        "descricao": "Clínica médica",
    },
    {
        "regex": r"HOSPITAL",
        "tag": "dedutivel_medico",
        "descricao": "Hospital",
    },
    {
        "regex": r"CONSULT",
        "tag": "dedutivel_medico",
        "descricao": "Consulta médica",
    },
    {
        "regex": r"PSIQ",
        "tag": "dedutivel_medico",
        "descricao": "Psiquiatra",
    },
    {
        "regex": r"PSICOL",
        "tag": "dedutivel_medico",
        "descricao": "Psicólogo",
    },
    {
        "regex": r"LUDENS",
        "tag": "dedutivel_medico",
        "descricao": "Ludens (saúde)",
    },
    {
        "regex": r"AG.SERVICOS.NEUROLOGIC",
        "tag": "dedutivel_medico",
        "descricao": "Serviços neurológicos",
    },
    {
        "regex": r"ASSUNCAO.*CORREIA.*SERVICOS EM SAUD",
        "tag": "dedutivel_medico",
        "descricao": "Serviços de saúde",
    },
    {
        "regex": r"DENTIST|ODONT|ORTODON",
        "tag": "dedutivel_medico",
        "descricao": "Dentista/Ortodontia",
    },
    {
        "regex": r"FISIOTER|FONOAUDI",
        "tag": "dedutivel_medico",
        "descricao": "Fisioterapia/Fonoaudiologia",
    },
    {
        "regex": r"LABORAT|EXAME|DIAGNOS",
        "tag": "dedutivel_medico",
        "descricao": "Exames/Laboratório",
    },
    {
        "regex": r"PLANO.*SAUDE|UNIMED|AMIL|BRADESCO.*SAUDE|SULAMERICA",
        "tag": "dedutivel_medico",
        "descricao": "Plano de saúde",
    },
    # --- Impostos pagos ---
    {
        "regex": r"DARF",
        "tag": "imposto_pago",
        "descricao": "DARF",
    },
    {
        "regex": r"DAS.MEI|DAS.*Simples",
        "tag": "imposto_pago",
        "descricao": "DAS MEI/Simples",
    },
    {
        "regex": r"RECEITA.FED",
        "tag": "imposto_pago",
        "descricao": "Receita Federal",
    },
    # --- INSS retido ---
    {
        "regex": r"INSS",
        "tag": "inss_retido",
        "descricao": "INSS retido",
    },
]

_REGRAS_COMPILADAS: list[dict] = []


def _compilar_regras() -> list[dict]:
    """Compila as regras regex uma única vez (cache).

    Fonte: mappings/irpf_regras.yaml quando disponível; caso contrário cai
    em REGRAS_IRPF hardcoded (retrocompat Sprint 35 / B3 2026-04-23).
    """
    global _REGRAS_COMPILADAS  # noqa: PLW0603
    if _REGRAS_COMPILADAS:
        return _REGRAS_COMPILADAS

    regras_yaml = _carregar_regras_yaml()
    regras_origem = regras_yaml if regras_yaml is not None else REGRAS_IRPF
    if regras_yaml is not None:
        logger.info(
            "irpf_tagger: %d regras carregadas de mappings/irpf_regras.yaml",
            len(regras_yaml),
        )

    for regra in regras_origem:
        try:
            regex_compilado = re.compile(regra["regex"], re.IGNORECASE)
            _REGRAS_COMPILADAS.append(
                {
                    "regex": regex_compilado,
                    "tag": regra["tag"],
                    "descricao": regra["descricao"],
                }
            )
        except re.error as e:
            logger.error("Regex IRPF inválido '%s': %s", regra["regex"], e)

    return _REGRAS_COMPILADAS


def _aplicar_tag(transacao: dict) -> Optional[str]:
    """Aplica tag IRPF a uma transação individual.

    Retorna a tag aplicada ou None se nenhuma regra casou.
    Não sobrescreve tag já existente (overrides/categorizer têm prioridade).
    """
    if transacao.get("tag_irpf") is not None:
        return transacao["tag_irpf"]

    texto_busca = " ".join(
        [
            transacao.get("_descricao_original", ""),
            transacao.get("local", ""),
        ]
    )

    regras = _compilar_regras()
    for regra in regras:
        if regra["regex"].search(texto_busca):
            return regra["tag"]

    return None


_REGEX_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}/\d{4}-?\d{2}")
_REGEX_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}")


def _extrair_cnpj_cpf(transacao: dict) -> Optional[str]:
    """Extrai CNPJ ou CPF do contraparte a partir da descrição da transação."""
    texto = " ".join(
        [
            transacao.get("_descricao_original") or "",
            transacao.get("local") or "",
            transacao.get("obs") or "",
        ]
    )

    match_cnpj = _REGEX_CNPJ.search(texto)
    if match_cnpj:
        return match_cnpj.group()

    match_cpf = _REGEX_CPF.search(texto)
    if match_cpf:
        return match_cpf.group()

    return None


def aplicar_tags_irpf(transacoes: list[dict]) -> list[dict]:
    """Aplica tags IRPF e extrai CNPJ/CPF do contraparte.

    Tags possíveis:
    - rendimento_tributavel: salários (G4F, Infobase)
    - rendimento_isento: bolsa NEES/UFAL, FGTS, rendimentos de poupança
    - dedutivel_medico: clínicas, hospitais, psicólogos, psiquiatras
    - imposto_pago: DARF, DAS MEI, IRRF retido
    - inss_retido: INSS descontado nos contracheques
    """
    total_tags = 0
    total_cnpj = 0
    contagem_por_tag: dict[str, int] = {}

    for t in transacoes:
        tag = _aplicar_tag(t)
        if tag is not None:
            t["tag_irpf"] = tag
            total_tags += 1
            contagem_por_tag[tag] = contagem_por_tag.get(tag, 0) + 1

        if t.get("tag_irpf") and not t.get("cnpj_cpf"):
            cnpj_cpf = _extrair_cnpj_cpf(t)
            if cnpj_cpf:
                t["cnpj_cpf"] = cnpj_cpf
                total_cnpj += 1

    if total_tags > 0:
        logger.info("Tags IRPF aplicadas: %d transações tagueadas", total_tags)
        for tag, qtd in sorted(contagem_por_tag.items()):
            logger.info("  %s: %d", tag, qtd)
    if total_cnpj > 0:
        logger.info("CNPJ/CPF extraídos: %d transações", total_cnpj)

    return transacoes


# "A justica e a vontade constante de dar a cada um o que e seu." -- Ulpiano
