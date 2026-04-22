"""Página de extrato detalhado do dashboard financeiro."""

from functools import lru_cache
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.dashboard.componentes.modal_transacao import mostrar_modal
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import CORES, FONTE_CORPO

_CAMINHO_CATEGORIAS_TRACKING: Path = (
    Path(__file__).resolve().parents[3] / "mappings" / "categorias_tracking.yaml"
)


@lru_cache(maxsize=1)
def _carregar_categorias_obrigatorias() -> frozenset[str]:
    """Lê `mappings/categorias_tracking.yaml` uma vez e cacheia em memória."""
    if not _CAMINHO_CATEGORIAS_TRACKING.exists():
        return frozenset()
    try:
        dados = yaml.safe_load(_CAMINHO_CATEGORIAS_TRACKING.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return frozenset()
    lista = (dados or {}).get("obrigatoria_tracking", []) or []
    return frozenset(str(c) for c in lista)


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de extrato."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para o extrato.")
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df = filtrar_por_periodo(extrato, gran, periodo)
    df = filtrar_por_pessoa(df, pessoa)
    df = filtrar_por_forma_pagamento(df, filtro_forma_ativo())

    if df.empty:
        st.info("Sem transações para o período selecionado.")
        return

    busca = st.text_input(
        "Buscar por local",
        key="busca_local",
        placeholder="Digite para filtrar...",
    )

    st.markdown(
        "<style>.stSelectbox { margin-bottom: 12px; }</style>",
        unsafe_allow_html=True,
    )

    with st.expander("Filtros avançados", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
            categoria_sel = st.selectbox("Categoria", categorias, key="filtro_categoria")

            bancos = ["Todos"] + sorted(df["banco_origem"].dropna().unique().tolist())
            banco_sel = st.selectbox("Banco", bancos, key="filtro_banco")

        with col2:
            classificacoes = ["Todas"] + sorted(df["classificacao"].dropna().unique().tolist())
            classificacao_sel = st.selectbox(
                "Classificação",
                classificacoes,
                key="filtro_classificacao",
            )

            tipos = ["Todos"] + sorted(df["tipo"].dropna().unique().tolist())
            tipo_sel = st.selectbox("Tipo", tipos, key="filtro_tipo")

    resultado = df.copy()

    if busca.strip():
        mascara = resultado["local"].fillna("").str.contains(busca.strip(), case=False, na=False)
        resultado = resultado[mascara]

    if categoria_sel != "Todas":
        resultado = resultado[resultado["categoria"] == categoria_sel]

    if classificacao_sel != "Todas":
        resultado = resultado[resultado["classificacao"] == classificacao_sel]

    if banco_sel != "Todos":
        resultado = resultado[resultado["banco_origem"] == banco_sel]

    if tipo_sel != "Todos":
        resultado = resultado[resultado["tipo"] == tipo_sel]

    _exibir_tabela(resultado)
    _inspecionar_transacao(resultado)


def _exibir_tabela(df: pd.DataFrame) -> None:
    """Exibe tabela interativa de transações e botão de export."""
    st.markdown(
        f'<p style="color: {CORES["destaque"]};'
        f" font-size: {FONTE_CORPO}px;"
        f' font-weight: bold; margin: 10px 0;">'
        f"{len(df)} transações encontradas</p>",
        unsafe_allow_html=True,
    )

    colunas_exibicao: list[str] = [
        "data",
        "valor",
        "local",
        "categoria",
        "classificacao",
        "banco_origem",
        "tipo",
        "quem",
    ]

    colunas_presentes = [c for c in colunas_exibicao if c in df.columns]
    df_exibir = df[colunas_presentes].copy()

    # Sprint 74 (ADR-20): coluna de tracking documental. Marca com "•" quando
    # a categoria é obrigatória e ainda não há comprovante conhecido no grafo.
    # Hoje usamos heurística simples por categoria; Sprint futura cruzará com
    # arestas `documento_de` para marcar como "OK" quando já há vínculo.
    obrigatorias = _carregar_categorias_obrigatorias()
    if obrigatorias and "categoria" in df_exibir.columns:
        df_exibir["tracking"] = df_exibir["categoria"].apply(
            lambda c: "!" if c in obrigatorias else ""
        )

    nomes_colunas: dict[str, str] = {
        "data": "Data",
        "valor": "Valor",
        "local": "Local",
        "categoria": "Categoria",
        "classificacao": "Classificação",
        "banco_origem": "Banco",
        "tipo": "Tipo",
        "quem": "Quem",
        "tracking": "Doc?",
    }

    if "data" in df_exibir.columns:
        datas = pd.to_datetime(df_exibir["data"], errors="coerce")
        df_exibir["data"] = datas.dt.strftime("%Y-%m-%d")

    df_exibir = df_exibir.rename(columns=nomes_colunas)

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )

    csv = "\ufeff" + df_exibir.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Exportar CSV",
        data=csv,
        file_name="extrato.csv",
        mime="text/csv",
    )


def _inspecionar_transacao(df: pd.DataFrame) -> None:
    """Sprint 74 — Modal detalhado de uma transação com preview de docs vinculados.

    Streamlit não suporta clique nativo em linha do `st.dataframe`; usamos um
    selectbox + botão como compromisso. O modal exibe metadados, estado
    documental e preview inline dos documentos (Sprint 74, ADR-20).
    """
    if df.empty:
        return

    st.markdown("---")
    st.markdown(
        f'<p style="color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px; '
        f'font-weight: bold; margin: 10px 0;">Inspecionar transação</p>',
        unsafe_allow_html=True,
    )

    rotulos: list[str] = []
    for _, row in df.head(500).iterrows():
        data_v = row.get("data")
        data_str = (
            pd.to_datetime(data_v).strftime("%Y-%m-%d")
            if data_v is not None and not pd.isna(data_v)
            else "-"
        )
        valor = float(row.get("valor") or 0.0)
        local = str(row.get("local", ""))[:40]
        rotulos.append(f"{data_str} — R$ {valor:.2f} — {local}")

    col_sel, col_btn = st.columns([4, 1])
    with col_sel:
        idx = st.selectbox(
            "Escolha uma transação (até 500 primeiras)",
            options=list(range(len(rotulos))),
            format_func=lambda i: rotulos[i] if i < len(rotulos) else "",
            key="extrato_tx_inspecionar",
        )
    with col_btn:
        st.write("")  # padding vertical
        clicou = st.button("Ver detalhes", key="extrato_btn_modal", type="primary")

    if clicou and idx is not None and idx < len(df):
        row = df.iloc[idx]
        tx = {
            "data": pd.to_datetime(row.get("data"))
            if row.get("data") is not None
            else None,
            "valor": float(row.get("valor") or 0.0),
            "categoria": row.get("categoria", "-"),
            "banco_origem": row.get("banco_origem", "-"),
            "local": row.get("local", "-"),
            "quem": row.get("quem", "-"),
        }
        mostrar_modal(tx, [])


# "O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon
