"""Mini-view Metas hoje -- Sprint UX-123.

Snapshot resumido das metas: total, % atingidas, top 3 metas com maior
progresso. Reusa `_carregar_metas` e `_atualizar_valor_atual` da página-irmã
`metas.py` para não duplicar parser YAML.

Limite: <200L. Read-only -- a edição detalhada continua na página principal.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard.dados import formatar_moeda
from src.dashboard.paginas._arquivadas._home_helpers import renderizar_kpi_compacto
from src.dashboard.paginas.metas import (
    _atualizar_valor_atual,
    _calcular_progresso,
    _carregar_metas,
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
    """Renderiza a mini-view Metas hoje.

    Snapshot do progresso atual das metas monetárias. Diferente das outras
    mini-views, "hoje" aqui significa "estado atual do progresso", não um
    filtro temporal sobre transações.
    """
    _ = ctx

    st.markdown(
        hero_titulo_html(
            "",
            "Metas hoje",
            "Snapshot do progresso atual: percentual atingido, metas em "
            "destaque e top 3 mais proximas da conclusao.",
        ),
        unsafe_allow_html=True,
    )

    metas = _carregar_metas()

    if not metas:
        st.markdown(
            callout_html(
                "warning",
                "Nenhuma meta encontrada. Verifique mappings/metas.yaml.",
            ),
            unsafe_allow_html=True,
        )
        return

    metas = _atualizar_valor_atual(metas, dados, mes_selecionado, pessoa)

    metas_valor = [m for m in metas if m.get("tipo") != "binario"]
    metas_binarias = [m for m in metas if m.get("tipo") == "binario"]

    # Calcula progresso de cada meta monetaria + total atingidas (>=100%).
    progressos: list[tuple[dict, float]] = []
    atingidas = 0
    for meta in metas_valor:
        pct = _calcular_progresso(meta)
        progressos.append((meta, pct))
        if pct >= 1.0:
            atingidas += 1

    pct_atingidas = (atingidas / len(metas_valor)) if metas_valor else 0.0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            renderizar_kpi_compacto(
                "Total de metas",
                str(len(metas)),
                CORES["destaque"],
            ),
            unsafe_allow_html=True,
        )
    with col2:
        cor_pct = CORES["positivo"] if pct_atingidas >= 0.5 else CORES["alerta"]
        st.markdown(
            renderizar_kpi_compacto(
                "Metas atingidas",
                f"{atingidas}/{len(metas_valor)} ({pct_atingidas:.0%})",
                cor_pct,
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            renderizar_kpi_compacto(
                "Metas binarias",
                str(len(metas_binarias)),
                CORES["neutro"],
            ),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("##### Top 3 metas mais proximas da conclusao")

    nao_atingidas = [(m, pct) for m, pct in progressos if pct < 1.0]
    nao_atingidas.sort(key=lambda x: x[1], reverse=True)
    top3 = nao_atingidas[:3]

    if not top3:
        st.markdown(
            callout_html("success", "Todas as metas monetarias atingidas. Parabens!"),
            unsafe_allow_html=True,
        )
        return

    linhas: list[dict] = []
    for meta, pct in top3:
        nome = meta.get("nome", "Sem nome")
        valor_atual = float(meta.get("valor_atual", 0))
        valor_alvo = float(meta.get("valor_alvo", 0))
        prazo = meta.get("prazo", "--")
        linhas.append(
            {
                "Meta": nome,
                "Atual": formatar_moeda(valor_atual),
                "Alvo": formatar_moeda(valor_alvo),
                "Progresso": f"{pct * 100:.0f}%",
                "Prazo": prazo,
            }
        )

    tabela = pd.DataFrame(linhas)
    st.dataframe(
        tabela,
        width="stretch",
        hide_index=True,
        column_config={
            "Meta": st.column_config.TextColumn("Meta", width="large"),
            "Atual": st.column_config.TextColumn("Atual", width="small"),
            "Alvo": st.column_config.TextColumn("Alvo", width="small"),
            "Progresso": st.column_config.TextColumn("%", width="small"),
            "Prazo": st.column_config.TextColumn("Prazo", width="small"),
        },
    )

    st.caption("Para timeline de prazos, metas binarias e cards detalhados: cluster Metas.")


# "Meta vista de longe parece distante; vista de hoje, parece possivel." -- desconhecido
