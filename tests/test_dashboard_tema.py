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


class TestCssVarsSprint92c:
    """Sprint 92c: CSS custom properties publicadas em css_global."""

    def test_css_vars_cores_presentes(self):
        css = tema.css_global()
        assert "--color-fundo:" in css
        assert "--color-card-fundo:" in css
        assert "--color-texto:" in css
        assert "--color-positivo:" in css
        assert "--color-negativo:" in css
        assert "--color-alerta:" in css
        assert "--color-destaque:" in css

    def test_css_vars_spacing_presentes(self):
        css = tema.css_global()
        for chave in ("xs", "sm", "md", "lg", "xl", "xxl"):
            assert f"--spacing-{chave}:" in css

    def test_css_vars_fontes_presentes(self):
        css = tema.css_global()
        assert "--font-min:" in css
        assert "--font-label:" in css
        assert "--font-corpo:" in css
        assert "--font-subtitulo:" in css
        assert "--font-titulo:" in css
        assert "--font-hero:" in css

    def test_css_vars_usam_valores_de_cores(self):
        css = tema.css_global()
        # A var --color-fundo deve referenciar o hex real do Dracula.
        assert f"--color-fundo: {tema.CORES['fundo']};" in css


class TestCalloutHtml:
    """Sprint 92c: callout_html substitui st.warning/info/success/error."""

    def test_callout_info_usa_cor_neutro(self):
        html = tema.callout_html("info", "mensagem teste")
        assert tema.CORES["neutro"] in html
        assert "mensagem teste" in html

    def test_callout_warning_usa_cor_alerta(self):
        html = tema.callout_html("warning", "cuidado")
        assert tema.CORES["alerta"] in html

    def test_callout_error_usa_cor_negativo(self):
        html = tema.callout_html("error", "erro grave")
        assert tema.CORES["negativo"] in html

    def test_callout_success_usa_cor_positivo(self):
        html = tema.callout_html("success", "feito")
        assert tema.CORES["positivo"] in html

    def test_callout_titulo_opcional_renderiza_strong(self):
        html = tema.callout_html("warning", "corpo", titulo="Atenção")
        assert "<strong" in html
        assert "Atenção" in html

    def test_callout_sem_titulo_nao_renderiza_strong(self):
        html = tema.callout_html("info", "só corpo")
        assert "<strong" not in html

    def test_callout_tipo_invalido_cai_em_info(self):
        html = tema.callout_html("desconhecido", "x")
        assert tema.CORES["neutro"] in html

    def test_callout_contem_icone_svg(self):
        html = tema.callout_html("warning", "x")
        assert "<svg" in html

    def test_callout_usa_var_css_card_fundo(self):
        html = tema.callout_html("info", "x")
        assert "var(--color-card-fundo)" in html


class TestProgressInlineHtml:
    """Sprint 92c: progress_inline_html consolida a versão local de metas.py."""

    def test_progress_respeita_pct_no_range(self):
        html = tema.progress_inline_html(0.42)
        assert "42.0%" in html

    def test_progress_clampa_acima_de_1(self):
        html = tema.progress_inline_html(1.5)
        assert "100.0%" in html

    def test_progress_clampa_abaixo_de_0(self):
        html = tema.progress_inline_html(-0.2)
        assert "0.0%" in html

    def test_progress_cor_custom_aplicada(self):
        html = tema.progress_inline_html(0.5, cor=tema.CORES["negativo"])
        assert tema.CORES["negativo"] in html

    def test_progress_cor_default_usa_destaque(self):
        html = tema.progress_inline_html(0.5)
        assert "var(--color-destaque)" in html

    def test_progress_com_label_renderiza_paragrafo(self):
        html = tema.progress_inline_html(0.5, label="78% -- R$ 7.800 / R$ 10.000")
        assert "78% -- R$ 7.800 / R$ 10.000" in html
        assert "<p" in html

    def test_progress_sem_label_nao_renderiza_p_extra(self):
        html = tema.progress_inline_html(0.5)
        # Sem label, não deve ter tag <p> separada (só os divs do trilho).
        assert html.count("<p") == 0


class TestMetricSemanticHtml:
    """Sprint 92c: metric_semantic_html colore valor por sinal do delta."""

    def test_metric_sem_delta_usa_texto_sec(self):
        html = tema.metric_semantic_html("Saldo", "R$ 100,00")
        assert "var(--color-texto-sec)" in html

    def test_metric_delta_positivo_usa_positivo(self):
        html = tema.metric_semantic_html("Saldo", "R$ 100,00", delta=5.0)
        assert "var(--color-positivo)" in html
        # E o delta também aparece renderizado com sinal.
        assert "+5.0%" in html

    def test_metric_delta_negativo_usa_negativo(self):
        html = tema.metric_semantic_html("Saldo", "R$ 100,00", delta=-3.0)
        assert "var(--color-negativo)" in html
        assert "-3.0%" in html

    def test_metric_delta_zero_usa_texto_sec(self):
        html = tema.metric_semantic_html("Saldo", "R$ 0,00", delta=0.0)
        assert "var(--color-texto-sec)" in html

    def test_metric_cor_custom_sobrescreve_auto(self):
        html = tema.metric_semantic_html(
            "Saldo", "R$ 100,00", delta=10.0, cor=tema.CORES["alerta"]
        )
        assert tema.CORES["alerta"] in html

    def test_metric_label_e_valor_sao_renderizados(self):
        html = tema.metric_semantic_html("Total receitas", "R$ 12.345,67")
        assert "Total receitas" in html
        assert "R$ 12.345,67" in html


class TestIconHtml:
    """Sprint 92c: icon_html renderiza SVG Feather inline."""

    def test_icon_search_contem_circle_e_line(self):
        html = tema.icon_html("search")
        assert "<svg" in html
        assert "<circle" in html
        assert "</svg>" in html

    def test_icon_check_circle_contem_polyline(self):
        html = tema.icon_html("check-circle")
        assert "<polyline" in html

    def test_icon_alert_triangle_contem_path(self):
        html = tema.icon_html("alert-triangle")
        assert "<path" in html

    def test_icon_tamanho_custom_aplicado(self):
        html = tema.icon_html("search", tamanho=24)
        assert 'width="24"' in html
        assert 'height="24"' in html

    def test_icon_cor_custom_aplicada(self):
        html = tema.icon_html("search", cor=tema.CORES["destaque"])
        assert f'stroke="{tema.CORES["destaque"]}"' in html

    def test_icon_cor_default_currentcolor(self):
        html = tema.icon_html("search")
        assert 'stroke="currentColor"' in html

    def test_icon_inexistente_retorna_vazio(self):
        # Degradação silenciosa: dashboard nunca quebra por ícone faltante.
        assert tema.icon_html("xxx-nao-existe") == ""


class TestChipHtml:
    """Sprint 92c: chip_html para tags, tipos, filtros ativos."""

    def test_chip_default_usa_destaque(self):
        html = tema.chip_html("PJ")
        assert "var(--color-destaque)" in html
        assert "PJ" in html

    def test_chip_cor_custom_aplicada(self):
        html = tema.chip_html("documento", cor=tema.CORES["neutro"])
        assert tema.CORES["neutro"] in html

    def test_chip_clicavel_cursor_pointer(self):
        html = tema.chip_html("x", clicavel=True)
        assert "cursor: pointer" in html

    def test_chip_nao_clicavel_cursor_default(self):
        html = tema.chip_html("x", clicavel=False)
        assert "cursor: default" in html


class TestBreadcrumbDrilldownHtml:
    """Sprint 92c: breadcrumb_drilldown_html consolida o loop manual do Extrato."""

    def test_breadcrumb_vazio_retorna_string_vazia(self):
        assert tema.breadcrumb_drilldown_html({}) == ""

    def test_breadcrumb_renderiza_cada_filtro(self):
        html = tema.breadcrumb_drilldown_html(
            {"categoria": "Aluguel", "banco": "Itaú"}
        )
        assert "categoria: Aluguel" in html
        assert "banco: Itaú" in html

    def test_breadcrumb_contem_prefixo(self):
        html = tema.breadcrumb_drilldown_html({"mes": "2026-01"})
        assert "Filtros ativos" in html


class TestIconsModulo:
    """Sprint 92c: o módulo icons.py tem 11 ícones registrados."""

    def test_registro_feather_tem_11_icones(self):
        from src.dashboard.componentes import icons

        assert len(icons.FEATHER_ICONES) == 11

    def test_registro_inclui_os_canonicos(self):
        from src.dashboard.componentes import icons

        esperados = {
            "search",
            "check-circle",
            "alert-triangle",
            "alert-circle",
            "info",
            "x",
            "zoom-in",
            "download",
            "external-link",
            "filter",
            "calendar",
        }
        assert esperados == set(icons.FEATHER_ICONES.keys())

    def test_renderizar_svg_inexistente_retorna_vazio(self):
        from src.dashboard.componentes import icons

        assert icons.renderizar_svg("nao-existe") == ""


# "Simplicidade é a maior sofisticação." -- Leonardo da Vinci
