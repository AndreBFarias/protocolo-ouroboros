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
# Sprint D2: diretórios brutos de pendência humana e DB de revisão.
CAMINHO_RAW_CLASSIFICAR: Path = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "_classificar"
)
CAMINHO_RAW_CONFERIR: Path = (
    Path(__file__).resolve().parents[2] / "data" / "raw" / "_conferir"
)
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
    """Filtra DataFrame por pessoa (André/Vitória/Todos)."""
    if pessoa == "Todos" or "quem" not in df.columns:
        return df
    return df[df["quem"] == pessoa].copy()


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


def filtrar_por_forma_pagamento(
    df: pd.DataFrame, forma: str | None
) -> pd.DataFrame:
    """Filtra DataFrame por `forma_pagamento` (Sprint 72).

    - `forma=None` ou ``"Todas"``: devolve o df sem filtrar.
    - Aplica canonicalização: "TED" e "DOC" são agrupados sob "Transferência",
      etc. (ver `_FORMAS_CANONICAS`).
    - Se a coluna `forma_pagamento` não existe, devolve o df intacto.
    """
    if not forma or forma == "Todas" or "forma_pagamento" not in df.columns:
        return df
    coluna_canonica = df["forma_pagamento"].fillna("").map(
        lambda v: _FORMAS_CANONICAS.get(v, v)
    )
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


@st.cache_data(ttl=60)
def carregar_subgrafo(node_id: int, radius: int = 1) -> dict:
    """Retorna subgrafo a `radius` hops do node alvo (read-only, BFS).

    Graceful degradation (ADR-10): grafo ausente devolve estrutura vazia.
    Retorno:
        {
            "nodes": [{"id", "tipo", "nome_canonico", "metadata"}...],
            "edges": [{"src_id", "dst_id", "tipo"}...],
            "center_id": node_id,
        }
    """
    vazio: dict = {"nodes": [], "edges": [], "center_id": node_id}
    if not CAMINHO_GRAFO.exists():
        logger.warning("grafo não encontrado em %s", CAMINHO_GRAFO)
        return vazio
    if radius < 0:
        return vazio

    import sqlite3

    conn = sqlite3.connect(f"file:{CAMINHO_GRAFO}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        visitados: set[int] = {node_id}
        fronteira: set[int] = {node_id}
        arestas_coletadas: list[dict] = []

        for _ in range(max(1, radius)):
            if not fronteira:
                break
            placeholders = ",".join("?" * len(fronteira))
            lista_ids = list(fronteira)
            sql_out = (
                f"SELECT src_id, dst_id, tipo FROM edge "
                f"WHERE src_id IN ({placeholders})"
            )
            sql_in = (
                f"SELECT src_id, dst_id, tipo FROM edge "
                f"WHERE dst_id IN ({placeholders})"
            )
            nova_fronteira: set[int] = set()
            for row in conn.execute(sql_out, lista_ids):
                arestas_coletadas.append(
                    {
                        "src_id": int(row["src_id"]),
                        "dst_id": int(row["dst_id"]),
                        "tipo": row["tipo"],
                    }
                )
                if int(row["dst_id"]) not in visitados:
                    nova_fronteira.add(int(row["dst_id"]))
            for row in conn.execute(sql_in, lista_ids):
                arestas_coletadas.append(
                    {
                        "src_id": int(row["src_id"]),
                        "dst_id": int(row["dst_id"]),
                        "tipo": row["tipo"],
                    }
                )
                if int(row["src_id"]) not in visitados:
                    nova_fronteira.add(int(row["src_id"]))
            visitados.update(nova_fronteira)
            fronteira = nova_fronteira

        # dedup de arestas (src,dst,tipo)
        vistos: set[tuple[int, int, str]] = set()
        arestas_unicas: list[dict] = []
        for ar in arestas_coletadas:
            chave = (ar["src_id"], ar["dst_id"], ar["tipo"])
            if chave in vistos:
                continue
            vistos.add(chave)
            arestas_unicas.append(ar)

        # carrega nodes visitados
        if not visitados:
            return vazio
        placeholders_n = ",".join("?" * len(visitados))
        nodes: list[dict] = []
        sql_nodes = (
            "SELECT id, tipo, nome_canonico, aliases, metadata "
            f"FROM node WHERE id IN ({placeholders_n})"
        )
        for row in conn.execute(sql_nodes, list(visitados)):
            try:
                meta = json.loads(row["metadata"] or "{}")
            except (json.JSONDecodeError, TypeError):
                meta = {}
            try:
                aliases_list = json.loads(row["aliases"] or "[]")
                if not isinstance(aliases_list, list):
                    aliases_list = []
            except (json.JSONDecodeError, TypeError):
                aliases_list = []
            nodes.append(
                {
                    "id": int(row["id"]),
                    "tipo": row["tipo"],
                    "nome_canonico": row["nome_canonico"],
                    "aliases": aliases_list,
                    "metadata": meta,
                }
            )
    finally:
        conn.close()

    return {"nodes": nodes, "edges": arestas_unicas, "center_id": node_id}


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
            receita_df.groupby("local")["valor"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
        )
        receita_list = [
            {"rotulo": str(rotulo), "valor": float(valor)}
            for rotulo, valor in agrup.items()
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
            {"rotulo": str(rotulo), "valor": float(valor)}
            for rotulo, valor in agrup.items()
        ]

    # --- fornecedor: top 10 locais de despesa ---
    fornecedor_list: list[dict] = []
    if not despesa_df.empty and "local" in despesa_df.columns:
        agrup = (
            despesa_df.groupby("local")["valor"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .head(10)
        )
        fornecedor_list = [
            {"rotulo": str(rotulo), "valor": float(valor)}
            for rotulo, valor in agrup.items()
        ]

    return {
        "receita": receita_list,
        "despesa": despesa_list,
        "fornecedor": fornecedor_list,
        "mes_ref": mes_ref,
    }


def listar_fornecedores_com_id() -> list[dict]:
    """Lista fornecedores do grafo com id + nome para seleção no selectbox.

    Ordenado alfabeticamente. Read-only. Devolve lista vazia se grafo ausente.
    """
    if not CAMINHO_GRAFO.exists():
        return []

    import sqlite3

    conn = sqlite3.connect(f"file:{CAMINHO_GRAFO}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        resultados: list[dict] = []
        for row in conn.execute(
            "SELECT id, nome_canonico, aliases, metadata FROM node "
            "WHERE tipo = 'fornecedor' ORDER BY nome_canonico LIMIT 500"
        ):
            try:
                aliases_list = json.loads(row["aliases"] or "[]")
                if not isinstance(aliases_list, list):
                    aliases_list = []
            except (json.JSONDecodeError, TypeError):
                aliases_list = []
            try:
                meta = json.loads(row["metadata"] or "{}")
                if not isinstance(meta, dict):
                    meta = {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            resultados.append(
                {
                    "id": int(row["id"]),
                    "nome_canonico": row["nome_canonico"],
                    "aliases": aliases_list,
                    "metadata": meta,
                }
            )
    finally:
        conn.close()
    return resultados


def listar_pendencias_revisao(
    caminho_grafo: Path | None = None,
    caminho_classificar: Path | None = None,
    caminho_conferir: Path | None = None,
    limite_confidence: float = 0.8,
) -> list[dict]:
    """Lista pendências para o Revisor Visual (Sprint D2).

    Critérios de inclusão (em ordem de prioridade):
      1. Arquivos em ``data/raw/_classificar/`` (não-classificados pelo
         pipeline -- prioridade máxima).
      2. Arquivos/diretórios em ``data/raw/_conferir/`` (fallback do
         supervisor com recall < limiar -- prioridade alta).
      3. Nodes ``documento`` do grafo com ``metadata.confidence``
         abaixo de ``limite_confidence``.
      4. Nodes ``documento`` sem aresta ``documento_de`` saindo
         (achado P0 da auditoria 2026-04-26: 0% docs vinculados).

    Parâmetros opcionais permitem injetar paths em testes (sem precisar
    monkeypatchear constantes globais).

    Cada pendência é um dict com:
      - ``item_id``: identificador estável (caminho relativo ou ``node_<id>``).
      - ``tipo``: ``raw_classificar`` | ``raw_conferir`` |
        ``grafo_low_confidence`` | ``grafo_sem_link``.
      - ``caminho``: Path absoluto do arquivo original (str) quando aplicável.
      - ``metadata``: dict com campos extras (tipo_documento, razao_social, etc.).
      - ``prioridade``: int 1 (mais alto) a 4.

    Read-only no grafo. Não toca em ``data/raw/``.
    """
    grafo = caminho_grafo if caminho_grafo is not None else CAMINHO_GRAFO
    raw_classificar = (
        caminho_classificar if caminho_classificar is not None else CAMINHO_RAW_CLASSIFICAR
    )
    raw_conferir = caminho_conferir if caminho_conferir is not None else CAMINHO_RAW_CONFERIR

    pendencias: list[dict] = []

    if raw_classificar.exists() and raw_classificar.is_dir():
        for arquivo in sorted(raw_classificar.iterdir()):
            if arquivo.is_file():
                pendencias.append(
                    {
                        "item_id": str(arquivo.relative_to(raw_classificar.parents[1])),
                        "tipo": "raw_classificar",
                        "caminho": str(arquivo),
                        "metadata": {"nome": arquivo.name},
                        "prioridade": 1,
                    }
                )

    if raw_conferir.exists() and raw_conferir.is_dir():
        for entrada in sorted(raw_conferir.iterdir()):
            pendencias.append(
                {
                    "item_id": str(entrada.relative_to(raw_conferir.parents[1])),
                    "tipo": "raw_conferir",
                    "caminho": str(entrada),
                    "metadata": {"nome": entrada.name, "eh_diretorio": entrada.is_dir()},
                    "prioridade": 2,
                }
            )

    if grafo.exists():
        import sqlite3

        conn = sqlite3.connect(f"file:{grafo}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            ids_vinculados: set[int] = set()
            for row in conn.execute(
                "SELECT DISTINCT src_id FROM edge WHERE tipo = 'documento_de'"
            ):
                ids_vinculados.add(int(row["src_id"]))

            for row in conn.execute(
                "SELECT id, nome_canonico, metadata FROM node WHERE tipo = 'documento'"
            ):
                node_id = int(row["id"])
                meta_raw = row["metadata"] or "{}"
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                confidence = meta.get("confidence")
                arquivo_origem = meta.get("arquivo_origem", "")

                if isinstance(confidence, (int, float)) and confidence < limite_confidence:
                    pendencias.append(
                        {
                            "item_id": f"node_{node_id}",
                            "tipo": "grafo_low_confidence",
                            "caminho": arquivo_origem,
                            "metadata": {
                                "nome_canonico": row["nome_canonico"],
                                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                                "confidence": float(confidence),
                                "razao_social": meta.get("razao_social", ""),
                                "data_emissao": meta.get("data_emissao", ""),
                                "total": float(meta.get("total", 0.0) or 0.0),
                            },
                            "prioridade": 3,
                        }
                    )
                    continue

                if node_id not in ids_vinculados:
                    pendencias.append(
                        {
                            "item_id": f"node_{node_id}",
                            "tipo": "grafo_sem_link",
                            "caminho": arquivo_origem,
                            "metadata": {
                                "nome_canonico": row["nome_canonico"],
                                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                                "razao_social": meta.get("razao_social", ""),
                                "data_emissao": meta.get("data_emissao", ""),
                                "total": float(meta.get("total", 0.0) or 0.0),
                            },
                            "prioridade": 4,
                        }
                    )
        finally:
            conn.close()

    pendencias.sort(key=lambda p: (p["prioridade"], p["item_id"]))
    return pendencias


# "Não é o homem que tem pouco, mas o que deseja mais, que é pobre." -- Sêneca
