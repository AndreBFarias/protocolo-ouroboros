"""Página de contas e dívidas do dashboard financeiro."""

import pandas as pd
import streamlit as st

from src.dashboard.dados import filtrar_por_mes, formatar_moeda

CORES: dict[str, str] = {
    "positivo": "#4ECDC4",
    "negativo": "#FF6B6B",
    "neutro": "#45B7D1",
    "fundo": "#0E1117",
    "card_fundo": "#1E2130",
}


def renderizar(dados: dict[str, pd.DataFrame], mes_selecionado: str, pessoa: str) -> None:
    """Renderiza a página de contas e dívidas."""
    tem_dividas = "dividas_ativas" in dados
    tem_prazos = "prazos" in dados

    if not tem_dividas and not tem_prazos:
        st.warning("Nenhum dado encontrado para contas e dívidas.")
        return

    if tem_dividas:
        _secao_dividas(dados["dividas_ativas"], mes_selecionado)

    if tem_prazos:
        _secao_prazos(dados["prazos"])


def _secao_dividas(df: pd.DataFrame, mes: str) -> None:
    """Exibe tabela de dívidas ativas com semáforo visual."""
    st.subheader("Dívidas Ativas")

    df_mes = filtrar_por_mes(df, mes)

    if df_mes.empty:
        st.info("Sem dívidas registradas para este mês.")
        return

    _resumo_pagamentos(df_mes)

    df_exibir = df_mes[["custo", "valor", "status", "obs"]].copy()

    df_exibir["status_visual"] = df_exibir["status"].apply(_semaforo_status)

    df_exibir["valor_fmt"] = df_exibir["valor"].apply(formatar_moeda)

    df_exibir["obs"] = df_exibir["obs"].fillna("-")

    tabela = df_exibir[["custo", "valor_fmt", "status_visual", "obs"]].copy()
    tabela.columns = ["Custo", "Valor", "Status", "Observação"]

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Custo": st.column_config.TextColumn("Custo", width="medium"),
            "Valor": st.column_config.TextColumn("Valor", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Observação": st.column_config.TextColumn("Observação", width="medium"),
        },
    )


def _gerar_html_tabela(tabela: pd.DataFrame, status_list: list[str]) -> str:
    """Gera HTML estilizado para a tabela de dívidas."""
    linhas_html: list[str] = []

    for i, (_, row) in enumerate(tabela.iterrows()):
        status = status_list[i] if i < len(status_list) else ""
        cor_fundo = (
            "rgba(78, 205, 196, 0.1)" if status == "Pago"
            else "rgba(255, 107, 107, 0.1)"
        )
        cor_borda = CORES["positivo"] if status == "Pago" else CORES["negativo"]

        linhas_html.append(f"""
        <tr style="background-color: {cor_fundo}; border-left: 3px solid {cor_borda};">
            <td style="padding: 10px; color: #FAFAFA;">{row['Custo']}</td>
            <td style="padding: 10px; color: #FAFAFA;">{row['Valor']}</td>
            <td style="padding: 10px; color: {cor_borda}; font-weight: bold;">{row['Status']}</td>
            <td style="padding: 10px; color: #AAAAAA;">{row['Observação']}</td>
        </tr>
        """)

    return f"""
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <thead>
            <tr style="background-color: {CORES['card_fundo']};">
                <th style="padding: 12px; text-align: left; color: #FAFAFA;">Custo</th>
                <th style="padding: 12px; text-align: left; color: #FAFAFA;">Valor</th>
                <th style="padding: 12px; text-align: left; color: #FAFAFA;">Status</th>
                <th style="padding: 12px; text-align: left; color: #FAFAFA;">Observação</th>
            </tr>
        </thead>
        <tbody>
            {"".join(linhas_html)}
        </tbody>
    </table>
    """


def _semaforo_status(status: str) -> str:
    """Retorna indicador visual do status de pagamento."""
    if pd.isna(status):
        return "[?] Indefinido"
    if status == "Pago":
        return "[OK] Pago"
    return "[!!] Não Pago"


def _resumo_pagamentos(df: pd.DataFrame) -> None:
    """Exibe resumo de pagamentos: total pago vs pendente."""
    total_pago = df[df["status"] == "Pago"]["valor"].sum()
    total_pendente = df[df["status"] == "Não Pago"]["valor"].sum()
    total_geral = total_pago + total_pendente

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            _card_resumo("Total Pago", formatar_moeda(total_pago), CORES["positivo"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _card_resumo("Total Pendente", formatar_moeda(total_pendente), CORES["negativo"]),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _card_resumo("Total Geral", formatar_moeda(total_geral), CORES["neutro"]),
            unsafe_allow_html=True,
        )


def _card_resumo(titulo: str, valor: str, cor: str) -> str:
    """Gera HTML de card de resumo."""
    return f"""
    <div style="
        background-color: {CORES['card_fundo']};
        border-left: 4px solid {cor};
        border-radius: 8px;
        padding: 15px;
        margin: 5px 0 15px 0;
    ">
        <p style="color: #AAAAAA; font-size: 13px; margin: 0;">{titulo}</p>
        <p style="color: {cor}; font-size: 20px; font-weight: bold;
            margin: 5px 0 0 0; white-space: nowrap;">{valor}</p>
    </div>
    """


def _secao_prazos(df: pd.DataFrame) -> None:
    """Exibe tabela de prazos de vencimento."""
    st.subheader("Prazos de Vencimento")

    if df.empty:
        st.info("Sem prazos cadastrados.")
        return

    df_exibir = df[["conta", "dia_vencimento"]].copy()
    df_exibir.columns = ["Conta", "Dia de Vencimento"]

    df_exibir = df_exibir.sort_values("Dia de Vencimento")

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Conta": st.column_config.TextColumn("Conta", width="medium"),
            "Dia de Vencimento": st.column_config.NumberColumn(
                "Dia de Vencimento", format="%d"
            ),
        },
    )


# "O preço de qualquer coisa é a quantidade de vida que você troca por ela." -- Henry David Thoreau
