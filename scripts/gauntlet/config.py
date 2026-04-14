"""Configuração central do gauntlet de testes."""

from dataclasses import dataclass, field
from pathlib import Path

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[2]
FIXTURES_DIR: Path = Path(__file__).resolve().parent / "fixtures"
REPORT_PATH: Path = RAIZ_PROJETO / "GAUNTLET_REPORT.md"

FASES_DISPONIVEIS: list[str] = [
    "extratores",
    "categorias",
    "dedup",
    "xlsx",
    "relatorio",
    "projecoes",
    "obsidian",
    "dashboard",
]

CATEGORIAS_ESPERADAS: dict[str, str] = {
    "IFOOD": "Delivery",
    "UBER TRIP": "Transporte",
    "DROGARIA RAIA": "Remédios",
    "NEOENERGIA BRASILIA": "Energia",
    "CAESB": "Água",
    "SHOPEE": "Compras Online",
    "PETZ": "Pets",
    "NETFLIX.COM": "Assinaturas",
    "MERCADO LIVRE": "Compras Online",
    "SESC NATACAO": "Educação e Esporte",
}

CLASSIFICACOES_ESPERADAS: dict[str, str] = {
    "IFOOD": "Questionável",
    "NEOENERGIA BRASILIA": "Obrigatório",
    "SHOPEE": "Supérfluo",
    "DROGARIA RAIA": "Obrigatório",
    "PETZ": "Obrigatório",
}

ABAS_XLSX_ESPERADAS: list[str] = [
    "extrato",
    "renda",
    "resumo_mensal",
    "dividas_ativas",
    "inventario",
    "prazos",
    "irpf",
    "analise",
]

COLUNAS_EXTRATO: list[str] = [
    "data",
    "valor",
    "forma_pagamento",
    "local",
    "quem",
    "categoria",
    "classificacao",
    "banco_origem",
    "tipo",
    "mes_ref",
    "tag_irpf",
    "obs",
]


@dataclass
class ResultadoTeste:
    """Resultado individual de um teste do gauntlet."""

    nome: str
    passou: bool
    tempo: float = 0.0
    detalhe: str = ""
    erro: str = ""


@dataclass
class ResultadoFase:
    """Resultado agregado de uma fase do gauntlet."""

    nome: str
    testes: list[ResultadoTeste] = field(default_factory=list)
    tempo_total: float = 0.0

    @property
    def total(self) -> int:
        return len(self.testes)

    @property
    def ok(self) -> int:
        return sum(1 for t in self.testes if t.passou)

    @property
    def falhas(self) -> int:
        return self.total - self.ok

    @property
    def passou(self) -> bool:
        return self.falhas == 0


# "Não existe vento favorável para quem não sabe onde quer chegar." -- Sêneca
