"""Testes da página Revisor Visual -- regressão da Sprint UX-117.

Cobre:
- Filtros 'Tipo de pendência' e 'Página' NÃO renderizam mais como
  ``st.sidebar.*`` em ``revisor.py`` (mudança canônica da Sprint UX-117).
- Filtros AGORA renderizam no corpo da página via ``st.multiselect`` /
  ``st.number_input`` dentro de ``st.columns([2, 1])``.
- ``app.py:_sidebar()`` continua sem esses filtros (regressão preventiva
  -- nunca esteve lá, mas garante que sprint futura não os adicione).
- Filtros transversais (Mês/Pessoa/Forma de pagamento) permanecem na
  sidebar global.
- Session-state keys preservadas: ``revisor_filtro_tipo`` e
  ``revisor_pagina`` (retrocompatibilidade com sprints anteriores).
- Renderização Streamlit via AppTest: a página executa sem exceção; o
  multiselect e o number_input aparecem; multiselect vazio rende callout
  'Nenhuma pendência casa o filtro atual'; multiselect com 1 valor filtra
  corretamente.
- Comportamento de paginação preservado: máximo de páginas correto e
  mesmas pendências para a mesma combinação de filtros (regressão
  funcional do contrato de ``listar_pendencias_revisao``).

Todos os testes baseados em AppTest monkey-patcham
``listar_pendencias_revisao`` para evitar dependência do grafo real.
"""

from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
FONTE_REVISOR = RAIZ / "src" / "dashboard" / "paginas" / "revisor.py"
FONTE_APP = RAIZ / "src" / "dashboard" / "app.py"


# -----------------------------------------------------------------------------
# Testes estáticos (string-based) -- proof estrutural da migração UX-117.
# -----------------------------------------------------------------------------


class TestSpriUx117EstruturaCodigo:
    """Verifica que a Sprint UX-117 moveu corretamente os widgets."""

    def test_revisor_nao_usa_st_sidebar_multiselect(self) -> None:
        """``st.sidebar.multiselect`` removido de revisor.py.

        Antes da UX-117 o multiselect 'Tipo de pendência' era criado em
        ``st.sidebar``, contaminando outras áreas (Hoje, Dinheiro,
        Análise, Metas).
        """
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert "st.sidebar.multiselect" not in fonte, (
            "revisor.py ainda invoca st.sidebar.multiselect; UX-117 "
            "exigiu mover para st.multiselect dentro de st.columns."
        )

    def test_revisor_nao_usa_st_sidebar_number_input(self) -> None:
        """``st.sidebar.number_input`` removido de revisor.py.

        O paginador 'Página' migrou para o corpo da página.
        """
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert "st.sidebar.number_input" not in fonte, (
            "revisor.py ainda invoca st.sidebar.number_input; UX-117 "
            "exigiu mover para st.number_input dentro de st.columns."
        )

    def test_revisor_renderiza_multiselect_no_corpo(self) -> None:
        """``st.multiselect`` (sem ``.sidebar``) presente em revisor.py."""
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert "st.multiselect(" in fonte
        assert '"Tipo de pendência"' in fonte

    def test_revisor_renderiza_number_input_no_corpo(self) -> None:
        """``st.number_input`` (sem ``.sidebar``) presente em revisor.py."""
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert "st.number_input(" in fonte
        assert '"Página"' in fonte

    def test_revisor_usa_st_columns_2_1(self) -> None:
        """Layout canônico: ``st.columns([2, 1])`` no topo."""
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert "st.columns([2, 1])" in fonte, (
            "UX-117 exige st.columns([2, 1]) -- multiselect (largura 2) "
            "à esquerda, number_input (largura 1) à direita."
        )

    def test_revisor_preserva_keys_session_state(self) -> None:
        """Keys de session_state permanecem para retrocompatibilidade."""
        fonte = FONTE_REVISOR.read_text(encoding="utf-8")
        assert 'key="revisor_filtro_tipo"' in fonte
        assert 'key="revisor_pagina"' in fonte


class TestSpriUx117SidebarGlobal:
    """Sidebar global em app.py NÃO contém os filtros movidos."""

    def test_sidebar_app_nao_tem_tipo_de_pendencia(self) -> None:
        """``_sidebar()`` em app.py não menciona 'Tipo de pendência'.

        Esses widgets são responsabilidade exclusiva da página Revisor.
        """
        fonte = FONTE_APP.read_text(encoding="utf-8")
        assert "Tipo de pendência" not in fonte
        assert "Tipo de pendencia" not in fonte

    def test_sidebar_app_nao_tem_filtro_pagina(self) -> None:
        """``_sidebar()`` não rende ``st.number_input`` para Página."""
        fonte = FONTE_APP.read_text(encoding="utf-8")
        # number_input geral pode existir em outras seções; aqui garantimos
        # que ele não está acoplado a "Página" como filtro do revisor.
        assert "revisor_pagina" not in fonte
        assert "revisor_filtro_tipo" not in fonte

    def test_sidebar_app_mantem_filtros_transversais(self) -> None:
        """Mês / Pessoa / Forma de pagamento permanecem globais.

        UX-V-01: as labels foram movidas de ``app.py`` para a fronteira
        ``componentes/ui.py::chip_bar_filtros_globais``. ``app.py`` apenas
        delega via ``_filtros_globais_main``. O contrato global permanece
        intacto -- testamos a fonte canônica nova.
        """
        from src.dashboard.componentes import ui as componentes_ui

        fonte_app = FONTE_APP.read_text(encoding="utf-8")
        # Delegação preservada (padrão (o) subregra retrocompatível).
        assert "chip_bar_filtros_globais" in fonte_app
        assert "_filtros_globais_main(dados)" in fonte_app

        # Labels canônicas vivem agora em componentes/ui.py.
        fonte_ui = Path(componentes_ui.__file__).read_text(encoding="utf-8")
        assert '"Mês"' in fonte_ui
        assert '"Pessoa"' in fonte_ui
        assert '"Forma de pagamento"' in fonte_ui


# -----------------------------------------------------------------------------
# Testes funcionais (AppTest) -- comportamento preservado.
# -----------------------------------------------------------------------------


@pytest.fixture
def pendencias_fixture() -> list[dict]:
    """Conjunto sintético de 25 pendências, 3 tipos distintos.

    25 itens forçam paginação a 3 páginas (10/10/5) e dão folga para
    testar multiselect com 0/1/3 valores.
    """
    pendencias: list[dict] = []
    for i in range(10):
        pendencias.append(
            {
                "item_id": f"raw_classificar/arquivo_{i:02d}.pdf",
                "tipo": "raw_classificar",
                "caminho": f"/tmp/fake/arquivo_{i:02d}.pdf",
                "metadata": {"tipo_documento": "desconhecido"},
                "prioridade": 1,
            }
        )
    for i in range(10):
        pendencias.append(
            {
                "item_id": f"raw_conferir/dir_{i:02d}",
                "tipo": "raw_conferir",
                "caminho": f"/tmp/fake/conferir_{i:02d}",
                "metadata": {"tipo_documento": "cupom"},
                "prioridade": 2,
            }
        )
    for i in range(5):
        pendencias.append(
            {
                "item_id": f"node_{1000 + i}",
                "tipo": "grafo_low_confidence",
                "caminho": "",
                "metadata": {"confidence": 0.5},
                "prioridade": 3,
            }
        )
    return pendencias


def _script_revisor(pendencias: list[dict]) -> str:
    """Gera script Streamlit isolado.

    O stub de ``listar_pendencias_revisao`` é aplicado por fixture
    pytest (``_stub_listar_pendencias``) com ``monkeypatch.setattr``,
    garantindo teardown automático e isolamento entre testes. Este
    script apenas configura o ``CAMINHO_REVISAO_HUMANA`` temporário e
    invoca ``revisor.renderizar()``.
    """
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st
from src.dashboard import dados as d

# Schema mínimo do SQLite de revisão (vazio).
import sqlite3
import tempfile
tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
tmp.close()
caminho_tmp = Path(tmp.name)
d.CAMINHO_REVISAO_HUMANA = caminho_tmp

from src.dashboard.paginas import revisor as r
r.CAMINHO_REVISAO_HUMANA = caminho_tmp
r.garantir_schema(caminho_tmp)
r.renderizar()
"""


class TestSpriUx117Renderizacao:
    """Testes funcionais via streamlit.testing.v1.AppTest."""

    @pytest.fixture(autouse=True)
    def _stub_listar_pendencias(self, monkeypatch, pendencias_fixture):
        """Substitui ``listar_pendencias_revisao`` via ``monkeypatch.setattr``.

        Atribuição direta (``d.listar_pendencias_revisao = stub``) persistia
        no cache de ``sys.modules`` e contaminava ``test_revisor.py::
        TestListarPendencias`` quando rodado em suite full. ``monkeypatch``
        registra teardown automático e restaura o atributo original ao fim
        do teste.
        """
        from src.dashboard import dados as d
        from src.dashboard.paginas import revisor as r

        def _stub(*args, **kwargs):
            return list(pendencias_fixture)

        monkeypatch.setattr(d, "listar_pendencias_revisao", _stub)
        # ``revisor.py`` importa a função estaticamente -- precisa do mesmo
        # patch no namespace do módulo importador.
        monkeypatch.setattr(r, "listar_pendencias_revisao", _stub)

    def test_pagina_renderiza_sem_excecao(self, pendencias_fixture):
        """Página Revisor executa com 25 pendências sem crashar."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        assert not at.exception, f"Página Revisor crashou: {[str(e) for e in at.exception]}"

    def test_multiselect_renderiza_no_corpo(self, pendencias_fixture):
        """``at.multiselect`` (NÃO sidebar) contém 'Tipo de pendência'."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        assert not at.exception
        labels = [m.label for m in at.multiselect]
        assert "Tipo de pendência" in labels, (
            f"multiselect 'Tipo de pendência' não encontrado: {labels}"
        )

    def test_number_input_pagina_renderiza(self, pendencias_fixture):
        """``at.number_input`` contém 'Página' com max_value correto."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        assert not at.exception
        labels = [n.label for n in at.number_input]
        assert "Página" in labels
        # 25 pendências / 10 por página = 3 páginas (10/10/5)
        page_input = next(n for n in at.number_input if n.label == "Página")
        assert page_input.max == 3

    def test_filtro_tipo_unico_reduz_pendencias(self, pendencias_fixture):
        """Multiselect com 1 valor filtra para esse tipo apenas.

        Verifica regressão funcional: o filtro continua reduzindo o
        número de pendências exibidas (caption mostra contagem).
        """
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        # Filtra para apenas raw_classificar (10 itens, 1 página).
        ms = next(m for m in at.multiselect if m.label == "Tipo de pendência")
        ms.set_value(["raw_classificar"]).run()
        assert not at.exception
        captions = " ".join(c.value for c in at.caption)
        assert "10 de 10" in captions, f"Caption esperado '10 de 10' não encontrado: {captions}"

    def test_filtro_vazio_mostra_callout(self, pendencias_fixture):
        """Multiselect vazio renderiza callout informativo."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        ms = next(m for m in at.multiselect if m.label == "Tipo de pendência")
        ms.set_value([]).run()
        assert not at.exception
        markdowns = " ".join(m.value for m in at.markdown).lower()
        assert "nenhuma pendência casa o filtro" in markdowns

    def test_paginacao_3_paginas_para_25_pendencias(self, pendencias_fixture):
        """Caption mostra 'página 1 de 3' com filtro completo (25 itens)."""
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_string(_script_revisor(pendencias_fixture))
        at.run()
        captions = " ".join(c.value for c in at.caption)
        assert "página 1 de 3" in captions, f"Caption de paginação não encontrado: {captions}"


# "Filtros que só importam em uma área pertencem àquela área. Tudo o mais é "
# "ruído cognitivo." -- princípio do escopo do filtro
