"""Página de projeções financeiras do dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import formatar_moeda

CORES: dict[str, str] = {
    "positivo": "#4ECDC4",
    "negativo": "#FF6B6B",
    "neutro": "#45B7D1",
    "alerta": "#FFA726",
    "fundo": "#0E1117",
    "card_fundo": "#1E2130",
    "reserva": "#4ECDC4",
    "ape": "#45B7D1",
    "divida": "#FFA726",
}


def _card_cenario(
    titulo: str,
    saldo_mensal: str,
    meses_reserva: str,
    meses_ape: str,
    cor: str,
) -> str:
    """Gera HTML de card para um cenário de projeção."""
    fundo = CORES["card_fundo"]
    return (
        f'<div style="background-color: {fundo};'
        f" border-left: 4px solid {cor};"
        ' border-radius: 8px; padding: 20px;'
        ' margin: 5px 0 10px 0;">'
        f'<p style="color: {cor}; font-size: 16px;'
        ' font-weight: bold;'
        f' margin: 0 0 10px 0;">{titulo}</p>'
        '<p style="color: #AAAAAA; font-size: 13px;'
        ' margin: 2px 0;">Saldo mensal: '
        '<span style="color: #FAFAFA;'
        f' font-weight: bold;">{saldo_mensal}</span></p>'
        '<p style="color: #AAAAAA; font-size: 13px;'
        ' margin: 2px 0;">Reserva emergencial: '
        f'<span style="color: #FAFAFA;">{meses_reserva}'
        "</span></p>"
        '<p style="color: #AAAAAA; font-size: 13px;'
        ' margin: 2px 0;">Entrada apartamento: '
        f'<span style="color: #FAFAFA;">{meses_ape}'
        "</span></p></div>"
    )


def _card_meta_ape(meta: dict, cor_ape: str, fundo: str) -> str:
    """Gera HTML do card de meta apartamento."""
    valor_alvo = formatar_moeda(meta["valor_alvo"])
    tempo = _formatar_meses(meta["meses_ate_entrada_ape"])
    eco_12 = formatar_moeda(meta["economia_necessaria_12m"])
    eco_24 = formatar_moeda(meta["economia_necessaria_24m"])

    return (
        f'<div style="background-color: {fundo};'
        f" border-left: 4px solid {cor_ape};"
        ' border-radius: 8px; padding: 20px;'
        ' margin: 5px 0 10px 0;">'
        f'<p style="color: {cor_ape}; font-size: 16px;'
        ' font-weight: bold;'
        ' margin: 0 0 10px 0;">Meta Apartamento</p>'
        '<p style="color: #AAAAAA; font-size: 13px;'
        ' margin: 2px 0;">Alvo: '
        '<span style="color: #FAFAFA;'
        f' font-weight: bold;">{valor_alvo}</span></p>'
        '<p style="color: #AAAAAA; font-size: 13px;'
        ' margin: 2px 0;">Tempo no ritmo atual: '
        f'<span style="color: #FAFAFA;">{tempo}</span></p>'
        '<p style="color: #AAAAAA; font-size: 13px;'
        " margin: 2px 0;\">"
        f"Economia necessária (12m): "
        f'<span style="color: #FAFAFA;">'
        f"{eco_12}/mês</span></p>"
        '<p style="color: #AAAAAA; font-size: 13px;'
        " margin: 2px 0;\">"
        f"Economia necessária (24m): "
        f'<span style="color: #FAFAFA;">'
        f"{eco_24}/mês</span></p></div>"
    )


def _formatar_meses(valor: int | None) -> str:
    """Formata quantidade de meses para exibição."""
    if valor is None:
        return "Inalcançável no ritmo atual"
    if valor == 0:
        return "Já atingido"
    return f"{valor} meses"


def _transacoes_do_extrato(
    dados: dict[str, pd.DataFrame],
) -> list[dict]:
    """Converte DataFrame de extrato para lista de dicts."""
    if "extrato" not in dados:
        return []

    df = dados["extrato"]
    registros: list[dict] = []
    for _, row in df.iterrows():
        registros.append(row.to_dict())

    return registros


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
) -> None:
    """Renderiza a página de projeções financeiras."""
    if "extrato" not in dados:
        st.warning(
            "Nenhum dado de extrato disponível para projeções."
        )
        return

    from src.projections.scenarios import (
        projetar_cenarios,
        projetar_com_economia,
    )

    transacoes = _transacoes_do_extrato(dados)

    if not transacoes:
        st.info("Sem transações suficientes para projeções.")
        return

    cenarios = projetar_cenarios(transacoes)

    st.subheader("Cenários de Projeção")

    col1, col2, col3 = st.columns(3)

    atual = cenarios["cenario_atual"]
    pos = cenarios["cenario_pos_infobase"]
    meta = cenarios["cenario_meta_ape"]

    with col1:
        cor = (
            CORES["positivo"]
            if atual["saldo_mensal"] > 0
            else CORES["negativo"]
        )
        st.markdown(
            _card_cenario(
                "Ritmo Atual",
                formatar_moeda(atual["saldo_mensal"]),
                _formatar_meses(
                    atual["meses_ate_reserva_emergencia"]
                ),
                _formatar_meses(atual["meses_ate_entrada_ape"]),
                cor,
            ),
            unsafe_allow_html=True,
        )

    with col2:
        cor = (
            CORES["positivo"]
            if pos["saldo_mensal"] > 0
            else CORES["negativo"]
        )
        st.markdown(
            _card_cenario(
                "Pós-Infobase",
                formatar_moeda(pos["saldo_mensal"]),
                _formatar_meses(
                    pos["meses_ate_reserva_emergencia"]
                ),
                _formatar_meses(pos["meses_ate_entrada_ape"]),
                cor,
            ),
            unsafe_allow_html=True,
        )
        if pos["saldo_mensal"] < 0:
            st.markdown(
                '<p style="color: #FFA726; font-size: 11px;'
                ' font-style: italic; margin-top: -5px;">'
                "Cenário sem salário Infobase. Saldo negativo"
                " indica necessidade de ajuste de despesas"
                " ou nova fonte de renda.</p>",
                unsafe_allow_html=True,
            )

    with col3:
        st.markdown(
            _card_meta_ape(
                meta, CORES["ape"], CORES["card_fundo"]
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")

    st.subheader("Patrimônio Acumulado Projetado (12 meses)")

    _grafico_projecao(cenarios)

    st.markdown("---")

    st.subheader("Simulação Personalizada")

    economia_extra = st.slider(
        "Se eu economizar a mais por mês (R$):",
        min_value=0,
        max_value=5000,
        value=0,
        step=100,
        key="slider_economia",
    )

    if economia_extra > 0:
        projecao_custom = projetar_com_economia(
            transacoes, float(economia_extra)
        )
        _grafico_simulacao(projecao_custom, economia_extra)


def _grafico_projecao(cenarios: dict) -> None:
    """Gráfico de linha: patrimônio acumulado projetado."""
    proj_atual = cenarios["cenario_atual"]["projecao_12_meses"]
    proj_pos = cenarios["cenario_pos_infobase"]["projecao_12_meses"]

    meses_labels = [p["mes"] for p in proj_atual]
    valores_atual = [p["acumulado"] for p in proj_atual]
    valores_pos = [p["acumulado"] for p in proj_pos]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=valores_atual,
        name="Ritmo Atual",
        mode="lines+markers",
        line=dict(color=CORES["positivo"], width=3),
        marker=dict(size=6),
    ))

    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=valores_pos,
        name="Pós-Infobase",
        mode="lines+markers",
        line=dict(
            color=CORES["alerta"], width=2, dash="dash"
        ),
        marker=dict(size=5),
    ))

    marcos: list[tuple[float, str, str]] = [
        (27000, "Reserva Emergência (R$ 27k)", CORES["reserva"]),
        (50000, "Entrada Apê (R$ 50k)", CORES["ape"]),
    ]

    for valor_marco, nome_marco, cor_marco in marcos:
        fig.add_hline(
            y=valor_marco,
            line_dash="dot",
            line_color=cor_marco,
            annotation_text=nome_marco,
            annotation_position="top left",
            annotation_font_color=cor_marco,
        )

    fig.update_layout(
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02
        ),
        margin=dict(l=60, r=20, t=40, b=40),
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)


def _grafico_simulacao(
    projecao: list[dict], economia: int
) -> None:
    """Gráfico de simulação com economia extra."""
    meses_labels = [p["mes"] for p in projecao]
    valores = [p["acumulado"] for p in projecao]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=valores,
        name=f"Economizando +R$ {economia}/mês",
        mode="lines+markers",
        line=dict(color=CORES["neutro"], width=3),
        marker=dict(size=6),
        fill="tozeroy",
        fillcolor="rgba(69, 183, 209, 0.1)",
    ))

    fig.add_hline(
        y=27000,
        line_dash="dot",
        line_color=CORES["reserva"],
        annotation_text="Reserva Emergência",
        annotation_position="top left",
        annotation_font_color=CORES["reserva"],
    )

    fig.add_hline(
        y=50000,
        line_dash="dot",
        line_color=CORES["ape"],
        annotation_text="Entrada Apê",
        annotation_position="top left",
        annotation_font_color=CORES["ape"],
    )

    fig.update_layout(
        plot_bgcolor=CORES["fundo"],
        paper_bgcolor=CORES["fundo"],
        font=dict(color="#FAFAFA"),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02
        ),
        margin=dict(l=60, r=20, t=40, b=40),
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
    )

    st.plotly_chart(fig, use_container_width=True)


# "A preparação de hoje determina a conquista de amanhã."
# -- Roger Staubach
