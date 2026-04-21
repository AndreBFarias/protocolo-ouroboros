"""Módulo de carregamento e cache de dados do Protocolo Ouroboros."""

import json
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


@st.cache_data(ttl=300)
def carregar_documentos_grafo() -> pd.DataFrame:
    """Carrega documentos do grafo SQLite como DataFrame read-only.

    Retorna DataFrame com colunas: doc_id, tipo_documento, cnpj_emitente,
    razao_social, data_emissao, total, status_linking, arquivo_origem.

    Status_linking é derivado assim:
      - "Vinculado": existe aresta documento_de saindo do documento
      - "Conflito": existe proposta em docs/propostas/linking/ cujo nome casa
                    com a chave canônica do documento (substring)
      - "Sem transação": caso contrário

    Se o grafo não existe, devolve DataFrame vazio (ADR-10).
    """
    if not CAMINHO_GRAFO.exists():
        logger.warning("grafo não encontrado em %s", CAMINHO_GRAFO)
        return pd.DataFrame(
            columns=[
                "doc_id",
                "tipo_documento",
                "cnpj_emitente",
                "razao_social",
                "data_emissao",
                "total",
                "status_linking",
                "arquivo_origem",
            ]
        )

    import sqlite3

    conn = sqlite3.connect(f"file:{CAMINHO_GRAFO}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        docs: list[dict] = []
        for row in conn.execute(
            "SELECT id, nome_canonico, metadata FROM node WHERE tipo = 'documento'"
        ):
            meta_raw = row["metadata"] or "{}"
            try:
                meta = json.loads(meta_raw)
            except (json.JSONDecodeError, TypeError):
                meta = {}
            docs.append(
                {
                    "doc_id": int(row["id"]),
                    "nome_canonico": row["nome_canonico"],
                    "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                    "cnpj_emitente": meta.get("cnpj_emitente", ""),
                    "razao_social": meta.get("razao_social", ""),
                    "data_emissao": meta.get("data_emissao", ""),
                    "total": float(meta.get("total", 0.0) or 0.0),
                    "arquivo_origem": meta.get("arquivo_origem", ""),
                }
            )

        ids_vinculados: set[int] = set()
        for row in conn.execute(
            "SELECT DISTINCT src_id FROM edge WHERE tipo = 'documento_de'"
        ):
            ids_vinculados.add(int(row["src_id"]))
    finally:
        conn.close()

    chaves_conflito: set[str] = set()
    if CAMINHO_PROPOSTAS_LINKING.exists():
        for arquivo in CAMINHO_PROPOSTAS_LINKING.glob("*.md"):
            chaves_conflito.add(arquivo.stem)

    for doc in docs:
        if doc["doc_id"] in ids_vinculados:
            doc["status_linking"] = "Vinculado"
        elif any(doc["nome_canonico"][:20] in chave for chave in chaves_conflito):
            doc["status_linking"] = "Conflito"
        else:
            doc["status_linking"] = "Sem transação"

    df = pd.DataFrame(docs)
    if df.empty:
        df = pd.DataFrame(
            columns=[
                "doc_id",
                "tipo_documento",
                "cnpj_emitente",
                "razao_social",
                "data_emissao",
                "total",
                "status_linking",
                "arquivo_origem",
            ]
        )
    return df


def contar_propostas_linking() -> int:
    """Conta arquivos .md em docs/propostas/linking/ (não conta subpastas)."""
    if not CAMINHO_PROPOSTAS_LINKING.exists():
        return 0
    return sum(1 for _ in CAMINHO_PROPOSTAS_LINKING.glob("*.md"))


@st.cache_data(ttl=60)
def buscar_global(termo: str) -> dict[str, list[dict]]:
    """Busca case-insensitive no grafo SQLite (read-only).

    Executa LIKE contra `nome_canonico`, `aliases` (JSON textual) e
    `metadata` (JSON textual) para os quatro tipos principais:
    fornecedor, documento, transacao e item.                       # noqa: accent

    Returns:
        Dict com 4 chaves: ``fornecedores``, ``documentos``,
        ``transacoes`` e ``itens``. Cada valor é lista de dicts    # noqa: accent
        enxutos (id + campos principais) pronta para renderizar.
        Se o grafo não existe ou termo é vazio, todas as listas vêm
        vazias.
    """
    vazio: dict[str, list[dict]] = {
        "fornecedores": [],
        "documentos": [],
        "transacoes": [],
        "itens": [],
    }

    if not termo or not termo.strip():
        return vazio

    if not CAMINHO_GRAFO.exists():
        logger.warning("grafo não encontrado em %s", CAMINHO_GRAFO)
        return vazio

    import sqlite3

    termo_norm = termo.strip()
    padrao = f"%{termo_norm.lower()}%"

    conn = sqlite3.connect(f"file:{CAMINHO_GRAFO}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        fornecedores = _buscar_fornecedores(conn, padrao)
        documentos = _buscar_documentos(conn, padrao)
        transacoes = _buscar_transacoes(conn, padrao)
        itens = _buscar_itens(conn, padrao)
    finally:
        conn.close()

    return {
        "fornecedores": fornecedores,
        "documentos": documentos,
        "transacoes": transacoes,
        "itens": itens,
    }


def _buscar_fornecedores(conn, padrao: str) -> list[dict]:
    """Retorna fornecedores cujo nome/alias/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, aliases, metadata "
        "FROM node "
        "WHERE tipo = 'fornecedor' "
        "  AND (LOWER(nome_canonico) LIKE ? "
        "    OR LOWER(aliases) LIKE ? "
        "    OR LOWER(metadata) LIKE ?) "
        "LIMIT 50"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao, padrao)):
        try:
            aliases = json.loads(row["aliases"] or "[]")
        except (json.JSONDecodeError, TypeError):
            aliases = []
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        fornecedor_id = int(row["id"])
        ndocs, total = _agregados_fornecedor(conn, fornecedor_id)
        resultados.append(
            {
                "id": fornecedor_id,
                "nome_canonico": row["nome_canonico"],
                "aliases": aliases,
                "cnpj": meta.get("cnpj", meta.get("cnpj_emitente", "")),
                "categoria": meta.get("categoria", ""),
                "total_documentos": ndocs,
                "total_gasto": total,
            }
        )
    return resultados


def _agregados_fornecedor(conn, fornecedor_id: int) -> tuple[int, float]:
    """Conta documentos e soma transações ligadas ao fornecedor."""
    ndocs = 0
    total = 0.0
    for row in conn.execute(
        "SELECT src_id FROM edge "
        "WHERE dst_id = ? AND tipo = 'fornecido_por'",
        (fornecedor_id,),
    ):
        doc_row = conn.execute(
            "SELECT tipo FROM node WHERE id = ?", (row["src_id"],)
        ).fetchone()
        if doc_row and doc_row["tipo"] == "documento":
            ndocs += 1

    for row in conn.execute(
        "SELECT src_id FROM edge "
        "WHERE dst_id = ? AND tipo = 'fornecido_por'",
        (fornecedor_id,),
    ):
        tx_row = conn.execute(
            "SELECT tipo, metadata FROM node WHERE id = ?", (row["src_id"],)
        ).fetchone()
        if tx_row and tx_row["tipo"] == "transacao":
            try:
                meta_tx = json.loads(tx_row["metadata"] or "{}")
                valor = float(meta_tx.get("valor", 0.0) or 0.0)
                total += abs(valor)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return ndocs, total


def _buscar_documentos(conn, padrao: str) -> list[dict]:
    """Retorna documentos cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'documento' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 100"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        resultados.append(
            {
                "id": int(row["id"]),
                "nome_canonico": row["nome_canonico"],
                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                "data": meta.get("data_emissao", ""),
                "razao_social": meta.get("razao_social", ""),
                "total": float(meta.get("total", 0.0) or 0.0),
            }
        )
    return resultados


def _buscar_transacoes(conn, padrao: str) -> list[dict]:
    """Retorna transações cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'transacao' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 200"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        data_raw = meta.get("data", "")
        data_str = str(data_raw)[:10] if data_raw else ""
        resultados.append(
            {
                "id": int(row["id"]),
                "data": data_str,
                "local": meta.get("local", ""),
                "valor": float(meta.get("valor", 0.0) or 0.0),
                "banco": meta.get("banco", ""),
                "tipo_transacao": meta.get("tipo", ""),
            }
        )
    resultados.sort(key=lambda r: r["data"], reverse=True)
    return resultados


def _buscar_itens(conn, padrao: str) -> list[dict]:
    """Retorna itens cujo nome/metadata casa com padrão."""
    sql = (
        "SELECT id, nome_canonico, metadata "
        "FROM node "
        "WHERE tipo = 'item' "
        "  AND (LOWER(nome_canonico) LIKE ? OR LOWER(metadata) LIKE ?) "
        "LIMIT 100"
    )
    resultados: list[dict] = []
    for row in conn.execute(sql, (padrao, padrao)):
        try:
            meta = json.loads(row["metadata"] or "{}")
        except (json.JSONDecodeError, TypeError):
            meta = {}
        resultados.append(
            {
                "id": int(row["id"]),
                "descricao": meta.get("descricao", row["nome_canonico"]),
                "data": meta.get("data_compra", ""),
                "valor": float(meta.get("valor_total", 0.0) or 0.0),
                "qtde": float(meta.get("qtde", 0.0) or 0.0),
                "cnpj": meta.get("cnpj_varejo", meta.get("cnpj", "")),
            }
        )
    return resultados


# "Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca
