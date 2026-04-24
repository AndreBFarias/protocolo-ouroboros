"""Página de análise por categorias do dashboard financeiro."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.componentes.drilldown import aplicar_drilldown
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_mes,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    MAPA_CLASSIFICACAO,
    aplicar_locale_ptbr,
    callout_html,
    hero_titulo_html,
)

MAPA_CLASSIFICACAO_COR: dict[str, str] = MAPA_CLASSIFICACAO

MAPA_CLASSIFICACAO_VALOR: dict[str, int] = {
    "Obrigatório": 0,
    "Questionável": 1,
    "Supérfluo": 2,
}


def _cor_texto_por_fundo(fundo_hex: str) -> str:
    """Sprint 92a item 2: escolhe cor de texto legível sobre o fundo informado.

    Usa luminância relativa WCAG 2.1 (https://www.w3.org/TR/WCAG21/#dfn-relative-luminance)
    para decidir entre preto e branco. Quando a luminância do fundo é
    > 0.6, retorna preto ("#000"); caso contrário, branco ("#fff").

    Aceita cor em formato `#RRGGBB` ou `#RGB`. Fallback seguro: retorna
    branco para cores inválidas (comportamento antigo, preserva contraste
    mínimo no Dracula dark default).
    """
    texto = str(fundo_hex or "").lstrip("#").strip()
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    if len(texto) != 6:
        return "#fff"
    try:
        r = int(texto[0:2], 16) / 255.0
        g = int(texto[2:4], 16) / 255.0
        b = int(texto[4:6], 16) / 255.0
    except ValueError:
        return "#fff"

    def _linearizar(canal: float) -> float:
        # Formula WCAG (gamma sRGB).
        return canal / 12.92 if canal <= 0.03928 else ((canal + 0.055) / 1.055) ** 2.4

    luminância = 0.2126 * _linearizar(r) + 0.7152 * _linearizar(g) + 0.0722 * _linearizar(b)
    return "#000" if luminância > 0.6 else "#fff"


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de categorias."""
    st.markdown(
        hero_titulo_html(
            "02",
            "Categorias",
            "Treemap de despesas por categoria, comparativos e destaques "
            "do período com drill-down clicável.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para análise de categorias."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    df_filtrado = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(extrato, pessoa), filtro_forma_ativo()
    )
    df = filtrar_por_periodo(df_filtrado, gran, periodo)
    df = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df.empty:
        st.markdown(
            callout_html("info", "Sem despesas para o período selecionado."),
            unsafe_allow_html=True,
        )
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

    # Sprint 77: treemap estético — título compacto, margens mínimas,
    # textfont monospace, bordas escuras entre quadrados, padding interno.
    layout = {
        **LAYOUT_PLOTLY,
        "margin": dict(l=0, r=0, t=10, b=0),
    }
    fig.update_layout(
        **layout,
        uniformtext=dict(minsize=12, mode="hide"),
    )

    # Sprint 92a item 2 (P1-05 WCAG AA): o treemap antes usava textfont global
    # branco sobre cores claras (ex.: green #50FA7B, yellow/orange) dando
    # contraste ~2.8:1. Agora calculamos a cor do texto por leaf via
    # luminância WCAG: preto em fundos claros (> 0.6), branco em escuros.
    # A cor de fundo de cada leaf é herdada do mapa classificacao->cor.  # noqa: accent
    cores_texto_leaf = [
        _cor_texto_por_fundo(MAPA_CLASSIFICACAO_COR.get(c, CORES["fundo"]))
        for c in agrupado["classificacao"]
    ]

    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>R$ %{value:,.2f}",
        textfont=dict(size=13, family="monospace", color=cores_texto_leaf),
        marker=dict(line=dict(color=CORES["fundo"], width=2)),
        textposition="middle center",
        tiling=dict(pad=4),
        customdata=agrupado["categoria"],
    )

    aplicar_locale_ptbr(fig)
    # Sprint 73 (ADR-19): clique em folha do treemap navega para aba Extrato
    # com filtro de categoria aplicado via query_params.
    aplicar_drilldown(
        fig,
        campo_customdata="categoria",
        tab_destino="Extrato",
        key_grafico="treemap_categorias",
    )


def _ranking_com_variacao(extrato_filtrado: pd.DataFrame, mes_atual: str) -> None:
    """Top 10 categorias com variação vs mês anterior.

    Nota (Sprint 87.1 / R73-1): este ranking é renderizado como tabela HTML,
    não como gráfico Plotly. Drill-down via clique não se aplica porque o
    Streamlit não suporta `on_select` em tabelas HTML/`st.dataframe` (mesma
    limitação registrada em R74-2). O drill-down da família "categoria"
    permanece garantido pelo treemap `_treemap_categorias` acima.
    """
    st.markdown(
        f'<p style="font-size: {FONTE_SUBTITULO}px; font-weight: bold;'
        f' color: {CORES["texto"]}; margin-bottom: 10px;">'
        f"Top 10 Categorias</p>",
        unsafe_allow_html=True,
    )

    df_desp = extrato_filtrado[extrato_filtrado["tipo"].isin(["Despesa", "Imposto"])]

    meses = sorted(df_desp["mes_ref"].dropna().unique().tolist())
    if mes_atual not in meses:
        st.markdown(
            callout_html("info", "Sem dados para o mês selecionado."),
            unsafe_allow_html=True,
        )
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
        st.markdown(
            callout_html("info", "Sem dados suficientes para evolução."),
            unsafe_allow_html=True,
        )
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

    aplicar_locale_ptbr(fig, valores_eixo_x=meses_periodo)
    st.plotly_chart(fig, width="stretch")


# "Cuide dos centavos e os reais cuidarão de si mesmos." -- Benjamin Franklin
