"""Página de projeções financeiras do dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import filtrar_por_pessoa, formatar_moeda
from src.dashboard.tema import CORES, FONTE_MINIMA, FONTE_SUBTITULO, LAYOUT_PLOTLY


def _card_cenario(
    titulo: str,
    linhas: list[tuple[str, str]],
    cor: str,
) -> str:
    """Gera HTML de card para um cenário de projeção."""
    itens = "".join(
        f'<p style="color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;'
        f' margin: 3px 0;">{label}: '
        f'<span style="color: {CORES["texto"]}; font-weight: bold;">'
        f"{valor}</span></p>"
        for label, valor in linhas
    )
    return (
        f'<div style="background-color: {CORES["card_fundo"]};'
        f" border-left: 4px solid {cor};"
        f' border-radius: 8px; padding: 18px;'
        f' margin: 5px 0 10px 0;">'
        f'<p style="color: {cor}; font-size: {FONTE_SUBTITULO}px;'
        f' font-weight: bold;'
        f' margin: 0 0 10px 0;">{titulo}</p>'
        f"{itens}</div>"
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
    pessoa: str = "Todos",
) -> list[dict]:
    """Converte DataFrame de extrato para lista de dicts, filtrando por pessoa."""
    if "extrato" not in dados:
        return []

    df = filtrar_por_pessoa(dados["extrato"], pessoa)
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

    transacoes = _transacoes_do_extrato(dados, pessoa)

    if not transacoes:
        st.info("Sem transações suficientes para projeções.")
        return

    cenarios = projetar_cenarios(transacoes)

    st.subheader("Cenários de Projeção")

    col1, col2 = st.columns(2)

    atual = cenarios["cenario_atual"]
    pos = cenarios["cenario_pos_infobase"]
    meta_ape = cenarios["cenario_meta_ape"]

    with col1:
        cor = (
            CORES["positivo"]
            if atual["saldo_mensal"] > 0
            else CORES["negativo"]
        )
        linhas_atual = [
            ("Saldo mensal", formatar_moeda(atual["saldo_mensal"])),
            ("Reserva emergencial", _formatar_meses(atual["meses_ate_reserva_emergencia"])),
            ("Entrada apartamento", _formatar_meses(atual["meses_ate_entrada_ape"])),
            (
                "Meta apê",
                f'{formatar_moeda(meta_ape["valor_alvo"])} em '
                f'{_formatar_meses(meta_ape["meses_ate_entrada_ape"])}',
            ),
        ]
        st.markdown(
            _card_cenario("Ritmo Atual", linhas_atual, cor),
            unsafe_allow_html=True,
        )

    with col2:
        cor = (
            CORES["positivo"]
            if pos["saldo_mensal"] > 0
            else CORES["negativo"]
        )
        linhas_pos = [
            ("Saldo mensal", formatar_moeda(pos["saldo_mensal"])),
            ("Reserva emergencial", _formatar_meses(pos["meses_ate_reserva_emergencia"])),
            ("Entrada apartamento", _formatar_meses(pos["meses_ate_entrada_ape"])),
        ]
        st.markdown(
            _card_cenario("Pós-Infobase", linhas_pos, cor),
            unsafe_allow_html=True,
        )
        if pos["saldo_mensal"] < 0:
            st.markdown(
                f'<p style="color: {CORES["alerta"]}; font-size: {FONTE_MINIMA}px;'
                ' font-style: italic; margin-top: -5px;">'
                "Cenário sem salário Infobase. Saldo negativo"
                " indica necessidade de ajuste de despesas"
                " ou nova fonte de renda.</p>",
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
        projecao_base = cenarios["cenario_atual"]["projecao_12_meses"]
        _grafico_simulacao(projecao_base, projecao_custom, economia_extra)


def _grafico_projecao(cenarios: dict) -> None:
    """Gráfico de linha: patrimônio acumulado projetado."""
    proj_atual = cenarios["cenario_atual"]["projecao_12_meses"]
    proj_pos = cenarios["cenario_pos_infobase"]["projecao_12_meses"]

    meses_labels = [p["mes"] for p in proj_atual]
    valores_atual = [p["acumulado"] for p in proj_atual]
    valores_pos = [p["acumulado"] for p in proj_pos]

    from src.projections.scenarios import VALOR_ENTRADA_APE, VALOR_RESERVA_EMERGENCIA

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

    label_reserva = f"Reserva ({formatar_moeda(VALOR_RESERVA_EMERGENCIA)})"
    label_ape = f"Entrada Apê ({formatar_moeda(VALOR_ENTRADA_APE)})"
    marcos: list[tuple[float, str, str]] = [
        (VALOR_RESERVA_EMERGENCIA, label_reserva, CORES["positivo"]),
        (VALOR_ENTRADA_APE, label_ape, CORES["neutro"]),
    ]

    for valor_marco, nome_marco, cor_marco in marcos:
        fig.add_hline(
            y=valor_marco,
            line_dash="dot",
            line_color=cor_marco,
            annotation_text=nome_marco,
            annotation_position="top left",
            annotation_font_color=cor_marco,
            annotation_font_size=FONTE_MINIMA,
        )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02
        ),
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")


def _grafico_simulacao(
    projecao_base: list[dict],
    projecao_custom: list[dict],
    economia: int,
) -> None:
    """Gráfico de simulação com comparação ao cenário base."""
    meses_labels = [p["mes"] for p in projecao_custom]
    valores_custom = [p["acumulado"] for p in projecao_custom]
    valores_base = [p["acumulado"] for p in projecao_base]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=valores_base,
        name="Cenário base",
        mode="lines",
        line=dict(color=CORES["texto_sec"], width=2, dash="dot"),
    ))

    fig.add_trace(go.Scatter(
        x=meses_labels,
        y=valores_custom,
        name=f"Economizando +R$ {economia}/mês",
        mode="lines+markers",
        line=dict(color=CORES["destaque"], width=3),
        marker=dict(size=6),
        fill="tonexty",
        fillcolor="rgba(189, 147, 249, 0.1)",
    ))

    from src.projections.scenarios import VALOR_ENTRADA_APE, VALOR_RESERVA_EMERGENCIA

    fig.add_hline(
        y=VALOR_RESERVA_EMERGENCIA,
        line_dash="dot",
        line_color=CORES["positivo"],
        annotation_text="Reserva Emergência",
        annotation_position="top left",
        annotation_font_color=CORES["positivo"],
        annotation_font_size=FONTE_MINIMA,
    )

    fig.add_hline(
        y=VALOR_ENTRADA_APE,
        line_dash="dot",
        line_color=CORES["neutro"],
        annotation_text="Entrada Apê",
        annotation_position="top left",
        annotation_font_color=CORES["neutro"],
        annotation_font_size=FONTE_MINIMA,
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02
        ),
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
    )

    st.plotly_chart(fig, width="stretch")


# "A preparação de hoje determina a conquista de amanhã." -- Roger Staubach
