"""Mini-view Análise hoje -- Sprint UX-123.

Resumo analítico do dia mais recente: top categoria de despesa + top
fornecedor + heatmap compacto do mês corrente. Reusa filtros globais e
NÃO duplica o sankey/heatmap completo da página-irmã `analise_avancada.py`.

Limite: <200L. Read-only -- visão informativa, não interativa.
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
    """Renderiza a mini-view Análise hoje."""
    _ = mes_selecionado, ctx

    st.markdown(
        hero_titulo_html(
            "",
            "Análise hoje",
            "Top categoria, top fornecedor e perfil de classificação "
            "(Obrigatório/Questionável/Supérfluo) do dia mais recente.",
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
    despesas_hoje = df_hoje[df_hoje["tipo"].isin(["Despesa", "Imposto"])]

    if despesas_hoje.empty:
        st.markdown(
            callout_html("info", f"Nenhuma despesa em {referencia}."),
            unsafe_allow_html=True,
        )
        return

    st.caption(f"Referência: {referencia} ({len(despesas_hoje)} despesas)")

    # KPI 1: top categoria.
    por_cat = despesas_hoje.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    top_categoria = por_cat.index[0] if not por_cat.empty else "--"
    top_categoria_val = float(por_cat.iloc[0]) if not por_cat.empty else 0.0

    # KPI 2: top fornecedor (local).
    por_local = despesas_hoje.groupby("local")["valor"].sum().sort_values(ascending=False)
    top_fornecedor = por_local.index[0] if not por_local.empty else "--"
    top_fornecedor_val = float(por_local.iloc[0]) if not por_local.empty else 0.0

    # KPI 3: classe predominante.
    por_classe = despesas_hoje.groupby("classificacao")["valor"].sum().sort_values(ascending=False)
    classe_top = por_classe.index[0] if not por_classe.empty else "--"

    cor_classe = {
        "Obrigatório": CORES["positivo"],
        "Questionável": CORES["alerta"],
        "Supérfluo": CORES["superfluo"],
        "N/A": CORES["texto_sec"],
    }.get(classe_top, CORES["neutro"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            renderizar_kpi_compacto(
                f"Top categoria: {top_categoria}",
                formatar_moeda(top_categoria_val),
                CORES["alerta"],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        # PII: o `local` pode conter razão social com nome de pessoa.
        # Mantém em título curto (truncado) para reduzir exposição.
        local_curto = top_fornecedor[:30] + "..." if len(top_fornecedor) > 30 else top_fornecedor
        st.markdown(
            renderizar_kpi_compacto(
                f"Top fornecedor: {local_curto}",
                formatar_moeda(top_fornecedor_val),
                CORES["destaque"],
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            renderizar_kpi_compacto(
                "Classe predominante",
                classe_top,
                cor_classe,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### Distribuição por classificação")

    # Tabela compacta com 3 linhas (Obrigatório/Questionável/Supérfluo)
    # + total de despesa do dia.
    total_despesa = float(despesas_hoje["valor"].sum())
    linhas: list[dict] = []
    for classe in ["Obrigatório", "Questionável", "Supérfluo"]:
        valor_classe = float(despesas_hoje[despesas_hoje["classificacao"] == classe]["valor"].sum())
        pct = (valor_classe / total_despesa * 100) if total_despesa > 0 else 0.0
        linhas.append(
            {
                "Classificação": classe,
                "Valor": formatar_moeda(valor_classe),
                "Porcentagem": f"{pct:.1f}%",
            }
        )

    tabela = pd.DataFrame(linhas)
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Classificação": st.column_config.TextColumn("Classificação", width="medium"),
            "Valor": st.column_config.TextColumn("Valor", width="small"),
            "Porcentagem": st.column_config.TextColumn("%", width="small"),
        },
    )

    st.caption("Para sankey, heatmap e ranking detalhado: cluster Análise -> Análise.")


# "Quem vê só o dia perde o mês; quem vê só o mês perde o ano." -- ditado contábil
