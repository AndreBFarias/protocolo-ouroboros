"""Cluster Bem-estar -- página "Memórias" (UX-RD-19).

Três sub-abas dentro de uma página única:

* **Treinos** -- heatmap 91 dias colorido por sessão registrada
  (reutiliza padrão do heatmap de humor mas com paleta neutra).
* **Fotos** -- galeria das fotos referenciadas em ``eventos.json``.
* **Marcos** -- lista cronológica DESC dos marcos registrados.

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: caches ausentes viram placeholders, sem crash.
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
        {"label": "Random", "title": "Memória aleatória"},
        {"label": "Capturar", "primary": True,
         "title": "Foto/áudio/texto/vídeo"},
    ])

    del dados, periodo, pessoa, ctx

    st.markdown(_page_header_html(), unsafe_allow_html=True)

    vault_root = descobrir_vault_root()

    if vault_root is None:
        st.warning(
            "Vault Bem-estar não encontrado. Configure `OUROBOROS_VAULT` "
            "para visualizar memórias."
        )
        return

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
