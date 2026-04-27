"""Página de análise avançada: Sankey, heatmap e tendências."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import tema
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_periodo,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import (
    CORES,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    callout_html,
    hero_titulo_html,
    rgba_cor,
)

CORES_CICLO: list[str] = [
    CORES["positivo"],
    CORES["negativo"],
    CORES["neutro"],
    CORES["alerta"],
    CORES["destaque"],
]

MAPA_CLASSIFICACAO_COR: dict[str, str] = {
    "Obrigatório": CORES["obrigatorio"],
    "Questionável": CORES["questionavel"],
    "Supérfluo": CORES["superfluo"],
}

DIAS_SEMANA_PT: list[str] = [
    "Seg",
    "Ter",
    "Qua",
    "Qui",
    "Sex",
    "Sáb",
    "Dom",
]


def _preparar_dados_sankey(df: pd.DataFrame) -> dict:
    """Prepara dados source-target-value para diagrama Sankey.

    Filtra apenas despesas e impostos, agrupa por categoria (top 10)
    e monta nós e links para o diagrama de fluxo financeiro.
    """
    df_gastos = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df_gastos.empty:
        return {}

    por_categoria = (
        df_gastos.groupby(["categoria", "classificacao"])["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
        .head(10)
    )

    if por_categoria.empty:
        return {}

    labels: list[str] = ["Receitas"]
    cores_nos: list[str] = [CORES["positivo"]]
    source: list[int] = []
    target: list[int] = []
    value: list[float] = []
    cores_links: list[str] = []

    for idx, row in por_categoria.iterrows():
        categoria = row["categoria"]
        classificacao = row["classificacao"]
        valor = row["valor"]

        cor_no = MAPA_CLASSIFICACAO_COR.get(classificacao, CORES["texto_sec"])

        labels.append(categoria)
        cores_nos.append(cor_no)

        indice_alvo = len(labels) - 1
        source.append(0)
        target.append(indice_alvo)
        value.append(valor)
        cores_links.append(rgba_cor(cor_no, 0.3))

    return {
        "labels": labels,
        "source": source,
        "target": target,
        "value": value,
        "colors": cores_nos,
        "link_colors": cores_links,
    }


def _preparar_dados_heatmap(df: pd.DataFrame) -> dict:
    """Prepara dados para heatmap de intensidade de gastos.

    Cria matriz com dias da semana nas linhas e semanas ISO nas colunas,
    onde cada célula representa o total de gastos naquele dia.
    """
    df_gastos = df[df["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df_gastos.empty or "data" not in df_gastos.columns:
        return {}

    df_gastos["data_dt"] = pd.to_datetime(df_gastos["data"], errors="coerce")
    df_gastos = df_gastos.dropna(subset=["data_dt"])

    if df_gastos.empty:
        return {}

    df_gastos["dia_semana"] = df_gastos["data_dt"].dt.dayofweek
    df_gastos["semana_iso"] = df_gastos["data_dt"].dt.isocalendar().week.astype(int)

    pivot = (
        df_gastos.groupby(["dia_semana", "semana_iso"])["valor"]
        .sum()
        .reset_index()
        .pivot(index="dia_semana", columns="semana_iso", values="valor")
        .reindex(range(7))
        .fillna(0)
    )

    pivot = pivot.reindex(sorted(pivot.columns), axis=1)

    semanas_labels = [str(s) for s in pivot.columns.tolist()]

    return {
        "z": pivot.values.tolist(),
        "x": semanas_labels,
        "y": DIAS_SEMANA_PT,
    }


def _renderizar_sankey(df: pd.DataFrame) -> None:
    """Renderiza diagrama Sankey de fluxo de despesas."""
    dados_sankey = _preparar_dados_sankey(df)

    if not dados_sankey:
        st.markdown(
            callout_html("info", "Dados insuficientes para o diagrama Sankey."),
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    pad=20,
                    thickness=25,
                    line=dict(color=CORES["card_fundo"], width=1),
                    label=dados_sankey["labels"],
                    color=dados_sankey["colors"],
                ),
                link=dict(
                    source=dados_sankey["source"],
                    target=dados_sankey["target"],
                    value=dados_sankey["value"],
                    color=dados_sankey["link_colors"],
                    hovertemplate=(
                        "%{source.label} → %{target.label}<br>R$ %{value:,.2f}<extra></extra>"
                    ),
                ),
            )
        ]
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text="Fluxo de Despesas por Categoria",
            font=dict(size=FONTE_SUBTITULO),
        ),
    )
    # Sprint 87.8: helper de legenda padroniza margem top/bottom.
    tema.legenda_abaixo(fig)
    # P2.2 2026-04-23: sobrepõe margem direita para 140px evitando
    # labels "Juros/Encargos", "Impostos", "Farmácia" cortados.
    fig.update_layout(margin=dict(l=40, r=140, t=fig.layout.margin.t, b=fig.layout.margin.b))
    st.plotly_chart(fig, use_container_width=True)


def _renderizar_heatmap(df: pd.DataFrame) -> None:
    """Renderiza heatmap de intensidade de gastos por dia da semana."""
    dados_heatmap = _preparar_dados_heatmap(df)

    if not dados_heatmap:
        st.markdown(
            callout_html("info", "Dados insuficientes para o heatmap de gastos."),
            unsafe_allow_html=True,
        )
        return

    escala_cores = [
        [0, CORES["fundo"]],
        [0.5, CORES["alerta"]],
        [1, CORES["negativo"]],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=dados_heatmap["z"],
            x=dados_heatmap["x"],
            y=dados_heatmap["y"],
            colorscale=escala_cores,
            hovertemplate="Semana %{x}<br>%{y}<br>R$ %{z:,.2f}<extra></extra>",
            colorbar=dict(
                title=dict(text="R$", font=dict(size=FONTE_MINIMA)),
                tickfont=dict(size=FONTE_MINIMA),
            ),
        )
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text="Intensidade de Gastos por Dia da Semana",
            font=dict(size=FONTE_SUBTITULO),
        ),
        xaxis_title="Semana ISO",
        yaxis_title="Dia da Semana",
        yaxis=dict(autorange="reversed"),
    )

    # Sprint 87.8 (R77-1): padroniza margens via helper (heatmap não tem
    # legenda, mas o helper ajusta margin top/bottom para consistência).
    tema.legenda_abaixo(fig)
    st.plotly_chart(fig, use_container_width=True)


def _renderizar_tendencias(df_total: pd.DataFrame) -> None:
    """Renderiza gráfico de tendências com média móvel de 3 meses.

    Utiliza dados completos (sem filtro de período) para exibir
    a evolução histórica das principais categorias de gasto.
    """
    df_gastos = df_total[df_total["tipo"].isin(["Despesa", "Imposto"])].copy()

    if df_gastos.empty:
        st.markdown(
            callout_html("info", "Dados insuficientes para análise de tendências."),
            unsafe_allow_html=True,
        )
        return

    por_mes_cat = df_gastos.groupby(["mes_ref", "categoria"])["valor"].sum().reset_index()

    top5 = df_gastos.groupby("categoria")["valor"].sum().nlargest(5).index.tolist()

    if not top5:
        st.markdown(
            callout_html("info", "Dados insuficientes para análise de tendências."),
            unsafe_allow_html=True,
        )
        return

    fig = go.Figure()

    for i, categoria in enumerate(top5):
        dados_cat = por_mes_cat[por_mes_cat["categoria"] == categoria].sort_values("mes_ref").copy()

        if dados_cat.empty:
            continue

        dados_cat["media_movel"] = dados_cat["valor"].rolling(window=3, min_periods=1).mean()

        cor = CORES_CICLO[i % len(CORES_CICLO)]

        fig.add_trace(
            go.Scatter(
                x=dados_cat["mes_ref"],
                y=dados_cat["media_movel"],
                name=categoria,
                mode="lines+markers",
                line=dict(color=cor, width=2),
                marker=dict(size=6),
                hovertemplate=(
                    f"{categoria}<br>Mês: %{{x}}<br>Média móvel: R$ %{{y:,.2f}}<extra></extra>"
                ),
            )
        )

    layout_base = {k: v for k, v in LAYOUT_PLOTLY.items() if k != "margin"}
    fig.update_layout(
        **layout_base,
        title=dict(
            text="Tendências -- Média Móvel 3 Meses (Top 5 Categorias)",
            font=dict(size=FONTE_SUBTITULO),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=FONTE_MINIMA),
        ),
        yaxis_title="Valor (R$)",
        xaxis_title="Mês",
        margin=dict(l=50, r=20, t=50, b=80),
    )

    st.plotly_chart(fig, use_container_width=True)


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza página de análise avançada com Sankey, heatmap e tendências."""
    st.markdown(
        hero_titulo_html(
            "08",
            "Análise",
            "Sankey de fluxo de despesas, heatmap por dia da semana e "
            "tendências históricas por classificação.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado encontrado para análise avançada."),
            unsafe_allow_html=True,
        )
        return

    gran = ctx.get("granularidade", "Mês") if ctx else "Mês"
    periodo_filtro = ctx.get("periodo", periodo) if ctx else periodo

    extrato = dados["extrato"]
    extrato_pessoa = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(extrato, pessoa), filtro_forma_ativo()
    )
    extrato_periodo = filtrar_por_periodo(extrato_pessoa, gran, periodo_filtro)

    st.subheader("Fluxo de Despesas")
    _renderizar_sankey(extrato_periodo)

    st.markdown("---")

    st.subheader("Mapa de Calor -- Gastos por Dia da Semana")
    _renderizar_heatmap(extrato_periodo)

    st.markdown("---")

    st.subheader("Tendências Históricas")
    _renderizar_tendencias(extrato_pessoa)


# "Riqueza não é ter muito, mas precisar de pouco." -- Epicuro
