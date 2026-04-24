"""Aba Completude: gap analysis documental (Sprint 75).

Exibe:
  - Heatmap mês × categoria com % de cobertura documental.
  - Lista de alertas inteligentes (recorrência sem contrato, valor alto
    sem comprovante, zero-cobertura).
  - Export CSV das transações órfãs.
  - Detalhe clicável mês/categoria → listagem de transações sem documento.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.gap_documental import (
    alertas,
    calcular_completude,
    carregar_categorias_obrigatorias,
    orfas_para_csv,
)
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import CORES, FONTE_CORPO, FONTE_SUBTITULO, LAYOUT_PLOTLY

# Sprint 92a item 3: limiar mínimo de transações para uma categoria entrar no
# heatmap quando o toggle "filtrar_ruido" está ativo. 2 é suficiente para
# cortar os falsos positivos de categorias com 1 tx isolada.
LIMIAR_MIN_TX_FILTRO_RUIDO: int = 2


def filtrar_categorias_por_volume(
    extrato: pd.DataFrame,
    categorias_obrigatorias: list[str],
    minimo_tx: int = LIMIAR_MIN_TX_FILTRO_RUIDO,
) -> list[str]:
    """Sprint 92a item 3: remove categorias com menos de `minimo_tx` transações.

    Pura e testável: recebe o extrato e a lista canônica de categorias
    obrigatórias, devolve a sublista com volume suficiente para não poluir
    o heatmap com alarme falso (1 tx solta = laranja escuro).
    """
    if extrato is None or extrato.empty or not categorias_obrigatorias:
        return list(categorias_obrigatorias)
    contagem = extrato["categoria"].value_counts()
    return [
        c for c in categorias_obrigatorias
        if int(contagem.get(c, 0)) >= minimo_tx
    ]


def _heatmap(resumo: dict) -> go.Figure | None:
    if not resumo:
        return None
    meses = sorted(resumo.keys())
    categorias = sorted({c for cats in resumo.values() for c in cats.keys()})
    if not meses or not categorias:
        return None

    z: list[list[float]] = []
    texto: list[list[str]] = []
    for cat in categorias:
        linha_z: list[float] = []
        linha_t: list[str] = []
        for mes in meses:
            info = resumo.get(mes, {}).get(cat)
            if info is None or info["total"] == 0:
                linha_z.append(float("nan"))
                linha_t.append("—")
            else:
                pct = (info["com_doc"] / info["total"]) * 100
                linha_z.append(pct)
                linha_t.append(f"{info['com_doc']}/{info['total']}")
        z.append(linha_z)
        texto.append(linha_t)

    # P2.2 2026-04-23: texto removido das células (ilegível em viewport 1600x
    # 1000 com 7 anos × N categorias). Mantido no hover via customdata.
    # Sprint 92a item 3: paleta trocada de [negativo, alerta, positivo]
    # (vermelho-laranja-verde, agressiva) para [alerta, info, positivo]
    # (laranja-amarelo-verde, informativa). Sem vermelho saturado, o heatmap
    # para de "gritar" com o usuario em meses incompletos por ruido.
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=meses,
            y=categorias,
            customdata=texto,
            hovertemplate="<b>%{y}</b><br>%{x}: %{customdata} com doc (%{z:.0f}%%)<extra></extra>",
            colorscale=[
                [0.0, CORES["alerta"]],
                [0.5, CORES["info"]],
                [1.0, CORES["positivo"]],
            ],
            zmin=0,
            zmax=100,
            colorbar=dict(title="% com doc", tickfont=dict(color=CORES["texto"])),
        )
    )
    layout = {**LAYOUT_PLOTLY, "margin": dict(l=140, r=40, t=60, b=80)}
    fig.update_layout(
        **layout,
        title=dict(text="Cobertura documental", font=dict(size=FONTE_SUBTITULO)),
    )
    return fig


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point da aba Completude."""
    del mes_selecionado, ctx  # Completude olha todos os meses por default.

    st.markdown(
        f'<p style="color: {CORES["destaque"]}; font-size: {FONTE_SUBTITULO}px; '
        f'font-weight: bold;">Completude Documental</p>',
        unsafe_allow_html=True,
    )

    if "extrato" not in dados:
        st.warning("Extrato não disponível.")
        return

    extrato = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa),
        filtro_forma_ativo(),
    )

    categorias = carregar_categorias_obrigatorias()
    if not categorias:
        st.warning(
            "Nenhuma categoria em `mappings/categorias_tracking.yaml`. "
            "Configure as categorias obrigatórias para ver o gap analysis."
        )
        return

    # Sprint 92a item 3: toggle para filtrar ruído (categorias obrigatórias
    # com 0 ou 1 transação no período inflavam o heatmap de laranja).
    filtrar_ruido = st.checkbox(
        "Mostrar só categorias com >=2 transações",
        value=True,
        key="completude_filtrar_ruido",
        help=(
            "Remove do heatmap categorias obrigatórias com menos de 2 transações "
            "no período filtrado -- reduz alarme falso por volume baixo."
        ),
    )
    if filtrar_ruido:
        categorias = filtrar_categorias_por_volume(extrato, categorias)
        if not categorias:
            st.info(
                "Nenhuma categoria obrigatória tem 2+ transações no período atual. "
                "Desative o filtro para ver o heatmap completo."
            )
            return

    resumo = calcular_completude(extrato, categorias_obrigatorias=categorias)

    if not resumo:
        st.info(
            "Nenhuma transação de categoria obrigatória no período. "
            "Verifique filtros ou a lista de categorias em "
            "`mappings/categorias_tracking.yaml`."
        )
        return

    # Heatmap
    fig = _heatmap(resumo)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    # Alertas
    st.markdown(
        f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto"]}; '
        f'font-weight: bold; margin-top:16px;">Alertas inteligentes</p>',
        unsafe_allow_html=True,
    )
    lista_alertas = alertas(resumo)
    if not lista_alertas:
        st.success("Nenhum alerta para o período — todas as categorias estão cobertas.")
    else:
        for a in lista_alertas[:20]:
            st.warning(a)
        if len(lista_alertas) > 20:
            st.caption(f"+{len(lista_alertas) - 20} alertas adicionais (export CSV abaixo).")

    # Detalhe mês × categoria
    st.markdown(
        f'<p style="font-size: {FONTE_CORPO}px; color: {CORES["texto"]}; '
        f'font-weight: bold; margin-top:16px;">Detalhe por mês e categoria</p>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        mes_sel = st.selectbox(
            "Mês", sorted(resumo.keys(), reverse=True), key="completude_mes"
        )
    with col2:
        cats_do_mes = sorted(resumo[mes_sel].keys()) if mes_sel else []
        cat_sel = (
            st.selectbox("Categoria", cats_do_mes, key="completude_cat")
            if cats_do_mes
            else None
        )
    if mes_sel and cat_sel:
        info = resumo[mes_sel][cat_sel]
        st.caption(
            f"{info['com_doc']} de {info['total']} transações com comprovante "
            f"em {mes_sel} / {cat_sel}"
        )
        if info["orfas"]:
            df_orfas = pd.DataFrame(info["orfas"])
            st.dataframe(df_orfas, use_container_width=True, hide_index=True)

    # Export CSV
    csv_df = orfas_para_csv(resumo)
    if not csv_df.empty:
        csv = "﻿" + csv_df.to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            label="Exportar transações sem comprovante (CSV)",
            data=csv,
            file_name="transacoes_sem_comprovante.csv",
            mime="text/csv",
        )


# "Cada mês sem comprovante é um lembrete para agir." — princípio Sprint 75
