"""Mini-view Docs hoje -- Sprint UX-123.

Exibe documentos do grafo cuja `data_emissao` casa com hoje (ou último
dia disponível) + KPI de pendências do dia. Reusa `carregar_documentos_grafo`
e `contar_propostas_linking` de `dados.py` para preservar contrato.

Limite: <200L. Read-only -- a catalogação detalhada continua na página-irmã.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard import dados as _dados
from src.dashboard.dados import (
    carregar_documentos_grafo,
    contar_propostas_linking,
    formatar_moeda,
)
from src.dashboard.paginas._arquivadas._home_helpers import (
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
    dados: dict[str, pd.DataFrame] | None = None,
    mes_selecionado: str = "",
    pessoa: str = "Todos",
    ctx: dict | None = None,
) -> None:
    """Renderiza a mini-view Docs hoje.

    Argumentos preservados por contrato N-para-N do roteador `app.main()`,
    embora a fonte de verdade aqui seja o grafo SQLite (igual `catalogacao.py`).
    """
    _ = dados, mes_selecionado, pessoa, ctx

    st.markdown(
        hero_titulo_html(
            "",
            "Docs hoje",
            "Documentos catalogados no dia mais recente + pendências "
            "abertas (propostas de linking aguardando revisão).",
        ),
        unsafe_allow_html=True,
    )

    if not _dados.CAMINHO_GRAFO.exists():
        st.markdown(
            callout_html(
                "warning",
                "Grafo SQLite não encontrado. Rode `./run.sh --tudo` para popular o catálogo.",
            ),
            unsafe_allow_html=True,
        )
        return

    docs = carregar_documentos_grafo()
    propostas_abertas = contar_propostas_linking()

    if docs.empty:
        st.markdown(
            callout_html("info", "Nenhum documento catalogado ainda."),
            unsafe_allow_html=True,
        )
        return

    # Filtro temporal: usa `data_emissao` como coluna canônica de tempo.
    referencia = data_referencia_hoje(docs, coluna_data="data_emissao")
    if referencia is None:
        st.markdown(
            callout_html(
                "info",
                "Documentos catalogados não têm `data_emissao` preenchida.",
            ),
            unsafe_allow_html=True,
        )
        return

    docs_hoje = filtrar_para_hoje(docs, coluna_data="data_emissao")

    st.caption(f"Referência: {referencia} ({len(docs_hoje)} documentos catalogados nesse dia)")

    # KPIs: chegaram, vinculados, pendências.
    if not docs_hoje.empty:
        vinculados_hoje = int((docs_hoje["status_linking"] == "Vinculado").sum())
        pct_link_hoje = vinculados_hoje / len(docs_hoje) if len(docs_hoje) > 0 else 0.0
    else:
        vinculados_hoje = 0
        pct_link_hoje = 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            renderizar_kpi_compacto(
                "Chegaram no dia",
                str(len(docs_hoje)),
                CORES["destaque"],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        cor_pct = CORES["positivo"] if pct_link_hoje >= 0.7 else CORES["alerta"]
        st.markdown(
            renderizar_kpi_compacto(
                "Vinculados a tx",
                f"{pct_link_hoje:.0%}",
                cor_pct,
            ),
            unsafe_allow_html=True,
        )
    with col3:
        cor_props = CORES["alerta"] if propostas_abertas > 0 else CORES["texto_sec"]
        st.markdown(
            renderizar_kpi_compacto(
                "Pendências linking",
                str(propostas_abertas),
                cor_props,
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### Documentos do dia")

    if docs_hoje.empty:
        st.markdown(
            callout_html("info", "Nenhum documento catalogado em " + referencia + "."),
            unsafe_allow_html=True,
        )
        return

    # Tabela compacta (4 colunas, alinhada com `catalogacao.py`).
    tabela = pd.DataFrame(
        {
            "Data": docs_hoje["data_emissao"].fillna("--"),
            "Fornecedor": (docs_hoje["razao_social"].fillna("").replace("", "--").str.title()),
            "Total": docs_hoje["total"].apply(lambda v: formatar_moeda(v) if v and v > 0 else "--"),
            "Status": docs_hoje["status_linking"],
        }
    )
    st.dataframe(
        tabela.head(10),
        width="stretch",
        hide_index=True,
        column_config={
            "Data": st.column_config.TextColumn("Data", width="small"),
            "Fornecedor": st.column_config.TextColumn("Fornecedor", width="large"),
            "Total": st.column_config.TextColumn("Total", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

    if len(docs_hoje) > 10:
        st.caption(
            f"Exibindo 10 de {len(docs_hoje)} documentos. Para ver todos, "
            "abra o cluster Documentos -> Catalogação."
        )


# "Um documento sem dia é nuvem; com dia, é prova." -- fragmento administrativo
