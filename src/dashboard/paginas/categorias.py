"""Página de análise por categorias do dashboard financeiro."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import filtrar_por_mes, filtrar_por_pessoa, formatar_moeda

CORES: dict[str, str] = {
    "positivo": "#4ECDC4",
    "negativo": "#FF6B6B",
    "neutro": "#45B7D1",
    "obrigatorio": "#4ECDC4",
    "questionavel": "#FFA726",
    "superfluo": "#FF6B6B",
    "na": "#78909C",
    "fundo": "#0E1117",
    "card_fundo": "#1E2130",
}

MAPA_CLASSIFICACAO_COR: dict[str, str] = {
    "Obrigatório": CORES["obrigatorio"],
    "Questionável": CORES["questionavel"],
    "Supérfluo": CORES["superfluo"],
}

ESCALA_CLASSIFICACAO: list[list[float | str]] = [
    [0.0, CORES["obrigatorio"]],
    [0.5, CORES["questionavel"]],
    [1.0, CORES["superfluo"]],
]

MAPA_CLASSIFICACAO_VALOR: dict[str, int] = {
    "Obrigatório": 0,
    "Questionável": 1,
    "Supérfluo": 2,
}


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de categorias."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para análise de categorias.")
        return

    extrato = dados["extrato"]
    df = filtrar_por_mes(extrato, mes_selecionado)
    df = filtrar_por_pessoa(df, pessoa)
    df = df[df["tipo"] == "Despesa"].copy()

    if df.empty:
        st.info("Sem despesas para o período selecionado.")
        return

    _treemap_categorias(df)

    col_esq, col_dir = st.columns(2)

    with col_esq:
        _ranking_categorias(df)

    with col_dir:
        _evolucao_categorias(extrato, mes_selecionado, pessoa)


def _treemap_categorias(df: pd.DataFrame) -> None:
    """Treemap de gastos por categoria com cor por classificação."""
    agrupado = (
        df.groupby(["categoria", "classificacao"])["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )

    if agrupado.empty:
        return

    agrupado["cor_num"] = agrupado["classificacao"].map(MAPA_CLASSIFICACAO_VALOR).fillna(1)

    agrupado["texto"] = agrupado.apply(
        lambda r: f"{r['categoria']}<br>{formatar_moeda(r['valor'])}", axis=1
    )

    fig = px.treemap(
        agrupado,
        path=["classificacao", "categoria"],
        values="valor",
        color="classificacao",
        color_discrete_map=MAPA_CLASSIFICACAO_COR,
    )

    fig.update_layout(
        title="Gastos por Categoria",
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        margin=dict(l=10, r=10, t=60, b=10),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate="%{label}<br>R$ %{value:,.2f}",
    )

    st.plotly_chart(fig, use_container_width=True)


def _ranking_categorias(df: pd.DataFrame) -> None:
    """Top 10 categorias em tabela ordenada por valor."""
    st.subheader("Top 10 Categorias")

    ranking = (
        df.groupby(["categoria", "classificacao"])["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    ranking.index = ranking.index + 1
    ranking["valor_fmt"] = ranking["valor"].apply(formatar_moeda)

    tabela = ranking[["categoria", "classificacao", "valor_fmt"]].copy()
    tabela.columns = ["Categoria", "Classificação", "Valor"]

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=False,
        column_config={
            "Categoria": st.column_config.TextColumn("Categoria", width="medium"),
            "Classificação": st.column_config.TextColumn("Classificação", width="medium"),
            "Valor": st.column_config.TextColumn("Valor", width="small"),
        },
    )


def _evolucao_categorias(
    extrato: pd.DataFrame,
    mes_atual: str,
    pessoa: str,
) -> None:
    """Gráfico de linhas: evolução temporal das top 5 categorias."""
    st.subheader("Evolução - Top 5 Categorias")

    df_filtrado = filtrar_por_pessoa(extrato, pessoa)
    df_despesas = df_filtrado[df_filtrado["tipo"] == "Despesa"].copy()

    meses_ordenados = sorted(df_despesas["mes_ref"].dropna().unique().tolist())

    if mes_atual in meses_ordenados:
        idx = meses_ordenados.index(mes_atual)
        inicio = max(0, idx - 5)
        meses_periodo = meses_ordenados[inicio : idx + 1]
    else:
        meses_periodo = meses_ordenados[-6:]

    df_periodo = df_despesas[df_despesas["mes_ref"].isin(meses_periodo)]

    top5 = (
        df_periodo.groupby("categoria")["valor"]
        .sum()
        .nlargest(5)
        .index.tolist()
    )

    df_top5 = df_periodo[df_periodo["categoria"].isin(top5)]
    evolucao = df_top5.groupby(["mes_ref", "categoria"])["valor"].sum().reset_index()

    if evolucao.empty:
        st.info("Sem dados suficientes para o gráfico de evolução.")
        return

    cores_linha: list[str] = [
        CORES["positivo"],
        CORES["negativo"],
        CORES["neutro"],
        CORES["questionavel"],
        CORES["na"],
    ]

    fig = go.Figure()
    for i, cat in enumerate(top5):
        dados_cat = evolucao[evolucao["categoria"] == cat].sort_values("mes_ref")
        fig.add_trace(go.Scatter(
            x=dados_cat["mes_ref"],
            y=dados_cat["valor"],
            name=cat,
            mode="lines+markers",
            line=dict(color=cores_linha[i % len(cores_linha)], width=2),
            marker=dict(size=6),
        ))

    fig.update_layout(
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=40, b=40),
        yaxis_title="Valor (R$)",
        xaxis_title="Mês",
    )

    st.plotly_chart(fig, use_container_width=True)


# "Cuide dos centavos e os reais cuidarão de si mesmos." -- Benjamin Franklin
