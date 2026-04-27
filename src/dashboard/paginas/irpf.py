"""Página de visualização IRPF no dashboard financeiro."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.dados import formatar_moeda
from src.dashboard.tema import (
    CORES,
    FONTE_CORPO,
    FONTE_MINIMA,
    FONTE_SUBTITULO,
    FONTE_TITULO,
    LAYOUT_PLOTLY,
    callout_html,
    card_html,
    hero_titulo_html,
    rgba_cor,
)
from src.irpf.checklist import gerar_checklist
from src.irpf.simulador import simular


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza a página de análise IRPF."""
    st.markdown(
        hero_titulo_html(
            "",
            "IRPF",
            "Tags de dedução, simulação de regimes, gráficos mensais e checklist de documentos.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Nenhum dado de extrato encontrado para análise IRPF."),
            unsafe_allow_html=True,
        )
        return

    extrato = dados["extrato"]
    anos_disponiveis = _extrair_anos(extrato)

    if not anos_disponiveis:
        st.markdown(
            callout_html("warning", "Nenhum ano disponível para análise IRPF."),
            unsafe_allow_html=True,
        )
        return

    ano_selecionado = st.selectbox(
        "Ano-calendário",
        anos_disponiveis,
        index=0,
        key="irpf_ano",
    )

    ano_int = int(ano_selecionado)
    df_ano = extrato[extrato["mes_ref"].str.startswith(ano_selecionado)].copy()

    if df_ano.empty:
        st.markdown(
            callout_html("info", f"Sem transações para o ano {ano_selecionado}."),
            unsafe_allow_html=True,
        )
        return

    totais = _calcular_totais_irpf(df_ano)

    _cards_resumo(totais)
    _simulacao_regimes(totais, ano_int)
    _grafico_mensal(df_ano, ano_selecionado)
    _checklist_documentos(df_ano)
    _grafico_distribuicao_tags(df_ano)


def _extrair_anos(extrato: pd.DataFrame) -> list[str]:
    """Extrai anos disponíveis do extrato, ordem decrescente."""
    if "mes_ref" not in extrato.columns:
        return []
    meses = extrato["mes_ref"].dropna().unique().tolist()
    anos = sorted({m[:4] for m in meses if len(m) >= 4}, reverse=True)
    return anos


def _calcular_totais_irpf(df: pd.DataFrame) -> dict[str, float]:
    """Calcula totais por tag IRPF."""
    resultado: dict[str, float] = {
        "rendimento_tributavel": 0.0,
        "rendimento_isento": 0.0,
        "dedutivel_medico": 0.0,
        "imposto_pago": 0.0,
        "inss_retido": 0.0,
    }

    if "tag_irpf" not in df.columns:
        return resultado

    for tag, valor in df.groupby("tag_irpf")["valor"].sum().items():
        if tag in resultado:
            resultado[tag] = abs(float(valor))

    return resultado


def _cards_resumo(totais: dict[str, float]) -> None:
    """Exibe cards de resumo dos principais valores IRPF."""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            card_html(
                "Rendimentos tributáveis",
                formatar_moeda(totais["rendimento_tributavel"]),
                CORES["positivo"],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            card_html(
                "Deduções médicas",
                formatar_moeda(totais["dedutivel_medico"]),
                CORES["neutro"],
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            card_html(
                "Impostos pagos",
                formatar_moeda(totais["imposto_pago"]),
                CORES["negativo"],
            ),
            unsafe_allow_html=True,
        )


def _simulacao_regimes(totais: dict[str, float], ano: int) -> None:
    """Simula regimes completo e simplificado e exibe comparação."""
    resultado = simular(
        rendimentos=totais["rendimento_tributavel"],
        inss=totais["inss_retido"],
        medicas=totais["dedutivel_medico"],
        impostos_pagos=totais["imposto_pago"],
        dependentes=0,
        ano=ano,
    )

    completo = resultado["completo"]
    simplificado = resultado["simplificado"]

    col_esq, col_dir = st.columns(2)

    with col_esq:
        _card_regime_completo(completo, resultado["impostos_pagos"], resultado["saldo_completo"])

    with col_dir:
        _card_regime_simplificado(
            simplificado, resultado["impostos_pagos"], resultado["saldo_simplificado"]
        )

    _banner_recomendacao(resultado)


def _card_regime_completo(completo: dict, impostos_pagos: float, saldo: float) -> None:
    """Exibe card detalhado do regime completo."""
    linhas = [
        ("Rendimentos", completo["rendimentos"], CORES["texto"]),
        ("(-) INSS retido", completo["deducoes_inss"], CORES["neutro"]),
        ("(-) Despesas médicas", completo["deducoes_medicas"], CORES["neutro"]),
        ("(-) Dependentes", completo["deducoes_dependentes"], CORES["neutro"]),
        ("= Base de cálculo", completo["base_calculo"], CORES["info"]),
        ("Imposto devido", completo["imposto_devido"], CORES["negativo"]),
        ("(-) Impostos pagos", impostos_pagos, CORES["neutro"]),
        ("= Saldo", saldo, CORES["positivo"] if saldo <= 0 else CORES["negativo"]),
    ]

    _renderizar_card_regime("Regime Completo", linhas, CORES["destaque"])


def _card_regime_simplificado(simplificado: dict, impostos_pagos: float, saldo: float) -> None:
    """Exibe card detalhado do regime simplificado."""
    linhas = [
        ("Rendimentos", simplificado["rendimentos"], CORES["texto"]),
        ("(-) Desconto padrão (20%)", simplificado["desconto_padrao"], CORES["neutro"]),
        ("= Base de cálculo", simplificado["base_calculo"], CORES["info"]),
        ("Imposto devido", simplificado["imposto_devido"], CORES["negativo"]),
        ("(-) Impostos pagos", impostos_pagos, CORES["neutro"]),
        ("= Saldo", saldo, CORES["positivo"] if saldo <= 0 else CORES["negativo"]),
    ]

    _renderizar_card_regime("Regime Simplificado", linhas, CORES["alerta"])


def _renderizar_card_regime(
    titulo: str,
    linhas: list[tuple[str, float, str]],
    cor_borda: str,
) -> None:
    """Renderiza card de regime tributário com breakdown de valores."""
    linhas_html = ""
    for rotulo, valor, cor in linhas:
        negrito = " font-weight: bold;" if rotulo.startswith("=") else ""
        separador = (
            f" border-top: 1px solid {CORES['texto_sec']}33; padding-top: 6px;"
            if rotulo.startswith("=")
            else ""
        )
        # Sprint 92c: classe .ouroboros-row-between absorve display:flex.
        # separador eh border-top dinamico por linha total.
        linhas_html += (
            '<div class="ouroboros-row-between"'
            f' style="padding: 4px 0;{separador}">'
            '<span style="color: var(--color-texto-sec);'
            f' font-size: {FONTE_CORPO}px;{negrito}">{rotulo}</span>'
            f'<span style="color: {cor};'
            f' font-size: {FONTE_CORPO}px;{negrito}">{formatar_moeda(valor)}</span>'
            "</div>"
        )

    html = (
        f'<div style="'
        f"background-color: {CORES['card_fundo']};"
        f" border: 1px solid {CORES['texto_sec']}33;"
        f" border-left: 4px solid {cor_borda};"
        f" border-radius: 8px;"
        f" padding: 18px 20px;"
        f" margin: 10px 0;"
        f" box-shadow: 0 2px 8px rgba(0,0,0,0.3);"
        f'">'
        f'<p style="color: {cor_borda};'
        f" font-size: {FONTE_TITULO}px;"
        f" font-weight: bold;"
        f' margin: 0 0 12px 0;">{titulo}</p>'
        f"{linhas_html}"
        f"</div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def _banner_recomendacao(resultado: dict) -> None:
    """Exibe banner com recomendação de regime."""
    recomendado = resultado["recomendado"]
    economia = resultado["economia"]

    if economia < 0.01:
        texto = "Ambos os regimes resultam no mesmo imposto devido."
        cor = CORES["info"]
    else:
        texto = (
            f"Regime {recomendado} é mais vantajoso, com economia de {formatar_moeda(economia)}."
        )
        cor = CORES["positivo"]

    st.markdown(
        f'<div style="'
        f"background-color: {rgba_cor(cor, 0.12)};"
        f" border: 1px solid {cor};"
        f" border-radius: 8px;"
        f" padding: 16px 20px;"
        f" margin: 10px 0 20px 0;"
        f" text-align: center;"
        f'">'
        f'<span style="color: {cor}; font-weight: bold;'
        f' font-size: {FONTE_SUBTITULO}px;">'
        f"{texto}</span></div>",
        unsafe_allow_html=True,
    )


def _grafico_mensal(df_ano: pd.DataFrame, ano: str) -> None:
    """Gráfico de barras empilhadas: rendimentos vs deduções por mês."""
    if "tag_irpf" not in df_ano.columns or "mes_ref" not in df_ano.columns:
        return

    df_tags = df_ano[df_ano["tag_irpf"].notna()].copy()
    if df_tags.empty:
        st.markdown(
            callout_html("info", "Sem transações com tags IRPF para exibir gráfico mensal."),
            unsafe_allow_html=True,
        )
        return

    tags_rendimento = {"rendimento_tributavel", "rendimento_isento"}
    tags_deducao = {"dedutivel_medico", "inss_retido", "imposto_pago"}

    df_tags["grupo"] = df_tags["tag_irpf"].apply(
        lambda t: (
            "Rendimentos" if t in tags_rendimento else ("Deduções" if t in tags_deducao else None)
        )
    )
    df_tags = df_tags[df_tags["grupo"].notna()]

    if df_tags.empty:
        return

    df_tags["valor_abs"] = df_tags["valor"].abs()
    agrupado = df_tags.groupby(["mes_ref", "grupo"])["valor_abs"].sum().reset_index()

    meses = sorted(agrupado["mes_ref"].unique())

    rend_vals = []
    ded_vals = []
    for m in meses:
        sub = agrupado[agrupado["mes_ref"] == m]
        rend = sub[sub["grupo"] == "Rendimentos"]["valor_abs"].sum()
        ded = sub[sub["grupo"] == "Deduções"]["valor_abs"].sum()
        rend_vals.append(float(rend))
        ded_vals.append(float(ded))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=meses,
            y=rend_vals,
            name="Rendimentos",
            marker_color=CORES["positivo"],
        )
    )
    fig.add_trace(
        go.Bar(
            x=meses,
            y=ded_vals,
            name="Deduções",
            marker_color=CORES["neutro"],
        )
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text=f"Rendimentos vs Deduções mensais ({ano})",
            font=dict(size=FONTE_SUBTITULO),
        ),
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis_title="Valor (R$)",
    )

    st.plotly_chart(fig, width="stretch")


def _checklist_documentos(df_ano: pd.DataFrame) -> None:
    """Exibe checklist de documentos em seção colapsável."""
    transacoes = df_ano.to_dict("records")
    checklist = gerar_checklist(transacoes)

    with st.expander("Checklist de documentos IRPF", expanded=False):
        linhas_html = ""
        for item in checklist:
            obrig = "Sim" if item["obrigatorio"] else "Não"

            if item["status"] == "Dados no sistema":
                cor_status = CORES["positivo"]
            else:
                cor_status = CORES["alerta"]

            linhas_html += (
                f"<tr>"
                f'<td style="padding: 8px; color: {CORES["texto"]};">'
                f"{item['documento']}</td>"
                f'<td style="padding: 8px; color: {CORES["texto_sec"]};">'
                f"{item['tipo']}</td>"
                f'<td style="padding: 8px; color: {CORES["texto"]};">'
                f"{obrig}</td>"
                f'<td style="padding: 8px; color: {cor_status}; font-weight: bold;">'
                f"{item['status']}</td>"
                f"</tr>"
            )

        html = (
            f'<table style="width: 100%; border-collapse: collapse;'
            f" background-color: {CORES['card_fundo']};"
            f' border-radius: 8px; overflow: hidden;">'
            f"<thead>"
            f'<tr style="border-bottom: 2px solid {CORES["texto_sec"]}33;">'
            f'<th style="padding: 10px; text-align: left;'
            f' color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px;">Documento</th>'
            f'<th style="padding: 10px; text-align: left;'
            f' color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px;">Tipo</th>'
            f'<th style="padding: 10px; text-align: left;'
            f' color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px;">Obrigatório</th>'
            f'<th style="padding: 10px; text-align: left;'
            f' color: {CORES["destaque"]}; font-size: {FONTE_CORPO}px;">Status</th>'
            f"</tr>"
            f"</thead>"
            f"<tbody>"
            f"{linhas_html}"
            f"</tbody>"
            f"</table>"
        )

        st.markdown(html, unsafe_allow_html=True)


def _grafico_distribuicao_tags(df_ano: pd.DataFrame) -> None:
    """Gráfico donut com distribuição de tags IRPF por valor."""
    if "tag_irpf" not in df_ano.columns:
        return

    df_tags = df_ano[df_ano["tag_irpf"].notna()].copy()
    if df_tags.empty:
        st.markdown(
            callout_html("info", "Sem tags IRPF para exibir distribuição."),
            unsafe_allow_html=True,
        )
        return

    nomes_tags: dict[str, str] = {
        "rendimento_tributavel": "Rendimento tributável",
        "rendimento_isento": "Rendimento isento",
        "dedutivel_medico": "Dedutível médico",
        "imposto_pago": "Imposto pago",
        "inss_retido": "INSS retido",
    }

    df_tags["valor_abs"] = df_tags["valor"].abs()
    agrupado = (
        df_tags.groupby("tag_irpf")
        .agg(
            valor_total=("valor_abs", "sum"),
            contagem=("valor_abs", "count"),
        )
        .reset_index()
    )

    agrupado["nome"] = agrupado["tag_irpf"].map(nomes_tags).fillna(agrupado["tag_irpf"])

    cores_tags: dict[str, str] = {
        "rendimento_tributavel": CORES["positivo"],
        "rendimento_isento": CORES["info"],
        "dedutivel_medico": CORES["neutro"],
        "imposto_pago": CORES["negativo"],
        "inss_retido": CORES["alerta"],
    }

    cores_lista = [cores_tags.get(tag, CORES["texto_sec"]) for tag in agrupado["tag_irpf"]]

    textos_hover = [
        f"{nome}<br>Valor: {formatar_moeda(val)}<br>Registros: {int(cnt)}"
        for nome, val, cnt in zip(agrupado["nome"], agrupado["valor_total"], agrupado["contagem"])
    ]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=agrupado["nome"],
                values=agrupado["valor_total"],
                hole=0.45,
                marker=dict(colors=cores_lista),
                textinfo="label+percent",
                textfont=dict(size=FONTE_MINIMA),
                hovertext=textos_hover,
                hoverinfo="text",
            )
        ]
    )

    fig.update_layout(
        **LAYOUT_PLOTLY,
        title=dict(
            text="Distribuição por tipo de tag IRPF",
            font=dict(size=FONTE_SUBTITULO),
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            font=dict(size=FONTE_MINIMA),
        ),
    )

    st.plotly_chart(fig, width="stretch")


# "Neste mundo, nada é certo, exceto a morte e os impostos." -- Benjamin Franklin
