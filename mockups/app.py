"""Entrypoint dos mockups Streamlit -- Sprints 20/51/52/53.

MOCKUP wireframe para validação de UX antes da implementação real.
Não é código de produção. Dados fictícios determinísticos.

Executar da raiz do projeto:
    .venv/bin/streamlit run mockups/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RAIZ_PROJETO: Path = Path(__file__).resolve().parents[1]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from mockups.pagina_20_redesign import renderizar as renderizar_20  # noqa: E402
from mockups.pagina_51_catalogacao import renderizar as renderizar_51  # noqa: E402
from mockups.pagina_52_busca import renderizar as renderizar_52  # noqa: E402
from mockups.pagina_53_grafo_obsidian import renderizar as renderizar_53  # noqa: E402
from mockups.tema_mockup import CORES, css_global  # noqa: E402

PAGINAS: dict[str, object] = {
    "51 — Catalogação de Documentos": renderizar_51,
    "52 — Busca Global": renderizar_52,
    "53 — Grafo + Obsidian": renderizar_53,
    "20 — Redesign Tipográfico": renderizar_20,
}


def _configurar() -> None:
    st.set_page_config(
        page_title="Mockups Ouroboros",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(css_global(), unsafe_allow_html=True)
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 1.8rem; max-width: 1360px; }}
        .stApp {{ background-color: {CORES["fundo"]}; }}
        [data-testid="stSidebar"] {{ background-color: {CORES["card_fundo"]}; }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            padding: 10px 12px;
            margin: 4px 0;
            border-radius: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _renderizar_sidebar() -> str:
    st.sidebar.markdown(
        f'<h2 style="color: {CORES["destaque"]}; margin: 8px 0 16px 0;">Mockups Ouroboros</h2>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f'<p style="color: {CORES["texto_sec"]}; font-size: 13px;'
        f' margin-bottom: 20px;">Wireframes navegáveis antes da implementação.'
        " Dados fictícios.</p>",
        unsafe_allow_html=True,
    )
    escolha = st.sidebar.radio(
        "Sprint",
        list(PAGINAS.keys()),
        label_visibility="collapsed",
    )
    st.sidebar.markdown(
        f'<div style="margin-top: 32px;'
        f" padding: 12px;"
        f" background-color: {CORES['fundo']};"
        f" border-radius: 8px;"
        f' border-left: 3px solid {CORES["alerta"]};">'
        f'<p style="color: {CORES["alerta"]}; font-size: 11px;'
        f" font-weight: 700; letter-spacing: 0.08em;"
        f' text-transform: uppercase; margin: 0 0 6px 0;">Aviso</p>'
        f'<p style="color: {CORES["texto_sec"]}; font-size: 12px;'
        f' margin: 0; line-height: 1.4;">Este app é mockup de UX.'
        " Não consulta grafo SQLite nem XLSX. Clique em ações não tem efeito real."
        "</p>"
        f"</div>",
        unsafe_allow_html=True,
    )
    return escolha


def main() -> None:
    _configurar()
    escolha = _renderizar_sidebar()
    renderizador = PAGINAS[escolha]
    renderizador()


if __name__ == "__main__":
    main()


# "O mapa não é o território." -- Alfred Korzybski
