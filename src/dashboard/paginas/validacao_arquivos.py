"""Stub de retrocompat -- Sprint UX-RD-11.

Esta página foi renomeada para "Extração Tripla" (layout 3 colunas:
lista de arquivos | viewer | tabela ETL × Opus × Humano editável).

A página antiga ``validacao_arquivos.py`` permanece como stub por **uma
sprint** para retrocompat de bookmarks e deep-links externos. Após a
próxima rodada de UX, este módulo deve ser removido em sprint formal.

Implementação real: ``src/dashboard/paginas/extracao_tripla.py``.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.tema import callout_html


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point legado: avisa o usuário e aponta para a página nova."""
    del dados, mes_selecionado, pessoa, ctx

    st.markdown(
        callout_html(
            "info",
            "Esta página foi renomeada para **Extração Tripla** (layout "
            "3 colunas: lista | viewer | tabela ETL × Opus × Humano). "
            "Use o link abaixo ou o atalho `?cluster=Documentos&"
            "tab=Extração+Tripla` na URL.",
        ),
        unsafe_allow_html=True,
    )

    st.markdown(
        "[Ir para Extração Tripla](?cluster=Documentos&tab=Extra%C3%A7%C3%A3o+Tripla)",
        unsafe_allow_html=True,
    )


# "Cada porta antiga aponta para a sua sucessora." -- princípio da
# retrocompat amigável
