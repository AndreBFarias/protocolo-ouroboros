"""Mini-view Dinheiro hoje -- Sprint UX-123.

Filtra o extrato por dia de referência (hoje ou último dia disponível) e
exibe 3 KPIs principais (Receita, Despesa, Saldo) + tabela compacta com
as transações do dia. Reusa `filtrar_por_pessoa` e `filtrar_por_forma_pagamento`
da página-irmã `extrato.py` para preservar contrato de filtros globais.

Limite: <200L. Drill-down próprio NÃO existe -- usa o global da Sprint 73
via clique nas páginas-irmãs. Nesta mini-view, a tabela é read-only.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
    formatar_moeda,
)
from src.dashboard.paginas._home_helpers import (
    data_referencia_hoje,
    filtrar_para_hoje,
    renderizar_kpi_compacto,
)
from src.dashboard.tema import (
    CORES,
    callout_html,
    hero_titulo_html,
)


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str = "",
    pessoa: str = "Todos",
    ctx: dict | None = None,
) -> None:
    """Renderiza a mini-view Dinheiro hoje.

    Assinatura compatível com páginas-irmãs (mes_selecionado/pessoa/ctx)
    embora apenas `pessoa` seja usado no filtro -- "hoje" é dimensão
    temporal própria desta mini-view.
    """
    _ = mes_selecionado, ctx

    # Sprint UX-125: tab agora se chama "Finanças" (sem sufixo "hoje").
    # Mantemos "hoje" no subtítulo do hero para sinalizar a dimensão
    # temporal própria desta mini-view (dia mais recente do dataset).
    st.markdown(
        hero_titulo_html(
            "",
            "Finanças hoje",
            "Resumo das transações do dia mais recente disponível: receita, despesa e saldo.",
        ),
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.markdown(
            callout_html("warning", "Sem extrato carregado."),
            unsafe_allow_html=True,
        )
        return

    extrato = dados["extrato"]
    df = filtrar_por_pessoa(extrato, pessoa)
    df = filtrar_por_forma_pagamento(df, filtro_forma_ativo())

    referencia = data_referencia_hoje(df)
    if referencia is None:
        st.markdown(
            callout_html("info", "Sem transações datadas no extrato."),
            unsafe_allow_html=True,
        )
        return

    df_hoje = filtrar_para_hoje(df)

    if df_hoje.empty:
        st.markdown(
            callout_html("info", f"Nenhuma transação em {referencia}."),
            unsafe_allow_html=True,
        )
        return

    receita = df_hoje[df_hoje["tipo"] == "Receita"]["valor"].sum()
    despesa = df_hoje[df_hoje["tipo"].isin(["Despesa", "Imposto"])]["valor"].sum()
    saldo = receita - despesa

    st.caption(f"Referência: {referencia} ({len(df_hoje)} transações)")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            renderizar_kpi_compacto("Receita do dia", formatar_moeda(receita), CORES["positivo"]),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            renderizar_kpi_compacto("Despesa do dia", formatar_moeda(despesa), CORES["negativo"]),
            unsafe_allow_html=True,
        )
    with col3:
        cor_saldo = CORES["positivo"] if saldo >= 0 else CORES["negativo"]
        st.markdown(
            renderizar_kpi_compacto("Saldo do dia", formatar_moeda(saldo), cor_saldo),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### Transações do dia")

    # Tabela compacta: 5 colunas read-only.
    tabela = pd.DataFrame(
        {
            "Local": df_hoje["local"].fillna("--"),
            "Categoria": df_hoje["categoria"].fillna("--"),
            "Tipo": df_hoje["tipo"].fillna("--"),
            "Banco": df_hoje["banco_origem"].fillna("--"),
            "Valor": df_hoje["valor"].apply(formatar_moeda),
        }
    )
    st.dataframe(
        tabela.head(15),
        width="stretch",
        hide_index=True,
        column_config={
            "Local": st.column_config.TextColumn("Local", width="medium"),
            "Categoria": st.column_config.TextColumn("Categoria", width="medium"),
            "Tipo": st.column_config.TextColumn("Tipo", width="small"),
            "Banco": st.column_config.TextColumn("Banco", width="small"),
            "Valor": st.column_config.TextColumn("Valor", width="small"),
        },
    )

    if len(df_hoje) > 15:
        st.caption(
            f"Exibindo 15 de {len(df_hoje)} transações. Para ver todas, "
            "abra o cluster Finanças -> Extrato."
        )


# "O dia diz mais quando se conta tarde." -- fragmento de almanaque
