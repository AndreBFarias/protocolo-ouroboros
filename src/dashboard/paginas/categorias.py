"""Página de análise por categorias do dashboard financeiro."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import (
    filtrar_por_mes,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    MAPA_CLASSIFICACAO,
)

MAPA_CLASSIFICACAO_COR: dict[str, str] = MAPA_CLASSIFICACAO

MAPA_CLASSIFICACAO_VALOR: dict[str, int] = {
    "Obrigatório": 0,
    "Questionável": 1,
    "Supérfluo": 2,
}


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de categorias."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para análise de categorias.")
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df_filtrado = filtrar_por_pessoa(extrato, pessoa)
    df = filtrar_por_periodo(df_filtrado, gran, periodo)
    df = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df.empty:
        st.info("Sem despesas para o período selecionado.")
        return

    _treemap_categorias(df)

    col_esq, col_dir = st.columns(2)

    with col_esq:
        _ranking_com_variacao(df_filtrado, mes_selecionado)

    with col_dir:
        _evolucao_categorias(df_filtrado, mes_selecionado)


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

    fig = px.treemap(
        agrupado,
        path=["classificacao", "categoria"],
        values="valor",
        color="classificacao",
        color_discrete_map=MAPA_CLASSIFICACAO_COR,
    )

    layout = {**LAYOUT_PLOTLY, "margin": dict(l=10, r=10, t=60, b=10)}
    fig.update_layout(
        **layout,
        title=dict(text="Gastos por Categoria", font=dict(size=FONTE_SUBTITULO)),
    )

    fig.update_traces(
        textinfo="label+value",
        texttemplate="%{label}<br>R$ %{value:,.2f}",
        textfont=dict(size=FONTE_CORPO),
    )

    st.plotly_chart(fig, width="stretch")


def _ranking_com_variacao(extrato_filtrado: pd.DataFrame, mes_atual: str) -> None:
    """Top 10 categorias com variação vs mês anterior."""
    st.markdown(
        f'<p style="font-size: {FONTE_SUBTITULO}px; font-weight: bold;'
        f' color: {CORES["texto"]}; margin-bottom: 10px;">'
        f"Top 10 Categorias</p>",
        unsafe_allow_html=True,
    )

    df_desp = extrato_filtrado[extrato_filtrado["tipo"].isin(["Despesa", "Imposto"])]

    meses = sorted(df_desp["mes_ref"].dropna().unique().tolist())
    if mes_atual not in meses:
        st.info("Sem dados para o mês selecionado.")
        return

    idx = meses.index(mes_atual)
    mes_ant = meses[idx - 1] if idx > 0 else None

    atual = (
        filtrar_por_mes(df_desp, mes_atual)
        .groupby("categoria")["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
        .head(10)
    )

    if mes_ant:
        anterior = (
            filtrar_por_mes(df_desp, mes_ant)
            .groupby("categoria")["valor"]
            .sum()
            .reset_index()
            .rename(columns={"valor": "anterior"})
        )
        tabela = atual.merge(anterior, on="categoria", how="left")
        tabela["anterior"] = tabela["anterior"].fillna(0)
        tabela["variação"] = tabela["valor"] - tabela["anterior"]
        tabela["var_%"] = (
            (tabela["variação"] / tabela["anterior"] * 100)
            .replace([float("inf"), float("-inf")], 0)
            .fillna(0)
        )
    else:
        tabela = atual.copy()
        tabela["variação"] = 0.0
        tabela["var_%"] = 0.0

    linhas_html: list[str] = []
    for _, row in tabela.iterrows():
        var_val = row["variação"]
        var_pct = row["var_%"]
        cor_var = CORES["negativo"] if var_val > 0 else CORES["positivo"]
        sinal = "+" if var_val > 0 else ""
        var_texto = (
            f"{sinal}{formatar_moeda(var_val)} ({sinal}{var_pct:.0f}%)" if mes_ant else "---"
        )

        linhas_html.append(
            f'<tr style="border-bottom: 1px solid {CORES["card_fundo"]};">'
            f'<td style="padding: 8px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px;">{row["categoria"]}</td>'
            f'<td style="padding: 8px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px; text-align: right;">'
            f"{formatar_moeda(row['valor'])}</td>"
            f'<td style="padding: 8px; color: {cor_var};'
            f' font-size: {FONTE_MINIMA}px; text-align: right;">'
            f"{var_texto}</td></tr>"
        )

    header_ant = f"vs {mes_ant}" if mes_ant else "Variação"
    css_tabela = (
        "<style>"
        ".tabela-top10 tr:nth-child(even) { background: rgba(68,71,90,0.3); }"
        ".tabela-top10 tr:hover { background: rgba(68,71,90,0.5); }"
        "</style>"
    )
    html = (
        f"{css_tabela}"
        f'<table class="tabela-top10" style="width: 100%; border-collapse: collapse;">'
        f'<thead><tr style="background-color: {CORES["card_fundo"]};">'
        f'<th style="padding: 8px; text-align: left; color: {CORES["texto_sec"]};'
        f' font-size: {FONTE_MINIMA}px;">Categoria</th>'
        f'<th style="padding: 8px; text-align: right; color: {CORES["texto_sec"]};'
        f' font-size: {FONTE_MINIMA}px;">Valor</th>'
        f'<th style="padding: 8px; text-align: right; color: {CORES["texto_sec"]};'
        f' font-size: {FONTE_MINIMA}px;">{header_ant}</th>'
        f"</tr></thead><tbody>{''.join(linhas_html)}</tbody></table>"
    )

    st.markdown(html, unsafe_allow_html=True)


def _evolucao_categorias(
    extrato_filtrado: pd.DataFrame,
    mes_atual: str,
) -> None:
    """Gráfico de linhas: evolução temporal das top 5 categorias do mês selecionado."""
    st.markdown(
        f'<p style="font-size: {FONTE_SUBTITULO}px; font-weight: bold;'
        f' color: {CORES["texto"]}; margin-bottom: 10px;">'
        f"Evolução - Top 5 do Mês</p>",
        unsafe_allow_html=True,
    )

    df_despesas = extrato_filtrado[extrato_filtrado["tipo"].isin(["Despesa", "Imposto"])].copy()

    meses_ordenados = sorted(df_despesas["mes_ref"].dropna().unique().tolist())

    if mes_atual in meses_ordenados:
        idx = meses_ordenados.index(mes_atual)
        inicio = max(0, idx - 5)
        meses_periodo = meses_ordenados[inicio : idx + 1]
    else:
        meses_periodo = meses_ordenados[-6:]

    top5_do_mes = (
        filtrar_por_mes(df_despesas, mes_atual)
        .groupby("categoria")["valor"]
        .sum()
        .nlargest(5)
        .index.tolist()
    )

    if not top5_do_mes:
        st.info("Sem dados suficientes para evolução.")
        return

    df_periodo = df_despesas[
        (df_despesas["mes_ref"].isin(meses_periodo)) & (df_despesas["categoria"].isin(top5_do_mes))
    ]
    evolucao = df_periodo.groupby(["mes_ref", "categoria"])["valor"].sum().reset_index()

    if evolucao.empty:
        return

    cores_linha: list[str] = [
        CORES["positivo"],
        CORES["negativo"],
        CORES["neutro"],
        CORES["alerta"],
        CORES["destaque"],
    ]

    fig = go.Figure()
    for i, cat in enumerate(top5_do_mes):
        dados_cat = evolucao[evolucao["categoria"] == cat].sort_values("mes_ref")
        fig.add_trace(
            go.Scatter(
                x=dados_cat["mes_ref"],
                y=dados_cat["valor"],
                name=cat,
                mode="lines+markers",
                line=dict(color=cores_linha[i % len(cores_linha)], width=2),
                marker=dict(size=6),
            )
        )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            font=dict(size=FONTE_MINIMA),
        ),
        yaxis_title="Valor (R$)",
        xaxis_title="Mês",
    )

    st.plotly_chart(fig, width="stretch")


# "Cuide dos centavos e os reais cuidarão de si mesmos." -- Benjamin Franklin
