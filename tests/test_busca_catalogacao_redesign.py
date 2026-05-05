"""Testes da Sprint UX-RD-09 -- Busca Global + Catalogação reescritas.

Cobre 8 acceptance criteria do redesign:

1. Busca: facetas laterais renderizadas (5 grupos: Tipo, Banco, Pessoa,
   Mês, Classificação).
2. Busca: snippet com ``<mark>...</mark>`` highlight do termo.
3. Busca: contagem unificada "N resultados · M documentos · K transações"
   (regressão UX-127 -- contagem nunca zera quando há docs).
4. Busca: resultado ``kind='aba'`` mostra mensagem inline SEM botão de
   navegação (regressão UX-127 AC4).
5. Busca: resultado ``kind='fornecedor'`` usa tabela inline via
   ``construir_dataframe_fornecedor`` (regressão UX-124).
6. Catalogação: page-header com título "CATALOGAÇÃO" e sprint-tag UX-RD-09.
7. Catalogação: tabela densa HTML com 7 colunas (sha8, Tipo, Fornecedor,
   Mês, Doc?, Valor, Pessoa).
8. Catalogação: ``COLUNAS_TABELA`` preservado (4 colunas canônicas).
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd
import pytest

from src.dashboard.paginas import busca as pag_busca
from src.dashboard.paginas import catalogacao as pag_cat

RAIZ = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# 1. Facetas laterais (Busca)
# ---------------------------------------------------------------------------


class TestFacetasLaterais:
    def test_funcao_facetas_existe(self) -> None:
        """Helper privado de facetas laterais foi adicionado."""
        assert hasattr(pag_busca, "_renderizar_facetas_laterais")
        assert callable(pag_busca._renderizar_facetas_laterais)

    def test_facetas_referenciam_5_grupos_canonicos(self) -> None:
        """Todos os 5 grupos canônicos aparecem no fonte da função."""
        fonte = inspect.getsource(pag_busca._renderizar_facetas_laterais)
        for grupo in ("Tipo", "Banco", "Pessoa", "Mês", "Classificação"):
            assert grupo in fonte, f"grupo de faceta '{grupo}' ausente"

    def test_facetas_calculam_contagens_dinamicas(self) -> None:
        """Função monta dicts cont_tipo / cont_banco / cont_pessoa / cont_mes /
        cont_class internamente."""
        fonte = inspect.getsource(pag_busca._renderizar_facetas_laterais)
        for nome in ("cont_tipo", "cont_banco", "cont_pessoa", "cont_mes", "cont_class"):
            assert nome in fonte, f"variável '{nome}' ausente em facetas"


# ---------------------------------------------------------------------------
# 2. Snippet highlight com <mark>
# ---------------------------------------------------------------------------


class TestSnippetHighlight:
    def test_helper_highlight_existe(self) -> None:
        assert hasattr(pag_busca, "_highlight_termo")
        assert callable(pag_busca._highlight_termo)

    def test_highlight_aplica_mark_em_match(self) -> None:
        """Texto com termo casado retorna ``<mark>...</mark>`` ao redor."""
        saida = pag_busca._highlight_termo(
            "Pagamento de aluguel mensal recorrente", "aluguel"
        )
        assert "<mark>" in saida
        assert "</mark>" in saida
        assert "aluguel" in saida.lower()

    def test_highlight_case_insensitive(self) -> None:
        """Match deve ser case-insensitive mas preservar caso original."""
        saida = pag_busca._highlight_termo("Compra na DROGARIA Mais", "drogaria")
        assert "<mark>DROGARIA</mark>" in saida

    def test_highlight_termo_vazio_devolve_truncado(self) -> None:
        """Termo vazio -> retorna texto truncado sem mark."""
        saida = pag_busca._highlight_termo("texto curto", "")
        assert "<mark>" not in saida
        assert "texto curto" in saida

    def test_highlight_termo_inexistente(self) -> None:
        """Termo que não casa -> retorna trecho inicial sem mark."""
        saida = pag_busca._highlight_termo("texto sem o termo procurado", "xpto")
        assert "<mark>" not in saida


# ---------------------------------------------------------------------------
# 3. Contagem unificada (regressão UX-127)
# ---------------------------------------------------------------------------


class TestContagemUnificada:
    def test_helper_contagem_unificada_existe(self) -> None:
        assert hasattr(pag_busca, "_renderizar_contagem_unificada")
        assert callable(pag_busca._renderizar_contagem_unificada)

    def test_contagem_unificada_inclui_termos_canonicos(self) -> None:
        """Função renderiza HTML mencionando 'resultados', 'documentos' e
        'transações' (UX-127 invariante)."""
        fonte = inspect.getsource(pag_busca._renderizar_contagem_unificada)
        assert "resultados" in fonte
        assert "documentos" in fonte
        assert "transações" in fonte


# ---------------------------------------------------------------------------
# 4. Resultado kind='aba' SEM botão de navegação (regressão UX-127 AC4)
# ---------------------------------------------------------------------------


class TestResultadoAbaSemBotao:
    def test_renderizar_rota_aba_nao_chama_st_button(self) -> None:
        """Ramo ``kind == "aba"`` da rota rápida NÃO contém ``st.button``,
        ``st.link_button``, ``st.switch_page`` ou ``st.rerun`` em código
        executável."""
        codigo = inspect.getsource(pag_busca._renderizar_rota_rapida)
        ini_aba = codigo.index('kind == "aba"')
        fim_aba = codigo.index('elif kind == "fornecedor"', ini_aba)
        bloco_aba = codigo[ini_aba:fim_aba]
        # Filtra comentários (linhas que começam com '#').
        linhas_executaveis = [
            ln for ln in bloco_aba.splitlines() if not ln.lstrip().startswith("#")
        ]
        bloco_executavel = "\n".join(linhas_executaveis)
        for proibido in ("st.button", "st.link_button", "st.switch_page", "st.rerun"):
            assert proibido not in bloco_executavel, (
                f"ramo kind='aba' contém '{proibido}': viola UX-127 AC4"
            )


# ---------------------------------------------------------------------------
# 5. Resultado kind='fornecedor' usa tabela inline (regressão UX-124)
# ---------------------------------------------------------------------------


class TestResultadoFornecedorTabelaInline:
    def test_pagina_busca_chama_construir_dataframe_fornecedor(self) -> None:
        """``paginas.busca`` referencia ``construir_dataframe_fornecedor``
        e ``st.dataframe`` no fonte (regressão UX-124)."""
        fonte = inspect.getsource(pag_busca)
        assert "construir_dataframe_fornecedor" in fonte
        assert "st.dataframe" in fonte

    def test_mensagem_resumo_fornecedor_preservada(self) -> None:
        """Strings literais 'casa o fornecedor' e 'transações encontradas'
        preservadas (regressão UX-124)."""
        fonte = inspect.getsource(pag_busca)
        assert "casa o fornecedor" in fonte
        assert "transações encontradas" in fonte


# ---------------------------------------------------------------------------
# 6. Catalogação: page-header redesign
# ---------------------------------------------------------------------------


class TestCatalogacaoPageHeader:
    def test_helper_page_header_html_existe(self) -> None:
        assert hasattr(pag_cat, "_page_header_html")
        assert callable(pag_cat._page_header_html)

    def test_page_header_contem_titulo_e_sprint_tag(self) -> None:
        """HTML do page-header contém título 'CATALOGAÇÃO' e
        ``sprint-tag UX-RD-09``."""
        html = pag_cat._page_header_html(num_arquivos=42)
        assert 'class="page-header"' in html
        assert 'class="page-title"' in html
        assert "CATALOGAÇÃO" in html
        assert "sprint-tag" in html
        assert "UX-RD-09" in html

    def test_page_header_pill_quando_tem_arquivos(self) -> None:
        """Pill com contagem aparece quando ``num_arquivos > 0``."""
        html_com = pag_cat._page_header_html(num_arquivos=42)
        html_sem = pag_cat._page_header_html(num_arquivos=0)
        assert "42 arquivos" in html_com
        assert "0 arquivos" not in html_sem

    def test_toolbar_html_existe(self) -> None:
        """Toolbar redesign foi adicionada."""
        assert hasattr(pag_cat, "_toolbar_html")
        html = pag_cat._toolbar_html(num_arquivos=12)
        assert 'class="ouroboros-cat-toolbar"' in html
        assert "12 no catálogo" in html


# ---------------------------------------------------------------------------
# 7. Catalogação: tabela densa HTML 7 colunas
# ---------------------------------------------------------------------------


class TestCatalogacaoTabelaDensa:
    def test_helper_tabela_densa_html_existe(self) -> None:
        assert hasattr(pag_cat, "_tabela_densa_html")
        assert callable(pag_cat._tabela_densa_html)

    def test_tabela_densa_renderiza_7_colunas(self) -> None:
        """Cabeçalho da tabela densa tem exatamente 7 cabeçalhos
        (sha8, Tipo, Fornecedor, Mês, Doc?, Valor, Pessoa)."""
        amostra = pd.DataFrame(
            [
                {
                    "sha8": "a3f9c1e2",
                    "tipo_documento": "boleto_servico",
                    "razao_social": "Neoenergia",
                    "data_emissao": "2026-04-15",
                    "status_linking": "Vinculado",
                    "total": 250.50,
                    "quem": "André",
                },
                {
                    "sha8": "b7d2a04f",
                    "tipo_documento": "fatura_cartao",
                    "razao_social": "C6 Bank",
                    "data_emissao": "2026-04-10",
                    "status_linking": "Sem transação",
                    "total": 1280.00,
                    "quem": "Vitória",
                },
            ]
        )
        html = pag_cat._tabela_densa_html(amostra)
        # Cabeçalhos canônicos
        for cab in ("sha8", "Tipo", "Fornecedor", "Mês", "Doc?", "Valor", "Pessoa"):
            assert f"<th>{cab}</th>" in html, f"cabeçalho '{cab}' ausente"
        # Conta exatamente 7 <th>...</th>
        assert html.count("<th>") == 7
        # Valor formatado em moeda BRL
        assert "R$" in html

    def test_tabela_densa_vazia_devolve_string_vazia(self) -> None:
        html = pag_cat._tabela_densa_html(pd.DataFrame())
        assert html == ""

    def test_tabela_densa_marca_vinculado_diferente(self) -> None:
        """Linhas com status 'Vinculado' têm marca verde diferente das
        demais (Sem transação / Conflito)."""
        amostra = pd.DataFrame(
            [
                {
                    "sha8": "aa", "tipo_documento": "boleto_servico",
                    "razao_social": "X", "data_emissao": "2026-04-01",
                    "status_linking": "Vinculado", "total": 10.0, "quem": "casal",
                },
                {
                    "sha8": "bb", "tipo_documento": "boleto_servico",
                    "razao_social": "Y", "data_emissao": "2026-04-02",
                    "status_linking": "Sem transação", "total": 20.0, "quem": "casal",
                },
            ]
        )
        html = pag_cat._tabela_densa_html(amostra)
        # Linha vinculado marca check codificado como entidade unicode.
        assert "&#x2713;" in html


# ---------------------------------------------------------------------------
# 8. Catalogação: invariantes preservadas (4 colunas canônicas)
# ---------------------------------------------------------------------------


class TestCatalogacaoInvariantes:
    def test_colunas_tabela_preservadas(self) -> None:
        """``COLUNAS_TABELA`` = 4 elementos canônicos (regressão Sprint 51)."""
        assert pag_cat.COLUNAS_TABELA == ["Data", "Fornecedor", "Total", "Status"]
        assert len(pag_cat.COLUNAS_TABELA) == 4

    def test_humanizar_importado_e_usado(self) -> None:
        """Import + uso real (regressão UX-126 AC1)."""
        fonte = inspect.getsource(pag_cat)
        assert "from src.dashboard.componentes.humanizar_tipos import humanizar" in fonte
        assert "humanizar(tipo_tec)" in fonte

    def test_columns_1_1_para_conflitos_e_gaps(self) -> None:
        """``st.columns([1, 1])`` envolve conflitos+gaps (regressão UX-126 AC3)."""
        fonte = inspect.getsource(pag_cat.renderizar)
        assert "st.columns([1, 1])" in fonte
        assert "_renderizar_painel_conflitos(docs)" in fonte
        assert "_renderizar_gaps(docs)" in fonte


# ---------------------------------------------------------------------------
# 9. Renderização ponta-a-ponta sem crash
# ---------------------------------------------------------------------------


class TestSmokeRedesign:
    def test_busca_renderiza_sem_grafo_sem_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Página Busca renderiza sem crash quando o grafo não existe."""
        from streamlit.testing.v1 import AppTest

        monkeypatch.setattr(
            pag_busca._dados, "CAMINHO_GRAFO", tmp_path / "_falso.sqlite"
        )

        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(RAIZ)!r})\n"
            "from pathlib import Path\n"
            "from src.dashboard import dados as d\n"
            f"d.CAMINHO_GRAFO = Path({str(tmp_path / '_falso.sqlite')!r})\n"
            "from src.dashboard.paginas import busca\n"
            "busca.renderizar()\n"
        )
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        # Page-header redesign aparece (busca pelo título mock)
        markdowns = " ".join(m.value for m in at.markdown)
        assert "BUSCA GLOBAL" in markdowns

    def test_catalogacao_renderiza_sem_grafo_sem_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Página Catalogação renderiza sem crash quando o grafo não existe."""
        from streamlit.testing.v1 import AppTest

        monkeypatch.setattr(
            pag_cat._dados, "CAMINHO_GRAFO", tmp_path / "_falso.sqlite"
        )

        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(RAIZ)!r})\n"
            "from pathlib import Path\n"
            "from src.dashboard import dados as d\n"
            f"d.CAMINHO_GRAFO = Path({str(tmp_path / '_falso.sqlite')!r})\n"
            "from src.dashboard.paginas import catalogacao\n"
            "catalogacao.renderizar()\n"
        )
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        markdowns = " ".join(m.value for m in at.markdown)
        assert "CATALOGAÇÃO" in markdowns
        # sprint-tag aparece
        assert "UX-RD-09" in markdowns


# "Reescrever sem regredir é a única estética que importa." -- princípio UX-RD
