"""Página de visão geral do dashboard financeiro."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.componentes import kpi_grid_html
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
    aplicar_locale_ptbr,
)


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de visão geral."""
    if "extrato" not in dados:
        st.warning("Nenhum dado encontrado para a visão geral.")
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo = ctx.get("periodo", mes_selecionado) if ctx else mes_selecionado

    extrato = dados["extrato"]
    extrato_filtrado = filtrar_por_pessoa(extrato, pessoa)
    extrato_mes = filtrar_por_periodo(extrato_filtrado, gran, periodo)

    receitas = extrato_mes[extrato_mes["tipo"] == "Receita"]["valor"].sum()
    despesas = extrato_mes[extrato_mes["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
    saldo = receitas - despesas

    superfluo = extrato_mes[
        (extrato_mes["classificacao"] == "Supérfluo")
        & (extrato_mes["tipo"].isin(["Despesa", "Imposto"]))
    ]["valor"].sum()

    taxa_poupanca = (saldo / receitas * 100) if receitas > 0 else 0.0

    top_cat = (
        extrato_mes[extrato_mes["tipo"].isin(["Despesa", "Imposto"])]
        .groupby("categoria")["valor"]
        .sum()
    )
    maior_gasto_cat = top_cat.idxmax() if not top_cat.empty else "---"
    maior_gasto_val = top_cat.max() if not top_cat.empty else 0.0

    cor_taxa = (
        CORES["positivo"]
        if taxa_poupanca > 10
        else (CORES["alerta"] if taxa_poupanca > 0 else CORES["negativo"])
    )
    cor_sup = CORES["superfluo"] if superfluo > 500 else CORES["texto_sec"]

    cards_kpi = [
        ("Taxa de poupança", f"{taxa_poupanca:.1f}%", cor_taxa),
        ("Gastos supérfluos", formatar_moeda(superfluo), cor_sup),
        (
            f"Maior gasto: {maior_gasto_cat}",
            formatar_moeda(maior_gasto_val),
            CORES["alerta"],
        ),
    ]
    st.markdown(kpi_grid_html(cards_kpi), unsafe_allow_html=True)

    _indicador_saude(receitas, saldo, superfluo)

    col_esq, col_dir = st.columns(2)

    with col_esq:
        _grafico_barras_historico(extrato_filtrado, mes_selecionado)

    with col_dir:
        _grafico_classificacao(extrato_mes)


def _indicador_saude(receita: float, saldo: float, superfluo: float) -> None:
    """Exibe indicador de saúde financeira com orientação."""
    if receita <= 0:
        return

    percentual = (saldo / receita) * 100

    if percentual > 30:
        nivel = "Saudável"
        cor = CORES["positivo"]
        orientacao = f"Poupança de {percentual:.0f}% da receita"
    elif percentual > 10:
        nivel = "Atenção"
        cor = CORES["alerta"]
        orientacao = f"Poupança de {percentual:.0f}%. Ideal: acima de 30%"
    else:
        nivel = "Crítico"
        cor = CORES["negativo"]
        if superfluo > 0:
            economia_necessaria = receita * 0.1 - saldo
            orientacao = (
                f"Poupança de apenas {percentual:.0f}%. "
                f"Cortar {formatar_moeda(min(economia_necessaria, superfluo))} "
                f"em supérfluos equilibra o orçamento"
            )
        else:
            orientacao = f"Poupança de apenas {percentual:.0f}%. Revisar despesas obrigatórias"

    st.markdown(
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border-left: 4px solid {cor};"
        f" border-radius: 8px;"
        f" padding: 20px;"
        f" margin: 10px 0 20px 0;"
        f'">'
        f'<span style="color: {cor}; font-weight: bold;'
        f' font-size: {FONTE_SUBTITULO}px;">'
        f"Saúde financeira: {nivel}</span>"
        f'<span style="color: {CORES["texto_sec"]};'
        f" margin-left: 15px;"
        f' font-size: {FONTE_CORPO}px;">'
        f"{orientacao}</span></div>",
        unsafe_allow_html=True,
    )


def _grafico_barras_historico(
    extrato: pd.DataFrame,
    mes_atual: str,
) -> None:
    """Gráfico de barras com linha de saldo: receita vs despesa últimos 6 meses."""
    meses_ordenados = sorted(extrato["mes_ref"].dropna().unique().tolist())

    if mes_atual in meses_ordenados:
        idx = meses_ordenados.index(mes_atual)
        inicio = max(0, idx - 5)
        meses_sel = meses_ordenados[inicio : idx + 1]
    else:
        meses_sel = meses_ordenados[-6:]

    receitas_list: list[float] = []
    despesas_list: list[float] = []
    saldos_list: list[float] = []

    for m in meses_sel:
        ext_m = filtrar_por_mes(extrato, m)
        rec = ext_m[ext_m["tipo"] == "Receita"]["valor"].sum()
        desp = ext_m[ext_m["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
        receitas_list.append(rec)
        despesas_list.append(desp)
        saldos_list.append(rec - desp)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=meses_sel,
            y=receitas_list,
            name="Receita",
            marker_color=CORES["positivo"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=meses_sel,
            y=despesas_list,
            name="Despesa",
            marker_color=CORES["negativo"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=meses_sel,
            y=saldos_list,
            name="Saldo",
            mode="lines+markers",
            line=dict(color=CORES["destaque"], width=3),
            marker=dict(size=8),
            yaxis="y2",
        )
    )

    layout_barras = {**LAYOUT_PLOTLY, "margin": dict(l=50, r=20, t=70, b=80)}
    fig.update_layout(
        **layout_barras,
        title=dict(
            text="Receita vs Despesa",
            font=dict(size=FONTE_SUBTITULO),
            y=0.96,
            yanchor="top",
        ),
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
        yaxis_title="Valor (R$)",
        yaxis2=dict(
            title=dict(text="Saldo (R$)", font=dict(color=CORES["destaque"])),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color=CORES["destaque"]),
        ),
    )

    aplicar_locale_ptbr(fig, valores_eixo_x=meses_sel)
    st.plotly_chart(fig, width="stretch")


def _grafico_classificacao(extrato_mes: pd.DataFrame) -> None:
    """Barras horizontais: distribuição por classificação."""
    df = extrato_mes[extrato_mes["tipo"].isin(["Despesa", "Imposto"])]

    if df.empty:
        st.info("Sem despesas para exibir a distribuição.")
        return

    agrupado = df.groupby("classificacao")["valor"].sum().reset_index()
    agrupado = agrupado.sort_values("valor", ascending=True)

    cores = [MAPA_CLASSIFICACAO.get(c, CORES["na"]) for c in agrupado["classificacao"]]

    fig = go.Figure(
        data=[
            go.Bar(
                x=agrupado["valor"],
                y=agrupado["classificacao"],
                orientation="h",
                marker_color=cores,
                text=[formatar_moeda(v) for v in agrupado["valor"]],
                textposition="auto",
                textfont=dict(size=FONTE_MINIMA),
            )
        ]
    )

    layout = {**LAYOUT_PLOTLY, "margin": dict(l=120, r=20, t=50, b=30)}
    fig.update_layout(
        **layout,
        title=dict(text="Despesas por Classificação", font=dict(size=FONTE_SUBTITULO)),
        xaxis_title="Valor (R$)",
        showlegend=False,
    )

    aplicar_locale_ptbr(fig)
    st.plotly_chart(fig, width="stretch")


# "A riqueza não consiste em ter grandes posses, mas em ter poucas necessidades." -- Epicteto
