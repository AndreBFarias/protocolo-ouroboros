"""Módulo de carregamento e cache de dados do Protocolo Ouroboros."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src.utils.logger import configurar_logger

logger = configurar_logger("dashboard.dados")

CAMINHO_XLSX: Path = Path(__file__).resolve().parents[2] / "data" / "output" / "ouroboros_2026.xlsx"
CAMINHO_GRAFO: Path = Path(__file__).resolve().parents[2] / "data" / "output" / "grafo.sqlite"
CAMINHO_PROPOSTAS_LINKING: Path = (
    Path(__file__).resolve().parents[2] / "docs" / "propostas" / "linking"
)
# Sprint D2: DB de revisão humana (constantes de pasta brutas movidas para
# dados_revisor.py em INFRA-D2a -- re-exportadas no fim do arquivo).
CAMINHO_REVISAO_HUMANA: Path = (
    Path(__file__).resolve().parents[2] / "data" / "output" / "revisao_humana.sqlite"
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


def renderizar_dataframe(df: pd.DataFrame, na_rep: str = "—") -> pd.DataFrame:
    """Substitui valores nulos por `na_rep` antes de enviar ao `st.dataframe`.

    Evita que células com `NaN` apareçam serializadas como a string
    literal `nan` no dashboard. A substituição é feita em todas as
    colunas (numéricas e de texto) via conversão para `object` para
    permitir misturar tipos. A operação é não destrutiva: retorna uma
    cópia, preserva o DataFrame original.
    """
    if df.empty:
        return df.copy()
    return df.astype(object).where(df.notna(), na_rep)


def filtrar_por_pessoa(df: pd.DataFrame, pessoa: str) -> pd.DataFrame:
    """Filtra DataFrame por pessoa.

    Aceita ``"Todos"``, o ``display_name`` exibido na UI (resolvido em
    runtime via ``src.utils.pessoas.nome_de``) ou o identificador
    genérico canônico (``"pessoa_a"``/``"pessoa_b"``/``"casal"``).

    A normalização bilateral via ``pessoa_id_de_legacy`` garante
    compatibilidade com XLSX antigos onde ``df["quem"]`` ainda contém
    rótulos históricos com nome real (Sprint MOB-bridge-1, ADR-23).
    """
    if pessoa == "Todos" or "quem" not in df.columns:
        return df
    if df.empty:
        return df.copy()
    from src.utils.pessoas import pessoa_id_de_legacy

    alvo = pessoa_id_de_legacy(pessoa)
    quem_canonico = df["quem"].apply(pessoa_id_de_legacy)
    return df[quem_canonico == alvo].copy()


# Sprint 72: normalização de variações históricas de `forma_pagamento`.
# A coluna pode conter rótulos diferentes para a mesma intenção (ex.: "TED"
# contado como "Transferência"). Mantemos um dict canônico; valores fora do
# dict passam intactos (respeito à fonte) e aparecem no selectbox como
# grupos extras quando presentes.
_FORMAS_CANONICAS: dict[str, str] = {
    "TED": "Transferência",
    "DOC": "Transferência",
    "Transferência Interna": "Transferência",
    "Débito automático": "Débito",
    "Debito": "Débito",
    "Credito": "Crédito",
}


def filtro_forma_ativo() -> str | None:
    """Lê o filtro de forma de pagamento da session_state (Sprint 72).

    Retorna ``None`` quando não há seleção (ou streamlit ausente), o que
    permite que `filtrar_por_forma_pagamento` pule o filtro. Serve como
    adaptador entre a sidebar e as páginas que aplicam o filtro.
    """
    try:
        import streamlit as st
    except ImportError:
        return None
    if not hasattr(st, "session_state"):
        return None
    valor = st.session_state.get("filtro_forma")  # type: ignore[union-attr]
    if not valor or valor == "Todas":
        return None
    return str(valor)


def filtrar_por_forma_pagamento(df: pd.DataFrame, forma: str | None) -> pd.DataFrame:
    """Filtra DataFrame por `forma_pagamento` (Sprint 72).

    - `forma=None` ou ``"Todas"``: devolve o df sem filtrar.
    - Aplica canonicalização: "TED" e "DOC" são agrupados sob "Transferência",
      etc. (ver `_FORMAS_CANONICAS`).
    - Se a coluna `forma_pagamento` não existe, devolve o df intacto.
    """
    if not forma or forma == "Todas" or "forma_pagamento" not in df.columns:
        return df
    coluna_canonica = df["forma_pagamento"].fillna("").map(lambda v: _FORMAS_CANONICAS.get(v, v))
    mascara = coluna_canonica == forma
    return df[mascara].copy()


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


@st.cache_data(ttl=60)
def obter_fluxo_receita_categoria_fornecedor(mes_ref: str) -> dict:
    """Agrega valores do extrato em três séries (para 3 bar charts).

    Retorno:
        {
            "receita": [{"rotulo", "valor"}...],     # top receitas por local
            "despesa": [{"rotulo", "valor"}...],     # top 10 categorias
            "fornecedor": [{"rotulo", "valor"}...],  # top 10 locais de despesa
            "mes_ref": mes_ref,
        }
    Se XLSX ausente ou sem dados no mês, todas as listas vêm vazias.
    """
    vazio: dict = {
        "receita": [],
        "despesa": [],
        "fornecedor": [],
        "mes_ref": mes_ref,
    }
    dados = carregar_dados()
    if "extrato" not in dados or dados["extrato"].empty:
        return vazio

    df = dados["extrato"].copy()
    if "mes_ref" in df.columns:
        df = df[df["mes_ref"] == mes_ref]
    if df.empty:
        return vazio

    # --- receita por local ---
    receita_df = df[df["tipo"] == "Receita"]
    receita_list: list[dict] = []
    if not receita_df.empty:
        agrup = (
            receita_df.groupby("local")["valor"].sum().abs().sort_values(ascending=False).head(10)
        )
        receita_list = [
            {"rotulo": str(rotulo), "valor": float(valor)} for rotulo, valor in agrup.items()
        ]

    # --- despesa por categoria ---
    despesa_df = df[df["tipo"].isin(["Despesa", "Imposto"])]
    despesa_list: list[dict] = []
    if not despesa_df.empty and "categoria" in despesa_df.columns:
        agrup = (
            despesa_df.groupby("categoria")["valor"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
        )
        despesa_list = [
            {"rotulo": str(rotulo), "valor": float(valor)} for rotulo, valor in agrup.items()
        ]

    # --- fornecedor: top 10 locais de despesa ---
    fornecedor_list: list[dict] = []
    if not despesa_df.empty and "local" in despesa_df.columns:
        agrup = (
            despesa_df.groupby("local")["valor"].sum().abs().sort_values(ascending=False).head(10)
        )
        fornecedor_list = [
            {"rotulo": str(rotulo), "valor": float(valor)} for rotulo, valor in agrup.items()
        ]

    return {
        "receita": receita_list,
        "despesa": despesa_list,
        "fornecedor": fornecedor_list,
        "mes_ref": mes_ref,
    }


# Sprint INFRA-D2a: re-export de listar_pendencias_revisao + constantes de
# diretórios brutos. Mantido para retrocompat com testes que monkeypatcham
# 'd.listar_pendencias_revisao' diretamente no namespace de dados.py.
# Sprint ANTI-MIGUE-08: re-export das consultas read-only ao grafo movidas
# para dados_grafo.py. Mantido para retrocompat de chamadas em paginas e
# testes (ex.: ``from src.dashboard.dados import buscar_global``).
from src.dashboard.dados_grafo import (  # noqa: E402
    buscar_global,
    carregar_documentos_grafo,
    carregar_subgrafo,
    contar_propostas_linking,
    listar_fornecedores_com_id,
)
from src.dashboard.dados_revisor import (  # noqa: E402
    CAMINHO_RAW_CLASSIFICAR,
    CAMINHO_RAW_CONFERIR,
    listar_pendencias_revisao,
)

__all__ = [
    "CAMINHO_RAW_CLASSIFICAR",
    "CAMINHO_RAW_CONFERIR",
    "buscar_global",
    "carregar_documentos_grafo",
    "carregar_subgrafo",
    "contar_propostas_linking",
    "listar_fornecedores_com_id",
    "listar_pendencias_revisao",
]


# "Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca
