"""Cluster Bem-estar · aba "Humor" (UX-RD-17).

Heatmap calendário 13 colunas × 7 linhas (91 dias) que consome o cache
JSON gerado por :func:`gerar_humor_heatmap` e renderiza em três modos:

* ``pessoa_a`` único.
* ``pessoa_b`` único.
* ``ambos`` -- overlay diagonal 50% (mockup 18).

Stats dos últimos 30 dias (média, registros, melhor, pior) ficam na
coluna direita. Detalhe ao clicar em um dia é resolvido por
``st.selectbox`` -- ao selecionar uma data válida, mostra os
4 valores (humor/energia/ansiedade/foco) das pessoas A e B.

Lições UX-RD aplicadas: HTML via :func:`minificar`, fallback graceful
quando o cache não existe, contrato uniforme
``renderizar(dados, periodo, pessoa, ctx)``.  # noqa: accent
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.heatmap_humor import (
    cor_para_humor,
    gerar_estilos_heatmap,
    gerar_heatmap_html,
    gerar_legenda_html,
)
from src.dashboard.componentes.html_utils import minificar
from src.dashboard.componentes.page_header import renderizar_page_header
from src.dashboard.componentes.ui import (
    callout_html,
    carregar_css_pagina,
    kpi_card,
    sparkline_html,
    sync_indicator_html,
)
from src.mobile_cache.humor_heatmap import gerar_humor_heatmap
from src.mobile_cache.varrer_vault import descobrir_vault_root

PERIODO_HEATMAP_DIAS: int = 91


def renderizar(  # noqa: accent
    dados: dict[str, pd.DataFrame],
    periodo: str,  # noqa: accent
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Humor (UX-T-18)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes

    renderizar_grupo_acoes(
        [
            {"label": "Exportar 90d", "glyph": "download", "title": "CSV de humor 91 dias"},
            {
                "label": "Registrar agora",
                "primary": True,
                "glyph": "plus",
                "href": "?cluster=Bem-estar&tab=Hoje",
                "title": "Voltar para Hoje e registrar humor",
            },
        ]
    )

    del dados, periodo, ctx  # noqa: accent

    st.markdown(gerar_estilos_heatmap(), unsafe_allow_html=True)
    st.markdown(minificar(carregar_css_pagina("be_humor")), unsafe_allow_html=True)

    hoje = date.today()
    vault_root = descobrir_vault_root()

    payload = _carregar_payload_heatmap(vault_root)
    items = payload.get("celulas", []) if payload else []
    stats_payload = payload.get("estatisticas", {}) if payload else {}

    st.markdown(_page_header_canonico(len(items)), unsafe_allow_html=True)
    # UX-V-04: indicador de observabilidade sync vault -> cache -> dashboard.
    st.markdown(
        f'<div class="sync-indicator-wrapper">{sync_indicator_html()}</div>',
        unsafe_allow_html=True,
    )

    if vault_root is None:
        st.markdown(
            callout_html(
                "warning",
                (
                    "Vault Bem-estar não encontrado. Configure OUROBOROS_VAULT "
                    "para visualizar o heatmap de humor."
                ),
            ),
            unsafe_allow_html=True,
        )
        return

    if not payload or not payload.get("celulas"):
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )

        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(13,1fr);'
            'gap:3px;margin-bottom:12px;">'
            + "".join(
                '<span class="skel-bloco" style="height:18px;min-width:0;'
                'border-radius:3px;"></span>'
                for _ in range(13 * 7)
            )
            + "</div>"
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:8px;">'
            '<div class="kpi"><span class="kpi-label">MÉDIA</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">DIAS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">PICO</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">VALE</span>'
            '<span class="kpi-value">--</span></div>'
            "</div>"
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="HUMOR · sem registros ainda",
                descricao=(  # noqa: accent
                    "Cada registro de humor no app mobile vira uma célula "
                    "colorida no heatmap de 13 semanas acima. Capture rápido "
                    "(<30s) na aba <code>Hoje</code> do app e a curva começa "
                    "a aparecer aqui após o próximo sync."
                ),
                skeleton_html=skeleton,
                cta_secao="humor",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    coluna_esq, coluna_dir = st.columns([1.8, 1])

    pessoa_default = pessoa if pessoa in {"pessoa_a", "pessoa_b"} else "ambos"

    with coluna_esq:
        modo = st.radio(
            "Modo de visualização",
            options=["pessoa_a", "pessoa_b", "ambos"],
            index=["pessoa_a", "pessoa_b", "ambos"].index(pessoa_default),
            horizontal=True,
            format_func=lambda v: {
                "pessoa_a": "Pessoa A",
                "pessoa_b": "Pessoa B",
                "ambos": "Sobreposto (50% A + 50% B)",
            }[v],
            key="be_humor_modo",
        )

        st.markdown(
            gerar_heatmap_html(
                items,
                pessoa=modo,
                periodo_dias=PERIODO_HEATMAP_DIAS,
                hoje=hoje,
            ),
            unsafe_allow_html=True,
        )
        st.markdown(gerar_legenda_html(), unsafe_allow_html=True)

        _renderizar_detalhe_dia(items, hoje)

    with coluna_dir:
        _renderizar_stats(items, stats_payload, hoje, modo)


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------


def _page_header_canonico(qtd_celulas: int) -> str:
    """Page-header canônico via UX-M-02 (substitui markup local)."""
    return renderizar_page_header(
        titulo="BEM-ESTAR · HUMOR",
        subtitulo=(
            "Heatmap 13×7 lê .ouroboros/cache/humor-heatmap.json gerado por "
            "mobile_cache.humor_heatmap. Modo Pessoa A, Pessoa B ou "
            "sobreposto. Célula vazia significa sem registro."
        ),
        sprint_tag="UX-RD-17",
        pills=[{"texto": f"{qtd_celulas} células", "tipo": "d7-graduado"}],
    )


# ---------------------------------------------------------------------------
# Cache loader
# ---------------------------------------------------------------------------


def _carregar_payload_heatmap(vault_root: Path | None) -> dict[str, Any] | None:
    """Lê ``<vault>/.ouroboros/cache/humor-heatmap.json``.

    Se o arquivo não existir, tenta gerá-lo on-the-fly antes de
    desistir (graceful, mas não-mascarador: se o vault realmente não
    tem dailies, ``items`` virá vazio e a UI mostra fallback).
    """
    if vault_root is None:
        return None
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        try:
            gerar_humor_heatmap(vault_root)
        except OSError:
            return None
    if not arquivo.exists():
        return None
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# Stats coluna direita
# ---------------------------------------------------------------------------


def _renderizar_stats(
    items: list[dict[str, Any]],
    stats_payload: dict[str, Any],
    hoje: date,
    modo: str,
) -> None:
    pessoa_foco = "pessoa_a" if modo == "ambos" else modo
    stats_pessoa = stats_payload.get(pessoa_foco, {}) or {}

    media_30d = stats_pessoa.get("media_humor_30d", 0.0)
    registros_30d = stats_pessoa.get("registros_30d", 0)

    melhor, pior = _melhor_pior_30d(items, hoje, pessoa_foco)
    serie_30d = _serie_humor_30d(items, hoje, pessoa_foco)
    media_anterior = _media_humor_30d_anteriores(items, hoje, pessoa_foco)
    streak_atual, streak_recorde = _streak_humor_alto(items, hoje, pessoa_foco)

    st.markdown(
        _card_media_humor_html(
            media_30d=float(media_30d),
            media_anterior=media_anterior,
            serie=serie_30d,
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        kpi_card(
            "registros · 30 dias",
            f"{registros_30d}/30",
            accent="cyan",
        ),
        unsafe_allow_html=True,
    )
    col_melhor, col_pior = st.columns(2)
    with col_melhor:
        st.markdown(
            kpi_card(
                "melhor",
                f"{melhor}/5" if melhor else "—",
                accent="green",
            ),
            unsafe_allow_html=True,
        )
    with col_pior:
        st.markdown(
            kpi_card(
                "pior",
                f"{pior}/5" if pior else "—",
                accent="red",
            ),
            unsafe_allow_html=True,
        )
    st.markdown(
        _card_streak_humor_html(
            streak_atual=streak_atual,
            streak_recorde=streak_recorde,
        ),
        unsafe_allow_html=True,
    )


def _melhor_pior_30d(
    items: list[dict[str, Any]],
    hoje: date,
    pessoa: str,
) -> tuple[int, int]:
    """Devolve ``(melhor, pior)`` humor nos últimos 30 dias para ``pessoa``."""
    limite = hoje - timedelta(days=29)
    valores: list[int] = []
    for it in items:
        if it.get("autor") != pessoa:
            continue
        data_iso = it.get("data")
        if not isinstance(data_iso, str):
            continue
        try:
            d_obj = date.fromisoformat(data_iso)
        except ValueError:
            continue
        if not (limite <= d_obj <= hoje):
            continue
        humor = it.get("humor")
        if isinstance(humor, int) and 1 <= humor <= 5:
            valores.append(humor)
    if not valores:
        return 0, 0
    return max(valores), min(valores)


def _serie_humor_30d(
    items: list[dict[str, Any]],
    hoje: date,
    pessoa: str,
) -> list[float]:
    """Série cronológica de humor (1..5) nos últimos 30 dias para ``pessoa``.

    Retorna lista ordenada por data ASC. Dias sem registro são omitidos
    (sparkline desenha apenas pontos com dado, sem chutar interpolação).
    """
    limite = hoje - timedelta(days=29)
    pontos: list[tuple[date, int]] = []
    for it in items:
        if it.get("autor") != pessoa:
            continue
        data_iso = it.get("data")
        if not isinstance(data_iso, str):
            continue
        try:
            d_obj = date.fromisoformat(data_iso)
        except ValueError:
            continue
        if not (limite <= d_obj <= hoje):
            continue
        humor = it.get("humor")
        if isinstance(humor, int) and 1 <= humor <= 5:
            pontos.append((d_obj, humor))
    pontos.sort(key=lambda p: p[0])
    return [float(v) for _, v in pontos]


def _media_humor_30d_anteriores(
    items: list[dict[str, Any]],
    hoje: date,
    pessoa: str,
) -> float | None:
    """Média de humor da janela [-60d, -30d) para comparar com a janela atual.

    Retorna ``None`` quando a janela anterior está vazia (não há base de
    comparação, evita delta enganoso).
    """
    inicio_anterior = hoje - timedelta(days=59)
    fim_anterior = hoje - timedelta(days=30)
    valores: list[int] = []
    for it in items:
        if it.get("autor") != pessoa:
            continue
        data_iso = it.get("data")
        if not isinstance(data_iso, str):
            continue
        try:
            d_obj = date.fromisoformat(data_iso)
        except ValueError:
            continue
        if not (inicio_anterior <= d_obj <= fim_anterior):
            continue
        humor = it.get("humor")
        if isinstance(humor, int) and 1 <= humor <= 5:
            valores.append(humor)
    if not valores:
        return None
    return sum(valores) / len(valores)


def _streak_humor_alto(
    items: list[dict[str, Any]],
    hoje: date,
    pessoa: str,
    limiar: int = 4,
) -> tuple[int, int]:
    """Conta dias consecutivos com humor >= ``limiar`` na janela 30d.

    Devolve ``(streak_atual, streak_recorde)``. ``streak_atual`` é a
    sequência ativa terminando em ``hoje``; ``streak_recorde`` é a maior
    sequência da janela de 30 dias.
    """
    limite = hoje - timedelta(days=29)
    por_data: dict[date, int] = {}
    for it in items:
        if it.get("autor") != pessoa:
            continue
        data_iso = it.get("data")
        if not isinstance(data_iso, str):
            continue
        try:
            d_obj = date.fromisoformat(data_iso)
        except ValueError:
            continue
        if not (limite <= d_obj <= hoje):
            continue
        humor = it.get("humor")
        if isinstance(humor, int) and 1 <= humor <= 5:
            por_data[d_obj] = humor

    streak_recorde = 0
    streak_atual = 0
    sequencia = 0
    dia_iter = limite
    while dia_iter <= hoje:
        humor = por_data.get(dia_iter)
        if humor is not None and humor >= limiar:
            sequencia += 1
            streak_recorde = max(streak_recorde, sequencia)
        else:
            sequencia = 0
        dia_iter = dia_iter + timedelta(days=1)
    # Streak ativa: conta para trás a partir de hoje.
    dia_iter = hoje
    while dia_iter >= limite:
        humor = por_data.get(dia_iter)
        if humor is None or humor < limiar:
            break
        streak_atual += 1
        dia_iter = dia_iter - timedelta(days=1)
    return streak_atual, streak_recorde


# ---------------------------------------------------------------------------
# Cards customizados (sparkline + delta + streak)
# ---------------------------------------------------------------------------


def _formatar_delta_humor(delta: float | None) -> tuple[str, str]:
    """Texto + classe CSS para delta de média de humor.

    ``None`` retorna ``("sem base anterior", "humor-delta-flat")``.
    """
    if delta is None:
        return ("sem base anterior", "humor-delta-flat")
    if abs(delta) < 0.05:
        return ("estável vs 30d anteriores", "humor-delta-flat")
    sinal = "↗" if delta > 0 else "↘"
    classe = "humor-delta-up" if delta > 0 else "humor-delta-down"
    valor = f"{delta:+.2f}".replace("-", "−")
    return (f"{sinal} {valor} vs 30d anteriores", classe)


def _card_media_humor_html(
    media_30d: float,
    media_anterior: float | None,
    serie: list[float],
) -> str:
    """Card MÉDIA 30 DIAS com valor, delta e sparkline embutido (UX-V-3.6).

    ``serie`` com <2 pontos suprime sparkline (degradação graciosa).
    """
    if media_30d:
        valor_html = (
            f'<span class="humor-card-valor-num">{media_30d:.2f}</span>'
            f'<span class="humor-card-valor-unid">/5</span>'
        )
    else:
        valor_html = '<span class="humor-card-valor-vazio">—</span>'

    delta = media_30d - media_anterior if (media_anterior is not None and media_30d) else None
    delta_txt, delta_cls = _formatar_delta_humor(delta)

    spark = (
        sparkline_html(
            serie,
            cor="var(--accent-purple)",
            largura=240,
            altura=38,
        )
        if len(serie) >= 2
        else ""
    )
    spark_block = f'<div class="humor-card-spark">{spark}</div>' if spark else ""
    return minificar(
        f'<div class="humor-card humor-card-media">'
        f'<div class="humor-card-label">média 30 dias</div>'
        f'<div class="humor-card-valor">{valor_html}</div>'
        f'<div class="humor-card-delta {delta_cls}">{delta_txt}</div>'
        f"{spark_block}"
        f"</div>"
    )


def _card_streak_humor_html(
    streak_atual: int,
    streak_recorde: int,
) -> str:
    """Card STREAK HUMOR ≥ 4 com valor + recorde da janela 30d (UX-V-3.6)."""
    if streak_recorde:
        valor_html = (
            f'<span class="humor-card-valor-num">{streak_recorde}</span>'
            f'<span class="humor-card-valor-unid">'
            f" dia{'s' if streak_recorde != 1 else ''}"
            f"</span>"
        )
    else:
        valor_html = '<span class="humor-card-valor-vazio">—</span>'

    if streak_atual > 0:
        sub = (
            f"sequência ativa: {streak_atual} "
            f"dia{'s' if streak_atual != 1 else ''} · "
            f"recorde da janela 30d"
        )
    else:
        sub = "recorde da janela 30d"

    return minificar(
        f'<div class="humor-card humor-card-streak">'
        f'<div class="humor-card-label">streak humor ≥ 4</div>'
        f'<div class="humor-card-valor">{valor_html}</div>'
        f'<div class="humor-card-delta humor-delta-flat">{sub}</div>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Detalhe do dia
# ---------------------------------------------------------------------------


def _renderizar_detalhe_dia(
    items: list[dict[str, Any]],
    hoje: date,
) -> None:
    """Selectbox de data com detalhe (humor/energia/ansiedade/foco) por pessoa."""
    datas_disponiveis = sorted(
        {it["data"] for it in items if isinstance(it.get("data"), str)},
        reverse=True,
    )
    if not datas_disponiveis:
        return

    with st.expander("Detalhe do dia", expanded=False):
        escolhida = st.selectbox(
            "Selecionar dia",
            options=datas_disponiveis,
            key="be_humor_detalhe_dia",
        )

        registros_dia = [it for it in items if it.get("data") == escolhida]
        if not registros_dia:
            st.info("Nenhum registro nesse dia.")
            return

        for reg in registros_dia:
            autor = reg.get("autor", "—")
            humor = reg.get("humor")
            energia = reg.get("energia")
            ansiedade = reg.get("ansiedade")
            foco = reg.get("foco")
            cor_humor_hex = cor_para_humor(humor)
            st.markdown(
                minificar(
                    f"""
                    <div class="detalhe-pessoa-card">
                      <div class="detalhe-pessoa-head">
                        <span class="detalhe-pessoa-nome">{autor}</span>
                        <span class="detalhe-pessoa-dia">{escolhida}</span>
                      </div>
                      <div class="detalhe-pessoa-grid">
                        <div><div class="l">humor</div>
                          <div class="v" style="color:{cor_humor_hex};">{humor}/5</div>
                        </div>
                        <div><div class="l">energia</div>
                          <div class="v">{energia}/5</div>
                        </div>
                        <div><div class="l">ansiedade</div>
                          <div class="v">{ansiedade}/5</div>
                        </div>
                        <div><div class="l">foco</div>
                          <div class="v">{foco}/5</div>
                        </div>
                      </div>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# CSS local
# ---------------------------------------------------------------------------


# CSS dedicado: src/dashboard/css/paginas/be_humor.css (UX-M-02.D residual).
# "Conhece-te a ti mesmo." -- Sócrates
