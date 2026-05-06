# ruff: noqa: E501
"""Cluster Bem-estar -- página "Marcos" (UX-RD-FIX-10).

Lista cronológica DESC dos marcos registrados no vault. Cada marco vem
de ``<vault>/marcos/<pessoa>/<data>.md`` com frontmatter:
    tipo: marco
    categoria: rotina | conquista | lembranca
    titulo: <texto>
    tags: [...]

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html`` sub-aba **Marcos**.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.dashboard.tema import CORES
from src.mobile_cache.varrer_vault import descobrir_vault_root

CORES_CATEGORIA: dict[str, str] = {
    "rotina": CORES.get("neutro", "#8be9fd"),
    "conquista": CORES.get("positivo", "#50fa7b"),
    "lembranca": CORES.get("alerta", "#f1fa8c"),
}


def _carregar_marcos(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "marcos.json"
    if not arquivo.exists():
        return []
    try:
        marcos = json.loads(arquivo.read_text(encoding="utf-8"))
        if not isinstance(marcos, list):
            return []
        return sorted(marcos, key=lambda m: str(m.get("data", "")), reverse=True)
    except (json.JSONDecodeError, OSError):
        return []


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Marcos no cluster Bem-estar."""
    st.markdown(
        minificar(
            """
            <header class="page-header">
              <div>
                <h1 class="page-title">BEM-ESTAR · MARCOS</h1>
                <p class="page-subtitle">
                  Lista cronológica DESC dos marcos registrados no vault.
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
    marcos = _carregar_marcos(vault_root)

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(
            minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">Total marcos</div>
                  <div class="kpi-value">{len(marcos)}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col_lista:
        if marcos:
            linhas = []
            for m in marcos:
                cat = str(m.get("categoria", "rotina")).lower()
                cor = CORES_CATEGORIA.get(cat, CORES_CATEGORIA["rotina"])
                data = m.get("data", "")
                titulo = (m.get("titulo") or m.get("title") or "").strip()
                tags = " · ".join(m.get("tags", [])) if m.get("tags") else ""
                linhas.append(
                    f'<article class="card" style="border-left: 3px solid {cor}; margin-bottom: var(--sp-3);">'
                    f'<div class="card-head">'
                    f'<span class="card-title">{cat.upper()}</span>'
                    f'<span class="mono" style="color: var(--text-muted)">{data}</span>'
                    f"</div>"
                    f'<p style="margin: 0; font-size: var(--fs-14)">{titulo}</p>'
                    + (
                        f'<p style="margin: var(--sp-1) 0 0; color: var(--text-muted); font-size: var(--fs-12)">{tags}</p>'
                        if tags
                        else ""
                    )
                    + "</article>"
                )
            st.markdown(minificar("".join(linhas)), unsafe_allow_html=True)
        else:
            st.markdown(
                minificar(
                    """
                    <div class="skill-instr">
                      <h4>NENHUM MARCO REGISTRADO</h4>
                      <p>Crie arquivos em <code>&lt;vault&gt;/marcos/&lt;pessoa&gt;/&lt;data&gt;.md</code> com frontmatter <code>tipo: marco</code>.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )


# "O passado nunca morre. Não é nem passado." -- William Faulkner
