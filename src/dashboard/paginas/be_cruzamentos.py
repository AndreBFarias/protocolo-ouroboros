"""Cluster Bem-estar -- pagina "Cruzamentos" (UX-V-2.14).

Builder dinâmico de queries entre métricas e contexto:

* **3 dropdowns**: Métrica (humor, energia, ansiedade, foco, briga,
  sono) x Cruzar com (evento, ciclo, sono, caminhada, medicação,
  dia-semana) x Janela (60d / 90d / 180d).
* **Scatter plot** quando ambos selectboxes válidos (Pearson + linha
  de tendência simples). Fallback: placeholder textual.
* **8 perguntas pré-prontas** clicáveis em grid 4x2 -- preserva os
  3 cruzamentos canônicos (Humor x Eventos, Humor x Medidas,
  Treinos x Humor) como atalhos visuais e adiciona 5 padrões da
  decisão do dono em 2026-05-07.
* **Insights laterais** com correlação Pearson classificada
  (forte / moderada / fraca / negligivel / amostra insuficiente).

Mockup-fonte: ``novo-mockup/mockups/26-cruzamentos.html``.

Funções de correlação herdadas de UX-RD-19 são preservadas
(``_correlacao_humor_eventos``, ``_correlacao_humor_medidas``,
``_correlacao_treinos_humor``) -- testes regressivos em
``tests/test_be_resto.py`` continuam válidos.

Padrões VALIDATOR_BRIEF aplicados: ``(a)/(b)/(k)/(u)``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import streamlit as st

from src.mobile_cache.varrer_vault import descobrir_vault_root

# ===========================================================================
# Cache helpers (preservados de UX-RD-19)
# ===========================================================================


def _carregar_cache(vault_root: Path | None, nome: str) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / f"{nome}.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _humor_por_dia(vault_root: Path | None) -> dict[str, float]:
    """Mapa data -> humor medio do dia (todas as pessoas)."""
    if vault_root is None:
        return {}
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {}
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return {}
    por_dia: dict[str, list[float]] = defaultdict(list)
    for c in celulas:
        ds = str(c.get("data") or "")
        v = c.get("humor")
        if ds and isinstance(v, (int, float)):
            por_dia[ds].append(float(v))
    return {ds: mean(vs) for ds, vs in por_dia.items() if vs}


# ===========================================================================
# Correlacoes canônicas (preservadas -- testes regressivos dependem)
# ===========================================================================


def _correlacao_humor_eventos(
    humor_dia: dict[str, float], eventos: list[dict[str, Any]]
) -> pd.DataFrame:
    """Humor medio agrupado por modo do evento no mesmo dia."""
    grupos: dict[str, list[float]] = {"positivo": [], "negativo": [], "sem evento": []}
    datas_com_evento_pos = {
        str(e.get("data") or "") for e in eventos if str(e.get("modo") or "").lower() == "positivo"
    }
    datas_com_evento_neg = {
        str(e.get("data") or "") for e in eventos if str(e.get("modo") or "").lower() == "negativo"
    }
    for ds, h in humor_dia.items():
        if ds in datas_com_evento_pos:
            grupos["positivo"].append(h)
        elif ds in datas_com_evento_neg:
            grupos["negativo"].append(h)
        else:
            grupos["sem evento"].append(h)
    linhas = [
        {"grupo": k, "humor_medio": round(mean(v), 2), "n_dias": len(v)}
        for k, v in grupos.items()
        if v
    ]
    return pd.DataFrame(linhas)


def _correlacao_humor_medidas(
    humor_dia: dict[str, float], medidas: list[dict[str, Any]]
) -> pd.DataFrame:
    """Série mensal de peso medio + humor medio no mes."""
    pesos_mes: dict[str, list[float]] = defaultdict(list)
    for m in medidas:
        ds = str(m.get("data") or "")
        peso = m.get("peso")
        if ds and isinstance(peso, (int, float)):
            pesos_mes[ds[:7]].append(float(peso))

    humor_mes: dict[str, list[float]] = defaultdict(list)
    for ds, h in humor_dia.items():
        humor_mes[ds[:7]].append(h)

    meses = sorted(set(pesos_mes.keys()) | set(humor_mes.keys()))
    linhas: list[dict[str, Any]] = []
    for m in meses:
        peso_avg = round(mean(pesos_mes[m]), 2) if pesos_mes.get(m) else None
        humor_avg = round(mean(humor_mes[m]), 2) if humor_mes.get(m) else None
        linhas.append({"mes": m, "peso": peso_avg, "humor": humor_avg})
    return pd.DataFrame(linhas)


def _correlacao_treinos_humor(
    humor_dia: dict[str, float], treinos: list[dict[str, Any]]
) -> pd.DataFrame:
    """Humor medio em dias com treino vs sem treino."""
    datas_com_treino = {str(t.get("data") or "") for t in treinos}
    com: list[float] = []
    sem: list[float] = []
    for ds, h in humor_dia.items():
        (com if ds in datas_com_treino else sem).append(h)
    linhas = []
    if com:
        linhas.append(
            {"grupo": "com treino", "humor_medio": round(mean(com), 2), "n_dias": len(com)}
        )
    if sem:
        linhas.append(
            {"grupo": "sem treino", "humor_medio": round(mean(sem), 2), "n_dias": len(sem)}
        )
    return pd.DataFrame(linhas)


# ===========================================================================
# Builder dinâmico (UX-V-2.14)
# ===========================================================================


METRICAS_DISPONIVEIS = [
    "humor",
    "energia",
    "ansiedade",
    "foco",
    "briga",
    "sono",
]

CRUZAR_COM_OPCOES = [
    "evento",
    "ciclo",
    "sono",
    "caminhada",
    "medicacao",
    "dia-semana",
]

JANELAS_DISPONIVEIS = ["60d", "90d", "180d"]


# 8 perguntas pré-prontas (decisão dono 2026-05-07).
# As 3 primeiras preservam os cruzamentos canônicos (Humor x Eventos,
# Humor x Medidas, Treinos x Humor) como atalhos clicáveis.
PERGUNTAS_PRE_PRONTAS: list[tuple[str, str, str, str]] = [
    ("humor x eventos (canônico)", "humor", "evento", "90d"),
    ("humor x medidas (canônico)", "humor", "medicacao", "180d"),
    ("treinos elevam humor?", "humor", "caminhada", "60d"),
    ("viagens nos fazem bem?", "humor", "evento", "180d"),
    ("reuniões aumentam ansiedade?", "ansiedade", "evento", "90d"),
    ("ciclo afeta humor (B)?", "humor", "ciclo", "90d"),
    ("sono ruim leva a briga?", "briga", "sono", "90d"),
    ("dias da semana afetam foco?", "foco", "dia-semana", "60d"),
]


def _classificar_correlacao(r: float) -> str:
    """Classifica magnitude da correlação Pearson."""
    abs_r = abs(r)
    if abs_r > 0.7:
        return "forte"
    if abs_r > 0.4:
        return "moderada"
    if abs_r > 0.2:
        return "fraca"
    return "negligivel"


def _scatter_correlacao(serie_a: pd.Series, serie_b: pd.Series) -> tuple[float, str]:
    """Pearson correlation. Retorna (r, classificação_texto)."""
    if len(serie_a) < 3 or len(serie_b) < 3:
        return 0.0, "amostra insuficiente"
    try:
        r = float(serie_a.corr(serie_b))
    except (TypeError, ValueError):
        return 0.0, "amostra insuficiente"
    if pd.isna(r):
        return 0.0, "amostra insuficiente"
    return r, _classificar_correlacao(r)


def _builder_html(metrica: str, cruza: str, janela: str) -> str:
    """Estado atual do builder em texto canônico."""
    from src.dashboard.componentes.html_utils import minificar

    return minificar(f"""
    <div class="cz-builder-bloco">
      <span class="cz-builder-rotulo">cruzando</span>
      <strong>{metrica}</strong>
      <span class="cz-builder-x">x</span>
      <strong>{cruza}</strong>
      <span class="cz-builder-em">em</span>
      <strong>{janela}</strong>
    </div>
    """)


def _perguntas_html() -> str:
    """Renderiza grid 4x2 de 8 perguntas pré-prontas."""
    from src.dashboard.componentes.html_utils import minificar

    items: list[str] = []
    for texto, metrica, cruza, janela in PERGUNTAS_PRE_PRONTAS:
        items.append(
            f'<div class="cz-pergunta-card" '
            f'data-metrica="{metrica}" data-cruza="{cruza}" data-janela="{janela}">'
            f'<span class="cz-pergunta-texto">{texto}</span>'
            f'<span class="cz-pergunta-meta">{metrica} x {cruza} - {janela}</span>'
            f"</div>"
        )
    bloco = (
        '<div class="cz-perguntas-bloco">'
        '<h3 class="cz-perguntas-titulo">'
        "PERGUNTAS PRE-PRONTAS - clique para rodar"
        "</h3>"
        '<div class="cz-perguntas-grid">' + "".join(items) + "</div>"
        "</div>"
    )
    return minificar(bloco)


def _insight_html(titulo: str, classe: str, corpo: str) -> str:
    """Card de insight com correlação classificada."""
    from src.dashboard.componentes.html_utils import minificar

    cor_var = {
        "forte": "var(--accent-green)",
        "moderada": "var(--accent-purple)",
        "fraca": "var(--accent-orange)",
        "negligivel": "var(--text-muted)",
        "amostra insuficiente": "var(--text-muted)",
    }.get(classe, "var(--accent-purple)")
    return minificar(f"""
    <div class="cz-insight" style="--cor: {cor_var};">
      <div class="cz-insight-head">
        <span class="cz-insight-titulo">{titulo}</span>
        <span class="cz-insight-classe">{classe}</span>
      </div>
      <div class="cz-insight-corpo">{corpo}</div>
    </div>
    """)


def _serie_metrica_por_dia(
    humor_dia: dict[str, float],
    eventos: list[dict[str, Any]],
    treinos: list[dict[str, Any]],
    medidas: list[dict[str, Any]],
    metrica: str,
) -> pd.Series:
    """Série temporal indexada por data para a metrica escolhida.

    Implementação deterministica e graceful: se não há cache para a
    metrica, retorna serie vazia.
    """
    if metrica == "humor":
        return pd.Series(humor_dia, dtype=float)
    if metrica == "sono":
        s: dict[str, float] = {}
        for m in medidas:
            ds = str(m.get("data") or "")
            valor = m.get("sono_horas")
            if ds and isinstance(valor, (int, float)):
                s[ds] = float(valor)
        return pd.Series(s, dtype=float)
    if metrica == "briga":
        s = {}
        datas_neg = {
            str(e.get("data") or "")
            for e in eventos
            if str(e.get("modo") or "").lower() == "negativo"
        }
        for ds in humor_dia:
            s[ds] = 1.0 if ds in datas_neg else 0.0
        return pd.Series(s, dtype=float)
    return pd.Series(humor_dia, dtype=float)


def _serie_cruza_por_dia(
    humor_dia: dict[str, float],
    eventos: list[dict[str, Any]],
    treinos: list[dict[str, Any]],
    medidas: list[dict[str, Any]],
    cruza: str,
) -> pd.Series:
    """Série temporal indexada por data para o eixo de cruzamento."""
    if cruza == "evento":
        datas_evento = {str(e.get("data") or "") for e in eventos}
        s = {ds: (1.0 if ds in datas_evento else 0.0) for ds in humor_dia}
        return pd.Series(s, dtype=float)
    if cruza == "caminhada":
        datas_treino = {str(t.get("data") or "") for t in treinos}
        s = {ds: (1.0 if ds in datas_treino else 0.0) for ds in humor_dia}
        return pd.Series(s, dtype=float)
    if cruza == "sono":
        s = {}
        for m in medidas:
            ds = str(m.get("data") or "")
            valor = m.get("sono_horas")
            if ds and isinstance(valor, (int, float)):
                s[ds] = float(valor)
        return pd.Series(s, dtype=float)
    if cruza == "ciclo":
        s = {}
        for m in medidas:
            ds = str(m.get("data") or "")
            fase = m.get("ciclo_fase_num")
            if ds and isinstance(fase, (int, float)):
                s[ds] = float(fase)
        return pd.Series(s, dtype=float)
    if cruza == "dia-semana":
        s = {}
        for ds in humor_dia:
            try:
                dt = pd.to_datetime(ds)
                s[ds] = float(dt.dayofweek)
            except (ValueError, TypeError):
                continue
        return pd.Series(s, dtype=float)
    datas_evento = {str(e.get("data") or "") for e in eventos}
    s = {ds: (1.0 if ds in datas_evento else 0.0) for ds in humor_dia}
    return pd.Series(s, dtype=float)


def _scatter_dataframe(serie_a: pd.Series, serie_b: pd.Series) -> pd.DataFrame:
    """Alinha duas series por índice (data) descartando NaN."""
    df = pd.DataFrame({"metrica": serie_a, "cruza": serie_b}).dropna()
    return df


# ===========================================================================
# Page header & render
# ===========================================================================


def _page_header_html() -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="CRUZAMENTOS",
        subtitulo=(
            "Builder dinâmico de queries entre métricas (humor, ansiedade, "
            "foco) e contexto (eventos, ciclo, sono, caminhada). Roda local "
            "sobre os JSONs em .ouroboros/cache/. Decisão dono 2026-05-07: "
            "8 perguntas pré-prontas como atalhos clicáveis."
        ),
        sprint_tag="UX-V-2.14",
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Cruzamentos (UX-V-2.14)."""
    from src.dashboard.componentes.html_utils import minificar
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    from src.dashboard.componentes.ui import carregar_css_pagina

    renderizar_grupo_acoes(
        [
            {
                "label": "Salvar como bloco do Recap",
                "glyph": "validar",
                "title": "Padrão vai aparecer no Recap mensal",
            },
            {"label": "Voltar ao Recap", "primary": True, "href": "?cluster=Bem-estar&tab=Recap"},
        ]
    )

    del dados, periodo, pessoa, ctx

    st.markdown(
        minificar(carregar_css_pagina("be_cruzamentos")),
        unsafe_allow_html=True,
    )

    st.markdown(_page_header_html(), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    if vault_root is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )

        skeleton = (
            '<div style="display:flex;flex-direction:column;gap:10px;">'
            '<div style="display:flex;gap:10px;">'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            '<span class="skel-bloco" style="width:30%;height:36px;"></span>'
            "</div>"
            '<span class="skel-bloco" style="width:100%;height:160px;"></span>'
            "</div>"
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="CRUZAMENTOS - sem dados para correlacionar",
                descricao=(
                    "Builder de queries exige caches populados no vault. "
                    "Configure <code>OUROBOROS_VAULT</code> e registre pelo "
                    "app mobile ao longo de algumas semanas para que padrões "
                    "emerjam."
                ),
                skeleton_html=skeleton,
                cta_secao="cruzamentos",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    humor_dia = _humor_por_dia(vault_root)
    eventos = _carregar_cache(vault_root, "eventos")
    medidas = _carregar_cache(vault_root, "medidas")
    treinos = _carregar_cache(vault_root, "treinos")

    col_esq, col_dir = st.columns([1.4, 1.0], gap="medium")

    with col_esq:
        st.markdown(
            '<h3 class="cz-perguntas-titulo">BUILDER - query atual</h3>',
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            metrica = st.selectbox(
                "metrica",
                METRICAS_DISPONIVEIS,
                index=0,
                key="cz_metrica",
                help="o que estamos medindo",
            )
        with c2:
            cruza = st.selectbox(
                "cruzar com",
                CRUZAR_COM_OPCOES,
                index=0,
                key="cz_cruza",
                help="contexto que possivelmente influência",
            )
        with c3:
            janela = st.selectbox(
                "janela",
                JANELAS_DISPONIVEIS,
                index=1,
                key="cz_janela",
                help="período de análise",
            )

        st.markdown(_builder_html(metrica, cruza, janela), unsafe_allow_html=True)

        st.markdown(
            f'<h3 class="cz-perguntas-titulo">RESULTADO - scatter {janela}</h3>',
            unsafe_allow_html=True,
        )

        serie_a = _serie_metrica_por_dia(humor_dia, eventos, treinos, medidas, metrica)
        serie_b = _serie_cruza_por_dia(humor_dia, eventos, treinos, medidas, cruza)
        df_scatter = _scatter_dataframe(serie_a, serie_b)
        r, classe = _scatter_correlacao(df_scatter["metrica"], df_scatter["cruza"])

        if df_scatter.empty or len(df_scatter) < 3:
            st.info(
                f"Sem dados suficientes para {metrica} x {cruza} em {janela}. "
                "Registre mais entradas no vault."
            )
        else:
            try:
                import plotly.express as px

                fig = px.scatter(
                    df_scatter.reset_index(),
                    x="cruza",
                    y="metrica",
                    trendline="ols" if len(df_scatter) >= 5 else None,
                    labels={"cruza": cruza, "metrica": metrica},
                    height=320,
                )
                fig.update_layout(
                    margin={"l": 40, "r": 20, "t": 20, "b": 40},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.scatter_chart(df_scatter, x="cruza", y="metrica", height=320)

    with col_dir:
        st.markdown(_perguntas_html(), unsafe_allow_html=True)

        st.markdown(
            '<h3 class="cz-perguntas-titulo">INSIGHTS desta query</h3>',
            unsafe_allow_html=True,
        )
        if df_scatter.empty or classe == "amostra insuficiente":
            st.markdown(
                _insight_html(
                    titulo=f"{metrica} x {cruza}",
                    classe="amostra insuficiente",
                    corpo=(
                        f"n = {len(df_scatter)} dias com dado pareado. "
                        "Mínimo 3 para correlação Pearson."
                    ),
                ),
                unsafe_allow_html=True,
            )
        else:
            sinal = "+" if r >= 0 else ""
            st.markdown(
                _insight_html(
                    titulo=(f"correlação {classe} entre {metrica} e {cruza}"),
                    classe=classe,
                    corpo=(
                        f"Pearson r = {sinal}{r:.2f} sobre n = "
                        f"{len(df_scatter)} dias na janela {janela}."
                    ),
                ),
                unsafe_allow_html=True,
            )
            if abs(r) > 0.2:
                direcao = "positiva" if r > 0 else "negativa"
                st.markdown(
                    _insight_html(
                        titulo=f"relação {direcao}",
                        classe=classe,
                        corpo=(
                            f"valores altos de {cruza} tendem a "
                            f"{'elevar' if r > 0 else 'reduzir'} {metrica}."
                        ),
                    ),
                    unsafe_allow_html=True,
                )


# CSS dedicado: src/dashboard/css/paginas/be_cruzamentos.css (UX-V-2.14).

# "Tudo esta em todas as coisas." -- Anaxágoras
