"""Cluster Bem-estar -- página "Recap" (UX-RD-19).

Resumo agregado dos últimos 7/30/90 dias com métricas determinísticas
calculadas sobre os caches Bem-estar (humor, eventos, treinos, medidas).
Sem LLM: ADR-13 proíbe API programática neste projeto, então a
"narrativa" do mockup vira um conjunto de KPIs + mini-charts honestos
sobre os dados reais do vault.

Mockup-fonte: ``novo-mockup/mockups/21-recap.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: vault ausente vira aviso, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

_PERIODOS_LABEL = {"7 dias": 7, "30 dias": 30, "90 dias": 90}


def _carregar_cache(vault_root: Path | None, nome: str) -> list[dict[str, Any]]:
    """Lê ``<vault>/.ouroboros/cache/<nome>.json`` retornando ``items``."""
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


def _filtrar_periodo(
    items: list[dict[str, Any]], dias: int, hoje: date
) -> list[dict[str, Any]]:
    limite = hoje - timedelta(days=dias - 1)
    saida: list[dict[str, Any]] = []
    for it in items:
        ds = str(it.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if limite <= d <= hoje:
            saida.append(it)
    return saida


def _agregados_humor(vault_root: Path | None, dias: int, hoje: date) -> dict[str, Any]:
    """Lê humor-heatmap.json e calcula média/qtd/melhor/pior do período."""
    if vault_root is None:
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    limite = hoje - timedelta(days=dias - 1)
    valores: list[float] = []
    for c in celulas:
        ds = str(c.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if not (limite <= d <= hoje):
            continue
        v = c.get("humor")
        if isinstance(v, (int, float)):
            valores.append(float(v))
    if not valores:
        return {"media": None, "qtd": 0, "melhor": None, "pior": None}
    return {
        "media": round(mean(valores), 2),
        "qtd": len(valores),
        "melhor": max(valores),
        "pior": min(valores),
    }


def _agregados_eventos(items: list[dict[str, Any]]) -> dict[str, Any]:
    pos = sum(1 for it in items if str(it.get("modo") or "").lower() == "positivo")
    neg = sum(1 for it in items if str(it.get("modo") or "").lower() == "negativo")
    bairros = Counter(
        str(it.get("bairro") or "").strip()
        for it in items
        if str(it.get("bairro") or "").strip()
    )
    return {
        "qtd": len(items),
        "positivos": pos,
        "negativos": neg,
        "top_bairros": bairros.most_common(3),
    }


def _agregados_treinos(items: list[dict[str, Any]]) -> dict[str, Any]:
    rotinas = Counter(
        str(it.get("rotina") or "").strip()
        for it in items
        if str(it.get("rotina") or "").strip()
    )
    duracoes = [
        float(it["duracao_min"])
        for it in items
        if isinstance(it.get("duracao_min"), (int, float))
    ]
    return {
        "qtd": len(items),
        "rotina_dominante": rotinas.most_common(1)[0][0] if rotinas else "--",
        "duracao_media": round(mean(duracoes), 1) if duracoes else None,
    }


def _agregados_medidas(items: list[dict[str, Any]]) -> dict[str, Any]:
    pesos = [
        (it.get("data"), float(it["peso"]))
        for it in items
        if isinstance(it.get("peso"), (int, float))
    ]
    pesos.sort(key=lambda p: str(p[0] or ""))
    if len(pesos) < 2:
        return {"qtd": len(pesos), "delta_peso": None, "primeiro": None, "ultimo": None}
    primeiro = pesos[0][1]
    ultimo = pesos[-1][1]
    return {
        "qtd": len(pesos),
        "delta_peso": round(ultimo - primeiro, 2),
        "primeiro": primeiro,
        "ultimo": ultimo,
    }


def _periodo_anterior(dias: int, hoje: date) -> tuple[date, date]:
    """Retorna ``(início, fim)`` da janela de ``dias`` imediatamente anterior.

    Exemplo: para ``dias=30`` e ``hoje=2026-05-07`` o periodo atual e
    ``[2026-04-08, 2026-05-07]``; o anterior e ``[2026-03-09, 2026-04-07]``.
    """
    fim_atual = hoje
    inicio_atual = fim_atual - timedelta(days=dias - 1)
    fim_ant = inicio_atual - timedelta(days=1)
    inicio_ant = fim_ant - timedelta(days=dias - 1)
    return inicio_ant, fim_ant


def _filtrar_intervalo(
    items: list[dict[str, Any]], inicio: date, fim: date
) -> list[dict[str, Any]]:
    """Filtra items por ``data`` ISO no intervalo fechado ``[início, fim]``."""
    saida: list[dict[str, Any]] = []
    for it in items:
        ds = str(it.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if inicio <= d <= fim:
            saida.append(it)
    return saida


def _humor_intervalo(
    vault_root: Path | None, inicio: date, fim: date
) -> dict[str, Any]:
    """Variante de :func:`_agregados_humor` para janela ``[início, fim]``."""
    if vault_root is None:
        return {"media": None, "qtd": 0}
    arquivo = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    if not arquivo.exists():
        return {"media": None, "qtd": 0}
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"media": None, "qtd": 0}
    celulas = payload.get("celulas") or []
    if not isinstance(celulas, list):
        return {"media": None, "qtd": 0}
    valores: list[float] = []
    for c in celulas:
        ds = str(c.get("data") or "")
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if not (inicio <= d <= fim):
            continue
        v = c.get("humor")
        if isinstance(v, (int, float)):
            valores.append(float(v))
    if not valores:
        return {"media": None, "qtd": 0}
    return {"media": round(mean(valores), 2), "qtd": len(valores)}


def _metricas_janela(
    vault_root: Path | None,
    inicio: date,
    fim: date,
) -> dict[str, float]:
    """Calcula métricas comparáveis para a janela ``[início, fim]``.

    Devolve apenas chaves que tem dado real (``None`` filtrado em
    :func:`_comparativo_html`). Conformidade ADR-13: tudo deterministico
    sobre caches do vault, zero LLM.
    """
    eventos_full = _carregar_cache(vault_root, "eventos")
    treinos_full = _carregar_cache(vault_root, "treinos")
    medidas_full = _carregar_cache(vault_root, "medidas")

    eventos = _filtrar_intervalo(eventos_full, inicio, fim)
    treinos = _filtrar_intervalo(treinos_full, inicio, fim)
    medidas = _filtrar_intervalo(medidas_full, inicio, fim)

    h = _humor_intervalo(vault_root, inicio, fim)
    e = _agregados_eventos(eventos)
    t = _agregados_treinos(treinos)
    m = _agregados_medidas(medidas)

    out: dict[str, float] = {
        "registros": float(h["qtd"]),
        "eventos": float(e["qtd"]),
        "treinos": float(t["qtd"]),
    }
    if h["media"] is not None:
        out["humor_medio"] = float(h["media"])
    if m["delta_peso"] is not None:
        out["peso_var"] = float(m["delta_peso"])
    return out


def _comparativo_html(
    metricas_atual: dict[str, float], metricas_ant: dict[str, float]
) -> str:
    """Tabela rica de comparação com delta sinalizado por métrica.

    Apenas chaves presentes nos dois lados são exibidas; faltantes ficam
    fora do bloco para não mentir 0 quando dado não existe.
    """
    chaves_legiveis = {
        "humor_medio": "humor médio",
        "registros": "registros · humor",
        "eventos": "eventos",
        "treinos": "treinos",
        "peso_var": "peso (variação kg)",
        "ansiedade_media": "ansiedade média",
        "tarefas_concluidas": "tarefas concluídas",
        "noites_curtas": "noites &lt; 6h sono",
    }
    linhas: list[str] = []
    for chave, label in chaves_legiveis.items():
        atual = metricas_atual.get(chave)
        ant = metricas_ant.get(chave)
        if atual is None or ant is None:
            continue
        delta = atual - ant
        if delta > 0.01:
            sinal = f'<span class="delta-pos">↗ {delta:+.2f}</span>'
        elif delta < -0.01:
            sinal = f'<span class="delta-neg">↘ {delta:+.2f}</span>'
        else:
            sinal = '<span class="delta-zero">= mesmo</span>'
        linhas.append(
            '<div class="comparativo-linha">'
            f'<span class="comp-label">{label}</span>'
            f'<span class="comp-valor">{atual:.2f}</span>'
            f'{sinal}'
            "</div>"
        )
    if not linhas:
        return minificar(
            '<div class="comparativo-bloco">'
            '<h3 class="comp-titulo">COMPARATIVO · vs 30D ANTERIORES</h3>'
            '<p class="destaques-vazio">Sem dado suficiente para comparar.</p>'
            '</div>'
        )
    return minificar(
        '<div class="comparativo-bloco">'
        '<h3 class="comp-titulo">COMPARATIVO · vs 30D ANTERIORES</h3>'
        + "".join(linhas)
        + '</div>'
    )


def _gerar_destaques(
    vault_root: Path | None, inicio: date, fim: date
) -> list[dict[str, str]]:
    """Gera até 5 destaques determinísticos da janela ``[início, fim]``.

    Heuristicas (todas sobre caches reais):
    - viagens: eventos com categoria contendo "viagem"
    - top bairro: bairro mais frequente em eventos do periodo
    - rotina dominante: rotina de treino mais frequente (>=3 ocorrencias)
    - melhora de humor: media da janela atual > media da anterior em >=0.5
    - perda de peso saudavel: variacao negativa entre -2.0kg e -0.1kg
    """
    if vault_root is None:
        return []

    destaques: list[dict[str, str]] = []
    eventos = _filtrar_intervalo(_carregar_cache(vault_root, "eventos"), inicio, fim)
    treinos = _filtrar_intervalo(_carregar_cache(vault_root, "treinos"), inicio, fim)
    medidas = _filtrar_intervalo(_carregar_cache(vault_root, "medidas"), inicio, fim)

    # Viagens
    viagens = [
        e for e in eventos
        if "viagem" in str(e.get("categoria") or "").lower()
    ]
    if viagens:
        primeiro = viagens[0]
        lugar = (
            primeiro.get("lugar")
            or primeiro.get("bairro")
            or primeiro.get("titulo")
            or "destino"
        )
        destaques.append({
            "tipo": "social",
            "rotulo": f"Viagem · {lugar}",
            "data": str(primeiro.get("data") or ""),
        })

    # Top bairro
    agg_eventos = _agregados_eventos(eventos)
    if agg_eventos["top_bairros"]:
        bairro, qtd = agg_eventos["top_bairros"][0]
        if qtd >= 3:
            destaques.append({
                "tipo": "social",
                "rotulo": f"{bairro} · {qtd} eventos",
                "data": "",
            })

    # Rotina dominante
    agg_treinos = _agregados_treinos(treinos)
    if agg_treinos["qtd"] >= 3 and agg_treinos["rotina_dominante"] != "--":
        destaques.append({
            "tipo": "vitoria",
            "rotulo": (
                f"{agg_treinos['rotina_dominante']} · "
                f"{agg_treinos['qtd']} treinos"
            ),
            "data": "",
        })

    # Melhora de humor entre janela anterior e atual
    dias = (fim - inicio).days + 1
    inicio_ant, fim_ant = _periodo_anterior(dias, fim)
    h_atual = _humor_intervalo(vault_root, inicio, fim)
    h_ant = _humor_intervalo(vault_root, inicio_ant, fim_ant)
    if (
        h_atual["media"] is not None
        and h_ant["media"] is not None
        and h_atual["media"] - h_ant["media"] >= 0.5
    ):
        destaques.append({
            "tipo": "conquista",
            "rotulo": (
                f"humor melhorou +{h_atual['media'] - h_ant['media']:.1f} "
                "vs janela anterior"
            ),
            "data": "",
        })

    # Perda de peso saudavel
    agg_medidas = _agregados_medidas(medidas)
    delta_peso = agg_medidas.get("delta_peso")
    if delta_peso is not None and -2.0 <= delta_peso <= -0.1:
        destaques.append({
            "tipo": "vitoria",
            "rotulo": f"peso · {delta_peso:+.1f} kg na janela",
            "data": "",
        })

    return destaques[:5]


def _destaques_html(destaques: list[dict[str, str]]) -> str:
    """Renderiza grid de destaques. Fallback claro quando vazio."""
    if not destaques:
        return minificar(
            '<div class="destaques-bloco">'
            '<h3 class="destaques-titulo">DESTAQUES DO MÊS</h3>'
            '<p class="destaques-vazio">Sem destaques no período.</p>'
            '</div>'
        )

    cards: list[str] = []
    for d in destaques:
        tipo = d.get("tipo") or "vitoria"
        rotulo = d.get("rotulo") or "(sem rótulo)"
        data_str = d.get("data") or ""
        cards.append(
            f'<div class="destaque-card destaque-{tipo}">'
            f'<span class="destaque-rotulo">{rotulo}</span>'
            f'<span class="destaque-data">{data_str}</span>'
            "</div>"
        )
    return minificar(
        '<div class="destaques-bloco">'
        f'<h3 class="destaques-titulo">DESTAQUES DO MÊS · {len(destaques)}</h3>'
        '<div class="destaques-grid">'
        + "".join(cards)
        + '</div>'
        '</div>'
    )


def _narrativa_manual_html(periodo: str) -> str:
    """Le ``docs/recaps/<periodo>.md`` se existir; senao renderiza CTA.

    Conformidade ADR-13: nenhum LLM via API. Conteúdo gerado por humano
    (Opus interativo via skill ``/gerar-recap``) e gravado a mao no
    arquivo Markdown. Aqui apenas exibimos.
    """
    raiz = Path(__file__).resolve().parents[3]
    recap_path = raiz / "docs" / "recaps" / f"{periodo}.md"

    if recap_path.exists():
        try:
            md = recap_path.read_text(encoding="utf-8")
        except OSError:
            md = ""
        if md.strip():
            return minificar(
                '<div class="narrativa-bloco">'
                f'<h3 class="narrativa-titulo">NARRATIVA · {periodo}</h3>'
                f'<div class="narrativa-corpo">{md}</div>'
                '</div>'
            )

    return minificar(
        '<div class="narrativa-bloco narrativa-vazia">'
        f'<h3 class="narrativa-titulo">NARRATIVA · {periodo}</h3>'
        '<p>Nenhuma narrativa gerada para este período. Use a skill canônica '
        f'<code>/gerar-recap {periodo}</code> no Claude Code interativo '
        '(Opus principal) para registrar a narrativa do mês em '
        f'<code>docs/recaps/{periodo}.md</code>. ADR-13: nenhum LLM via '
        'API é chamado pelo dashboard.</p>'
        '</div>'
    )


def _kpi_card_html(titulo: str, valor: str, subtitulo: str) -> str:
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:16px;">'
        f'  <div style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                letter-spacing:0.10em;text-transform:uppercase;'
        f'                color:{CORES["texto_muted"]};margin-bottom:8px;">'
        f"{titulo}</div>"
        f'  <div style="font-size:24px;font-weight:500;color:{CORES["texto"]};'
        f'                font-variant-numeric:tabular-nums;">{valor}</div>'
        f'  <div style="font-size:11px;color:{CORES["texto_sec"]};'
        f'                margin-top:4px;">{subtitulo}</div>'
        f"</div>"
    )


def _page_header_html(periodo_label: str) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo=f"RECAP · {periodo_label.upper()}",
        subtitulo=(
            "Resumo agregado determinístico sobre os caches do vault. "
            "Sem narrativa LLM (ADR-13)."
        ),
        sprint_tag="UX-RD-19",
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Recap (UX-T-21)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Re-gerar agora", "glyph": "refresh",
         "title": "Gerar Recap do período"},
        {"label": "Compartilhar com Pessoa B", "primary": True,
         "title": "Vista resumida sem trechos íntimos"},
    ])

    del dados, periodo, pessoa, ctx

    periodo_label = st.radio(
        "Período",
        options=list(_PERIODOS_LABEL.keys()),
        index=1,
        horizontal=True,
        key="be_recap_periodo",
    )
    dias = _PERIODOS_LABEL[periodo_label]

    # CSS dedicado dos blocos UX-V-2.17 (comparativo/destaques/narrativa).
    from src.dashboard.componentes.ui import carregar_css_pagina
    css_recap = carregar_css_pagina("be_recap")
    if css_recap:
        st.markdown(minificar(css_recap), unsafe_allow_html=True)

    st.markdown(_page_header_html(periodo_label), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()
    hoje = date.today()

    if vault_root is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:10px;margin-bottom:12px;">'
            '<div class="kpi"><span class="kpi-label">HUMOR MÉDIO</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">EVENTOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">TREINOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">MEDIDAS</span>'
            '<span class="kpi-value">--</span></div>'
            '</div>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:80%;"></span>'
            '<span class="skel-bloco" style="width:65%;"></span>'
            '<span class="skel-bloco" style="width:90%;height:0.9em;"></span>'
            '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="RECAP · sem dados no período",
                descricao=(
                    "O recap agrega humor, eventos, treinos e medidas dos "
                    "últimos N dias. Configure <code>OUROBOROS_VAULT</code> "
                    "apontando para o vault Obsidian compartilhado com o app "
                    "mobile para popular este painel."
                ),
                skeleton_html=skeleton,
                cta_secao="recap",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    eventos = _filtrar_periodo(_carregar_cache(vault_root, "eventos"), dias, hoje)
    treinos = _filtrar_periodo(_carregar_cache(vault_root, "treinos"), dias, hoje)
    medidas = _filtrar_periodo(_carregar_cache(vault_root, "medidas"), dias, hoje)

    h = _agregados_humor(vault_root, dias, hoje)
    e = _agregados_eventos(eventos)
    t = _agregados_treinos(treinos)
    m = _agregados_medidas(medidas)

    col1, col2, col3, col4 = st.columns(4)
    media_humor_str = f"{h['media']:.2f}" if h["media"] is not None else "--"
    delta_peso_str = (
        f"{m['delta_peso']:+.1f} kg" if m["delta_peso"] is not None else "--"
    )

    with col1:
        st.markdown(
            _kpi_card_html(
                "humor médio",
                media_humor_str,
                f"{h['qtd']} registros no período",
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _kpi_card_html(
                "eventos",
                str(e["qtd"]),
                f"{e['positivos']} positivos · {e['negativos']} negativos",
            ),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _kpi_card_html(
                "treinos",
                str(t["qtd"]),
                f"rotina dominante: {t['rotina_dominante']}",
            ),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            _kpi_card_html(
                "peso · variação",
                delta_peso_str,
                f"{m['qtd']} medidas registradas",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("###### ")
    col_humor, col_bairros = st.columns([1.4, 1], gap="large")

    with col_humor:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
            f"Comparativo de humor</h3>",
            unsafe_allow_html=True,
        )
        if h["media"] is None:
            st.info("Sem registros de humor no período.")
        else:
            df_humor = pd.DataFrame(
                {
                    "métrica": ["média", "melhor", "pior"],
                    "valor": [h["media"], h["melhor"], h["pior"]],
                }
            )
            st.bar_chart(df_humor.set_index("métrica"), height=240)

    with col_bairros:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 8px;">'
            f"Bairros mais frequentes</h3>",
            unsafe_allow_html=True,
        )
        if not e["top_bairros"]:
            st.info("Sem bairros tagueados.")
        else:
            for bairro, qtd in e["top_bairros"]:
                st.markdown(
                    minificar(
                        f'<div style="background:{CORES["fundo_inset"]};'
                        f'border:1px solid {CORES["texto_sec"]}33;'
                        f'border-radius:4px;padding:8px 12px;margin-bottom:6px;'
                        f'display:flex;justify-content:space-between;">'
                        f'<span style="color:{CORES["texto"]};font-size:13px;">{bairro}</span>'
                        f'<span style="font-family:ui-monospace,monospace;font-size:11px;'
                        f'color:{CORES["texto_muted"]};">{qtd}x</span>'
                        f"</div>"
                    ),
                    unsafe_allow_html=True,
                )

    # ------------------------------------------------------------------
    # UX-V-2.17 -- Comparativo + Destaques + Narrativa manual (ADR-13).
    # ------------------------------------------------------------------
    inicio_atual = hoje - timedelta(days=dias - 1)
    inicio_ant, fim_ant = _periodo_anterior(dias, hoje)
    metricas_atual = _metricas_janela(vault_root, inicio_atual, hoje)
    metricas_ant = _metricas_janela(vault_root, inicio_ant, fim_ant)
    destaques = _gerar_destaques(vault_root, inicio_atual, hoje)
    periodo_recap = hoje.strftime("%Y-%m")

    st.markdown("###### ")
    col_narr, col_comp = st.columns([2, 1], gap="large")
    with col_narr:
        st.markdown(_narrativa_manual_html(periodo_recap), unsafe_allow_html=True)
        st.markdown(_destaques_html(destaques), unsafe_allow_html=True)
    with col_comp:
        st.markdown(
            _comparativo_html(metricas_atual, metricas_ant),
            unsafe_allow_html=True,
        )


# "Lembrar é a única forma de continuar." -- adágio popular brasileiro
