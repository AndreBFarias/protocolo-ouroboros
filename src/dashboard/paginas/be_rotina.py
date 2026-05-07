"""Cluster Bem-estar -- página "Rotina" (UX-RD-19).

Visualização de alarmes, tarefas e contadores recorrentes a partir de
``<vault>/.ouroboros/rotina.toml`` (ou ``~/.ouroboros/rotina.toml`` no
fallback). Lê o arquivo, parseia via :mod:`tomllib` e renderiza três
seções como cartões agrupados por horário/categoria.

Esta página é o lado visual do par ``Editor TOML`` (UX-RD-19): aquele
edita o arquivo, esta materializa em UI o que o arquivo declara. Se
``rotina.toml`` ainda não existe, a página exibe um aviso explicando
que o usuário deve criar via Editor TOML antes.

Mockup-fonte: ``novo-mockup/mockups/20-rotina.html``.

Lições UX-RD aplicadas:

* HTML emitido via :func:`minificar` (UX-RD-04).
* Cores via ``CORES`` em :mod:`src.dashboard.tema` -- nunca hex literal.
* Fallback graceful: rotina.toml ausente vira mensagem clara.
* Contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

_DIAS_LABEL = {
    "seg": "S",
    "ter": "T",
    "qua": "Q",
    "qui": "Q",
    "sex": "S",
    "sab": "S",
    "dom": "D",
}
_ORDEM_DIAS = ("seg", "ter", "qua", "qui", "sex", "sab", "dom")


def _resolver_caminho_rotina() -> Path:
    vault_root = descobrir_vault_root()
    base = vault_root if vault_root is not None else Path.home()
    return base / ".ouroboros" / "rotina.toml"


def _ler_rotina(caminho: Path) -> dict[str, Any] | None:
    if not caminho.exists():
        return None
    try:
        return tomllib.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _page_header_html(qtd_alarmes: int, qtd_tarefas: int, qtd_contadores: int) -> str:
    """UX-U-03: usa helper canônico ``componentes/page_header``."""
    from src.dashboard.componentes.page_header import renderizar_page_header

    return renderizar_page_header(
        titulo="ROTINA",
        subtitulo=(
            "Alarmes recorrentes, tarefas e contadores diários. "
            "Persiste em .ouroboros/rotina.toml."
        ),
        sprint_tag="UX-RD-19",
        pills=[{
            "texto": (
                f"{qtd_alarmes} alarmes · {qtd_tarefas} tarefas · "
                f"{qtd_contadores} contadores"
            ),
            "tipo": "generica",
        }],
    )


def _alarme_card_html(alarme: dict[str, Any]) -> str:
    nome = str(alarme.get("nome") or alarme.get("id") or "alarme").strip()
    hora = str(alarme.get("hora") or "--:--").strip()
    dias = alarme.get("dias") or []
    if not isinstance(dias, list):
        dias = []
    chips_dias = "".join(
        f'<span style="display:inline-block;width:18px;height:18px;'
        f"line-height:18px;text-align:center;font-family:ui-monospace,monospace;"
        f"font-size:10px;border-radius:3px;margin-right:2px;"
        f'background:{CORES["destaque"] if d in dias else CORES["fundo_inset"]};'
        f'color:{CORES["fundo"] if d in dias else CORES["texto_muted"]};">'
        f"{_DIAS_LABEL.get(d, d[:1].upper())}</span>"
        for d in _ORDEM_DIAS
    )
    tags = alarme.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    chips_tags = "".join(
        f'<span style="display:inline-block;background:{CORES["fundo_inset"]};'
        f'color:{CORES["texto_sec"]};font-family:ui-monospace,monospace;'
        f"font-size:10px;padding:2px 8px;border-radius:10px;margin-right:4px;"
        f'border:1px solid {CORES["texto_sec"]}33;">'
        f"{tag}</span>"
        for tag in tags
    )
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:14px;margin-bottom:10px;">'
        f'  <div style="display:flex;justify-content:space-between;'
        f'              align-items:center;margin-bottom:8px;">'
        f'    <strong style="color:{CORES["texto"]};font-size:14px;">{nome}</strong>'
        f'    <span style="font-family:ui-monospace,monospace;font-size:18px;'
        f'                  color:{CORES["destaque"]};">{hora}</span>'
        f"  </div>"
        f'  <div style="margin-bottom:6px;">{chips_dias}</div>'
        f"  <div>{chips_tags}</div>"
        f"</div>"
    )


def _tarefa_card_html(tarefa: dict[str, Any]) -> str:
    nome = str(tarefa.get("nome") or tarefa.get("id") or "tarefa").strip()
    duracao = tarefa.get("duracao_min")
    duracao_str = f"~{duracao}min" if isinstance(duracao, (int, float)) else "--"
    tipo = str(tarefa.get("tipo") or "geral").strip()
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:12px 14px;margin-bottom:8px;'
        f'display:flex;align-items:center;gap:10px;">'
        f'  <div style="width:14px;height:14px;'
        f'              border:1.5px solid {CORES["destaque"]};'
        f'              border-radius:3px;flex-shrink:0;"></div>'
        f'  <div style="flex:1;color:{CORES["texto"]};font-size:13px;">{nome}'
        f'    <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                  color:{CORES["texto_muted"]};margin-left:8px;">{duracao_str}</span>'
        f"  </div>"
        f'  <span style="font-family:ui-monospace,monospace;font-size:10px;'
        f'                color:{CORES["texto_muted"]};">tipo: {tipo}</span>'
        f"</div>"
    )


def _contador_card_html(contador: dict[str, Any]) -> str:
    nome = str(contador.get("nome") or contador.get("id") or "contador").strip()
    meta = contador.get("meta")
    meta_str = str(meta) if meta is not None else "--"
    reset = str(contador.get("reset") or "diario").strip()
    return (
        f'<div style="background:{CORES["card_fundo"]};'
        f'border:1px solid {CORES["texto_sec"]}33;border-radius:6px;'
        f'padding:12px 14px;margin-bottom:8px;">'
        f'  <div style="color:{CORES["texto"]};font-size:14px;">{nome}</div>'
        f'  <div style="font-family:ui-monospace,monospace;font-size:11px;'
        f'                color:{CORES["texto_muted"]};margin-top:4px;">'
        f"meta: {meta_str} · reset {reset}"
        f"  </div>"
        f"</div>"
    )


def renderizar(
    dados: dict[str, pd.DataFrame],
    periodo: str,
    pessoa: str,
    ctx: dict | None = None,
) -> None:
    """Renderiza Bem-estar / Rotina (UX-T-20)."""
    from src.dashboard.componentes.topbar_actions import renderizar_grupo_acoes
    renderizar_grupo_acoes([
        {"label": "Hoje", "glyph": "calendar",
         "href": "?cluster=Bem-estar&tab=Hoje"},
        {"label": "Novo", "primary": True, "glyph": "plus",
         "title": "Wizard alarme/tarefa/contador"},
    ])

    del dados, periodo, pessoa, ctx

    caminho = _resolver_caminho_rotina()
    cfg = _ler_rotina(caminho)

    alarmes = cfg.get("alarme", []) if cfg else []
    tarefas = cfg.get("tarefa", []) if cfg else []
    contadores = cfg.get("contador", []) if cfg else []

    if not isinstance(alarmes, list):
        alarmes = []
    if not isinstance(tarefas, list):
        tarefas = []
    if not isinstance(contadores, list):
        contadores = []

    st.markdown(
        _page_header_html(len(alarmes), len(tarefas), len(contadores)),
        unsafe_allow_html=True,
    )

    if cfg is None:
        from src.dashboard.componentes.ui import (
            fallback_estado_inicial_html,
            ler_sync_info,
        )
        skeleton = (
            '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
            'gap:10px;margin-bottom:14px;">'
            '<div class="kpi"><span class="kpi-label">ALARMES</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">TAREFAS</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">CONTADORES</span>'
            '<span class="kpi-value">--</span></div>'
            '<div class="kpi"><span class="kpi-label">STREAK</span>'
            '<span class="kpi-value">--</span></div>'
            '</div>'
            '<div style="display:grid;grid-template-columns:1.2fr 1fr 0.8fr;'
            'gap:14px;">'
            '<div><span class="skel-bloco" style="width:40%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:90%;"></span>'
            '<span class="skel-bloco" style="width:70%;"></span>'
            '</div></div>'
            '<div><span class="skel-bloco" style="width:40%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:85%;"></span>'
            '<span class="skel-bloco" style="width:75%;"></span>'
            '</div></div>'
            '<div><span class="skel-bloco" style="width:50%;height:0.8em;'
            'margin-bottom:8px;"></span>'
            '<div style="display:flex;flex-direction:column;gap:6px;">'
            '<span class="skel-bloco" style="width:80%;"></span>'
            '<span class="skel-bloco" style="width:60%;"></span>'
            '</div></div>'
            '</div>'
        )
        st.markdown(
            fallback_estado_inicial_html(
                titulo="ROTINA · sem configuração ainda",
                descricao=(
                    "Alarmes, tarefas recorrentes e contadores diários são "
                    "definidos em <code>privacidade/rotina.toml</code>. Use a "
                    "aba <code>Editor TOML</code> ao lado para criar a "
                    "configuração inicial -- ou edite o arquivo direto no "
                    "app mobile, que sincroniza com o vault."
                ),
                skeleton_html=skeleton,
                cta_label="Configure pelo Editor TOML ou pelo app mobile",
                cta_secao="rotina",
                sync_info=ler_sync_info(),
            ),
            unsafe_allow_html=True,
        )
        return

    col_alarmes, col_tarefas, col_contadores = st.columns([1.2, 1, 0.8], gap="large")

    with col_alarmes:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Alarmes</h3>',
            unsafe_allow_html=True,
        )
        if not alarmes:
            st.info("Nenhum alarme configurado.")
        else:
            html = "".join(_alarme_card_html(a) for a in alarmes if isinstance(a, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)

    with col_tarefas:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Tarefas</h3>',
            unsafe_allow_html=True,
        )
        if not tarefas:
            st.info("Nenhuma tarefa configurada.")
        else:
            html = "".join(_tarefa_card_html(t) for t in tarefas if isinstance(t, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)

    with col_contadores:
        st.markdown(
            f'<h3 style="font-family:ui-monospace,monospace;font-size:11px;'
            f'letter-spacing:0.10em;text-transform:uppercase;'
            f'color:{CORES["texto_muted"]};margin:0 0 12px;">Contadores</h3>',
            unsafe_allow_html=True,
        )
        if not contadores:
            st.info("Nenhum contador configurado.")
        else:
            html = "".join(_contador_card_html(c) for c in contadores if isinstance(c, dict))
            st.markdown(minificar(html), unsafe_allow_html=True)


# "A rotina é a coluna vertebral da liberdade." -- Friedrich Nietzsche
