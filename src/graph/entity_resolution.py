"""Entity resolution para fornecedores via rapidfuzz. Sprint 42.

Estratégia em 2 passos:

  1. Normalização determinística: upper, strip, remoção de sufixos
     societários (S/A, LTDA, ME, EIRELI, EPP), remoção de pontuação.
     Resolve NEOENERGIA == "Neoenergia S/A" sem fuzzy.
  2. Fuzzy via rapidfuzz contra a lista de canônicos existentes; se
     similaridade >= threshold (85), unifica.

Decisões:
- Threshold 85 por padrão -- balanceia false positive vs false negative.
- Faixa 85-95 produz sugestão (caller registra em propostas).
- < 85 -> sempre cadastra novo.
- CNPJ desempata: se ambos têm CNPJ e diferem, NÃO unifica
  (conferência manual). Sprint 42 expõe como flag `cnpj_a` opcional.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz, process

from src.utils.logger import configurar_logger

logger = configurar_logger("graph.entity_resolution")

THRESHOLD_PADRAO: int = 85
THRESHOLD_SUGESTAO: int = 95  # >= 95 é match forte; 85-94 vira proposta


_SUFIXOS_SOCIETARIOS: tuple[str, ...] = (
    " S/A",
    " S.A.",
    " S A",
    " SA",
    " LTDA",
    " ME",
    " EIRELI",
    " EPP",
    " MEI",
)


# ============================================================================
# Estruturas
# ============================================================================


@dataclass(frozen=True)
class ResultadoResolucao:
    """Decisão sobre resolver um fornecedor novo contra uma lista existente."""

    nome_canonico: str
    similaridade: int
    decisao: Literal["match", "sugestao", "novo"]
    fonte: str  # "deterministico" | "fuzzy" | "novo"


# ============================================================================
# API pública
# ============================================================================


def normalizar_fornecedor(nome: str) -> str:
    """Aplica regras determinísticas: upper, strip, remove sufixos e pontuação.

    NEOENERGIA, "Neoenergia S/A", "neoenergia ltda" -> todos viram "NEOENERGIA".
    Útil como pre-processamento antes do fuzzy.
    """
    nome_upper = nome.strip().upper()
    for sufixo in _SUFIXOS_SOCIETARIOS:
        if nome_upper.endswith(sufixo):
            nome_upper = nome_upper[: -len(sufixo)].strip()
    # Remove pontuação leve (mantém acentos para preservar identidade visual)
    nome_upper = re.sub(r"[.,;:\-()/]+", " ", nome_upper)
    nome_upper = re.sub(r"\s+", " ", nome_upper).strip()
    return nome_upper


def resolver_fornecedor(
    nome_bruto: str,
    candidatos_existentes: list[str],
    threshold: int = THRESHOLD_PADRAO,
    cnpj_novo: str | None = None,
    cnpjs_por_canonico: dict[str, str] | None = None,
) -> ResultadoResolucao:
    """Decide se nome_bruto deve ser unificado com algum candidato existente.

    Args:
        nome_bruto: nome do fornecedor recém extraído (ex.: 'NEOENERGIA S/A')
        candidatos_existentes: lista de nomes canônicos já no grafo
        threshold: pontuação mínima rapidfuzz (0-100) para unificação
        cnpj_novo: CNPJ do fornecedor novo (se conhecido) -- desempata
        cnpjs_por_canonico: CNPJ conhecido por canônico existente

    Returns:
        ResultadoResolucao com nome_canonico escolhido e fonte da decisão.
    """
    nome_normalizado = normalizar_fornecedor(nome_bruto)

    # Primeiro: match determinístico exato após normalização
    for candidato in candidatos_existentes:
        if normalizar_fornecedor(candidato) == nome_normalizado:
            if not _cnpj_conflita(cnpj_novo, cnpjs_por_canonico, candidato):
                return ResultadoResolucao(
                    nome_canonico=candidato,
                    similaridade=100,
                    decisao="match",
                    fonte="deterministico",
                )

    # Segundo: fuzzy match
    if not candidatos_existentes:
        return ResultadoResolucao(
            nome_canonico=nome_normalizado,
            similaridade=0,
            decisao="novo",
            fonte="novo",
        )

    candidatos_normalizados = [normalizar_fornecedor(c) for c in candidatos_existentes]
    melhor = process.extractOne(
        nome_normalizado,
        candidatos_normalizados,
        scorer=fuzz.token_sort_ratio,
    )
    if melhor is None:
        return ResultadoResolucao(
            nome_canonico=nome_normalizado,
            similaridade=0,
            decisao="novo",
            fonte="novo",
        )

    _, score, indice = melhor
    score_int = int(score)
    canonico_correspondente = candidatos_existentes[indice]

    if score_int < threshold:
        return ResultadoResolucao(
            nome_canonico=nome_normalizado,
            similaridade=score_int,
            decisao="novo",
            fonte="novo",
        )

    if _cnpj_conflita(cnpj_novo, cnpjs_por_canonico, canonico_correspondente):
        # Mesmo nome similar, CNPJs diferentes -> não unifica
        return ResultadoResolucao(
            nome_canonico=nome_normalizado,
            similaridade=score_int,
            decisao="novo",
            fonte="cnpj_diferente",
        )

    if score_int >= THRESHOLD_SUGESTAO:
        return ResultadoResolucao(
            nome_canonico=canonico_correspondente,
            similaridade=score_int,
            decisao="match",
            fonte="fuzzy",
        )

    return ResultadoResolucao(
        nome_canonico=canonico_correspondente,
        similaridade=score_int,
        decisao="sugestao",
        fonte="fuzzy",
    )


# ============================================================================
# Internals
# ============================================================================


def _cnpj_conflita(
    cnpj_novo: str | None,
    cnpjs_por_canonico: dict[str, str] | None,
    canonico: str,
) -> bool:
    """True se ambos têm CNPJ e são diferentes (nunca unificar nesse caso)."""
    if not cnpj_novo or not cnpjs_por_canonico:
        return False
    cnpj_existente = cnpjs_por_canonico.get(canonico)
    if not cnpj_existente:
        return False
    return _normalizar_cnpj_chave(cnpj_novo) != _normalizar_cnpj_chave(cnpj_existente)


def _normalizar_cnpj_chave(cnpj: str) -> str:
    return re.sub(r"\D", "", cnpj)


# "Identidade não é semelhança -- mas semelhança é início." -- princípio do entity-resolution
