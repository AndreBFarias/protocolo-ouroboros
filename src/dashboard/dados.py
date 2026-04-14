"""Módulo de carregamento e cache de dados do controle de bordo."""

from pathlib import Path

import pandas as pd
import streamlit as st

CAMINHO_XLSX: Path = (
    Path(__file__).resolve().parents[2] / "data" / "output" / "controle_bordo_2026.xlsx"
)

ABAS: list[str] = [
    "extrato",
    "renda",
    "dividas_ativas",
    "inventario",
    "prazos",
    "resumo_mensal",
    "irpf",
    "analise",
]


@st.cache_data(ttl=300)
def carregar_dados() -> dict[str, pd.DataFrame]:
    """Carrega todas as abas do XLSX e retorna dict de DataFrames.

    Retorna dicionário vazio se o arquivo não existir.
    """
    if not CAMINHO_XLSX.exists():
        return {}

    resultado: dict[str, pd.DataFrame] = {}
    xls = pd.ExcelFile(CAMINHO_XLSX)

    for aba in ABAS:
        if aba in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=aba)
            resultado[aba] = df

    return resultado


def obter_meses_disponiveis(dados: dict[str, pd.DataFrame]) -> list[str]:
    """Retorna lista ordenada de meses disponíveis no extrato."""
    if "extrato" not in dados:
        return []

    meses = dados["extrato"]["mes_ref"].dropna().unique().tolist()
    return sorted(meses, reverse=True)


def filtrar_por_mes(df: pd.DataFrame, mes: str, coluna: str = "mes_ref") -> pd.DataFrame:
    """Filtra DataFrame por mês de referência."""
    if coluna not in df.columns:
        return df
    return df[df[coluna] == mes].copy()


def filtrar_por_pessoa(df: pd.DataFrame, pessoa: str) -> pd.DataFrame:
    """Filtra DataFrame por pessoa (André/Vitória/Todos)."""
    if pessoa == "Todos" or "quem" not in df.columns:
        return df
    return df[df["quem"] == pessoa].copy()


def formatar_moeda(valor: float) -> str:
    """Formata valor numérico como moeda brasileira."""
    if pd.isna(valor):
        return "R$ 0,00"
    sinal = "-" if valor < 0 else ""
    valor_abs = abs(valor)
    return f"{sinal}R$ {valor_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# "Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca
