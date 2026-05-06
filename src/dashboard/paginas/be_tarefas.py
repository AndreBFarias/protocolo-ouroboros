# ruff: noqa: E501
"""Cluster Bem-estar -- página "Tarefas" (UX-RD-FIX-10).

TODO operacional lido de ``<vault>/tarefas/<pessoa>/*.md`` (cache via
``<vault>/.ouroboros/cache/tarefas.json``) ou seção ``[[tarefas]]`` em
``rotina.toml``.

Schema:
    [[tarefas]]
    titulo = "Renovar CNH"
    prioridade = "alta"     # alta | media | baixa
    feita = false
    prazo = "2026-06-15"

Mockup-fonte: ``novo-mockup/mockups/20-rotina.html`` seção ``.tarefa-row``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

CORES_PRIORIDADE: dict[str, str] = {
    "alta": CORES.get("negativo", "#ff5555"),
    "media": CORES.get("alerta", "#f1fa8c"),
    "baixa": CORES.get("texto_muted", "#6c6f7d"),
}

PESO_PRIORIDADE: dict[str, int] = {"alta": 0, "media": 1, "baixa": 2}


def _carregar_tarefas(vault_root: Path | None) -> list[dict[str, Any]]:
    """Tenta cache JSON; cai para rotina.toml se ausente."""
    if vault_root is not None:
        cache = vault_root / ".ouroboros" / "cache" / "tarefas.json"
        if cache.exists():
            try:
                import json

                dados = json.loads(cache.read_text(encoding="utf-8"))
                return dados if isinstance(dados, list) else []
            except (Exception,):  # noqa: BLE001
                pass

    candidatos: list[Path] = []
    if vault_root is not None:
        candidatos.append(vault_root / ".ouroboros" / "rotina.toml")
    candidatos.append(Path.home() / ".ouroboros" / "rotina.toml")
    for caminho in candidatos:
        if caminho.exists():
            try:
                rotina = tomllib.loads(caminho.read_text(encoding="utf-8"))
                return rotina.get("tarefas", []) or []
            except (tomllib.TOMLDecodeError, OSError):
                continue
    return []


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Tarefas no cluster Bem-estar."""
    st.markdown(
        minificar(
            """
            <header class="page-header">
              <div>
                <h1 class="page-title">BEM-ESTAR · TAREFAS</h1>
                <p class="page-subtitle">
                  TODO operacional ordenado por prioridade. Read-only nesta sprint.
                </p>
              </div>
              <div class="page-meta">
                <span class="sprint-tag">UX-RD-FIX-10</span>
              </div>
            </header>
            """
        ),
        unsafe_allow_html=True,
    )

    vault_root = descobrir_vault_root()
    tarefas = _carregar_tarefas(vault_root)
    # ordem: não-feitas primeiro, depois prioridade alta -> baixa
    tarefas_ordenadas = sorted(
        tarefas,
        key=lambda t: (
            bool(t.get("feita")),
            PESO_PRIORIDADE.get(str(t.get("prioridade", "media")).lower(), 1),
        ),
    )

    pendentes = [t for t in tarefas if not t.get("feita")]

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(
            minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">Pendentes / Total</div>
                  <div class="kpi-value">{len(pendentes)} / {len(tarefas)}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col_lista:
        if not tarefas:
            st.markdown(
                minificar(
                    """
                    <div class="skill-instr">
                      <h4>NENHUMA TAREFA REGISTRADA</h4>
                      <p>Crie arquivos em <code>&lt;vault&gt;/tarefas/&lt;pessoa&gt;/*.md</code> ou seção <code>[[tarefas]]</code> em <code>rotina.toml</code>.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        else:
            linhas = []
            for t in tarefas_ordenadas:
                titulo = t.get("titulo", "(sem título)")
                prio = str(t.get("prioridade", "media")).lower()
                cor_prio = CORES_PRIORIDADE.get(prio, CORES_PRIORIDADE["media"])
                feita = bool(t.get("feita"))
                prazo = t.get("prazo", "")
                check = "[x]" if feita else "[ ]"
                style_feita = (
                    "opacity: 0.55; text-decoration: line-through;" if feita else ""
                )
                linhas.append(
                    f'<article class="card" style="display: grid; grid-template-columns: 24px 1fr auto; gap: var(--sp-3); align-items: center; margin-bottom: var(--sp-2); {style_feita}">'
                    f'<div class="mono" style="font-size: var(--fs-14); color: var(--text-muted);">{check}</div>'
                    f"<div>"
                    f'<p style="margin: 0; font-size: var(--fs-14); font-weight: 500;">{titulo}</p>'
                    + (
                        f'<p style="margin: 2px 0 0; color: var(--text-muted); font-size: var(--fs-11);">prazo {prazo}</p>'
                        if prazo
                        else ""
                    )
                    + f'<div class="pill" style="color: {cor_prio}; border-color: {cor_prio};">{prio.upper()}</div>'
                    + "</article>"
                )
            st.markdown(minificar("".join(linhas)), unsafe_allow_html=True)


# "A tarefa é simples: faça o próximo certo." -- Marco Aurélio (paráfrase)
