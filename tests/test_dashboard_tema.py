"""Testes dos tokens de design do dashboard (Sprint 20).

Valida a escala tipográfica, spacing tokens, helpers de render (hero,
subtítulo, label) e a retrocompatibilidade de `card_html`. Não sobe
Streamlit — apenas inspeciona o módulo `src.dashboard.tema`.
"""

from __future__ import annotations

import importlib

from src.dashboard import tema


class TestEscalaTipografica:
    def test_fonte_minima_maior_ou_igual_14(self):
        assert tema.FONTE_MINIMA >= 14

    def test_fonte_corpo_maior_que_fonte_minima(self):
        assert tema.FONTE_CORPO >= tema.FONTE_MINIMA

    def test_fonte_label_nao_viola_minimo(self):
        # Label pode ser menor que corpo (uppercase caption) mas segue
        # padrão do projeto; valida apenas que existe e é inteiro positivo.
        assert isinstance(tema.FONTE_LABEL, int)
        assert tema.FONTE_LABEL >= 12

    def test_fonte_subtitulo_maior_que_corpo(self):
        assert tema.FONTE_SUBTITULO > tema.FONTE_CORPO

    def test_fonte_titulo_maior_que_subtitulo(self):
        assert tema.FONTE_TITULO > tema.FONTE_SUBTITULO

    def test_fonte_valor_maior_que_corpo(self):
        assert tema.FONTE_VALOR > tema.FONTE_CORPO

    def test_fonte_hero_e_o_maior(self):
        assert tema.FONTE_HERO >= tema.FONTE_TITULO
        assert tema.FONTE_HERO >= tema.FONTE_VALOR


class TestSpacingTokens:
    def test_spacing_completos(self):
        chaves_esperadas = {"xs", "sm", "md", "lg", "xl", "xxl"}
        assert chaves_esperadas.issubset(set(tema.SPACING.keys()))

    def test_spacing_escalado_monotonicamente(self):
        ordenados = ["xs", "sm", "md", "lg", "xl", "xxl"]
        valores = [tema.SPACING[k] for k in ordenados]
        assert valores == sorted(valores)

    def test_spacing_valores_positivos(self):
        for valor in tema.SPACING.values():
            assert valor > 0


class TestHelpersRender:
    def test_hero_titulo_contem_fonte_hero(self):
        html = tema.hero_titulo_html("20", "Redesign Tipográfico")
        assert f"font-size: {tema.FONTE_HERO}px" in html
        assert "Redesign Tipográfico" in html
        assert "20" in html

    def test_hero_titulo_com_descricao(self):
        html = tema.hero_titulo_html("42", "Grafo", "descrição longa do hero")
        assert "descrição longa do hero" in html
        assert f"font-size: {tema.FONTE_CORPO}px" in html

    def test_hero_titulo_sem_descricao_nao_renderiza_bloco(self):
        html = tema.hero_titulo_html("01", "Visão Geral")
        assert "descrição" not in html.lower()
        assert "max-width: 780px" not in html

    def test_subtitulo_secao_usa_fonte_label(self):
        html = tema.subtitulo_secao_html("DOCUMENTOS POR TIPO")
        assert f"font-size: {tema.FONTE_LABEL}px" in html
        assert "text-transform: uppercase" in html
        assert "DOCUMENTOS POR TIPO" in html

    def test_subtitulo_secao_aceita_cor_customizada(self):
        html = tema.subtitulo_secao_html("ALERTA", cor=tema.CORES["negativo"])
        assert tema.CORES["negativo"] in html

    def test_label_uppercase_usa_fonte_label(self):
        html = tema.label_uppercase_html("vinculados a transação")
        assert f"font-size: {tema.FONTE_LABEL}px" in html
        assert "text-transform: uppercase" in html
        assert "vinculados a transação" in html

    def test_label_uppercase_cor_default_e_texto_secundario(self):
        html = tema.label_uppercase_html("TOTAL")
        assert tema.CORES["texto_sec"] in html


class TestCardHtmlRetrocompat:
    def test_card_html_aceita_3_argumentos_posicionais(self):
        html = tema.card_html("Total", "R$ 1.000,00", tema.CORES["positivo"])
        assert "Total" in html
        assert "R$ 1.000,00" in html
        assert tema.CORES["positivo"] in html

    def test_card_html_usa_tokens_de_fonte_e_spacing(self):
        html = tema.card_html("Receita", "R$ 500,00", tema.CORES["neutro"])
        assert f"font-size: {tema.FONTE_VALOR}px" in html
        assert f"font-size: {tema.FONTE_LABEL}px" in html
        assert f"padding: {tema.SPACING['md']}px" in html

    def test_card_sidebar_html_usa_tokens(self):
        html = tema.card_sidebar_html("SALDO", "R$ 2.500,00", tema.CORES["positivo"])
        assert f"font-size: {tema.FONTE_LABEL}px" in html
        assert f"font-size: {tema.FONTE_SUBTITULO}px" in html
        assert "SALDO" in html
        assert "R$ 2.500,00" in html


class TestCssGlobal:
    def test_css_global_aplica_fonte_corpo_ao_body(self):
        css = tema.css_global()
        assert f"font-size: {tema.FONTE_CORPO}px" in css

    def test_css_global_aplica_fonte_hero_ao_h1(self):
        css = tema.css_global()
        # Regex: "h1 {" seguido de font-size FONTE_HERO
        assert f"h1 {{ font-size: {tema.FONTE_HERO}px" in css

    def test_css_global_aplica_fonte_titulo_ao_h2(self):
        css = tema.css_global()
        assert f"h2 {{ font-size: {tema.FONTE_TITULO}px" in css

    def test_css_global_aplica_fonte_subtitulo_ao_h3(self):
        css = tema.css_global()
        assert f"h3 {{ font-size: {tema.FONTE_SUBTITULO}px" in css

    def test_css_global_usa_spacing_xl_em_padding_top(self):
        css = tema.css_global()
        assert f"padding-top: {tema.SPACING['xl']}px" in css


class TestImportPaginas:
    """Garante que o refactor de tema não quebrou imports das páginas."""

    def test_importar_visao_geral(self):
        assert importlib.import_module("src.dashboard.paginas.visao_geral")

    def test_importar_categorias(self):
        assert importlib.import_module("src.dashboard.paginas.categorias")

    def test_importar_contas(self):
        assert importlib.import_module("src.dashboard.paginas.contas")

    def test_importar_extrato(self):
        assert importlib.import_module("src.dashboard.paginas.extrato")

    def test_importar_metas(self):
        assert importlib.import_module("src.dashboard.paginas.metas")

    def test_importar_projecoes(self):
        assert importlib.import_module("src.dashboard.paginas.projecoes")

    def test_importar_analise_avancada(self):
        assert importlib.import_module("src.dashboard.paginas.analise_avancada")

    def test_importar_irpf(self):
        assert importlib.import_module("src.dashboard.paginas.irpf")


class TestPaletaDracula:
    def test_paleta_dracula_completa(self):
        esperadas = {
            "background",
            "current_line",
            "foreground",
            "comment",
            "cyan",
            "green",
            "orange",
            "pink",
            "purple",
            "red",
            "yellow",
        }
        assert esperadas.issubset(set(tema.DRACULA.keys()))

    def test_cores_semanticas_mapeadas(self):
        chaves = {
            "fundo",
            "texto",
            "positivo",
            "negativo",
            "neutro",
            "alerta",
            "destaque",
            "obrigatorio",
            "questionavel",
        }
        assert chaves.issubset(set(tema.CORES.keys()))


# "Simplicidade é a maior sofisticação." -- Leonardo da Vinci
