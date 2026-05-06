# ruff: noqa: E501
"""Cluster Bem-estar -- página "Alarmes" (UX-RD-FIX-10).

Lista de alarmes ativos lidos de ``<vault>/.ouroboros/rotina.toml`` (ou
``~/.ouroboros/rotina.toml`` no fallback) seção ``[[alarmes]]``. Toggle
on/off é VISUAL (read-only nesta sprint; edição futura vai via Editor TOML
em FIX-14).

Schema esperado:
    [[alarmes]]
    hora = "06:30"
    titulo = "Acordar"
    dias = ["seg","ter","qua","qui","sex"]
    ativo = true

Mockup-fonte: ``novo-mockup/mockups/20-rotina.html`` seção ``.alarme-row``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root


def _carregar_rotina_toml(vault_root: Path | None) -> dict[str, Any]:
    """Carrega rotina.toml. Retorna dict vazio se ausente ou inválido."""
    candidatos: list[Path] = []
    if vault_root is not None:
        candidatos.append(vault_root / ".ouroboros" / "rotina.toml")
    candidatos.append(Path.home() / ".ouroboros" / "rotina.toml")

    for caminho in candidatos:
        if caminho.exists():
            try:
                return tomllib.loads(caminho.read_text(encoding="utf-8"))
            except (tomllib.TOMLDecodeError, OSError):
                continue
    return {}


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Alarmes no cluster Bem-estar."""
    st.markdown(
        minificar(
            """
            <header class="page-header">
              <div>
                <h1 class="page-title">BEM-ESTAR · ALARMES</h1>
                <p class="page-subtitle">
                  Alarmes ativos lidos do vault rotina.toml. Toggle visual (read-only).
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
    rotina = _carregar_rotina_toml(vault_root)
    alarmes: list[dict[str, Any]] = rotina.get("alarmes", []) or []

    ativos = [a for a in alarmes if a.get("ativo")]

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(
            minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">Ativos / Total</div>
                  <div class="kpi-value">{len(ativos)} / {len(alarmes)}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col_lista:
        if not alarmes:
            st.markdown(
                minificar(
                    """
                    <div class="skill-instr">
                      <h4>NENHUM ALARME REGISTRADO</h4>
                      <p>Crie <code>&lt;vault&gt;/.ouroboros/rotina.toml</code> com seção <code>[[alarmes]]</code>. Veja Editor TOML para template.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        else:
            linhas = []
            cor_ativo = CORES.get("destaque", "#bd93f9")
            cor_inativo = CORES.get("texto_muted", "#6c6f7d")
            for a in alarmes:
                hora = a.get("hora", "--:--")
                titulo = a.get("titulo", "(sem título)")
                dias = " ".join((d or "")[:1].upper() for d in (a.get("dias") or []))
                ativo = bool(a.get("ativo"))
                cor = cor_ativo if ativo else cor_inativo
                linhas.append(
                    f'<article class="card" style="display: grid; grid-template-columns: 80px 1fr auto; gap: var(--sp-3); align-items: center; margin-bottom: var(--sp-2); border-left: 3px solid {cor};">'
                    f'<div class="mono" style="font-size: var(--fs-20); font-weight: 500;">{hora}</div>'
                    f"<div>"
                    f'<p style="margin: 0; font-size: var(--fs-14); font-weight: 500;">{titulo}</p>'
                    f'<p style="margin: 2px 0 0; color: var(--text-muted); font-size: var(--fs-11);">{dias or "(diário)"}</p>'
                    f"</div>"
                    f'<div class="pill" style="color: {cor}; border-color: {cor};">{"ATIVO" if ativo else "PAUSADO"}</div>'
                    f"</article>"
                )
            st.markdown(minificar("".join(linhas)), unsafe_allow_html=True)


# "O tempo é o material de que o homem é feito." -- Jorge Luis Borges
