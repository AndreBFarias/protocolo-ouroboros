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
    return minificar(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:flex-end;
                    margin-bottom:18px;border-bottom:1px solid {CORES['texto_sec']}33;
                    padding-bottom:14px;">
            <div>
                <h1 style="margin:0;font-size:24px;letter-spacing:0.04em;
                            color:{CORES['texto']};">ROTINA</h1>
                <p style="margin:4px 0 0;color:{CORES['texto_sec']};font-size:13px;">
                    Alarmes recorrentes, tarefas e contadores diários.
                    Persiste em
                    <code style="color:{CORES['destaque']};
                                  background:{CORES['fundo_inset']};
                                  padding:1px 6px;border-radius:2px;">
                        .ouroboros/rotina.toml
                    </code>.
                </p>
            </div>
            <div style="font-family:ui-monospace,monospace;font-size:11px;
                        color:{CORES['texto_muted']};letter-spacing:0.04em;">
                <span style="background:{CORES['fundo_inset']};padding:3px 8px;
                              border:1px solid {CORES['texto_sec']}33;
                              border-radius:4px;">UX-RD-19</span>
                <span style="margin-left:8px;">
                    {qtd_alarmes} alarmes · {qtd_tarefas} tarefas · {qtd_contadores} contadores
                </span>
            </div>
        </div>
        """
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
    """Renderiza a página Bem-estar / Rotina.

    Args:
        dados: estrutura padrão (não consumida).
        periodo: período da sidebar (ignorado).
        pessoa: pessoa da sidebar (ignorado nesta visualização).
        ctx: contexto extra (ignorado).
    """
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
        st.warning(
            f"Arquivo `{caminho}` não encontrado. "
            "Use a aba **Editor TOML** para criar a rotina inicial."
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
