"""Módulo de carregamento e cache de dados do Protocolo Ouroboros."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils.logger import configurar_logger

logger = configurar_logger("dashboard.dados")

CAMINHO_XLSX: Path = Path(__file__).resolve().parents[2] / "data" / "output" / "ouroboros_2026.xlsx"

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

# Abas cujo cabeçalho de colunas está na linha 2 (linha 1 = aviso de snapshot)
ABAS_COM_AVISO: set[str] = {"dividas_ativas", "inventario", "prazos"}


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
            skip = 1 if aba in ABAS_COM_AVISO else 0
            df = pd.read_excel(
                xls,
                sheet_name=aba,
                keep_default_na=False,
                na_values=[""],
                skiprows=skip,
            )
            resultado[aba] = df

    return resultado


def obter_meses_disponiveis(dados: dict[str, pd.DataFrame]) -> list[str]:
    """Retorna lista de meses disponíveis, com o mês atual (ou mais próximo) primeiro."""
    if "extrato" not in dados:
        return []

    from datetime import date

    meses = sorted(dados["extrato"]["mes_ref"].dropna().unique().tolist(), reverse=True)
    mes_atual = date.today().strftime("%Y-%m")

    if mes_atual in meses:
        meses.remove(mes_atual)
        meses.insert(0, mes_atual)
    else:
        anteriores = [m for m in meses if m <= mes_atual]
        if anteriores:
            mais_proximo = anteriores[0]
            meses.remove(mais_proximo)
            meses.insert(0, mais_proximo)

    return meses


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


def calcular_saldo_acumulado(
    dados: dict[str, pd.DataFrame],
    mes: str,
    pessoa: str = "Todos",
) -> float:
    """Calcula saldo acumulado (receitas - despesas) até o mês informado."""
    if "extrato" not in dados:
        return 0.0

    df = dados["extrato"].copy()
    df = filtrar_por_pessoa(df, pessoa)

    if "mes_ref" in df.columns:
        df = df[df["mes_ref"] <= mes]

    df = df[df["tipo"] != "Transferência Interna"]

    receita = df[df["tipo"] == "Receita"]["valor"].sum()
    despesa = df[df["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()

    return float(receita - despesa)


def obter_semanas_do_mes(dados: dict[str, pd.DataFrame], mes: str) -> list[str]:
    """Retorna semanas disponíveis dentro de um mês (formato 'Sem N - DD/MM a DD/MM')."""
    if "extrato" not in dados or "data" not in dados["extrato"].columns:
        return []

    df = dados["extrato"].copy()
    df = df[df["mes_ref"] == mes]
    if df.empty:
        return []

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data_dt"])
    df["semana_iso"] = df["data_dt"].dt.isocalendar().week.astype(int)

    semanas: list[str] = []
    for sem_num in sorted(df["semana_iso"].unique()):
        subset = df[df["semana_iso"] == sem_num]
        inicio = subset["data_dt"].min().strftime("%d/%m")
        fim = subset["data_dt"].max().strftime("%d/%m")
        label = f"Sem {sem_num} - {inicio} a {fim}"
        semanas.append(label)
    return semanas


def obter_dias_do_mes(dados: dict[str, pd.DataFrame], mes: str) -> list[str]:
    """Retorna dias disponíveis dentro de um mês (formato DD/MM/YYYY)."""
    if "extrato" not in dados or "data" not in dados["extrato"].columns:
        return []

    df = dados["extrato"].copy()
    df = df[df["mes_ref"] == mes]
    if df.empty:
        return []

    df["data_dt"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data_dt"])
    dias = sorted(df["data_dt"].dt.date.unique(), reverse=True)
    return [d.strftime("%d/%m/%Y") for d in dias]


def obter_anos_disponiveis(dados: dict[str, pd.DataFrame]) -> list[str]:
    """Retorna lista ordenada de anos disponíveis no extrato."""
    if "extrato" not in dados:
        return []
    meses = dados["extrato"]["mes_ref"].dropna().unique().tolist()
    anos = sorted({m[:4] for m in meses if len(m) >= 4}, reverse=True)
    return anos


def filtrar_por_periodo(
    df: pd.DataFrame,
    granularidade: str,
    periodo: str,
) -> pd.DataFrame:
    """Filtra DataFrame conforme granularidade e período selecionado."""
    if granularidade == "Ano":
        if "mes_ref" not in df.columns:
            return df
        return df[df["mes_ref"].str.startswith(periodo)].copy()

    if granularidade == "Dia" and "data" in df.columns:
        from datetime import datetime

        try:
            data_alvo = datetime.strptime(periodo, "%d/%m/%Y").date()
            df_copia = df.copy()
            df_copia["_data_dt"] = pd.to_datetime(df_copia["data"], errors="coerce").dt.date
            resultado = df_copia[df_copia["_data_dt"] == data_alvo].drop(columns=["_data_dt"])
            return resultado
        except (ValueError, KeyError) as err:
            logger.debug("Filtro diário com período '%s' falhou: %s", periodo, err)

    if granularidade == "Semana" and "data" in df.columns:
        if periodo.startswith("Sem "):
            try:
                sem_num = int(periodo.split(" ")[1])
                df_copia = df.copy()
                df_copia["_data_dt"] = pd.to_datetime(df_copia["data"], errors="coerce")
                df_copia["_semana"] = df_copia["_data_dt"].dt.isocalendar().week.astype(int)
                resultado = df_copia[df_copia["_semana"] == sem_num].drop(
                    columns=["_data_dt", "_semana"]
                )
                return resultado
            except (ValueError, KeyError) as err:
                logger.debug("Filtro semanal com período '%s' falhou: %s", periodo, err)

    if "mes_ref" not in df.columns:
        return df
    return df[df["mes_ref"] == periodo].copy()


def formatar_moeda(valor: float) -> str:
    """Formata valor numérico como moeda brasileira."""
    if pd.isna(valor):
        return "R$ 0,00"
    sinal = "-" if valor < 0 else ""
    valor_abs = abs(valor)
    return f"{sinal}R$ {valor_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# "Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca
