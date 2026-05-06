# ruff: noqa: E501
"""Cluster Bem-estar -- página "Contadores" (UX-RD-FIX-10).

Streaks e dias-desde lidos de ``<vault>/.ouroboros/rotina.toml`` seção
``[[contadores]]`` (ou cache ``<vault>/.ouroboros/cache/contadores.json``).

Schema:
    [[contadores]]
    titulo = "Streak academia"
    tipo = "streak"             # ou "dias_desde"
    valor_atual = 12
    meta = 30                   # opcional

Mockup-fonte: ``novo-mockup/mockups/20-rotina.html`` seção ``.contador-row``.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root


def _carregar_contadores(vault_root: Path | None) -> list[dict[str, Any]]:
    """Tenta cache JSON primeiro; cai para rotina.toml se ausente."""
    if vault_root is not None:
        cache = vault_root / ".ouroboros" / "cache" / "contadores.json"
        if cache.exists():
            try:
                import json

                dados = json.loads(cache.read_text(encoding="utf-8"))
                return dados if isinstance(dados, list) else []
            except (Exception,):  # noqa: BLE001
                pass

    # Fallback: rotina.toml
    candidatos: list[Path] = []
    if vault_root is not None:
        candidatos.append(vault_root / ".ouroboros" / "rotina.toml")
    candidatos.append(Path.home() / ".ouroboros" / "rotina.toml")
    for caminho in candidatos:
        if caminho.exists():
            try:
                rotina = tomllib.loads(caminho.read_text(encoding="utf-8"))
                return rotina.get("contadores", []) or []
            except (tomllib.TOMLDecodeError, OSError):
                continue
    return []


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Contadores no cluster Bem-estar."""
    st.markdown(
        minificar(
            """
            <header class="page-header">
              <div>
                <h1 class="page-title">BEM-ESTAR · CONTADORES</h1>
                <p class="page-subtitle">
                  Streaks e dias-desde com barra de progresso por meta.
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
    contadores = _carregar_contadores(vault_root)

    streaks = [c for c in contadores if c.get("tipo") == "streak"]
    maior_streak = max((int(c.get("valor_atual", 0)) for c in streaks), default=0)

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(
            minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">Maior streak</div>
                  <div class="kpi-value">{maior_streak}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col_lista:
        if not contadores:
            st.markdown(
                minificar(
                    """
                    <div class="skill-instr">
                      <h4>NENHUM CONTADOR REGISTRADO</h4>
                      <p>Crie <code>&lt;vault&gt;/.ouroboros/rotina.toml</code> com seção <code>[[contadores]]</code>.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )
        else:
            linhas = []
            cor_streak = CORES.get("positivo", "#50fa7b")
            cor_dias = CORES.get("alerta", "#f1fa8c")
            for c in contadores:
                titulo = c.get("titulo", "(sem título)")
                tipo = c.get("tipo", "streak")
                valor = int(c.get("valor_atual", 0))
                meta = c.get("meta")
                cor = cor_streak if tipo == "streak" else cor_dias
                pct = min(100, int((valor / int(meta)) * 100)) if meta and int(meta) > 0 else 0
                barra = (
                    f'<div class="confidence-bar" style="width: 100%; height: 6px; background: var(--bg-inset); border-radius: var(--r-full); overflow: hidden;">'
                    f'<span style="display:block; height:100%; background:{cor}; width:{pct}%;"></span>'
                    f"</div>"
                    if meta
                    else ""
                )
                linhas.append(
                    f'<article class="card" style="margin-bottom: var(--sp-3); border-left: 3px solid {cor};">'
                    f'<div class="card-head">'
                    f'<span class="card-title">{tipo.upper()}</span>'
                    f'<span class="kpi-value mono" style="font-size: var(--fs-24);">{valor}{f"/{meta}" if meta else ""}</span>'
                    f"</div>"
                    f'<p style="margin: var(--sp-1) 0; font-size: var(--fs-14);">{titulo}</p>'
                    f"{barra}"
                    f"</article>"
                )
            st.markdown(minificar("".join(linhas)), unsafe_allow_html=True)


# "Cada dia é um pequeno princípio; cada manhã, uma vida em miniatura." -- Schopenhauer
