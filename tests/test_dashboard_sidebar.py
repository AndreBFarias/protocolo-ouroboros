"""Testes da Sprint UX-113 -- sidebar refactor (Buscar primeiro + Área dropdown).

Foco:
- Ordem dos elementos no novo ``_sidebar()`` (Logo -> Buscar -> Área ->
  Granularidade -> Mês -> Pessoa -> Forma de pagamento).
- Widget de Área é ``st.selectbox`` (era ``st.radio``).
- Default da Área lê de ``st.session_state[CHAVE_SESSION_CLUSTER_ATIVO]``
  populado por ``ler_filtros_da_url`` a partir de ``query_params['cluster']``.
- Componente de busca delega para o roteador da Sprint UX-114 quando ele
  estiver disponível; fallback graceful caso ainda não mergeada.
- Drill-down (Sprint 73) preservado -- chaves ``filtro_*`` e ``avancado_*``
  permanecem em namespaces separados de ``seletor_*``.
- Feedback do dono 2026-04-27: glyphs íntegros, min-width, ícone search.

Padrão canônico do projeto: monkeypatch ``sys.modules['streamlit']`` com fake
mínimo (BRIEF §161, ver ``tests/test_dashboard_drilldown.py``).
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import pytest

from src.dashboard.componentes import busca_global_sidebar

# ============================================================================
# Fakes mínimos
# ============================================================================


class _FakeSidebarContext:
    """Context manager fake para `with st.sidebar:`."""

    def __init__(self, parent: "_FakeStSidebar") -> None:
        self._parent = parent

    def __enter__(self) -> "_FakeStSidebar":
        return self._parent

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _FakeStSidebar:
    """Mock mínimo de ``streamlit`` que registra ordem de chamadas.

    Cada widget que aparecer na sidebar é registrado em ``self.ordem`` na
    sequência exata em que foi chamado, permitindo asserir a ordem prescrita
    pela Sprint UX-113.
    """

    def __init__(
        self,
        meses: list[str] | None = None,
        query_params: dict[str, Any] | None = None,
        text_input_return: str = "",
    ) -> None:
        self.session_state: dict = {}
        self.query_params: dict = query_params if query_params is not None else {}
        self.ordem: list[str] = []
        self.markdowns: list[str] = []
        self._meses = meses or ["2026-04", "2026-03"]
        self._text_input_return = text_input_return
        self.selectbox_calls: list[dict] = []
        self.radio_calls: list[dict] = []
        self.text_input_calls: list[dict] = []

    @property
    def sidebar(self) -> _FakeSidebarContext:
        return _FakeSidebarContext(self)

    def markdown(self, body: str, **_: Any) -> None:
        self.ordem.append("markdown")
        self.markdowns.append(body)

    def title(self, _: str) -> None:
        self.ordem.append("title")

    def caption(self, _: str) -> None:
        self.ordem.append("caption")

    def warning(self, _: str) -> None:
        self.ordem.append("warning")

    def text_input(
        self,
        label: str,
        value: str = "",
        placeholder: str = "",
        key: str = "",
        **_: Any,
    ) -> str:
        self.ordem.append(f"text_input:{label}")
        self.text_input_calls.append(
            {"label": label, "placeholder": placeholder, "key": key, "value": value}
        )
        return self._text_input_return

    def selectbox(
        self,
        label: str,
        options: list,
        index: int = 0,
        key: str = "",
        **_: Any,
    ) -> Any:
        self.ordem.append(f"selectbox:{label}")
        self.selectbox_calls.append(
            {"label": label, "options": list(options), "index": index, "key": key}
        )
        # Streamlit escreve o valor selecionado em session_state[key].
        if options:
            valor = options[index]
            if key:
                self.session_state[key] = valor
            return valor
        return None

    def radio(self, label: str, options: list, **_: Any) -> Any:
        self.ordem.append(f"radio:{label}")
        self.radio_calls.append({"label": label, "options": list(options)})
        return options[0] if options else None


# ============================================================================
# Acceptance: ordem dos elementos da sidebar
# ============================================================================


class TestOrdemSidebar:
    def test_renderizar_input_busca_chama_text_input_com_placeholder_canonico(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC #1: primeiro elemento abaixo do logo é st.text_input com
        placeholder 'Buscar (documento, fornecedor, aba...)'."""
        fake = _FakeStSidebar()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()
        assert any(c["label"] == "Buscar" for c in fake.text_input_calls)
        ph = fake.text_input_calls[0]["placeholder"]
        assert "Buscar" in ph
        assert "documento" in ph
        assert "fornecedor" in ph
        assert "aba" in ph

    def test_text_input_aparece_antes_de_qualquer_selectbox_quando_renderizado(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Confirma que renderizar_input_busca emite text_input + markdown
        (CSS) e não selectbox."""
        fake = _FakeStSidebar()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()
        # markdown (CSS overflow fix) + text_input apenas; nenhum selectbox.
        eventos_selectbox = [e for e in fake.ordem if e.startswith("selectbox")]
        eventos_text = [e for e in fake.ordem if e.startswith("text_input")]
        assert eventos_text, "text_input deveria ter sido chamado"
        assert not eventos_selectbox, (
            "renderizar_input_busca não deve emitir selectbox; "
            "Área é responsabilidade de _selecionar_cluster"
        )


# ============================================================================
# Acceptance: Área é st.selectbox (era radio)
# ============================================================================


class TestAreaComoSelectbox:
    def test_selecionar_cluster_usa_selectbox_em_vez_de_radio(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC #2: widget Área agora é dropdown (selectbox)."""
        from src.dashboard import app as app_mod

        fake = _FakeStSidebar()
        monkeypatch.setattr(app_mod, "st", fake)

        cluster = app_mod._selecionar_cluster()
        assert cluster in {"Home", "Dinheiro", "Documentos", "Análise", "Metas"}
        labels_selectbox = [c["label"] for c in fake.selectbox_calls]
        labels_radio = [c["label"] for c in fake.radio_calls]
        assert "Área" in labels_selectbox, "Área deveria ser selectbox após Sprint UX-113"
        assert "Área" not in labels_radio, "Área não deve ser radio mais"

    def test_selectbox_area_tem_5_opcoes_canonicas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC #2 + Sprint UX-121: opções do dropdown Área = ('Home', 'Dinheiro',
        'Documentos', 'Análise', 'Metas') -- 'Hoje' renomeado para 'Home'."""
        from src.dashboard import app as app_mod

        fake = _FakeStSidebar()
        monkeypatch.setattr(app_mod, "st", fake)

        app_mod._selecionar_cluster()
        chamada_area = next(c for c in fake.selectbox_calls if c["label"] == "Área")
        assert chamada_area["options"] == [
            "Home",
            "Dinheiro",
            "Documentos",
            "Análise",
            "Metas",
        ]


# ============================================================================
# Acceptance: leitura de query_params['cluster'] como default
# ============================================================================


class TestDefaultLeQueryParams:
    def test_query_params_cluster_define_indice_default(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC #2: default lê de ``query_params['cluster']`` via
        ``CHAVE_SESSION_CLUSTER_ATIVO``."""
        from src.dashboard import app as app_mod
        from src.dashboard.componentes.drilldown import CHAVE_SESSION_CLUSTER_ATIVO

        fake = _FakeStSidebar()
        # Simula efeito de ler_filtros_da_url para cluster=Documentos.
        fake.session_state[CHAVE_SESSION_CLUSTER_ATIVO] = "Documentos"
        monkeypatch.setattr(app_mod, "st", fake)

        app_mod._selecionar_cluster()
        chamada_area = next(c for c in fake.selectbox_calls if c["label"] == "Área")
        assert chamada_area["index"] == 2  # Documentos é índice 2

    def test_sem_query_params_default_e_indice_zero(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.dashboard import app as app_mod

        fake = _FakeStSidebar()
        monkeypatch.setattr(app_mod, "st", fake)

        app_mod._selecionar_cluster()
        chamada_area = next(c for c in fake.selectbox_calls if c["label"] == "Área")
        assert chamada_area["index"] == 0  # default = primeiro (Hoje)


# ============================================================================
# Acceptance: roteador (mock) é chamado em submissão
# ============================================================================


class TestDelegacaoRoteadorMock:
    def test_roteador_kind_aba_atualiza_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Quando roteador retorna kind='aba', query_params recebe cluster+tab."""
        fake = _FakeStSidebar(text_input_return="Revisor")
        monkeypatch.setitem(sys.modules, "streamlit", fake)

        # Mock do módulo busca_roteador (Sprint UX-114) com retorno fixo.
        import types

        mod = types.ModuleType("src.dashboard.componentes.busca_roteador")
        mod.rotear = lambda q: {  # type: ignore[attr-defined]
            "kind": "aba",
            "cluster": "Documentos",
            "tab": "Revisor",
        }
        monkeypatch.setitem(sys.modules, "src.dashboard.componentes.busca_roteador", mod)

        busca_global_sidebar.renderizar_input_busca()

        assert fake.query_params.get("cluster") == "Documentos"
        assert fake.query_params.get("tab") == "Revisor"

    def test_roteador_kind_fornecedor_navega_para_busca_global(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeStSidebar(text_input_return="Neoenergia")
        monkeypatch.setitem(sys.modules, "streamlit", fake)

        import types

        mod = types.ModuleType("src.dashboard.componentes.busca_roteador")
        mod.rotear = lambda q: {  # type: ignore[attr-defined]
            "kind": "fornecedor",
            "fornecedor": "Neoenergia",
        }
        monkeypatch.setitem(sys.modules, "src.dashboard.componentes.busca_roteador", mod)

        busca_global_sidebar.renderizar_input_busca()
        assert fake.query_params.get("cluster") == "Documentos"
        assert fake.query_params.get("tab") == "Busca Global"

    def test_fallback_graceful_quando_roteador_nao_existe(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Branch reversível (Sprint 97): se UX-114 não foi mergeada ainda,
        componente loga warning mas não quebra."""
        fake = _FakeStSidebar(text_input_return="qualquer_coisa")
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        # Garante que busca_roteador não está em sys.modules.
        monkeypatch.delitem(sys.modules, "src.dashboard.componentes.busca_roteador", raising=False)
        # Cria carregador que sempre falha import:
        import importlib.abc
        import importlib.machinery

        class _Bloqueador(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
                if fullname == "src.dashboard.componentes.busca_roteador":
                    raise ImportError("UX-114 não disponível (test stub)")
                return None

        bloqueador = _Bloqueador()
        sys.meta_path.insert(0, bloqueador)
        try:
            with caplog.at_level(logging.WARNING):
                busca_global_sidebar.renderizar_input_busca()
        finally:
            sys.meta_path.remove(bloqueador)

        # Não deve haver navegação automática.
        assert fake.query_params.get("cluster") is None
        # Mensagem do warning é informativa.
        textos = " ".join(r.message for r in caplog.records)
        assert "UX-114" in textos or "busca_roteador" in textos


# ============================================================================
# Acceptance: drill-down (Sprint 73) preservado
# ============================================================================


class TestDrillDownPreservado:
    def test_chaves_seletor_distintas_de_filtro_e_avancado(self) -> None:
        """BRIEF §137: namespaces seletor_*/filtro_*/avancado_* são reservados.

        UX-113 não pode introduzir colisão.
        """
        # Lê texto fonte do app.py para checar chaves.
        import inspect

        from src.dashboard import app as app_mod

        codigo = inspect.getsource(app_mod)
        # Chaves do seletor de filtros transversais (sidebar):
        for chave in (
            "seletor_granularidade",
            "seletor_mes_base",
            "seletor_pessoa",
            "seletor_forma_pagamento",
        ):
            assert chave in codigo, f"Chave {chave} sumiu do _sidebar"

    def test_componente_busca_usa_chave_dedicada_session_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeStSidebar(text_input_return="x")
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()
        assert busca_global_sidebar.CHAVE_SESSION_BUSCA == "busca_global_query"
        assert fake.session_state.get(busca_global_sidebar.CHAVE_SESSION_BUSCA) == "x"


# ============================================================================
# Adições do feedback do dono 2026-04-27 (glyphs e overflow)
# ============================================================================


class TestGlyphsEOverflow:
    def test_css_overflow_fix_define_min_width_260px(self) -> None:
        """AC: sidebar tem largura mínima 260px (sem isso glyphs cortam)."""
        css = busca_global_sidebar.css_sidebar_overflow_fix()
        assert "min-width" in css
        assert "260" in css

    def test_css_overflow_fix_oculta_overflow_x(self) -> None:
        """AC: ``overflow-x: hidden`` no container da sidebar."""
        css = busca_global_sidebar.css_sidebar_overflow_fix()
        assert "overflow-x: hidden" in css

    def test_css_overflow_fix_define_word_break_e_nowrap(self) -> None:
        """AC: rótulos curtos ('Mês') não quebram no meio do glyph."""
        css = busca_global_sidebar.css_sidebar_overflow_fix()
        assert "word-break" in css
        assert "nowrap" in css

    def test_css_icone_search_minimo_18px(self) -> None:
        """AC feedback dono: ícone search >=18px."""
        css = busca_global_sidebar.css_sidebar_overflow_fix()
        assert "18" in css
        # busca svg com width: 18px
        assert "svg" in css.lower()

    def test_constante_largura_minima_corresponde_ao_ac(self) -> None:
        assert busca_global_sidebar.LARGURA_MINIMA_SIDEBAR_PX == 260
        assert busca_global_sidebar.TAMANHO_MINIMO_ICONE_SEARCH_PX == 18

    def test_selectbox_mes_renderiza_valor_completo_2026_04(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC feedback dono: selectbox Mês exibe '2026-04' inteiro -- regressão
        contra '2A26-04' truncado pelo overflow.

        Não há como inspecionar o DOM renderizado pelo Streamlit em
        testunit; o que validamos é que o CSS injetado garante que o
        seletor não corta no meio do glyph (text-overflow ellipsis cobre
        o pior caso, mas com min-width 260 a string '2026-04' cabe inteira).
        """
        css = busca_global_sidebar.css_sidebar_overflow_fix()
        # ellipsis fallback para casos extremos:
        assert "text-overflow: ellipsis" in css
        # E o valor selecionado (combobox) tem white-space: nowrap forçado:
        assert 'data-baseweb="select"' in css

    def test_componente_emite_css_uma_vez_por_render(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``renderizar_input_busca`` deve emitir o CSS junto com o input,
        não exigir chamada separada pelo app.py."""
        fake = _FakeStSidebar()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()
        css_markdowns = [m for m in fake.markdowns if "min-width" in m]
        assert len(css_markdowns) >= 1


# ============================================================================
# Acceptance: import do app.py não quebra (smoke test estático)
# ============================================================================


class TestImportSmokeApp:
    def test_app_importavel_sem_streamlit_real_no_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """O módulo app.py deve poder ser importado mesmo se busca_roteador
        (UX-114) não existe ainda. Branch reversível ativo."""
        # Garante import limpo.
        sys.modules.pop("src.dashboard.app", None)
        # Mantém streamlit real disponível para o import.
        from src.dashboard import app as app_mod

        # _sidebar e _selecionar_cluster existem após refactor.
        assert hasattr(app_mod, "_sidebar")
        assert hasattr(app_mod, "_selecionar_cluster")
        # Import do componente novo é declarado em app.py.
        assert "renderizar_input_busca" in dir(app_mod) or any(
            "renderizar_input_busca" in line
            for line in __import__("inspect").getsource(app_mod).splitlines()
        )


class TestSprintUX119SidebarAgrupada:
    """Sprint UX-119 AC4: separadores intermediarios removidos de _sidebar().

    Antes de UX-119, _sidebar() emitia 4 chamadas de st.markdown("---"):
        1. após logo+caption (preserva: marca fronteira cabeçalho/filtros)
        2. após renderizar_input_busca (REMOVER: separa Buscar de Área)
        3. após _selecionar_cluster (REMOVER: separa Área de Granularidade)
        4. após forma_pagamento (preserva: marca fronteira filtros/cards)

    UX-119 remove os 2 separadores intermediários (entre os 6 filtros). O
    bloco de filtros vira um agrupamento visual contínuo. Os 2 separadores
    de fronteira (cabeçalho/cards) permanecem.
    """

    def test_ac4_apenas_dois_separadores_intermediarios_removidos(self) -> None:
        # Lê o código-fonte direto: o número total de st.markdown("---")
        # em app.py deve ser 2 (cabeçalho/filtros + filtros/cards), não 4.
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "src/dashboard/app.py"
        fonte = path.read_text(encoding="utf-8")
        # Conta apenas chamadas reais (não matches em comentários).
        ocorrencias = [
            linha
            for linha in fonte.splitlines()
            if 'st.markdown("---")' in linha and not linha.lstrip().startswith("#")
        ]
        assert len(ocorrencias) == 2, (
            f"Esperado 2 separadores em app.py (cabecalho + cards); "
            f"encontrei {len(ocorrencias)}: {ocorrencias}"
        )


# "Quem busca primeiro, navega depois." -- princípio do mental model honesto
# (Don Norman, The Design of Everyday Things, capítulo 4 sobre constraints
# cognitivos de navegação hierárquica).
