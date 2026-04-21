"""Testes de responsividade do dashboard (Sprint 62).

Valida o novo grid fluido de KPI cards e a tipografia `clamp()` que
substituem o layout rígido `st.columns(3)` nas páginas que o adotarem.
Os testes não sobem Streamlit; inspecionam apenas o HTML/CSS gerado pelos
helpers em `src.dashboard.componentes.card` e o CSS global em
`src.dashboard.tema`.
"""

from __future__ import annotations

import re

from src.dashboard import tema
from src.dashboard.componentes import card


class TestTokensFluidos:
    def test_fluid_valor_kpi_usa_clamp(self):
        assert tema.FLUID_VALOR_KPI.startswith("clamp(")
        assert "vw" in tema.FLUID_VALOR_KPI

    def test_fluid_label_kpi_usa_clamp(self):
        assert tema.FLUID_LABEL_KPI.startswith("clamp(")
        assert "vw" in tema.FLUID_LABEL_KPI

    def test_fluid_valor_min_maior_igual_fonte_minima_menos_1(self):
        # clamp(14px, 2vw, 22px) → min=14px; deve respeitar legibilidade.
        match = re.match(r"clamp\((\d+)px", tema.FLUID_VALOR_KPI)
        assert match is not None, "FLUID_VALOR_KPI deve começar com clamp(Npx, ...)"
        minimo = int(match.group(1))
        assert minimo >= 14, f"Mínimo de {minimo}px viola legibilidade (>=14)"

    def test_breakpoints_definidos_e_ordenados(self):
        assert tema.BREAKPOINT_COMPACTO > tema.BREAKPOINT_MINIMO
        assert tema.BREAKPOINT_COMPACTO <= 1200
        assert tema.BREAKPOINT_MINIMO >= 500


class TestKpiCardHtml:
    def test_card_contem_classes_responsivas(self):
        html = card.kpi_card_html("Taxa", "25%", tema.CORES["positivo"])
        assert 'class="kpi-card"' in html
        assert 'class="kpi-label"' in html
        assert 'class="kpi-valor"' in html

    def test_card_preserva_conteudo(self):
        html = card.kpi_card_html("Maior gasto: Impostos", "R$ 1.463,35", tema.CORES["alerta"])
        assert "Maior gasto: Impostos" in html
        assert "R$ 1.463,35" in html
        assert tema.CORES["alerta"] in html

    def test_card_aplica_cor_valor(self):
        html = card.kpi_card_html("Saldo", "R$ 0,00", tema.CORES["negativo"])
        # A cor deve aparecer duas vezes: borda esquerda e texto do valor.
        assert html.count(tema.CORES["negativo"]) >= 2


class TestKpiGridHtml:
    def test_grid_envolve_cards_com_classe(self):
        html = card.kpi_grid_html(
            [
                ("Taxa", "25%", tema.CORES["positivo"]),
                ("Gastos", "R$ 500,00", tema.CORES["superfluo"]),
                ("Maior", "R$ 1.463,35", tema.CORES["alerta"]),
            ]
        )
        assert '<div class="kpi-grid">' in html
        assert html.count('class="kpi-card"') == 3

    def test_grid_vazio_nao_quebra(self):
        html = card.kpi_grid_html([])
        assert '<div class="kpi-grid">' in html
        assert "kpi-card" not in html


class TestCssInlineFluido:
    def test_css_inline_contem_media_query(self):
        css = card.css_inline_fluido()
        assert "@media" in css
        assert "max-width" in css

    def test_css_inline_contem_clamp(self):
        css = card.css_inline_fluido()
        assert "clamp(" in css

    def test_css_inline_grid_fluido(self):
        css = card.css_inline_fluido()
        assert "grid-template-columns" in css
        assert "auto-fit" in css
        assert "minmax(" in css


class TestCssGlobalResponsivo:
    def test_css_global_contem_media_query_compacto(self):
        css = tema.css_global()
        assert f"@media (max-width: {tema.BREAKPOINT_COMPACTO}px)" in css

    def test_css_global_contem_media_query_minimo(self):
        css = tema.css_global()
        assert f"@media (max-width: {tema.BREAKPOINT_MINIMO}px)" in css

    def test_css_global_contem_clamp_valor(self):
        css = tema.css_global()
        assert tema.FLUID_VALOR_KPI in css

    def test_css_global_contem_clamp_label(self):
        css = tema.css_global()
        assert tema.FLUID_LABEL_KPI in css

    def test_css_global_grid_auto_fit(self):
        css = tema.css_global()
        assert "grid-template-columns: repeat(auto-fit" in css

    def test_css_global_kpi_grid_fallback_em_compacto(self):
        """No breakpoint compacto, o grid deve virar 2 colunas."""
        css = tema.css_global()
        # Busca o bloco @media (max-width: COMPACTO)
        trecho = css.split(f"@media (max-width: {tema.BREAKPOINT_COMPACTO}px)")[1]
        assert "repeat(2" in trecho

    def test_css_global_kpi_grid_fallback_em_minimo(self):
        """No breakpoint mínimo, o grid deve virar 1 coluna."""
        css = tema.css_global()
        trecho = css.split(f"@media (max-width: {tema.BREAKPOINT_MINIMO}px)")[1]
        assert "grid-template-columns: 1fr" in trecho


class TestIntegracaoVisaoGeral:
    """Garante que a refatoração não quebrou o import da página."""

    def test_visao_geral_importa_kpi_grid(self):
        from src.dashboard.paginas import visao_geral

        # `kpi_grid_html` deve estar disponível no namespace da página.
        assert hasattr(visao_geral, "kpi_grid_html")

    def test_componentes_expoe_helpers(self):
        from src.dashboard import componentes

        assert hasattr(componentes, "kpi_card_html")
        assert hasattr(componentes, "kpi_grid_html")


# "Responsivo é respeito ao usuário móvel." -- princípio web
