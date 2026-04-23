"""Filtro determinístico de fontes reais de renda operacional.

Usado por src/load/xlsx_writer.py::_criar_aba_renda para decidir quais
transações "Receita" do extrato entram na aba `renda`.

Contrato: uma transação é renda operacional se a descrição casa ao menos
um padrão da whitelist em `mappings/fontes_renda.yaml` E não casa nenhum
padrão da blacklist. Holerites extraídos do contracheque_pdf.py não passam
por este filtro (são autoritários).

Motivo: aba `renda` antes continha 459 linhas (reembolsos PIX, cashback,
PIX entre amigos, estornos) -- quase todas falso-positivas. Filtro reduz
a fontes reais sem mexer no classificador de tipo global.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

_CAMINHO_YAML = Path(__file__).resolve().parents[2] / "mappings" / "fontes_renda.yaml"


@lru_cache(maxsize=1)
def _carregar_padroes() -> tuple[list[re.Pattern[str]], list[re.Pattern[str]]]:
    """Carrega YAML e compila regex. Cacheado por processo."""
    if not _CAMINHO_YAML.exists():
        return [], []

    with _CAMINHO_YAML.open("r", encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}

    whitelist: list[re.Pattern[str]] = []
    for grupo in (dados.get("fontes") or {}).values():
        for padrao in grupo or []:
            try:
                whitelist.append(re.compile(padrao))
            except re.error:
                continue

    blacklist_raw = dados.get("blacklist") or []
    blacklist = [re.compile(p) for p in blacklist_raw]
    return whitelist, blacklist


def eh_fonte_real_de_renda(descricao: str) -> bool:
    """True se descrição casa whitelist (mesmo que também case blacklist).

    Ordem: whitelist tem prioridade (ex: 'Transferência recebida pelo Pix -
    F2 MARKETING' casa whitelist mei_andre e também blacklist 'Transferência
    recebida' -- whitelist vence porque é mais específica).

    Uso típico: filtrar transações Receita inferidas antes de popular a
    aba `renda`. Holerites do extrator de contracheque vão direto (não
    chamam esta função).
    """
    if not descricao:
        return False

    whitelist, blacklist = _carregar_padroes()

    for pat in whitelist:
        if pat.search(descricao):
            return True

    for pat in blacklist:
        if pat.search(descricao):
            return False

    return False


# "Na dúvida, fora da renda." -- Karl Popper (princípio da falseabilidade)
