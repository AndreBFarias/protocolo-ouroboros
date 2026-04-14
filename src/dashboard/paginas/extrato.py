"""Página de extrato detalhado do dashboard financeiro."""

import pandas as pd
import streamlit as st

from src.dashboard.dados import filtrar_por_mes, filtrar_por_pessoa


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de extrato."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para o extrato.")
        return

    extrato = dados["extrato"]
    df = filtrar_por_mes(extrato, mes_selecionado)
    df = filtrar_por_pessoa(df, pessoa)

    if df.empty:
        st.info("Sem transações para o período selecionado.")
        return

    df_filtrado = _aplicar_filtros(df)

    _exibir_tabela(df_filtrado)


def _aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica filtros interativos ao extrato."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        categorias = ["Todas"] + sorted(df["categoria"].dropna().unique().tolist())
        categoria_sel = st.selectbox("Categoria", categorias, key="filtro_categoria")

    with col2:
        classificacoes = ["Todas"] + sorted(df["classificacao"].dropna().unique().tolist())
        classificacao_sel = st.selectbox(
            "Classificação", classificacoes, key="filtro_classificacao",
        )

    with col3:
        bancos = ["Todos"] + sorted(df["banco_origem"].dropna().unique().tolist())
        banco_sel = st.selectbox("Banco", bancos, key="filtro_banco")

    with col4:
        tipos = ["Todos"] + sorted(df["tipo"].dropna().unique().tolist())
        tipo_sel = st.selectbox("Tipo", tipos, key="filtro_tipo")

    busca = st.text_input(
        "Buscar por local", key="busca_local", placeholder="Digite para filtrar...",
    )

    resultado = df.copy()

    if categoria_sel != "Todas":
        resultado = resultado[resultado["categoria"] == categoria_sel]

    if classificacao_sel != "Todas":
        resultado = resultado[resultado["classificacao"] == classificacao_sel]

    if banco_sel != "Todos":
        resultado = resultado[resultado["banco_origem"] == banco_sel]

    if tipo_sel != "Todos":
        resultado = resultado[resultado["tipo"] == tipo_sel]

    if busca.strip():
        mascara = resultado["local"].fillna("").str.contains(busca.strip(), case=False, na=False)
        resultado = resultado[mascara]

    return resultado


def _exibir_tabela(df: pd.DataFrame) -> None:
    """Exibe tabela interativa de transações e botão de export."""
    st.markdown(f"**{len(df)} transações encontradas**")

    colunas_exibicao: list[str] = [
        "data", "valor", "local", "categoria", "classificacao",
        "banco_origem", "tipo", "quem",
    ]

    colunas_presentes = [c for c in colunas_exibicao if c in df.columns]
    df_exibir = df[colunas_presentes].copy()

    if "data" in df_exibir.columns:
        df_exibir["data"] = pd.to_datetime(df_exibir["data"]).dt.strftime("%d/%m/%Y")

    nomes_colunas: dict[str, str] = {
        "data": "Data",
        "valor": "Valor",
        "local": "Local",
        "categoria": "Categoria",
        "classificacao": "Classificação",
        "banco_origem": "Banco",
        "tipo": "Tipo",
        "quem": "Quem",
    }

    df_exibir = df_exibir.rename(columns=nomes_colunas)

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )

    csv = df_exibir.to_csv(index=False, sep=";", decimal=",")
    st.download_button(
        label="Exportar CSV",
        data=csv,
        file_name="extrato.csv",
        mime="text/csv",
    )


# "O dinheiro é um bom servo, mas um mau mestre." -- Francis Bacon
