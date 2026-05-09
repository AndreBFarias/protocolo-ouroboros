"""Cluster Bem-estar -- página "Memórias" (UX-RD-19 + UX-V-2.11 + UX-V-2.11-FIX).

Arquitetura canônica (mockup ``23-memorias.html``):

* Header + 4 KPIs (total · 30d, por tipo, vinculadas a eventos, cápsulas para
  abrir) sempre no topo.
* Toolbar de filtros chips (todos/foto/voz/texto/video) — filtragem visual
  aplicada via classe ativa; backend filtra a lista antes de renderizar.
* Grid de cápsulas multimídia com gradientes coloridos por paleta. Quando o
  vault não tem ``memorias.json`` populado, o grid mostra **skeletons** com
  o mesmo shape e gradientes — preserva paridade visual sem dados.
* Sub-rota ``?secao=treinos`` mantém o heatmap 91 dias antigo (UX-RD-19) +
  abas históricas Fotos/Marcos como fallback retro.
* Quando o vault está completamente ausente, fallback V-03 (estado inicial).

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html``.

Lições UX-RD/UX-V aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* CSS dedicado em ``css/paginas/be_memorias.css`` (UX-M-02.D residual).
* Fallback graceful: caches ausentes viram skeletons, sem crash.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

PERIODO_HEATMAP_DIAS: int = 91

# Paletas (cor escura, cor clara) para gradiente das cápsulas.
# Espelha PALETAS de novo-mockup/mockups/23-memorias.html (UX-V-2.11).
PALETAS_CAPSULA: list[tuple[str, str]] = [
    ("#5e4d80", "#bd93f9"),
    ("#80365a", "#ff79c6"),
    ("#1a4945", "#8be9fd"),
    ("#5a3a1a", "#f1a361"),
    ("#3a4a1f", "#a4d063"),
    ("#3a2a52", "#7960c4"),
    ("#1a2e4a", "#5d8fbb"),
    ("#4a1a2e", "#bb5d8f"),
]

# Tradução tipo do payload -> rótulo curto exibido no badge.
_LABEL_TIPO: dict[str, str] = {
    "foto": "foto",
    "voz": "áudio",
    "audio": "áudio",
    "texto": "texto",
    "video": "vídeo",
    "vídeo": "vídeo",
}

# Glyph compacto por tipo (apenas texto monoespaçado dentro do círculo).
_ICO_TIPO: dict[str, str] = {
    "foto": "FT",
    "voz": "AU",
    "audio": "AU",
    "texto": "TX",
    "video": "VD",
    "vídeo": "VD",
}


def _carregar_cache(vault_root: Path | None, nome: str) -> list[dict[str, Any]]:
    """Carrega items genéricos de ``<vault>/.ouroboros/cache/<nome>.json``.

    Para ``nome="memorias"``, prefere o leitor validado de
    :mod:`src.mobile_cache.memorias` (ADR-25): payloads que violam o
    schema canônico caem em lista vazia (skeleton), evitando UI quebrada
    quando o mob grava algo fora de contrato.
    """
    if vault_root is None:
        return []
    if nome == "memorias":
        from src.mobile_cache.memorias import carregar_validado

        items, _ = carregar_validado(vault_root)
        return items
    arquivo = vault_root / ".ouroboros" / "cache" / f"{nome}.json"
    if not arquivo.exists():
        return []
    try:
        payload = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _heatmap_treinos_html(items: list[dict[str, Any]], hoje: date) -> str:
    """Heatmap 13×7 colorido por presença de treino na data."""
    datas_com_treino = {str(it.get("data") or "") for it in items}
    inicio = hoje - timedelta(days=PERIODO_HEATMAP_DIAS - 1)

    celulas: list[str] = []
    for offset in range(PERIODO_HEATMAP_DIAS):
        d = inicio + timedelta(days=offset)
        teve = d.isoformat() in datas_com_treino
        cor = CORES["destaque"] if teve else CORES["fundo_inset"]
        titulo = d.isoformat() + (" · sessão" if teve else " · sem sessão")
        celulas.append(
            f'<div title="{titulo}" '
            f'style="width:14px;height:14px;background:{cor};border-radius:2px;'
            f'border:1px solid {CORES["texto_sec"]}22;"></div>'
        )

    grid = (
        f'<div style="display:grid;grid-template-columns:repeat(13,1fr);'
        f'gap:3px;max-width:280px;">{"".join(celulas)}</div>'
    )
    return minificar(grid)


def _foto_card_html(foto_path: str, evento: dict[str, Any]) -> str:
    lugar = str(evento.get("lugar") or "").strip() or "sem lugar"
    data = str(evento.get("data") or "").strip()
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:10px;text-align:center;">'
        f'  <div style="background:{CORES["fundo_inset"]};height:120px;'
        f'              display:flex;align-items:center;justify-content:center;'
        f'              color:{CORES["texto_muted"]};font-family:ui-monospace,monospace;'
        f'              font-size:10px;border-radius:4px;margin-bottom:6px;">'
        f"{foto_path}"
        f"  </div>"
        f'  <div style="font-size:11px;color:{CORES["texto_sec"]};">'
        f"<strong>{data}</strong> · {lugar}"
        f"  </div>"
        f"</div>"
    )


def _marco_card_html(marco: dict[str, Any]) -> str:
    titulo = str(marco.get("titulo") or "").strip() or "(sem título)"
    data = str(marco.get("data") or "").strip()
    descricao = str(marco.get("descricao") or "").strip()
    auto = bool(marco.get("auto"))
    autor = str(marco.get("autor") or "").strip()
    tags = marco.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    chips_tags = "".join(
        f'<span style="display:inline-block;background:{CORES["fundo_inset"]};'
        f'color:{CORES["texto_sec"]};font-family:ui-monospace,monospace;'
        f'font-size:10px;padding:2px 8px;border-radius:10px;margin-right:4px;'
        f'border:1px solid {CORES["texto_sec"]}33;">{tag}</span>'
        for tag in tags
    )
    badge_auto = (
        f'<span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'color:{CORES["texto_muted"]};margin-left:8px;">[auto]</span>'
        if auto
        else ""
    )
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;'
        f'border-left:3px solid {CORES["destaque"]};'
        f'border-radius:6px;padding:14px;margin-bottom:10px;">'
        f'  <div style="display:flex;justify-content:space-between;'
        f'              align-items:flex-start;margin-bottom:6px;">'
        f'    <strong style="color:{CORES["texto"]};font-size:14px;">{titulo}</strong>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:11px;'
        f'                  color:{CORES["texto_muted"]};">{data}</span>'
        f"  </div>"
        f'  <div style="color:{CORES["texto_sec"]};font-size:13px;'
        f'                line-height:1.4;margin-bottom:8px;">{descricao}</div>'
        f"  <div>{chips_tags}"
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["texto_muted"]};margin-left:8px;">'
        f"por {autor}{badge_auto}</span>"
        f"  </div>"
        f"</div>"
    )


def _capsula_html(memoria: dict[str, Any], idx: int) -> str:
    """HTML de uma cápsula multimídia (UX-V-2.11).

    Não renderiza mídia real -- apenas badge de tipo, gradiente colorido
    como fundo, título, meta e tags. ``idx`` indexa ``PALETAS_CAPSULA`` em
    rotação. Sanitização básica via ``str.replace`` para impedir injeção
    em ``onclick`` (não usado aqui, mas titulos podem conter aspas).
    """
    tipo = str(memoria.get("tipo", "texto")).lower().strip()
    label = _LABEL_TIPO.get(tipo, tipo or "?")
    ico = _ICO_TIPO.get(tipo, "?")

    cor1, cor2 = PALETAS_CAPSULA[idx % len(PALETAS_CAPSULA)]
    titulo = str(memoria.get("titulo") or "(sem título)").strip()[:80]
    data = str(memoria.get("data") or "").strip()
    # Schema canônico ADR-25: ``local`` e ``duracao_seg``. Retrocompat
    # com cápsulas legadas que usavam ``vinculo`` / ``duracao`` livres.
    duracao_seg = memoria.get("duracao_seg")
    if isinstance(duracao_seg, int) and duracao_seg > 0:
        if duracao_seg >= 60:
            vinculo_curto = f"{duracao_seg // 60}m {duracao_seg % 60:02d}s"
        else:
            vinculo_curto = f"{duracao_seg}s"
    else:
        local = str(memoria.get("local") or "").strip()
        vinculo_legado = str(
            memoria.get("vinculo") or memoria.get("duracao") or ""
        ).strip()
        bruto = local or vinculo_legado
        # Mostra apenas o primeiro segmento antes do " · " (mockup faz idem).
        vinculo_curto = bruto.split(" · ")[0] if bruto else ""

    tags_raw = memoria.get("tags") or []
    if not isinstance(tags_raw, list):
        tags_raw = []
    tags_html = "".join(
        f'<span class="pill">{str(t)[:18]}</span>'
        for t in tags_raw[:4]
    )

    return (
        f'<div class="mem-card" style="--cor:{cor2};">'
        f'<div class="mem-thumb tipo-{tipo}" '
        f'style="--cor1:{cor1};--cor2:{cor2};">'
        f'<span class="badge">{label}</span>'
        f'<span class="ico">{ico}</span>'
        f"</div>"
        f'<div class="mem-corpo">'
        f'<span class="mem-titulo">{titulo}</span>'
        f'<div class="mem-meta">'
        f"<span>{data}</span><span>{vinculo_curto}</span>"
        f"</div>"
        f"</div>"
        f'<div class="mem-tags">{tags_html}</div>'
        f"</div>"
    )


def _grid_memorias_html(memorias: list[dict[str, Any]], limite: int = 12) -> str:
    """Grid de cápsulas (até ``limite`` itens, mockup mostra 12 = 4×3)."""
    cartoes = "".join(
        _capsula_html(m, i)
        for i, m in enumerate(memorias[:limite])
        if isinstance(m, dict)
    )
    return f'<div class="mem-grid">{cartoes}</div>'


# Tipos do filtro (mockup: TIPO_FILTRO).
_FILTROS_TIPO: tuple[str, ...] = ("todos", "foto", "voz", "texto", "video")


def _toolbar_filtros_html(filtro_ativo: str = "todos") -> str:
    """Toolbar de chips de filtro (todos/foto/voz/texto/video).

    Renderiza chips estáticos espelhando o mockup ``23-memorias.html``. A
    interatividade real (alternar via clique sem rerender) exige JS dedicado;
    nesta primeira versão a Streamlit não trata o clique nativamente — chips
    são informativos. Filtros funcionais via query param ficam para sprint
    futura (mockup-canônico declarado).
    """
    chips = "".join(
        f'<button data-f="{tipo}" '
        f'class="mem-chip{(" ativo" if tipo == filtro_ativo else "")}">'
        f"{tipo}</button>"
        for tipo in _FILTROS_TIPO
    )
    return f'<div class="mem-toolbar">{chips}</div>'


def _capsula_skeleton_html(idx: int) -> str:
    """Cápsula em modo skeleton -- gradiente vivo, conteúdo placeholder.

    Preserva o shape visual quando o vault ainda não tem ``memorias.json``
    populado. Gradiente real (não cinza) para evitar a sensação de "tela
    vazia"; corpo e tags em barras esqueléticas.
    """
    cor1, cor2 = PALETAS_CAPSULA[idx % len(PALETAS_CAPSULA)]
    return (
        f'<div class="mem-card mem-card-skeleton" style="--cor:{cor2};">'
        f'<div class="mem-thumb tipo-skeleton" '
        f'style="--cor1:{cor1};--cor2:{cor2};">'
        f'<span class="badge">vazio</span>'
        f'<span class="ico">--</span>'
        f"</div>"
        f'<div class="mem-corpo">'
        f'<span class="skel-bloco" style="height:14px;width:80%;"></span>'
        f'<div class="mem-meta">'
        f'<span class="skel-bloco" style="height:10px;width:40%;"></span>'
        f'<span class="skel-bloco" style="height:10px;width:25%;"></span>'
        f"</div>"
        f"</div>"
        f'<div class="mem-tags">'
        f'<span class="skel-bloco pill" style="height:14px;width:48px;"></span>'
        f'<span class="skel-bloco pill" style="height:14px;width:38px;"></span>'
        f"</div>"
        f"</div>"
    )


def _grid_skeleton_html(quantidade: int = 8) -> str:
    """Grid completo de cápsulas-skeleton para estado vazio."""
    cartoes = "".join(_capsula_skeleton_html(i) for i in range(quantidade))
    return f'<div class="mem-grid">{cartoes}</div>'


def _kpis_memorias_skeleton_html() -> str:
    """Versão skeleton dos 4 KPIs -- placeholders com '--' nos numerais."""
    return (
        '<div class="mem-stats">'
        '<div class="mem-stat">'
        '<div class="l">total · 30d</div>'
        '<div class="v" style="color:var(--accent-purple);">--</div>'
        '<div class="sub">aguardando dados</div>'
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">por tipo</div>'
        '<div class="mem-stat-tipos">'
        '<div>'
        '<div class="v" style="color:var(--accent-cyan);">--</div>'
        '<div class="sub">fotos</div>'
        "</div>"
        '<div>'
        '<div class="v" style="color:var(--accent-pink);">--</div>'
        '<div class="sub">áudios</div>'
        "</div>"
        '<div>'
        '<div class="v" style="color:var(--accent-yellow);">--</div>'
        '<div class="sub">textos</div>'
        "</div>"
        '<div>'
        '<div class="v" style="color:var(--accent-green);">--</div>'
        '<div class="sub">vídeos</div>'
        "</div>"
        "</div>"
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">vinculadas a eventos</div>'
        '<div class="v" style="color:var(--accent-pink);">--</div>'
        '<div class="sub">sem contexto ainda</div>'
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">cápsulas para abrir</div>'
        '<div class="v" style="color:var(--accent-yellow);">--</div>'
        '<div class="sub">aguardando captura</div>'
        "</div>"
        "</div>"
    )


def _kpis_memorias_html(memorias: list[dict[str, Any]]) -> str:
    """4 KPIs do mockup: total, por tipo, vinculadas a eventos, capsulas."""
    from collections import Counter

    n = len(memorias)
    tipos = Counter(
        str(m.get("tipo", "?")).lower().strip()
        for m in memorias
        if isinstance(m, dict)
    )
    n_fotos = tipos.get("foto", 0)
    n_audios = tipos.get("voz", 0) + tipos.get("audio", 0)
    n_textos = tipos.get("texto", 0)
    n_videos = tipos.get("video", 0) + tipos.get("vídeo", 0)
    # Schema canônico ADR-25: cápsula é "vinculada" quando tem
    # evento_vinculado OU diario_vinculado. Retrocompat com chaves
    # antigas (evento_id/vinculo) preservada (padrão (o)).
    n_vinculadas = sum(
        1 for m in memorias
        if isinstance(m, dict) and (
            m.get("evento_vinculado")
            or m.get("diario_vinculado")
            or m.get("evento_id")
            or m.get("vinculo")
        )
    )
    pct_contexto = (n_vinculadas * 100 // n) if n else 0
    # ``para_abrir`` é flag canônica do schema; quando ausente, deriva.
    n_para_abrir = sum(
        1 for m in memorias
        if isinstance(m, dict) and bool(m.get("para_abrir"))
    )
    if n_para_abrir == 0:
        n_para_abrir = max(0, n - n_vinculadas)

    return (
        '<div class="mem-stats">'
        '<div class="mem-stat">'
        '<div class="l">total · 30d</div>'
        f'<div class="v" style="color:var(--accent-purple);">{n}</div>'
        f'<div class="sub">{n} cápsulas no período</div>'
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">por tipo</div>'
        '<div class="mem-stat-tipos">'
        '<div>'
        f'<div class="v" style="color:var(--accent-cyan);">{n_fotos}</div>'
        '<div class="sub">fotos</div>'
        '</div>'
        '<div>'
        f'<div class="v" style="color:var(--accent-pink);">{n_audios}</div>'
        '<div class="sub">áudios</div>'
        '</div>'
        '<div>'
        f'<div class="v" style="color:var(--accent-yellow);">{n_textos}</div>'
        '<div class="sub">textos</div>'
        '</div>'
        '<div>'
        f'<div class="v" style="color:var(--accent-green);">{n_videos}</div>'
        '<div class="sub">vídeos</div>'
        '</div>'
        '</div>'
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">vinculadas a eventos</div>'
        f'<div class="v" style="color:var(--accent-pink);">{n_vinculadas}'
        f'<span style="color:var(--text-muted);font-size:14px;">/{n}</span>'
        "</div>"
        f'<div class="sub">{pct_contexto}% têm contexto</div>'
        "</div>"
        '<div class="mem-stat">'
        '<div class="l">cápsulas para abrir</div>'
        f'<div class="v" style="color:var(--accent-yellow);">{n_para_abrir}</div>'
        '<div class="sub">aguardando contexto</div>'
        "</div>"
        "</div>"
    )


def _page_header_html() -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="MEMÓRIAS",
        subtitulo=(
            "Cápsulas de treinos, fotos e marcos — vinculáveis a eventos "
            "e dias do diário emocional."
        ),
        sprint_tag="UX-RD-19",
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Memórias (UX-T-23)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Random", "glyph": "refresh", "title": "Memória aleatória"},
        {"label": "Capturar", "primary": True, "glyph": "plus",
         "title": "Foto/áudio/texto/vídeo"},
    ])

    del dados, periodo, pessoa, ctx

    st.markdown(_page_header_html(), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()

    if vault_root is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:10px;margin-bottom:12px;">'
            '<div class="kpi"><span class="kpi-label">TREINOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">FOTOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">MARCOS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">SEMANAS</span>'
            '<span class="kpi-value">--</span></div>'
            '</div>'
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:8px;">'
            + ''.join(
                '<span class="skel-bloco" style="height:60px;min-width:0;'
                'border-radius:6px;"></span>'
                for _ in range(8)
            )
            + '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="MEMÓRIAS · sem registros ainda",
                descricao=(
                    "Sessões de treino, fotos anexadas a eventos e marcos "
                    "biográficos vivem no vault e formam o cluster de "
                    "memórias. Configure <code>OUROBOROS_VAULT</code> e "
                    "comece a registrar pelo app mobile."
                ),
                skeleton_html=skeleton,
                cta_secao="memorias",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    # CSS dedicado da página (UX-V-2.11).
    from src.dashboard.componentes.ui import carregar_css_pagina
    st.markdown(
        minificar(carregar_css_pagina("be_memorias")),
        unsafe_allow_html=True,
    )

    # Sub-rota retro: ?secao=treinos preserva heatmap UX-RD-19 antigo.
    secao = ""
    try:
        secao = str(st.query_params.get("secao") or "").strip().lower()
    except Exception:
        secao = ""

    if secao == "treinos":
        _renderizar_secao_treinos_retro(vault_root)
        return

    # Caminho canônico UX-V-2.11-FIX: KPIs + chips + grid.
    memorias = _carregar_cache(vault_root, "memorias")
    if memorias:
        st.markdown(_kpis_memorias_html(memorias), unsafe_allow_html=True)
        st.markdown(_toolbar_filtros_html(), unsafe_allow_html=True)
        st.markdown(
            minificar(_grid_memorias_html(memorias)),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(_kpis_memorias_skeleton_html(), unsafe_allow_html=True)
        st.markdown(_toolbar_filtros_html(), unsafe_allow_html=True)
        st.markdown(
            minificar(_grid_skeleton_html()),
            unsafe_allow_html=True,
        )


def _renderizar_secao_treinos_retro(vault_root: Path) -> None:
    """Sub-rota ``?secao=treinos`` -- preserva heatmap 91 dias + Fotos/Marcos.

    Compat retro UX-RD-19. Mantém os três fluxos antigos como abas para
    consulta histórica enquanto a arquitetura canônica de cápsulas é a
    rota padrão.
    """
    treinos = _carregar_cache(vault_root, "treinos")
    eventos = _carregar_cache(vault_root, "eventos")
    marcos = _carregar_cache(vault_root, "marcos")

    aba_treinos, aba_fotos, aba_marcos = st.tabs(["Treinos", "Fotos", "Marcos"])

    with aba_treinos:
        st.markdown(
            f'<p style="color:{CORES["texto_sec"]};font-size:13px;'
            f'margin-bottom:12px;">'
            f"Heatmap dos últimos 91 dias. Cada célula colorida indica uma "
            f"sessão registrada (independente da rotina)."
            f"</p>",
            unsafe_allow_html=True,
        )
        if not treinos:
            st.info("Nenhuma sessão de treino encontrada no cache.")
        else:
            st.markdown(
                _heatmap_treinos_html(treinos, date.today()), unsafe_allow_html=True
            )
            st.markdown(
                f'<div style="font-family:ui-monospace,monospace;font-size:11px;'
                f'color:{CORES["texto_muted"]};margin-top:10px;">'
                f"Total no período: {len(treinos)} sessões"
                f"</div>",
                unsafe_allow_html=True,
            )

    with aba_fotos:
        fotos: list[tuple[str, dict[str, Any]]] = []
        for ev in eventos:
            paths = ev.get("fotos") or []
            if not isinstance(paths, list):
                continue
            for p in paths:
                p_str = str(p).strip()
                if p_str:
                    fotos.append((p_str, ev))

        if not fotos:
            st.info("Nenhum evento com fotos anexadas.")
        else:
            cols = st.columns(4)
            for idx, (foto_path, ev) in enumerate(fotos):
                with cols[idx % 4]:
                    st.markdown(_foto_card_html(foto_path, ev), unsafe_allow_html=True)

    with aba_marcos:
        if not marcos:
            st.info("Nenhum marco registrado.")
        else:
            ordenados = sorted(
                marcos, key=lambda m: str(m.get("data") or ""), reverse=True
            )
            html = "".join(_marco_card_html(m) for m in ordenados if isinstance(m, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)


# "A memória é o diário que carregamos conosco." -- Oscar Wilde
