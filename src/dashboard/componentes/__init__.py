"""Componentes reutilizáveis do dashboard.

Sprint 62 introduziu o primeiro componente com responsividade embutida:
`card.kpi_card_html` e `card.kpi_grid_html` substituem o uso direto de
`st.columns(3)` + `tema.card_html()` quando se deseja grid fluido com
breakpoints CSS em vez de layout rígido.
"""

from src.dashboard.componentes.card import (
    kpi_card_html,
    kpi_grid_html,
)

__all__ = [
    "kpi_card_html",
    "kpi_grid_html",
]


# "A forma segue a função." -- Louis Sullivan
