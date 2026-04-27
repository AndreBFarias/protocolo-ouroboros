"""Testes do drill-down interativo do dashboard (Sprint 73, ADR-19)."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from src.dashboard.componentes import drilldown

# ============================================================================
# Versão mínima do Streamlit (acceptance #1)
# ============================================================================


class TestStreamlitVersaoMinima:
    def test_streamlit_pelo_menos_1_31(self) -> None:
        import streamlit

        versao = streamlit.__version__
        partes = versao.split(".")
        major = int(partes[0])
        minor = int(partes[1]) if len(partes) > 1 else 0
        assert (major, minor) >= (1, 31), f"Sprint 73 exige streamlit>=1.31, atual={versao}"


# ============================================================================
# Helpers puros
# ============================================================================


class TestExtrairValorDoPonto:
    def test_prefere_customdata(self) -> None:
        ponto = {"customdata": "Farmácia", "label": "X", "x": "Y"}
        assert drilldown._extrair_valor_do_ponto(ponto) == "Farmácia"

    def test_cai_em_label_se_sem_customdata(self) -> None:
        ponto = {"label": "Saúde"}
        assert drilldown._extrair_valor_do_ponto(ponto) == "Saúde"

    def test_cai_em_x_como_ultimo_recurso(self) -> None:
        ponto = {"x": "2026-04"}
        assert drilldown._extrair_valor_do_ponto(ponto) == "2026-04"

    def test_devolve_none_quando_vazio(self) -> None:
        assert drilldown._extrair_valor_do_ponto({}) is None


# ============================================================================
# aplicar_drilldown — debounce
# ============================================================================


class _FakeFig:
    """Stub de fig do Plotly com `update_layout` mas sem estado real."""

    def __init__(self) -> None:
        self.layout_updates: list[dict] = []

    def update_layout(self, **kwargs: Any) -> None:
        self.layout_updates.append(kwargs)


class _FakeSt:
    """Mock mínimo de `streamlit` para testes do helper."""

    def __init__(self, pontos: list[dict]) -> None:
        self.session_state: dict = {}
        self.query_params: dict = {}
        self._pontos = pontos
        self.rerun_count = 0
        self.plot_kwargs: list[dict] = []

    def plotly_chart(self, fig: Any, **kwargs: Any) -> dict:
        self.plot_kwargs.append(kwargs)
        return {"selection": {"points": self._pontos}}

    def rerun(self) -> None:
        self.rerun_count += 1


class TestAplicarDrilldown:
    def test_key_grafico_obrigatorio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fig = _FakeFig()
        monkeypatch.setitem(sys.modules, "streamlit", _FakeSt([]))
        with pytest.raises(ValueError, match="key_grafico"):
            drilldown.aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="")

    def test_clique_dispara_rerun_e_grava_query_params(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeSt([{"customdata": "Farmácia"}])
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.aplicar_drilldown(_FakeFig(), "categoria", "Extrato", key_grafico="k1")
        assert fake.rerun_count == 1
        assert fake.query_params["categoria"] == "Farmácia"
        assert fake.query_params["tab"] == "Extrato"

    def test_segundo_clique_mesmo_valor_nao_dispara_rerun(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Debounce (acceptance #7 do spec)."""
        fake = _FakeSt([{"customdata": "Farmácia"}])
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.aplicar_drilldown(_FakeFig(), "categoria", "Extrato", key_grafico="k2")
        drilldown.aplicar_drilldown(_FakeFig(), "categoria", "Extrato", key_grafico="k2")
        assert fake.rerun_count == 1

    def test_sem_pontos_nao_faz_nada(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeSt([])
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.aplicar_drilldown(_FakeFig(), "categoria", "Extrato", key_grafico="k3")
        assert fake.rerun_count == 0
        assert "categoria" not in fake.query_params

    def test_clickmode_setado_no_fig(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeSt([])
        fig = _FakeFig()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.aplicar_drilldown(fig, "categoria", "Extrato", key_grafico="k4")
        assert any(u.get("clickmode") == "event+select" for u in fig.layout_updates)

    def test_plotly_chart_recebe_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeSt([])
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.aplicar_drilldown(_FakeFig(), "categoria", "Extrato", key_grafico="mykey")
        kwargs = fake.plot_kwargs[0]
        assert kwargs.get("key") == "mykey"
        assert kwargs.get("on_select") == "rerun"


# ============================================================================
# ler_filtros_da_url
# ============================================================================


class _FakeStUrlFiltros:
    def __init__(self, qp: dict[str, Any]) -> None:
        self.session_state: dict = {}
        self.query_params = qp


class TestLerFiltrosDaUrl:
    def test_popula_session_state_dos_campos_conhecidos(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeStUrlFiltros({"categoria": "Saúde", "tab": "Extrato"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state["filtro_categoria"] == "Saúde"
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extrato"

    def test_ignora_campos_fora_da_whitelist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStUrlFiltros({"randomico": "x", "categoria": "A"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert "filtro_randomico" not in fake.session_state
        assert fake.session_state["filtro_categoria"] == "A"

    def test_aceita_lista_como_valor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Alguns proxies retornam lista quando query tem duplicata (?a=1&a=2).
        fake = _FakeStUrlFiltros({"categoria": ["Saúde", "IRPF"]})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state["filtro_categoria"] == "Saúde"

    def test_url_especial_acentos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Acceptance A73-5: Saúde com ú não pode quebrar."""
        fake = _FakeStUrlFiltros({"categoria": "Saúde"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state["filtro_categoria"] == "Saúde"


# ============================================================================
# filtros_ativos + limpar_filtro
# ============================================================================


class TestFiltrosAtivos:
    def test_retorna_apenas_filtros_com_valor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStUrlFiltros({})
        fake.session_state = {
            "filtro_categoria": "Saúde",
            "filtro_banco": "",
            "filtro_outra_coisa": "ignorado",
        }
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        ativos = drilldown.filtros_ativos_do_session_state()
        assert ativos == {"categoria": "Saúde"}


class TestLimparFiltro:
    def test_remove_da_session_state_e_query_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStUrlFiltros({"categoria": "X"})
        fake.session_state = {"filtro_categoria": "X"}
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.limpar_filtro("categoria")
        assert "filtro_categoria" not in fake.session_state
        assert "categoria" not in fake.query_params
