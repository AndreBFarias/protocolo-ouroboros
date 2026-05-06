"""Aba Completude — gap analysis documental, redesign UX-RD-10.

Reescrita a partir da Sprint 75 (heatmap Plotly) seguindo o mockup
``novo-mockup/mockups/08-completude.html``:

* ``page-header`` "COMPLETUDE" + ``sprint-tag`` UX-RD-10 + pill cobertura
  global;
* Matriz **tipo (linha) × mês (coluna)** dos últimos 12 meses, com cell
  colorida pela paleta D7 (graduado/calibracao/regredindo/pendente);
* Tooltip por célula mostra ``com_doc/total · pct%``;
* Click na célula re-direciona para a aba Catalogação com filtros pré-
  preenchidos via deep-link ``?cluster=Documentos&tab=Catalogação&...``;
* Bloco "Lacunas detectadas" com alertas inteligentes (recorrência, valor
  alto, zero-cobertura);
* Export CSV das transações órfãs preservado.

Aprendizados aplicados:
  * ``minificar()`` para HTML grande, sem ``<pre>``/``<code>`` em
    ``st.markdown``;
  * Cores via tokens CSS (``--d7-graduado``, ``--accent-yellow``, etc.).
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.analysis.gap_documental import (
    alertas,
    calcular_completude,
    carregar_categorias_obrigatorias,
    orfas_para_csv,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.dados import (
    filtrar_por_forma_pagamento,
    filtrar_por_pessoa,
    filtro_forma_ativo,
)
from src.dashboard.tema import (
    CORES,
    FONTE_SUBTITULO,
    LAYOUT_PLOTLY,
    callout_html,
)

# Sprint 92a item 3: limiar mínimo de transações para uma categoria entrar na
# matriz quando o toggle "filtrar_ruido" está ativo. 2 é suficiente para
# cortar os falsos positivos de categorias com 1 tx isolada.
LIMIAR_MIN_TX_FILTRO_RUIDO: int = 2

# Limite de meses exibidos na matriz (mockup mostra 12). Configurável aqui
# para casar mudanças futuras do mockup sem refactor profundo.
JANELA_MESES_MATRIZ: int = 12


def filtrar_categorias_por_volume(
    extrato: pd.DataFrame,
    categorias_obrigatorias: list[str],
    minimo_tx: int = LIMIAR_MIN_TX_FILTRO_RUIDO,
) -> list[str]:
    """Sprint 92a item 3: remove categorias com menos de ``minimo_tx`` tx.

    Pura e testável: recebe o extrato e a lista canônica de categorias
    obrigatórias, devolve a sublista com volume suficiente para não poluir
    a matriz com alarme falso (1 tx solta = laranja escuro).
    """
    if extrato is None or extrato.empty or not categorias_obrigatorias:
        return list(categorias_obrigatorias)
    contagem = extrato["categoria"].value_counts()
    return [c for c in categorias_obrigatorias if int(contagem.get(c, 0)) >= minimo_tx]


def _heatmap(resumo: dict) -> go.Figure | None:
    """Heatmap Plotly legado (Sprint 75 + 92a).

    Mantido como API exportada para compatibilidade com testes existentes
    (``tests/test_dashboard_completude.py``). A UI ativa do redesign UX-RD-10
    usa ``_matriz_html`` em vez deste heatmap; ``_heatmap`` continua puro
    para não regredir contratos públicos.
    """
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

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=meses,
            y=categorias,
            customdata=texto,
            hovertemplate=(
                "<b>%{y}</b><br>%{x}: %{customdata} com doc "
                "(%{z:.0f}%%)<extra></extra>"
            ),
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


def _classificar_celula_d7(pct: float, total: int) -> str:
    """Mapeia ``pct`` de cobertura para classe D7.

    Tabela canônica (mockup 08-completude.html `.cal-c.full/.partial/.missing/.empty`):
      * ``empty``     -> sem transações naquele mês/tipo (total == 0)
      * ``full``      -> 100% (D7 graduado, verde)
      * ``partial``   -> >= 50% (D7 calibracao, amarelo)
      * ``missing``   -> < 50% (D7 regredindo, vermelho)
    """
    if total == 0:
        return "empty"
    if pct >= 99.999:
        return "full"
    if pct >= 50.0:
        return "partial"
    return "missing"


def _ordenar_meses(meses: list[str], janela: int = JANELA_MESES_MATRIZ) -> list[str]:
    """Devolve os últimos ``janela`` meses ordenados ascendentemente.

    Aceita strings ``YYYY-MM`` (formato canônico do extrato). Meses fora do
    formato (ex: ``sem-mes``) ficam no final ordenados lexicograficamente.
    """
    canonicos = sorted(m for m in meses if len(m) == 7 and m[4] == "-")
    extras = sorted(m for m in meses if not (len(m) == 7 and m[4] == "-"))
    janela_canonica = canonicos[-janela:] if len(canonicos) > janela else canonicos
    return janela_canonica + extras


def _cell_label(estado: str) -> str:
    """Marca textual interna da célula (espelha mockup: vazio/~/!)."""
    return {"full": "", "partial": "~", "missing": "!", "empty": ""}[estado]


def _matriz_html(
    resumo: dict[str, dict[str, dict[str, Any]]],
    categorias: list[str],
    meses: list[str],
) -> str:
    """Renderiza a matriz tipo × mês como HTML.

    Cada célula é um link ``<a>`` que navega para a Catalogação filtrada via
    deep-link. Para mês ``YYYY-MM`` e categoria ``Cat``, o link gerado é
    ``?cluster=Documentos&tab=Catalogação&completude_mes=YYYY-MM&completude_cat=Cat``.

    HTML emitido com classes literais ``cal-c full|partial|missing|empty``
    para casar o CSS do redesign (tema_css.py preserva os tokens D7 e o
    mockup já define ``.cal-c.*`` como referência visual; tema_css.py emite
    classes equivalentes via ``.completude-cell-*``).
    """
    head_html = (
        '<div class="completude-matriz-h" aria-hidden="true"></div>'
        + "".join(
            f'<div class="completude-matriz-h">{m}</div>' for m in meses
        )
    )
    linhas: list[str] = []
    for cat in categorias:
        cells: list[str] = [
            f'<div class="completude-matriz-rotulo" title="{cat}">{cat}</div>'
        ]
        for mes in meses:
            info = resumo.get(mes, {}).get(cat)
            if info is None or info["total"] == 0:
                estado = "empty"
                tooltip = f"{cat} · {mes} · sem transações"
                href = ""
            else:
                pct = (info["com_doc"] / info["total"]) * 100.0
                estado = _classificar_celula_d7(pct, info["total"])
                tooltip = f"{cat} · {mes} · {info['com_doc']}/{info['total']} ({pct:.0f}%)"
                # Deep-link Catalogação filtrada (UX-RD-10).
                href = (
                    f"?cluster=Documentos&tab=Catalogação"
                    f"&completude_mes={mes}&completude_cat={cat}"
                )
            label = _cell_label(estado)
            if href:
                cells.append(
                    f'<a class="completude-cell completude-cell-{estado}" '
                    f'href="{href}" target="_self" title="{tooltip}" '
                    f'data-completude-cat="{cat}" data-completude-mes="{mes}">'
                    f"{label}</a>"
                )
            else:
                cells.append(
                    f'<div class="completude-cell completude-cell-{estado}" '
                    f'title="{tooltip}">{label}</div>'
                )
        linhas.append("".join(cells))

    grid = head_html + "".join(linhas)
    return minificar(
        f"""
        <div class="completude-matriz-card">
          <div class="completude-matriz-grid"
               style="grid-template-columns: 160px repeat({len(meses)}, 1fr);">
            {grid}
          </div>
          <div class="completude-matriz-legenda">
            <span><span class="dot completude-cell-full"></span>completo</span>
            <span><span class="dot completude-cell-partial"></span>parcial</span>
            <span><span class="dot completude-cell-missing"></span>ausente</span>
          </div>
        </div>
        """
    )


def _page_header_html(pct_global: float, lacunas_total: int) -> str:
    """HTML do page-header UX-RD-10."""
    if pct_global >= 90.0:
        pill_classe = "pill-d7-graduado"
    elif pct_global >= 70.0:
        pill_classe = "pill-d7-calibracao"
    else:
        pill_classe = "pill-d7-regredindo"
    return minificar(
        f"""
        <div class="page-header">
          <div>
            <h1 class="page-title">COMPLETUDE</h1>
            <p class="page-subtitle">
              Mapa de cobertura documental por tipo &times; mês. Verde = todos
              os comprovantes esperados estão presentes; amarelo = parcial;
              vermelho = faltam. <strong>{lacunas_total}</strong> lacunas no
              período.
            </p>
          </div>
          <div class="page-meta">
            <span class="sprint-tag">UX-RD-10</span>
            <span class="pill {pill_classe}">cobertura {pct_global:.0f}%</span>
          </div>
        </div>
        """
    )


def _calcular_metricas_globais(
    resumo: dict[str, dict[str, dict[str, Any]]],
) -> tuple[float, int, int]:
    """Devolve (pct_global, lacunas_total, tipos_completos)."""
    total = 0
    com_doc = 0
    lacunas = 0
    cats_completas: set[str] = set()
    cats_todas: set[str] = set()
    for cats in resumo.values():
        for cat, info in cats.items():
            cats_todas.add(cat)
            total += info["total"]
            com_doc += info["com_doc"]
            lacunas += info["sem_doc"]
            if info["total"] > 0 and info["sem_doc"] == 0:
                # cat completa em ESSE mês -- não significa global, contagem
                # final é por categoria com ZERO lacuna em todos os meses.
                pass
    for cat in cats_todas:
        sem_doc_cat = sum(
            resumo.get(m, {}).get(cat, {"sem_doc": 0})["sem_doc"]
            for m in resumo.keys()
        )
        if sem_doc_cat == 0:
            cats_completas.add(cat)
    pct = (com_doc / total) * 100.0 if total else 100.0
    return pct, lacunas, len(cats_completas)


def renderizar(
    dados: dict[str, pd.DataFrame],
    mes_selecionado: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Entry point da aba Completude (UX-RD-10 + UX-T-08)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Reprocessar", "title": "Reanalisar completude"},
        {"label": "Exportar gaps", "primary": True,
         "title": "Exportar lista de lacunas"},
    ])

    del mes_selecionado, ctx

    if "extrato" not in dados:
        st.markdown(_page_header_html(0.0, 0), unsafe_allow_html=True)
        st.markdown(
            callout_html("warning", "Extrato não disponível."),
            unsafe_allow_html=True,
        )
        return

    extrato = filtrar_por_forma_pagamento(
        filtrar_por_pessoa(dados["extrato"], pessoa),
        filtro_forma_ativo(),
    )

    categorias = list(carregar_categorias_obrigatorias())
    if not categorias:
        st.markdown(_page_header_html(0.0, 0), unsafe_allow_html=True)
        st.markdown(
            callout_html(
                "warning",
                "Nenhuma categoria em `mappings/categorias_tracking.yaml`. "
                "Configure as categorias obrigatórias para ver o gap analysis.",
            ),
            unsafe_allow_html=True,
        )
        return

    # Sprint 92a item 3: toggle para filtrar ruído. Renderizado APÓS o header
    # mas ANTES da matriz para o usuário ver o efeito imediato.
    pct_inicial, lacunas_inicial, _ = _calcular_metricas_globais(
        calcular_completude(extrato, categorias_obrigatorias=frozenset(categorias))
    )
    st.markdown(
        _page_header_html(pct_inicial, lacunas_inicial), unsafe_allow_html=True
    )

    filtrar_ruido = st.checkbox(
        "Mostrar só categorias com >=2 transações",
        value=True,
        key="completude_filtrar_ruido",
        help=(
            "Remove da matriz categorias obrigatórias com menos de 2 "
            "transações no período filtrado -- reduz alarme falso por "
            "volume baixo."
        ),
    )
    if filtrar_ruido:
        categorias = filtrar_categorias_por_volume(extrato, categorias)
        if not categorias:
            st.markdown(
                callout_html(
                    "info",
                    "Nenhuma categoria obrigatória tem 2+ transações no "
                    "período atual. Desative o filtro para ver a matriz "
                    "completa.",
                ),
                unsafe_allow_html=True,
            )
            return

    resumo = calcular_completude(
        extrato, categorias_obrigatorias=frozenset(categorias)
    )
    if not resumo:
        st.markdown(
            callout_html(
                "info",
                "Nenhuma transação de categoria obrigatória no período. "
                "Verifique filtros ou a lista de categorias em "
                "`mappings/categorias_tracking.yaml`.",
            ),
            unsafe_allow_html=True,
        )
        return

    meses_ordenados = _ordenar_meses(list(resumo.keys()))
    categorias_ordenadas = sorted(categorias)

    # Matriz HTML
    st.markdown(
        _matriz_html(resumo, categorias_ordenadas, meses_ordenados),
        unsafe_allow_html=True,
    )

    # Alertas
    st.markdown(
        '<h3 class="completude-secao-titulo">Lacunas detectadas</h3>',
        unsafe_allow_html=True,
    )
    lista_alertas = alertas(resumo)
    if not lista_alertas:
        st.markdown(
            callout_html(
                "success",
                "Nenhum alerta para o período -- todas as categorias estão "
                "cobertas.",
            ),
            unsafe_allow_html=True,
        )
    else:
        for a in lista_alertas[:20]:
            st.markdown(callout_html("warning", a), unsafe_allow_html=True)
        if len(lista_alertas) > 20:
            st.caption(
                f"+{len(lista_alertas) - 20} alertas adicionais (export CSV "
                "abaixo)."
            )

    # Detalhe mês × categoria (drill-down nativo Streamlit)
    st.markdown(
        '<h3 class="completude-secao-titulo">Detalhe por mês e categoria</h3>',
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        # Pré-popular do deep-link UX-RD-10 (?completude_mes=YYYY-MM).
        mes_default_idx = 0
        meses_desc = sorted(resumo.keys(), reverse=True)
        try:
            qs = st.query_params  # type: ignore[attr-defined]
            mes_qs = qs.get("completude_mes")
            if mes_qs and mes_qs in meses_desc:
                mes_default_idx = meses_desc.index(mes_qs)
        except Exception:
            pass
        mes_sel = st.selectbox(
            "Mês",
            meses_desc,
            index=mes_default_idx,
            key="completude_mes",
        )
    with col2:
        cats_do_mes = sorted(resumo[mes_sel].keys()) if mes_sel else []
        cat_default_idx = 0
        try:
            qs = st.query_params  # type: ignore[attr-defined]
            cat_qs = qs.get("completude_cat")
            if cat_qs and cat_qs in cats_do_mes:
                cat_default_idx = cats_do_mes.index(cat_qs)
        except Exception:
            pass
        cat_sel = (
            st.selectbox(
                "Categoria",
                cats_do_mes,
                index=cat_default_idx,
                key="completude_cat",
            )
            if cats_do_mes
            else None
        )
    if mes_sel and cat_sel:
        info = resumo[mes_sel][cat_sel]
        st.caption(
            f"{info['com_doc']} de {info['total']} transações com "
            f"comprovante em {mes_sel} / {cat_sel}"
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


# "Cada mês sem comprovante é um lembrete para agir." -- princípio Sprint 75
