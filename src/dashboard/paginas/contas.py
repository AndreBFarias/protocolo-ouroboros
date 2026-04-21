"""Página de contas e dívidas do dashboard financeiro."""

from datetime import date

import pandas as pd
import streamlit as st

from src.dashboard.dados import (
    filtrar_por_mes,
    filtrar_por_pessoa,
    formatar_moeda,
    renderizar_dataframe,
)
from src.dashboard.tema import CORES, FONTE_CORPO, FONTE_MINIMA, card_html, rgba_cor

AVISO_SNAPSHOT: str = (
    "Dados congelados desde 2023 — snapshot histórico não é atualizado "
    "automaticamente. Para atualizar, edite manualmente "
    "`data/output/ouroboros_2026.xlsx` nas abas dividas_ativas, "
    "inventario e prazos."
)


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de contas e dívidas."""
    tem_dividas = "dividas_ativas" in dados
    tem_inventario = "inventario" in dados
    tem_prazos = "prazos" in dados

    if not tem_dividas and not tem_inventario and not tem_prazos:
        st.warning("Nenhum dado encontrado para contas e dívidas.")
        return

    if tem_dividas:
        _secao_dividas(dados["dividas_ativas"], mes_selecionado, pessoa)

    if tem_inventario:
        _secao_inventario(dados["inventario"])

    if tem_prazos:
        _secao_prazos(dados["prazos"])


def _secao_dividas(df: pd.DataFrame, mes: str, pessoa: str) -> None:
    """Exibe tabela de dívidas ativas com indicadores visuais."""
    st.subheader("Dívidas Ativas")
    st.warning(AVISO_SNAPSHOT)

    df_mes = filtrar_por_mes(df, mes)
    if "recorrente" in df.columns:
        df_recorrentes = df[
            (df["recorrente"] == True) & (df["status"] != "Pago")  # noqa: E712
        ]
        df_mes = pd.concat([df_mes, df_recorrentes]).drop_duplicates()
    df_mes = filtrar_por_pessoa(df_mes, pessoa)

    if df_mes.empty:
        st.info("Sem dívidas registradas para este período.")
        return

    _resumo_pagamentos(df_mes)

    df_mes = renderizar_dataframe(df_mes)

    linhas_html: list[str] = []
    for _, row in df_mes.iterrows():
        status = row.get("status", "")
        cor_borda = CORES["positivo"] if status == "Pago" else CORES["negativo"]
        cor_fundo = (
            rgba_cor(CORES["positivo"], 0.08)
            if status == "Pago"
            else rgba_cor(CORES["negativo"], 0.08)
        )
        status_texto = "Pago" if status == "Pago" else "Pendente"
        obs_raw = row.get("obs", "")
        obs = obs_raw if obs_raw not in ("", "—", None) else "—"

        linhas_html.append(
            f'<tr style="background-color: {cor_fundo};'
            f' border-left: 3px solid {cor_borda};">'
            f'<td style="padding: 12px 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px;">{row.get("custo", "")}</td>'
            f'<td style="padding: 12px 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px; text-align: right;">'
            f"{formatar_moeda(row.get('valor', 0))}</td>"
            f'<td style="padding: 12px 10px; color: {cor_borda};'
            f' font-weight: bold; font-size: {FONTE_CORPO}px;">'
            f"{status_texto}</td>"
            f'<td style="padding: 12px 10px; color: {CORES["texto_sec"]};'
            f' font-size: {FONTE_MINIMA}px;">{obs}</td></tr>'
        )

    html = (
        f'<table style="width: 100%; border-collapse: collapse;'
        f' margin: 10px 0 20px 0;">'
        f'<thead><tr style="background-color: {CORES["card_fundo"]};">'
        f'<th style="padding: 10px; text-align: left;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Custo</th>'
        f'<th style="padding: 10px; text-align: right;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Valor</th>'
        f'<th style="padding: 10px; text-align: left;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Status</th>'
        f'<th style="padding: 10px; text-align: left;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Obs</th>'
        f"</tr></thead><tbody>{''.join(linhas_html)}</tbody></table>"
    )

    st.markdown(html, unsafe_allow_html=True)


def _resumo_pagamentos(df: pd.DataFrame) -> None:
    """Exibe resumo de pagamentos: total pago vs pendente."""
    total_pago = df[df["status"] == "Pago"]["valor"].sum()
    total_pendente = df[df["status"] == "Não Pago"]["valor"].sum()
    total_geral = total_pago + total_pendente

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            card_html("Total Pago", formatar_moeda(total_pago), CORES["positivo"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            card_html("Total Pendente", formatar_moeda(total_pendente), CORES["negativo"]),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            card_html("Total Geral", formatar_moeda(total_geral), CORES["neutro"]),
            unsafe_allow_html=True,
        )


def _secao_inventario(df: pd.DataFrame) -> None:
    """Exibe inventário de bens com depreciação."""
    st.subheader("Inventário")
    st.warning(AVISO_SNAPSHOT)

    if df.empty:
        st.info("Sem bens cadastrados no inventário.")
        return

    df = renderizar_dataframe(df)
    st.dataframe(df, width="stretch", hide_index=True)


def _secao_prazos(df: pd.DataFrame) -> None:
    """Exibe prazos de vencimento com indicador de urgência."""
    st.subheader("Prazos de Vencimento")
    st.warning(AVISO_SNAPSHOT)

    if df.empty:
        st.info("Sem prazos cadastrados.")
        return

    hoje = date.today()
    dia_atual = hoje.day

    linhas_html: list[str] = []
    for _, row in df.sort_values("dia_vencimento").iterrows():
        conta = row.get("conta", "")
        dia = int(row.get("dia_vencimento", 0))
        dias_ate = dia - dia_atual

        if dias_ate < 0:
            urgencia = "Vencido"
            cor = CORES["negativo"]
        elif dias_ate <= 3:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["alerta"]
        elif dias_ate <= 7:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["info"]
        else:
            urgencia = f"Em {dias_ate} dias"
            cor = CORES["texto_sec"]

        linhas_html.append(
            f'<tr style="border-bottom: 1px solid {CORES["card_fundo"]};">'
            f'<td style="padding: 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px;">{conta}</td>'
            f'<td style="padding: 10px; color: {CORES["texto"]};'
            f' font-size: {FONTE_CORPO}px; text-align: center;">Dia {dia}</td>'
            f'<td style="padding: 10px; color: {cor};'
            f' font-size: {FONTE_CORPO}px; font-weight: bold;">'
            f"{urgencia}</td></tr>"
        )

    html = (
        f'<table style="width: 100%; border-collapse: collapse;">'
        f'<thead><tr style="background-color: {CORES["card_fundo"]};">'
        f'<th style="padding: 10px; text-align: left;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Conta</th>'
        f'<th style="padding: 10px; text-align: center;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Vencimento</th>'
        f'<th style="padding: 10px; text-align: left;'
        f' color: {CORES["texto_sec"]}; font-size: {FONTE_MINIMA}px;">Urgência</th>'
        f"</tr></thead><tbody>{''.join(linhas_html)}</tbody></table>"
    )

    st.markdown(html, unsafe_allow_html=True)


# "O preço de qualquer coisa é a quantidade de vida que você troca por ela." -- Henry David Thoreau
