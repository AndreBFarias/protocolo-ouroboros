"""Aba Pagamentos (Sprint 79): tracking por forma (Boletos/Pix/Crédito)."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.pagamentos import (
    STATUS_ATRASADO,
    STATUS_PAGO,
    STATUS_PENDENTE,
    alertas_vencimento,
    carregar_boletos,
    faturas_credito,
    top_beneficiarios_pix,
)
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import CORES, FONTE_CORPO, FONTE_SUBTITULO, LAYOUT_PLOTLY


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    del mes_selecionado, ctx

    st.markdown(
        f'<p style="color: {CORES["destaque"]}; font-size: {FONTE_SUBTITULO}px; '
        f'font-weight: bold;">Pagamentos</p>',
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.warning("Extrato não disponível.")
        return

    # Sprint 72: respeita o filtro global de forma de pagamento (mesmo estando
    # na aba "Pagamentos", o André pode querer restringir a Pix apenas etc.).
    extrato = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa),
        filtro_forma_ativo(),
    )
    prazos = dados.get("prazos", pd.DataFrame())

    tab_boletos, tab_pix, tab_credito = st.tabs(["Boletos", "Pix", "Crédito"])

    with tab_boletos:
        _renderizar_boletos(extrato, prazos)

    with tab_pix:
        _renderizar_pix(extrato)

    with tab_credito:
        _renderizar_credito(extrato)


def _renderizar_boletos(extrato: pd.DataFrame, prazos: pd.DataFrame) -> None:
    boletos = carregar_boletos(extrato, prazos)
    if boletos.empty:
        st.info("Nenhum boleto identificado no período/filtros atuais.")
        return

    # Alertas acima da tabela
    alertas = alertas_vencimento(boletos, dias_aviso=3)
    for a in alertas[:10]:
        st.warning(a)
    if len(alertas) > 10:
        st.caption(f"+{len(alertas) - 10} alertas adicionais.")

    # Resumo por status
    if "status" in boletos.columns:
        col_pago, col_pend, col_atr = st.columns(3)
        col_pago.metric("Pagos", int((boletos["status"] == STATUS_PAGO).sum()))
        col_pend.metric(
            "Pendentes", int((boletos["status"] == STATUS_PENDENTE).sum())
        )
        col_atr.metric(
            "Atrasados", int((boletos["status"] == STATUS_ATRASADO).sum())
        )

    st.dataframe(
        boletos,
        use_container_width=True,
        hide_index=True,
        column_config={
            "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
        },
    )


def _renderizar_pix(extrato: pd.DataFrame) -> None:
    top = top_beneficiarios_pix(extrato, top_n=20)
    if top.empty:
        st.info("Nenhum Pix encontrado no período/filtros atuais.")
        return

    total = float(top["total"].sum())
    qtd_beneficiarios = int(top.shape[0])
    col1, col2 = st.columns(2)
    total_br = (
        f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    col1.metric("Total Top 20", total_br)
    col2.metric("Beneficiários", qtd_beneficiarios)

    fig = px.bar(
        top,
        x="total",
        y="local",
        orientation="h",
        text="total",
        labels={"total": "Valor (R$)", "local": "Beneficiário"},
    )
    fig.update_traces(
        texttemplate="R$ %{text:,.2f}",
        textposition="outside",
        marker=dict(color=CORES["destaque"]),
    )
    layout = {**LAYOUT_PLOTLY, "margin": dict(l=160, r=60, t=40, b=40)}
    fig.update_layout(**layout, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto_sec"]};">'
        "Tabela completa:</p>",
        unsafe_allow_html=True,
    )
    st.dataframe(top, use_container_width=True, hide_index=True)


def _renderizar_credito(extrato: pd.DataFrame) -> None:
    faturas = faturas_credito(extrato)
    if not faturas:
        st.info("Nenhuma despesa em Crédito no período/filtros atuais.")
        return

    for banco, df_banco in faturas.items():
        st.markdown(
            f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto"]}; '
            f'font-weight: bold; margin-top:16px;">Cartão {banco}</p>',
            unsafe_allow_html=True,
        )
        total = float(df_banco["valor_total"].sum())
        st.caption(
            f"{len(df_banco)} meses — total R$ "
            f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        fig = px.line(
            df_banco,
            x="mes_ref",
            y="valor_total",
            markers=True,
        )
        fig.update_layout(
            **LAYOUT_PLOTLY,
            yaxis_title="Valor (R$)",
            xaxis_title="Mês",
        )
        fig.update_traces(line=dict(color=CORES["alerta"], width=2))
        st.plotly_chart(fig, use_container_width=True)


# "Por forma de pagamento é como o banco pensa." — princípio Sprint 79
