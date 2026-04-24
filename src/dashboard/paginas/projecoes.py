"""Página de projeções financeiras do dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard import tema
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.tema import (
    CORES,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    aplicar_locale_ptbr,
    callout_html,
    hero_titulo_html,
    rgba_cor,
)


def _card_cenario(
    titulo: str,
    linhas: list[tuple[str, str]],
    cor: str,
) -> str:
    """Gera HTML de card para um cenário de projeção."""
    itens = "".join(
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_MINIMA}px;"
        f' margin: 3px 0;">{label}: '
        '<span style="color: var(--color-texto); font-weight: bold;">'
        f"{valor}</span></p>"
        for label, valor in linhas
    )
    # Sprint 92c: o card de cenário não tem um padrão reutilizável ainda
    # (border-left por cor semântica varia). Preservamos a tag div mas
    # usando var(--...) no lugar de hex direto do f-string.
    return (
        '<div style="background-color: var(--color-card-fundo);'
        f" border-left: 4px solid {cor};"
        " border-radius: 8px; padding: 18px;"
        ' margin: 5px 0 10px 0;">'
        f'<p style="color: {cor}; font-size: {FONTE_SUBTITULO}px;'
        " font-weight: bold;"
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

    df = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa), filtro_forma_ativo()
    )
    registros: list[dict] = []
    for _, row in df.iterrows():
        registros.append(row.to_dict())

    return registros


def _formatar_ritmo(valor: float | None) -> str:
    """Formata um ritmo mensal para exibição. ``None`` vira texto explicativo."""
    if valor is None:
        return "Dados insuficientes"
    return formatar_moeda(valor)


def _cor_por_sinal_ritmo(valor: float | None) -> str:
    """Sprint 92a.10: cor Dracula do ritmo conforme o sinal do valor.

    Retorna hex pronto para CSS: verde quando positivo, vermelho quando
    negativo, cinza (``texto_sec``) quando ``None``. Valor exatamente zero
    é tratado como neutro (cinza) para não fingir saudável sem ritmo real.
    """
    if valor is None or valor == 0:
        return CORES["texto_sec"]
    return CORES["positivo"] if valor > 0 else CORES["negativo"]


def _metric_ritmo_html(titulo: str, valor: float | None) -> str:
    """Sprint 92a.10: renderização custom do cartão de ritmo com cor por sinal.

    Substitui ``st.metric`` para permitir coloração por sinal do valor
    (verde positivo, vermelho negativo, cinza quando ``None``). Mantém
    contraste visual Dracula e tipografia equivalente ao widget nativo.
    """
    cor = _cor_por_sinal_ritmo(valor)
    texto = _formatar_ritmo(valor)
    # Sprint 92c: classe utilitaria .ouroboros-ritmo-card absorve o padding.
    return (
        '<div class="ouroboros-ritmo-card">'
        '<p style="color: var(--color-texto-sec);'
        f" font-size: {FONTE_MINIMA}px;"
        f' margin: 0 0 2px 0;">{titulo}</p>'
        f'<p style="color: {cor};'
        " font-size: 28px;"
        " font-weight: 700;"
        f' margin: 0;">{texto}</p>'
        "</div>"
    )


def _saldo_do_mes(
    dados: dict[str, pd.DataFrame],
    mes: str,
    pessoa: str,
) -> float:
    """Saldo parcial (receita - despesa) do mês selecionado, já filtrado por pessoa."""
    if "extrato" not in dados or not mes:
        return 0.0
    df = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa), filtro_forma_ativo()
    )
    if "mes_ref" not in df.columns:
        return 0.0
    df = df[df["mes_ref"] == mes]
    df = df[df["tipo"] != "Transferência Interna"]
    receita = df[df["tipo"] == "Receita"]["valor"].sum()
    despesa = df[df["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
    return float(receita - despesa)


def _renderizar_ritmos(
    ritmos: dict[str, float | None],
    mes_selecionado: str,
    dados: dict[str, pd.DataFrame],
    pessoa: str,
) -> None:
    """Renderiza os três cartões de ritmo e callouts explicativos."""
    st.subheader("Ritmo de Saldo Médio Mensal")

    # Sprint 92a.10: ritmos renderizados com cor por sinal (verde positivo,
    # vermelho negativo, cinza quando None). st.metric não suporta cor no
    # valor -- só no delta -- por isso montamos HTML custom.
    col1, col2, col3 = st.columns(3)
    col1.markdown(
        _metric_ritmo_html("Ritmo histórico", ritmos.get("historico")),
        unsafe_allow_html=True,
    )
    col2.markdown(
        _metric_ritmo_html("Ritmo 12 meses", ritmos.get("12_meses")),
        unsafe_allow_html=True,
    )
    col3.markdown(
        _metric_ritmo_html("Ritmo 3 meses", ritmos.get("3_meses")),
        unsafe_allow_html=True,
    )

    st.markdown(
        callout_html(
            "info",
            "Ritmo = saldo médio mensal observado (receita menos despesa). "
            "O ritmo histórico cobre todo o período disponível; "
            "os ritmos de 12 e 3 meses mostram tendências mais recentes. "
            "Se houver divergência grande entre eles, "
            "a rotina financeira mudou recentemente.",
        ),
        unsafe_allow_html=True,
    )

    saldo_mes = _saldo_do_mes(dados, mes_selecionado, pessoa)
    if mes_selecionado:
        st.markdown(
            callout_html(
                "warning",
                f"Mês corrente ({mes_selecionado}): saldo parcial de "
                f"{formatar_moeda(saldo_mes)}. "
                "Este valor NÃO está incluído na projeção, "
                "pois o mês pode estar incompleto "
                "(snapshot até a última transação importada).",
            ),
            unsafe_allow_html=True,
        )


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
) -> None:
    """Renderiza a página de projeções financeiras."""
    st.markdown(
        hero_titulo_html(
            "06",
            "Projeções",
            "Ritmos de receita, despesa e saldo médio, com cenários atuais "
            "e projeções de economia.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado de extrato disponível para projeções."),
            unsafe_allow_html=True,
        )
        return

    from src.projections.scenarios import (
        calcular_ritmos,
        projetar_cenarios,
        projetar_com_economia,
    )

    transacoes = _transacoes_do_extrato(dados, pessoa)

    if not transacoes:
        st.markdown(
            callout_html("info", "Sem transações suficientes para projeções."),
            unsafe_allow_html=True,
        )
        return

    cenarios = projetar_cenarios(transacoes)
    ritmos = calcular_ritmos(transacoes)

    _renderizar_ritmos(ritmos, mes_selecionado, dados, pessoa)

    st.markdown("---")

    st.subheader("Cenários de Projeção")

    col1, col2 = st.columns(2)

    atual = cenarios["cenario_atual"]
    pos = cenarios["cenario_pos_infobase"]
    meta_ape = cenarios["cenario_meta_ape"]

    with col1:
        cor = CORES["positivo"] if atual["saldo_mensal"] > 0 else CORES["negativo"]
        linhas_atual = [
            ("Saldo mensal", formatar_moeda(atual["saldo_mensal"])),
            ("Reserva emergencial", _formatar_meses(atual["meses_ate_reserva_emergencia"])),
            ("Entrada apartamento", _formatar_meses(atual["meses_ate_entrada_ape"])),
            (
                "Meta apê",
                f"{formatar_moeda(meta_ape['valor_alvo'])} em "
                f"{_formatar_meses(meta_ape['meses_ate_entrada_ape'])}",
            ),
        ]
        st.markdown(
            _card_cenario("Ritmo Atual", linhas_atual, cor),
            unsafe_allow_html=True,
        )

    with col2:
        cor = CORES["positivo"] if pos["saldo_mensal"] > 0 else CORES["negativo"]
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

    _grafico_projecao(cenarios, ritmos)

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
        projecao_custom = projetar_com_economia(transacoes, float(economia_extra))
        projecao_base = cenarios["cenario_atual"]["projecao_12_meses"]
        _grafico_simulacao(projecao_base, projecao_custom, economia_extra)


def _grafico_projecao(cenarios: dict, ritmos: dict[str, float | None] | None = None) -> None:
    """Gráfico de linha: patrimônio acumulado projetado.

    Traça linhas para os cenários histórico (Ritmo Atual), Pós-Infobase e,
    quando ``ritmos`` é fornecido, também para os cenários "últimos 12 meses"
    e "últimos 3 meses" (tendências recentes).
    """
    proj_atual = cenarios["cenario_atual"]["projecao_12_meses"]
    proj_pos = cenarios["cenario_pos_infobase"]["projecao_12_meses"]

    meses_labels = [p["mes"] for p in proj_atual]
    valores_atual = [p["acumulado"] for p in proj_atual]
    valores_pos = [p["acumulado"] for p in proj_pos]

    from src.projections.scenarios import (
        MESES_PROJECAO,
        VALOR_ENTRADA_APE,
        VALOR_RESERVA_EMERGENCIA,
        _projecao_acumulada,
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_atual,
            name="Ritmo histórico",
            mode="lines+markers",
            line=dict(color=CORES["positivo"], width=3),
            marker=dict(size=6),
        )
    )

    if ritmos is not None:
        if ritmos.get("12_meses") is not None:
            proj_12 = _projecao_acumulada(float(ritmos["12_meses"]), 0.0, MESES_PROJECAO)
            fig.add_trace(
                go.Scatter(
                    x=[p["mes"] for p in proj_12],
                    y=[p["acumulado"] for p in proj_12],
                    name="Ritmo 12 meses",
                    mode="lines+markers",
                    line=dict(color=CORES["destaque"], width=2, dash="dot"),
                    marker=dict(size=5),
                )
            )
        if ritmos.get("3_meses") is not None:
            proj_3 = _projecao_acumulada(float(ritmos["3_meses"]), 0.0, MESES_PROJECAO)
            fig.add_trace(
                go.Scatter(
                    x=[p["mes"] for p in proj_3],
                    y=[p["acumulado"] for p in proj_3],
                    name="Ritmo 3 meses",
                    mode="lines+markers",
                    line=dict(color=CORES["neutro"], width=2, dash="dashdot"),
                    marker=dict(size=5),
                )
            )

    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_pos,
            name="Pós-Infobase",
            mode="lines+markers",
            line=dict(color=CORES["alerta"], width=2, dash="dash"),
            marker=dict(size=5),
        )
    )

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
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
        hovermode="x unified",
    )

    # Sprint 87.8 (R77-1): legenda padronizada abaixo do gráfico.
    tema.legenda_abaixo(fig)
    aplicar_locale_ptbr(fig, valores_eixo_x=meses_labels)
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

    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_base,
            name="Cenário base",
            mode="lines",
            line=dict(color=CORES["texto_sec"], width=2, dash="dot"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=meses_labels,
            y=valores_custom,
            name=f"Economizando +R$ {economia}/mês",
            mode="lines+markers",
            line=dict(color=CORES["destaque"], width=3),
            marker=dict(size=6),
            fill="tonexty",
            fillcolor=rgba_cor(CORES["destaque"], 0.08),
        )
    )

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
        yaxis_title="Patrimônio Acumulado (R$)",
        xaxis_title="Mês",
    )

    # Sprint 87.8 (R77-1): legenda padronizada abaixo do gráfico.
    tema.legenda_abaixo(fig)
    aplicar_locale_ptbr(fig, valores_eixo_x=meses_labels)
    st.plotly_chart(fig, width="stretch")


# "A preparação de hoje determina a conquista de amanhã." -- Roger Staubach
