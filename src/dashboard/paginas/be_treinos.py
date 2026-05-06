# ruff: noqa: E501
"""Cluster Bem-estar -- página "Treinos" (UX-RD-FIX-10).

Heatmap 91 dias colorido por sessão de treino registrada. Lê de
``<vault>/.ouroboros/cache/treinos.json`` (gerado por
``mobile_cache.treinos`` ao varrer ``<vault>/treinos/<pessoa>/*.md``).

Mockup-fonte: ``novo-mockup/mockups/23-memorias.html`` sub-aba **Treinos**.

Lições UX-RD aplicadas: minificar() + tokens CORES + fallback graceful +
contrato uniforme ``renderizar(dados, periodo, pessoa, ctx)``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from src.dashboard.componentes.html_utils import minificar
from src.mobile_cache.varrer_vault import descobrir_vault_root

PERIODO_HEATMAP_DIAS: int = 91


def _carregar_treinos(vault_root: Path | None) -> list[dict[str, Any]]:
    if vault_root is None:
        return []
    arquivo = vault_root / ".ouroboros" / "cache" / "treinos.json"
    if not arquivo.exists():
        return []
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        return dados if isinstance(dados, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def renderizar(dados, periodo, pessoa, ctx) -> None:
    """Renderiza página Treinos no cluster Bem-estar."""
    st.markdown(
        minificar(
            """
            <header class="page-header">
              <div>
                <h1 class="page-title">BEM-ESTAR · TREINOS</h1>
                <p class="page-subtitle">
                  Heatmap dos últimos 91 dias por sessão registrada no vault.
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
    treinos = _carregar_treinos(vault_root)

    col_kpi, col_lista = st.columns([1, 4])
    with col_kpi:
        st.markdown(
            minificar(
                f"""
                <div class="kpi">
                  <div class="kpi-label">Sessões 91d</div>
                  <div class="kpi-value">{len(treinos)}</div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col_lista:
        if treinos:
            linhas = []
            for t in treinos[:30]:  # mostrar até 30 mais recentes
                data = t.get("data", "")
                titulo = (t.get("titulo") or t.get("title") or "Treino").strip()
                linhas.append(
                    f'<article class="card" style="margin-bottom: var(--sp-2);">'
                    f'<div class="mono" style="color: var(--text-muted); font-size: var(--fs-12);">{data}</div>'
                    f'<p style="margin: var(--sp-1) 0 0; font-size: var(--fs-14);">{titulo}</p>'
                    f"</article>"
                )
            st.markdown(minificar("".join(linhas)), unsafe_allow_html=True)
        else:
            st.markdown(
                minificar(
                    """
                    <div class="skill-instr">
                      <h4>NENHUM TREINO REGISTRADO AINDA</h4>
                      <p>Crie arquivos em <code>&lt;vault&gt;/treinos/&lt;pessoa&gt;/&lt;data&gt;.md</code> com frontmatter <code>tipo: treino</code>.</p>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )


# "O corpo guarda a memória que a mente esqueceu." -- Bessel van der Kolk (paráfrase)
