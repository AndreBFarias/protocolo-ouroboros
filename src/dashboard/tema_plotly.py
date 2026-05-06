"""Template Plotly Dracula espelhando a paleta tokens.css do mockup.

Espelha as cores e tipografia canônicas de ``novo-mockup/_shared/tokens.css``
e oferece um wrapper `st_plotly_chart_dracula(fig, **kwargs)` que:

1. Aplica template Dracula in-place no `fig` (paper bg, plot bg, axis,
   font Inter, color-sequence Dracula).
2. Suprime modebar (`displayModeBar: False`).
3. Repassa `**kwargs` para `st.plotly_chart` (suporta `on_select`,
   `key`, `width`, etc.).

Origem: UX-RD-FIX-09 (auditoria 2026-05-05 §7.12 + §8.4).
"""

from __future__ import annotations

from typing import Any, Final

import plotly.graph_objects as go

# Paleta canônica Dracula -- espelha tokens.css do mockup.
PALETA_DRACULA: Final[list[str]] = [
    "#bd93f9",  # purple (primary)
    "#ff79c6",  # pink
    "#50fa7b",  # green
    "#8be9fd",  # cyan
    "#f1fa8c",  # yellow
    "#ffb86c",  # orange
    "#ff5555",  # red
]

COR_BG_BASE: Final[str] = "#0e0f15"
COR_BG_SURFACE: Final[str] = "#1a1d28"
COR_BORDER_SUBTLE: Final[str] = "#313445"
COR_BORDER_STRONG: Final[str] = "#4a4f63"
COR_TEXT_PRIMARY: Final[str] = "#f8f8f2"
COR_TEXT_MUTED: Final[str] = "#6c6f7d"

# Layout template -- aplicado via fig.update_layout(**TEMPLATE_DRACULA["layout"]).
TEMPLATE_DRACULA: Final[dict[str, dict[str, Any]]] = {
    "layout": {
        "paper_bgcolor": COR_BG_BASE,
        "plot_bgcolor": COR_BG_SURFACE,
        "font": {"family": "Inter, sans-serif", "color": COR_TEXT_PRIMARY, "size": 13},
        "title": {
            "font": {
                "family": "JetBrains Mono",
                "size": 14,
                "color": COR_TEXT_PRIMARY,
            },
        },
        "colorway": PALETA_DRACULA,
        "xaxis": {
            "gridcolor": COR_BORDER_SUBTLE,
            "linecolor": COR_BORDER_STRONG,
            "tickfont": {
                "family": "JetBrains Mono",
                "size": 11,
                "color": COR_TEXT_MUTED,
            },
            "zerolinecolor": COR_BORDER_SUBTLE,
        },
        "yaxis": {
            "gridcolor": COR_BORDER_SUBTLE,
            "linecolor": COR_BORDER_STRONG,
            "tickfont": {
                "family": "JetBrains Mono",
                "size": 11,
                "color": COR_TEXT_MUTED,
            },
            "zerolinecolor": COR_BORDER_SUBTLE,
        },
        "legend": {
            "font": {
                "family": "Inter",
                "size": 12,
                "color": COR_TEXT_PRIMARY,
            },
        },
        "hoverlabel": {
            "font": {"family": "JetBrains Mono", "size": 12},
            "bgcolor": COR_BG_SURFACE,
            "bordercolor": COR_BORDER_STRONG,
        },
        "margin": {"l": 40, "r": 16, "t": 32, "b": 40},
    },
}

# Config Plotly canônica do mockup (zero modebar, sem logo, responsive).
PLOTLY_CONFIG_NO_MODEBAR: Final[dict[str, Any]] = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}


def aplicar_tema(fig: go.Figure) -> go.Figure:
    """Aplica template Dracula in-place no `fig` e retorna a referência.

    Não altera dados; apenas paleta + axis + fonts + bg colors.
    """
    fig.update_layout(**TEMPLATE_DRACULA["layout"])
    return fig


def st_plotly_chart_dracula(fig: go.Figure, **kwargs: Any) -> Any:
    """Wrapper que aplica template Dracula + suprime modebar + repassa kwargs.

    Args:
        fig: figura Plotly. Será modificada in-place via `aplicar_tema`.
        **kwargs: repassados para ``st.plotly_chart``. Comuns:
            - ``use_container_width=True`` (default deste wrapper).
            - ``on_select="rerun"`` (drilldown).
            - ``key="..."`` (múltiplos charts na mesma tela).
            - ``config={...}`` (merge com PLOTLY_CONFIG_NO_MODEBAR; o wrapper
              garante displayModeBar=False sempre).

    Returns:
        Mesmo retorno de ``st.plotly_chart`` (pode ser dict de seleção
        quando ``on_select`` é passado).
    """
    # Import lazy permite monkeypatch.setitem(sys.modules, "streamlit", fake)
    # nos testes que substituem o módulo streamlit por dublê.
    import streamlit as st  # noqa: PLC0415

    fig = aplicar_tema(fig)
    config_user = kwargs.pop("config", {}) or {}
    config = {**PLOTLY_CONFIG_NO_MODEBAR, **config_user, "displayModeBar": False}
    if "use_container_width" not in kwargs and "width" not in kwargs:
        kwargs["use_container_width"] = True
    return st.plotly_chart(fig, config=config, **kwargs)


# "A graça do desenho está em saber o que omitir." -- Mies van der Rohe (paráfrase)
