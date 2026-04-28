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


class TestSprintUX122HeroSemNumero:
    """Sprint UX-122: ``hero_titulo_html`` aceita ``numero=''`` por default.

    Quando numero == '', o ``<span>`` do badge não é renderizado (HTML
    enxuto, header mostra apenas o título). Retrocompat: chamadas antigas
    com primeiro arg numérico seguem renderizando o badge.
    """

    def test_hero_sem_numero_omite_span_de_badge(self):
        # Default: numero=''. <span> de 48px (badge) não aparece.
        html = tema.hero_titulo_html("", "Visão Geral")
        assert "Visão Geral" in html
        assert "font-size: 48px" not in html  # badge font-size

    def test_hero_sem_numero_via_keyword(self):
        # Chamada nova canônica: hero_titulo_html(texto='X')
        html = tema.hero_titulo_html(texto="Pagamentos")
        assert "Pagamentos" in html
        assert "font-size: 48px" not in html

    def test_hero_com_numero_retrocompat_preserva_badge(self):
        # Retrocompat: chamada antiga 2-args posicional renderiza badge.
        html = tema.hero_titulo_html("07", "Metas")
        assert "Metas" in html
        assert "font-size: 48px" in html
        assert ">07</span>" in html

    def test_hero_sem_numero_com_descricao_renderiza_descricao(self):
        html = tema.hero_titulo_html("", "Categorias", "Treemap de despesas")
        assert "Treemap de despesas" in html
        assert "font-size: 48px" not in html
        assert f"font-size: {tema.FONTE_CORPO}px" in html

    def test_paginas_nao_passam_prefixo_numerico_ao_hero(self):
        # Sweep agregado: nenhum arquivo em paginas/ passa "DD" como
        # primeiro arg de hero_titulo_html. Sprint UX-122.
        import re
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "paginas"
        padrao = re.compile(r"hero_titulo_html\(\s*[\"']\d")
        violacoes: list[str] = []
        for arquivo in raiz.glob("*.py"):
            texto = arquivo.read_text(encoding="utf-8")
            for linha_idx, _linha in enumerate(texto.splitlines(), start=1):
                # Olha 2 linhas seguintes também (chamada multilinha).
                janela = "\n".join(texto.splitlines()[linha_idx - 1 : linha_idx + 2])
                if padrao.search(janela):
                    violacoes.append(f"{arquivo.name}:{linha_idx}")
                    break
        assert not violacoes, (
            f"Sprint UX-122 violada: arquivos passam prefixo numérico ao hero: {violacoes}"
        )

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

    def test_sprint_ux111_comment_customizado_para_contraste_alto(self):
        """Sprint UX-111: DRACULA['comment'] foi customizado de #6272A4 (Dracula
        original) para #c9c9cc para aumentar contraste contra fundo escuro
        em telas de baixo brilho. CORES['texto_sec'] e CORES['na'] herdam.
        """
        assert tema.DRACULA["comment"].lower() == "#c9c9cc"
        assert tema.CORES["texto_sec"].lower() == "#c9c9cc"
        assert tema.CORES["na"].lower() == "#c9c9cc"

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
        html = tema.metric_semantic_html("Saldo", "R$ 100,00", delta=10.0, cor=tema.CORES["alerta"])
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
        html = tema.breadcrumb_drilldown_html({"categoria": "Aluguel", "banco": "Itaú"})
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


class TestSprintUX112TokensSpacingBorda:
    """Sprint UX-112: tokens universais de padding/borda + regras em css_global."""

    def test_padding_interno_definido_e_24px(self):
        assert tema.PADDING_INTERNO == 24

    def test_padding_chip_definido_e_16px(self):
        assert tema.PADDING_CHIP == 16

    def test_borda_raio_definido_e_8px(self):
        assert tema.BORDA_RAIO == 8

    def test_borda_ativa_definida_e_2px(self):
        assert tema.BORDA_ATIVA_PX == 2

    def test_css_global_publica_tokens_em_root(self):
        css = tema.css_global()
        assert f"--padding-interno: {tema.PADDING_INTERNO}px" in css
        assert f"--padding-chip: {tema.PADDING_CHIP}px" in css
        assert f"--borda-raio: {tema.BORDA_RAIO}px" in css
        assert f"--borda-ativa-px: {tema.BORDA_ATIVA_PX}px" in css

    def test_css_global_aplica_borda_em_inputs(self):
        css = tema.css_global()
        assert '[data-testid="stTextInput"]' in css
        assert '[data-testid="stSelectbox"]' in css
        assert '[data-testid="stMultiSelect"]' in css
        assert "border-radius: var(--borda-raio)" in css

    def test_css_global_aplica_borda_destacada_em_focus(self):
        css = tema.css_global()
        assert '[data-testid="stTextInput"]:focus-within' in css
        assert "border: var(--borda-ativa-px) solid" in css

    def test_css_global_aplica_padding_no_painel_de_tabs(self):
        css = tema.css_global()
        assert '.stTabs [data-baseweb="tab-panel"]' in css
        assert "padding-top: var(--padding-chip)" in css

    def test_css_global_aplica_borda_em_expander(self):
        css = tema.css_global()
        assert '[data-testid="stExpander"]' in css


class TestSprintUX116Padding4Direcoes:
    """Sprint UX-116: padding 4 direcoes universal em .main e sidebar.

    UX-112 estabeleceu PADDING_INTERNO=24 e PADDING_CHIP=16 mas aplicou
    apenas em inputs/expanders. UX-116 publica regras explicitas
    padding-{top,right,bottom,left} em dois retangulos universais
    (.main .block-container e [data-testid='stSidebar'] > div:first-child)
    para garantir respiro visual em todas as abas.
    """

    def test_main_block_container_tem_4_paddings_explicitos(self):
        css = tema.css_global()
        valor = f"{tema.PADDING_INTERNO}px"
        assert f"padding-top: {valor}" in css
        assert f"padding-right: {valor}" in css
        assert f"padding-bottom: {valor}" in css
        assert f"padding-left: {valor}" in css

    def test_main_block_container_usa_token_padding_interno(self):
        # Garante que valor deriva do token (não hardcoded). Se alguém mudar
        # PADDING_INTERNO para 32, o CSS muda junto.
        css = tema.css_global()
        assert ".main .block-container" in css
        assert css.count(f"padding-top: {tema.PADDING_INTERNO}px") >= 1
        assert css.count(f"padding-right: {tema.PADDING_INTERNO}px") >= 1
        assert css.count(f"padding-bottom: {tema.PADDING_INTERNO}px") >= 1
        assert css.count(f"padding-left: {tema.PADDING_INTERNO}px") >= 1

    def test_sidebar_interna_tem_4_paddings_explicitos(self):
        css = tema.css_global()
        valor = f"{tema.PADDING_CHIP}px"
        assert '[data-testid="stSidebar"] > div:first-child' in css
        assert f"padding-top: {valor}" in css
        assert f"padding-right: {valor}" in css
        assert f"padding-bottom: {valor}" in css
        assert f"padding-left: {valor}" in css

    def test_sidebar_interna_usa_token_padding_chip(self):
        css = tema.css_global()
        assert css.count(f"padding-top: {tema.PADDING_CHIP}px") >= 1
        assert css.count(f"padding-right: {tema.PADDING_CHIP}px") >= 1
        assert css.count(f"padding-bottom: {tema.PADDING_CHIP}px") >= 1
        assert css.count(f"padding-left: {tema.PADDING_CHIP}px") >= 1

    def test_regressao_sprint_76_padding_pagina_padrao_continua_definido(self):
        # Sprint 76 estabeleceu PADDING_PAGINA_PADRAO_PX=24 como contrato.
        # UX-116 substitui shorthand por 4 declaracoes explicitas, mas o token
        # da Sprint 76 e o valor canonico (24px == PADDING_INTERNO) continuam.
        assert tema.PADDING_PAGINA_PADRAO_PX == 24
        assert tema.PADDING_INTERNO == tema.PADDING_PAGINA_PADRAO_PX

    def test_regressao_main_block_container_continua_no_css(self):
        # Garante que o seletor .main .block-container continua presente
        # apos a refatoracao do shorthand para 4 direcoes (Sprint 76 + UX-116).
        css = tema.css_global()
        assert ".main .block-container" in css


class TestSprintUX115FaixasVaziasAlinhamento:
    """Sprint UX-115 + Sprint UX-119 AC14: pinta faixas vazias do bloco
    principal e unifica a cor com o sidebar.

    Antes de UX-115 o container externo do conteúdo (`[data-testid='stMain']`)
    ficava em `#282A36` (color-fundo), criando faixas escuras em volta do
    bloco interno. UX-115 pintou com literal `#444659` (gambiarra). UX-119
    AC14 substituiu o literal por `var(--color-card-fundo)` (token
    `CORES['card_fundo']` = `#44475A`), unificando exatamente com o tom da
    sidebar e eliminando a diferença de 1 ponto no canal verde detectada
    visualmente. Também garantimos contrato explícito de alinhamento à
    esquerda para `.ouroboros-label-icon`, usado pelo label "Busca global"
    da página de busca.
    """

    def test_st_main_usa_token_card_fundo_apos_ux119(self):
        # Sprint UX-119 AC14: literal `#444659` substituido por
        # var(--color-card-fundo). Garantimos que o seletor stMain ainda
        # existe e que o literal antigo desapareceu inteiramente do CSS.
        css = tema.css_global()
        assert '[data-testid="stMain"]' in css
        assert "#444659" not in css

    def test_st_main_background_associado_ao_seletor(self):
        # Verifica que a regra `background-color: var(--color-card-fundo)`
        # aparece logo depois do seletor stMain (a janela de 400 chars
        # cobre o bloco de declaracoes da regra).
        css = tema.css_global()
        idx_seletor = css.find('[data-testid="stMain"] {')
        assert idx_seletor >= 0, "seletor stMain ausente do css_global()"
        bloco = css[idx_seletor : idx_seletor + 400]
        assert "background-color: var(--color-card-fundo)" in bloco

    def test_label_icon_alinhado_a_esquerda(self):
        # Sprint UX-115: contrato explícito de alinhamento à esquerda no
        # label "Busca global" -- precisa começar exatamente em x=0 do
        # block-container, igual ao input principal.
        css = tema.css_global()
        idx = css.find(".ouroboros-label-icon {")
        assert idx >= 0, "regra .ouroboros-label-icon ausente"
        # Janela ampla -- a regra ganhou comentário multilinha + 3 declarações
        # novas além das 7 originais.
        bloco = css[idx : idx + 800]
        assert "margin-left: 0" in bloco
        assert "padding-left: 0" in bloco
        assert "justify-content: flex-start" in bloco

    def test_st_main_e_stapp_compartilham_token_card_fundo(self):
        # Sprint UX-119 AC14: stMain (UX-115) e stApp (UX-118) ambos usam
        # var(--color-card-fundo). Antes de UX-119, stMain era literal
        # `#444659` e stApp era `var(--color-card-fundo)`. Agora ambos
        # apontam para o mesmo token, eliminando a divergencia de 1 ponto
        # no canal verde (`#444659` vs `#44475A`) detectada visualmente.
        css = tema.css_global()
        idx_main = css.find('[data-testid="stMain"] {')
        idx_app = css.find('[data-testid="stApp"] {')
        assert idx_main >= 0 and idx_app >= 0
        bloco_main = css[idx_main : idx_main + 200]
        bloco_app = css[idx_app : idx_app + 200]
        assert "var(--color-card-fundo)" in bloco_main
        assert "var(--color-card-fundo)" in bloco_app


class TestSprintUX118PolishCombo:
    """Sprint UX-118: 4 micro-ajustes pós UX-115/116/117.

    1. Tabs sticky (.stTabs [data-baseweb='tab-list']) com border-bottom
       2px solid var(--color-destaque), position: sticky, top: 0, z-index: 10.
    2. [data-testid='stApp'] background trocado de #282A36 (default Dracula)
       para var(--color-card-fundo) (#44475A). Tokens permanecem intocados;
       apenas o seletor stApp passa a usar o tom card.
    3. Logo emitida com class='ouroboros-logo-img' e width=120; CSS global
       declara max-width: 120px, height: auto, aspect-ratio: 724 / 733.
    4. card_sidebar_html() injeta margin-left: 0 e box-sizing: border-box no
       <div> wrapper para evitar transbordo da borda 3px sobre o
       padding-left de 16px (PADDING_CHIP) da sidebar (UX-116).
    """

    # AC1 -- tabs sticky + linha 2px destaque
    def test_ac1_tabs_tem_position_sticky_e_top_zero(self):
        css = tema.css_global()
        # Localiza o segundo bloco da regra .stTabs [data-baseweb="tab-list"]
        # (introduzido pela UX-118; o primeiro define gap/background/min-height).
        idx = css.find('.stTabs [data-baseweb="tab-list"] {')
        assert idx >= 0, "regra UX-118 dedicada ao tab-list ausente"
        bloco = css[idx : idx + 400]
        assert "position: sticky" in bloco
        assert "top: 0" in bloco
        assert "z-index: 10" in bloco

    def test_ac1_tabs_tem_border_bottom_2px_destaque(self):
        css = tema.css_global()
        idx = css.find('.stTabs [data-baseweb="tab-list"] {')
        assert idx >= 0
        bloco = css[idx : idx + 400]
        assert "border-bottom: 2px solid var(--color-destaque)" in bloco

    def test_ac1_regras_originais_do_tab_list_preservadas(self):
        # Subregra retrocompatível (padrão l): regras antigas do bloco
        # .stTabs [data-baseweb="tab-list"], > div, > div:first-child
        # continuam presentes (gap, background-color, min-height,
        # overflow). UX-118 apenas adiciona uma regra dedicada.
        css = tema.css_global()
        idx = css.find('.stTabs [data-baseweb="tab-list"],')
        assert idx >= 0, "bloco original (3 seletores) ausente"
        bloco = css[idx : idx + 600]
        assert "gap:" in bloco
        assert "background-color:" in bloco
        assert "min-height: 60px" in bloco
        assert "overflow: visible" in bloco

    # AC2 -- stApp com card_fundo
    def test_ac2_stapp_tem_background_card_fundo(self):
        css = tema.css_global()
        idx = css.find('[data-testid="stApp"] {')
        assert idx >= 0, "seletor [data-testid='stApp'] ausente"
        bloco = css[idx : idx + 200]
        assert "background-color: var(--color-card-fundo)" in bloco

    def test_ac2_token_cores_fundo_intocado_em_282a36(self):
        # AC explicito do spec: token CORES['fundo'] permanece em #282A36
        # (DRACULA default). UX-118 muda apenas o seletor stApp, não o token.
        assert tema.CORES["fundo"].lower() == "#282a36"
        assert tema.DRACULA["background"].lower() == "#282a36"

    # AC3 -- logo dimensoes
    def test_ac3_css_logo_class_definida(self):
        css = tema.css_global()
        assert ".ouroboros-logo-img" in css
        idx = css.find(".ouroboros-logo-img {")
        assert idx >= 0
        bloco = css[idx : idx + 200]
        assert "max-width: 120px" in bloco
        assert "height: auto" in bloco
        assert "aspect-ratio: 724 / 733" in bloco

    def test_ac3_logo_sidebar_html_emite_class_e_width_120(self):
        # Emissão do <img> com class e width novos. Só roda se assets/icon.png
        # existir; pula caso ausente (mesmo padrão da Sprint 76).
        from pathlib import Path

        if not (Path(__file__).resolve().parents[1] / "assets" / "icon.png").exists():
            import pytest as _pytest

            _pytest.skip("assets/icon.png ausente -- skip emissão do <img>")
        html = tema.logo_sidebar_html()
        assert 'class="ouroboros-logo-img"' in html
        assert 'width="120"' in html

    def test_ac3_logo_sidebar_html_default_largura_e_120(self):
        # Default da assinatura subiu de 96 para 120 px (UX-118).
        import inspect

        sig = inspect.signature(tema.logo_sidebar_html)
        assert sig.parameters["largura_px"].default == 120

    # AC4 -- card_sidebar_html overflow fix
    def test_ac4_card_sidebar_tem_margin_left_zero(self):
        html = tema.card_sidebar_html("Saldo", "R$ 100,00", tema.CORES["positivo"])
        assert "margin-left: 0" in html

    def test_ac4_card_sidebar_tem_box_sizing_border_box(self):
        html = tema.card_sidebar_html("Saldo", "R$ 100,00", tema.CORES["positivo"])
        assert "box-sizing: border-box" in html

    def test_ac4_card_sidebar_preserva_border_left_3px(self):
        # Defesa: o fix UX-118 não remove a borda colorida 3px que dá
        # identidade visual aos cards (Receita verde / Despesa vermelha
        # / Saldo dependente do sinal). margin-left:0 + box-sizing:border-box
        # apenas evitam que a borda transborde a sidebar.
        html = tema.card_sidebar_html("Saldo", "R$ 100,00", "#50FA7B")
        assert "border-left: 3px solid #50FA7B" in html


class TestSprintUX119PolishV2:
    """Sprint UX-119: 11 micro-ajustes de polish pos cluster v1.

    AC1 -- label_visibility='collapsed' em busca_global_sidebar.py.
    AC2 -- stStatusWidget/stToast/stAlertContainer/stHeader em card_fundo.
    AC3 -- stSelectbox: min-height 44px + nowrap + overflow:hidden.
    AC4 -- 5 separadores intermediarios removidos de _sidebar() em app.py.
    AC6 -- stSidebar ganha border-right 2px solid var(--color-destaque).
    AC7 -- h1 dentro de stMainBlockContainer ganha margin-bottom: spacing-xl.
    AC10/11 -- chips e sugestoes uniformes via classes
              .ouroboros-chips-container e .ouroboros-sugestoes-container.
    AC13 -- [data-testid='stButton'] > button: min-height 44px + min-width
           140px + nowrap (cobre cards Catalogacao + chips + botoes em geral).
    AC14 -- literal #444659 trocado por var(--color-card-fundo) em tema.py
           (testado em TestSprintUX115FaixasVaziasAlinhamento).
    AC15 -- residuais #282A36 cobertos via stHeader/stStatusWidget/stToast/
           stAlertContainer (AC2 ja cobre).
    """

    # AC2 -- status widget e toast em card_fundo
    def test_ac2_status_widget_e_toast_em_card_fundo(self):
        css = tema.css_global()
        idx = css.find('[data-testid="stStatusWidget"]')
        assert idx >= 0, "regra UX-119 AC2 (stStatusWidget) ausente"
        bloco = css[idx : idx + 400]
        assert '[data-testid="stToast"]' in bloco
        assert '[data-testid="stAlertContainer"]' in bloco
        assert '[data-testid="stHeader"]' in bloco
        assert "background-color: var(--color-card-fundo)" in bloco

    # AC3 -- selectboxes com altura minima e nowrap
    def test_ac3_selectbox_min_height_44px(self):
        css = tema.css_global()
        # AC3: regra dedicada (a UX-119 adiciona um bloco para
        # `[data-testid="stSelectbox"] > div > div`) com min-height 44px.
        # Detectamos pelo "marcador" min-height: 44px proximo do seletor.
        idx = css.find('[data-testid="stSelectbox"] > div > div,')
        assert idx >= 0, "regra UX-119 AC3 (stSelectbox altura) ausente"
        bloco = css[idx : idx + 400]
        assert "min-height: 44px" in bloco
        assert "white-space: nowrap" in bloco

    def test_ac3_selectbox_combobox_overflow_hidden(self):
        css = tema.css_global()
        # Valor selecionado: overflow:hidden + text-overflow:ellipsis.
        idx = css.find('[data-testid="stSelectbox"] div[role="combobox"] > div')
        assert idx >= 0, "regra UX-119 AC3 (combobox interior) ausente"
        bloco = css[idx : idx + 200]
        assert "overflow: hidden" in bloco
        assert "text-overflow: ellipsis" in bloco

    # AC6 -- separador vertical roxo entre sidebar e body
    def test_ac6_sidebar_border_right_destaque(self):
        css = tema.css_global()
        # AC6: regra dedicada (segundo bloco) para stSidebar com
        # border-right 2px solid destaque.
        # Procuramos a substring exata que so existe no bloco UX-119.
        assert "border-right: 2px solid var(--color-destaque)" in css

    def test_ac6_sidebar_background_preservado(self):
        # Subregra retrocompatível (padrão l): a regra antiga UX-116
        # `[data-testid="stSidebar"] { background-color: ... }`
        # continua presente. UX-119 adiciona uma SEGUNDA regra com
        # border-right; não reescreve a primeira. Como UX-119 é inserida
        # ANTES (cosmeticamente) da regra original UX-116, ambas regras
        # com seletor `[data-testid="stSidebar"] {` coexistem; basta
        # detectar background-color em algum bloco do CSS após algum
        # `[data-testid="stSidebar"] {`.
        css = tema.css_global()
        # Conta quantas regras `[data-testid="stSidebar"] {` (com chave
        # aberta) existem no CSS -- esperamos pelo menos 2 (UX-119 nova
        # com border-right + UX-116 original com background).
        ocorrencias = css.count('[data-testid="stSidebar"] {')
        assert ocorrencias >= 2, (
            f'Esperado pelo menos 2 regras `[data-testid="stSidebar"] {{`'
            f" (UX-119 + UX-116); encontrei {ocorrencias}"
        )
        # Background da regra original (UX-116) sobrevive: pega a SEGUNDA
        # ocorrencia (rfind apos a primeira).
        idx_primeira = css.find('[data-testid="stSidebar"] {')
        idx_segunda = css.find('[data-testid="stSidebar"] {', idx_primeira + 1)
        assert idx_segunda >= 0
        bloco_segunda = css[idx_segunda : idx_segunda + 200]
        assert "background-color:" in bloco_segunda

    # AC7 -- padding-top header (h1 com margin-bottom)
    def test_ac7_h1_em_main_block_container_tem_margin_bottom(self):
        css = tema.css_global()
        idx = css.find('[data-testid="stMainBlockContainer"] h1')
        assert idx >= 0, "regra UX-119 AC7 (h1 main block container) ausente"
        bloco = css[idx : idx + 200]
        assert "margin-bottom:" in bloco

    # AC10/11 -- chips e sugestoes uniformes
    def test_ac10_chips_container_flex_wrap(self):
        css = tema.css_global()
        idx = css.find(".ouroboros-chips-container")
        assert idx >= 0, "classe UX-119 AC10 (chips-container) ausente"
        # Janela ampla cobre o bloco de chips + sugestoes (mesma regra).
        bloco = css[idx : idx + 600]
        assert "flex-wrap: wrap" in bloco
        assert "display: flex" in bloco

    def test_ac11_sugestoes_container_flex_wrap(self):
        css = tema.css_global()
        # AC11 espelha AC10: classe .ouroboros-sugestoes-container
        # registrada no CSS para uso futuro pela pagina busca.
        assert ".ouroboros-sugestoes-container" in css

    def test_ac10_11_buttons_internos_min_width_140(self):
        css = tema.css_global()
        # Regra especifica para botoes dentro dos containers de chips/
        # sugestoes: min-width 140px + nowrap + overflow ellipsis.
        idx = css.find('.ouroboros-chips-container [data-testid="stButton"]')
        assert idx >= 0, "regra UX-119 AC10/11 (button dentro de chips) ausente"
        bloco = css[idx : idx + 400]
        assert "min-width: 140px" in bloco
        assert "white-space: nowrap" in bloco

    # AC13 -- padronização global de stButton
    def test_ac13_stbutton_global_min_height_44_min_width_140(self):
        css = tema.css_global()
        # Regra global aplicada a TODOS os stButton do dashboard.
        # Encontra o bloco UX-119 dedicado (o último `[data-testid="stButton"] > button {`
        # do CSS). Reusamos rfind para pegar a regra UX-119, distinguindo
        # de regras parecidas em UX-112/UX-118 que mexem em downloadButton.
        idx = css.rfind('[data-testid="stButton"] > button {')
        assert idx >= 0, "regra UX-119 AC13 (stButton global) ausente"
        bloco = css[idx : idx + 300]
        assert "min-height: 44px" in bloco
        assert "min-width: 140px" in bloco
        assert "white-space: nowrap" in bloco

    # AC15 -- residuais #282A36 cobertos
    def test_ac15_stheader_em_card_fundo(self):
        # Coberto via mesma regra do AC2 (stHeader é um dos seletores).
        css = tema.css_global()
        idx = css.find('[data-testid="stHeader"]')
        assert idx >= 0, "AC15 (stHeader) não encontrado"
        # Confere que está dentro do bloco UX-119 (background card_fundo)
        # buscando a declaração em janela após o seletor agrupado.
        idx_bloco = css.find('[data-testid="stStatusWidget"]')
        bloco = css[idx_bloco : idx_bloco + 400]
        assert '[data-testid="stHeader"]' in bloco
        assert "background-color: var(--color-card-fundo)" in bloco

    # AC1 (UX-119) -- label_visibility revertido pela Sprint UX-125 AC4.
    # Agora a label "Busca Global" volta a ser visível (placeholder vazio).
    def test_ac1_busca_global_sidebar_label_visible(self):
        # Sprint UX-125 reverte UX-119 AC1: label_visibility "visible".
        # Texto duplicado some com placeholder="" (em vez de
        # "Buscar (documento, fornecedor, aba...)").
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[1]
            / "src/dashboard/componentes/busca_global_sidebar.py"
        )
        fonte = path.read_text(encoding="utf-8")
        assert 'label_visibility="visible"' in fonte
        assert 'label_visibility="collapsed"' not in fonte


# "Simplicidade é a maior sofisticação." -- Leonardo da Vinci
