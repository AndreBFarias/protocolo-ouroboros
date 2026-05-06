"""Testes regressivos da Sprint UX-126 -- Polish iteração 3.

Cobre os 6 ACs:
- AC1: nomes humanizados nos balões "Documentos por tipo" via mapping YAML.
- AC2: padding simétrico ao redor dos cards de tipos.
- AC3: layout vertical "Documentos Recentes" 100% width + "Conflitos | Gaps"
        em st.columns([1, 1]) abaixo.
- AC4: hero `hero_titulo_html` chamado no topo de `catalogacao.renderizar()`.
- AC5: CSS `.ouroboros-logo-img` com `width: 120px !important`.
- AC6: caption sidebar reformatada em duas linhas centralizadas com travessões.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from src.dashboard.componentes.humanizar_tipos import (
    _resetar_cache_para_teste,
    carregar_mapping,
    humanizar,
)
from src.dashboard.tema import css_global

RAIZ = Path(__file__).resolve().parents[1]
MAPPING_PATH = RAIZ / "mappings" / "tipos_documento_humanizado.yaml"
CATALOGACAO_PATH = RAIZ / "src" / "dashboard" / "paginas" / "catalogacao.py"
APP_PATH = RAIZ / "src" / "dashboard" / "app.py"


class TestSprintUX126PolishIteracao3:
    """Bloco regressivo da Sprint UX-126."""

    def setup_method(self) -> None:
        """Limpa cache do humanizador antes de cada teste."""
        _resetar_cache_para_teste()

    # ----------------------------------------------------------------
    # AC1 -- mapping YAML + helper humanizar()
    # ----------------------------------------------------------------

    def test_ac1_mapping_yaml_existe_e_cobre_pelo_menos_oito_tipos(self) -> None:
        """O YAML existe e tem pelo menos 8 entradas canônicas."""
        assert MAPPING_PATH.exists(), f"YAML ausente em {MAPPING_PATH}"
        with MAPPING_PATH.open("r", encoding="utf-8") as f:
            conteudo = yaml.safe_load(f)
        assert isinstance(conteudo, dict)
        assert len(conteudo) >= 8, f"esperado >=8 entradas, achei {len(conteudo)}"
        # Tipos críticos do feedback do dono.
        for chave in (
            "holerite",
            "das_parcsn_andre",
            "boleto_servico",
            "dirpf_retif",
        ):
            assert chave in conteudo, f"chave canônica '{chave}' ausente"

    def test_ac1_humanizar_substitui_slugs_canonicos_por_nomes_humanos(self) -> None:
        """`humanizar()` devolve o nome humano dos slugs cobertos."""
        assert humanizar("holerite") == "Holerite"
        assert humanizar("das_parcsn_andre") == "DAS Parcelado André"  # anonimato-allow
        assert humanizar("boleto_servico") == "Boleto de Serviço"
        assert humanizar("dirpf_retif") == "DIRPF Retificadora"
        assert humanizar("nfce_modelo_65") == "Nota Fiscal Eletrônica"

    def test_ac1_humanizar_fallback_para_slug_nao_listado(self) -> None:
        """Slug não listado cai no fallback `replace('_', ' ').title()`."""
        # `slug_inexistente_xyz` -> "Slug Inexistente Xyz"
        assert humanizar("slug_inexistente_xyz") == "Slug Inexistente Xyz"

    def test_ac1_humanizar_string_vazia_devolve_vazio(self) -> None:
        """Defensivo: slug vazio -> string vazia."""
        assert humanizar("") == ""

    def test_ac1_carregar_mapping_devolve_dict_com_str(self) -> None:
        """`carregar_mapping()` devolve dict[str, str] (sanity check)."""
        mapping = carregar_mapping()
        assert isinstance(mapping, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items())

    def test_ac1_catalogacao_importa_humanizar(self) -> None:
        """A página Catalogação importa o helper de humanização."""
        conteudo = CATALOGACAO_PATH.read_text(encoding="utf-8")
        assert "from src.dashboard.componentes.humanizar_tipos import humanizar" in conteudo
        # Uso real (não import morto).
        assert "humanizar(tipo_tec)" in conteudo

    # ----------------------------------------------------------------
    # AC2 -- padding simétrico no container de cards
    # ----------------------------------------------------------------

    def test_ac2_css_aplica_margin_simetrico_em_horizontal_block(self) -> None:
        """CSS global tem margin-top e margin-bottom iguais em
        ``[data-testid="stHorizontalBlock"]``."""
        css = css_global()
        # Captura o bloco da regra.
        match = re.search(
            r'\[data-testid="stHorizontalBlock"\]\s*\{([^}]+)\}',
            css,
            re.DOTALL,
        )
        assert match, "regra para stHorizontalBlock não encontrada no CSS"
        bloco = match.group(1)
        # Extrai margin-top e margin-bottom.
        m_top = re.search(r"margin-top:\s*(\d+)px", bloco)
        m_bot = re.search(r"margin-bottom:\s*(\d+)px", bloco)
        assert m_top and m_bot, f"margin-top/bottom ausentes em: {bloco}"
        assert m_top.group(1) == m_bot.group(1), (
            f"padding NÃO simétrico: top={m_top.group(1)}px, bot={m_bot.group(1)}px"
        )

    # ----------------------------------------------------------------
    # AC3 -- layout vertical na Catalogação
    # ----------------------------------------------------------------

    def test_ac3_layout_documentos_recentes_ocupa_largura_total(self) -> None:
        """`catalogacao.renderizar` chama `_renderizar_tabela_documentos`
        FORA de `st.columns` (largura total)."""
        conteudo = CATALOGACAO_PATH.read_text(encoding="utf-8")
        # Captura a função renderizar (até o próximo def).
        match = re.search(
            r"def renderizar\(.*?\) -> None:(.*?)(?=\ndef\s)",
            conteudo,
            re.DOTALL,
        )
        assert match, "função renderizar não encontrada"
        corpo = match.group(1)
        # AC3a: tabela está fora de columns.
        # Procura por `_renderizar_tabela_documentos(docs)` precedido por linha
        # SEM indentação extra de `with col_principal:`.
        # Padrão antigo (ruim): `with col_principal:\n        _renderizar_tabela_documentos`.
        padrao_antigo = re.search(
            r"with col_principal:[^\n]*\n\s+_renderizar_tabela_documentos",
            corpo,
        )
        assert not padrao_antigo, (
            "layout antigo detectado: tabela ainda dentro de st.columns([2, 1])"
        )
        # Padrão novo: chamada na coluna base (4 espaços de indent).
        # Aceita qualquer indent menor que o de `with col_*:`.
        padrao_novo = re.search(
            r"\n    _renderizar_tabela_documentos\(docs\)",
            corpo,
        )
        assert padrao_novo, "tabela deveria ser chamada na largura total"

    def test_ac3_conflitos_e_gaps_em_columns_50_50(self) -> None:
        """`st.columns([1, 1])` envolve Conflitos+Gaps (não [2, 1])."""
        conteudo = CATALOGACAO_PATH.read_text(encoding="utf-8")
        # Captura função renderizar.
        match = re.search(
            r"def renderizar\(.*?\) -> None:(.*?)(?=\ndef\s)",
            conteudo,
            re.DOTALL,
        )
        assert match
        corpo = match.group(1)
        assert "st.columns([1, 1])" in corpo, "esperado st.columns([1, 1]) para Conflitos | Gaps"
        # Ambas as funções ainda são chamadas.
        assert "_renderizar_painel_conflitos(docs)" in corpo
        assert "_renderizar_gaps(docs)" in corpo

    # ----------------------------------------------------------------
    # AC4 -- hero visível no topo
    # ----------------------------------------------------------------

    def test_ac4_hero_titulo_html_chamado_no_topo(self) -> None:
        """`hero_titulo_html('', 'Catalogação de Documentos', ...)` está no topo."""
        conteudo = CATALOGACAO_PATH.read_text(encoding="utf-8")
        # Procura padrão chave: hero com título "Catalogação de Documentos".
        assert "hero_titulo_html(" in conteudo
        assert "Catalogação de Documentos" in conteudo

    # ----------------------------------------------------------------
    # AC5 -- logo 120px efetivo
    # ----------------------------------------------------------------

    def test_ac5_css_logo_120px_com_important(self) -> None:
        """Regra `.ouroboros-logo-img` tem `width: 120px !important`."""
        css = css_global()
        match = re.search(
            r"\.ouroboros-logo-img\s*\{([^}]+)\}",
            css,
            re.DOTALL,
        )
        assert match, "regra .ouroboros-logo-img ausente"
        bloco = match.group(1)
        assert "width: 120px !important" in bloco
        assert "height: auto !important" in bloco
        assert "aspect-ratio: 724 / 733 !important" in bloco
        assert "display: block !important" in bloco

    @pytest.mark.skip(reason="UX-U-04: logo_sidebar_html removido da sidebar (shell-only)")
    def test_ac5_app_chama_logo_com_120px(self) -> None:
        """Sprint UX-126 AC5 era válido até UX-RD-03. UX-U-04 corta widgets
        antigos da sidebar (sidebar = shell HTML puro). O brand canônico vem
        do glyph SVG ouroboros (FIX-07) emitido pelo ``renderizar_brand_html``
        em ``componentes/shell.py``. Logo escudo ``logo_sidebar_html`` segue
        existindo no módulo ``tema.py`` mas não é mais chamado por ``app.py``.
        """

    # ----------------------------------------------------------------
    # AC6 -- caption sidebar reformatada (UX-U-04 removeu)
    # ----------------------------------------------------------------

    @pytest.mark.skip(reason="UX-U-04: caption 'Dados de' removida da sidebar (shell-only)")
    def test_ac6_caption_sidebar_em_duas_linhas_centralizadas(self) -> None:
        """Sprint UX-126 AC6 era válido até UX-RD-03. UX-U-04 corta widgets
        antigos da sidebar; caption ``Dados de DD/MM — HH:MM —`` foi
        eliminada porque o mockup canônico (00-shell-navegacao.html) não
        tem caption na sidebar — apenas o footer ``D7 cobertura
        observável`` em monospace."""


# "Detalhe não é poluição -- é a borda da credibilidade." -- princípio do polish honesto
