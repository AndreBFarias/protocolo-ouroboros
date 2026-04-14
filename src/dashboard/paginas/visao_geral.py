"""Página de visão geral do dashboard financeiro."""

import pandas as pd
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

MAPA_CLASSIFICACAO: dict[str, str] = {
    "Obrigatório": CORES["obrigatorio"],
    "Questionável": CORES["questionavel"],
    "Supérfluo": CORES["superfluo"],
}


def _criar_card_metrica(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de um card de métrica estilizado."""
    return f"""
    <div style="
        background-color: {CORES['card_fundo']};
        border-left: 4px solid {cor};
        border-radius: 8px;
        padding: 20px;
        margin: 5px 0;
    ">
        <p style="color: #AAAAAA; font-size: 14px; margin: 0;">{titulo}</p>
        <p style="color: {cor}; font-size: 24px; font-weight: bold;
            margin: 5px 0 0 0; white-space: nowrap;">{valor}</p>
    </div>
    """


def _calcular_indicador_saude(receita: float, saldo: float) -> tuple[str, str, str]:
    """Calcula indicador de saúde financeira.

    Returns:
        Tupla com (nível, cor, descrição).
    """
    if receita <= 0:
        return "Sem receita", CORES["na"], "Sem dados de receita para calcular"

    percentual = (saldo / receita) * 100

    if percentual > 30:
        return "Saudável", CORES["positivo"], f"Saldo representa {percentual:.1f}% da receita"
    if percentual > 10:
        return "Atenção", CORES["questionavel"], f"Saldo representa {percentual:.1f}% da receita"
    return "Crítico", CORES["negativo"], f"Saldo representa {percentual:.1f}% da receita"


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de visão geral."""
    if "resumo_mensal" not in dados or "extrato" not in dados:
        st.warning("Nenhum dado encontrado para a visão geral.")
        return

    resumo = dados["resumo_mensal"]
    extrato = dados["extrato"]

    resumo_mes = filtrar_por_mes(resumo, mes_selecionado)

    if pessoa != "Todos":
        extrato_filtrado = filtrar_por_pessoa(extrato, pessoa)
        extrato_mes = filtrar_por_mes(extrato_filtrado, mes_selecionado)
        despesas = extrato_mes[extrato_mes["tipo"] == "Despesa"]["valor"].sum()
        receitas = extrato_mes[extrato_mes["tipo"] == "Receita"]["valor"].sum()
        saldo = receitas - despesas
    elif not resumo_mes.empty:
        receitas = float(resumo_mes["receita_total"].iloc[0])
        despesas = float(resumo_mes["despesa_total"].iloc[0])
        saldo = float(resumo_mes["saldo"].iloc[0])
    else:
        receitas = 0.0
        despesas = 0.0
        saldo = 0.0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            _criar_card_metrica("Receita", formatar_moeda(receitas), CORES["positivo"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _criar_card_metrica("Despesa", formatar_moeda(despesas), CORES["negativo"]),
            unsafe_allow_html=True,
        )
    with col3:
        cor_saldo = CORES["positivo"] if saldo >= 0 else CORES["negativo"]
        st.markdown(
            _criar_card_metrica("Saldo", formatar_moeda(saldo), cor_saldo),
            unsafe_allow_html=True,
        )

    nivel, cor_saude, descricao = _calcular_indicador_saude(receitas, saldo)
    st.markdown(
        f"""
        <div style="
            background-color: {CORES['card_fundo']};
            border-left: 4px solid {cor_saude};
            border-radius: 8px;
            padding: 12px 20px;
            margin: 10px 0 20px 0;
        ">
            <span style="color: {cor_saude}; font-weight: bold;">Saúde financeira: {nivel}</span>
            <span style="color: #AAAAAA; margin-left: 15px;">{descricao}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_esq, col_dir = st.columns(2)

    with col_esq:
        _grafico_barras_historico(resumo, mes_selecionado, pessoa, extrato)

    with col_dir:
        _grafico_pizza_classificacao(extrato, mes_selecionado, pessoa)


def _grafico_barras_historico(
    resumo: pd.DataFrame,
    mes_atual: str,
    pessoa: str,
    extrato: pd.DataFrame,
) -> None:
    """Gráfico de barras: Receita vs Despesa nos últimos 6 meses."""
    meses_ordenados = sorted(resumo["mes_ref"].dropna().unique().tolist())

    if mes_atual in meses_ordenados:
        idx = meses_ordenados.index(mes_atual)
        inicio = max(0, idx - 5)
        meses_selecionados = meses_ordenados[inicio : idx + 1]
    else:
        meses_selecionados = meses_ordenados[-6:]

    if pessoa != "Todos":
        receitas_list: list[float] = []
        despesas_list: list[float] = []
        for m in meses_selecionados:
            ext_m = filtrar_por_pessoa(filtrar_por_mes(extrato, m), pessoa)
            receitas_list.append(ext_m[ext_m["tipo"] == "Receita"]["valor"].sum())
            despesas_list.append(ext_m[ext_m["tipo"] == "Despesa"]["valor"].sum())
    else:
        dados_periodo = resumo[resumo["mes_ref"].isin(meses_selecionados)].sort_values("mes_ref")
        receitas_list = dados_periodo["receita_total"].tolist()
        despesas_list = dados_periodo["despesa_total"].tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=meses_selecionados,
        y=receitas_list,
        name="Receita",
        marker_color=CORES["positivo"],
    ))
    fig.add_trace(go.Bar(
        x=meses_selecionados,
        y=despesas_list,
        name="Despesa",
        marker_color=CORES["negativo"],
    ))

    fig.update_layout(
        title="Receita vs Despesa",
        barmode="group",
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
        yaxis_title="Valor (R$)",
    )

    st.plotly_chart(fig, use_container_width=True)


def _grafico_pizza_classificacao(
    extrato: pd.DataFrame,
    mes: str,
    pessoa: str,
) -> None:
    """Gráfico pizza: distribuição por classificação."""
    df = filtrar_por_mes(extrato, mes)
    df = filtrar_por_pessoa(df, pessoa)
    df = df[df["tipo"] == "Despesa"]

    if df.empty:
        st.info("Sem despesas para exibir a distribuição.")
        return

    agrupado = df.groupby("classificacao")["valor"].sum().reset_index()
    agrupado = agrupado.sort_values("valor", ascending=False)

    cores = [MAPA_CLASSIFICACAO.get(c, CORES["na"]) for c in agrupado["classificacao"]]

    fig = go.Figure(data=[go.Pie(
        labels=agrupado["classificacao"],
        values=agrupado["valor"],
        marker=dict(colors=cores),
        hole=0.4,
        textinfo="label+percent",
        textfont=dict(size=12),
    )])

    fig.update_layout(
        title="Classificação",
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1),
    )

    st.plotly_chart(fig, use_container_width=True)


# "A riqueza não consiste em ter grandes posses, mas em ter poucas necessidades." -- Epicteto
