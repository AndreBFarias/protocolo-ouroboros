"""Testes da reorganização em clusters do dashboard (Sprint 92b, ADR-22).

Foco: navegação de 2 níveis (cluster -> aba), backward compatibility de URLs
antigas, whitelist de `cluster` em `ler_filtros_da_url`, e contratos canônicos
de `MAPA_ABA_PARA_CLUSTER` / `CLUSTERS_VALIDOS`.

Testes evitam subir servidor Streamlit real: usam mock `_FakeSt` injetado via
`monkeypatch.setitem(sys.modules, "streamlit", fake)`, padrão canônico do
projeto (ver BRIEF §161).
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

from src.dashboard.componentes import drilldown

# ============================================================================
# Contratos canônicos (Sprint 92b)
# ============================================================================


class TestContratosCanonicos:
    def test_clusters_validos_sao_cinco(self) -> None:
        """Acceptance A92b-1: 5 clusters Hoje/Dinheiro/Documentos/Análise/Metas."""
        assert drilldown.CLUSTERS_VALIDOS == (
            "Hoje",
            "Dinheiro",
            "Documentos",
            "Análise",
            "Metas",
        )

    def test_whitelist_inclui_cluster(self) -> None:
        """Acceptance: campo cluster lido da URL via ler_filtros_da_url."""
        assert "cluster" in drilldown.CAMPOS_FILTRO_RECONHECIDOS

    def test_mapa_aba_para_cluster_cobre_13_abas(self) -> None:
        """Acceptance: todas as 13 abas mapeadas para um dos 5 clusters."""
        esperadas = {
            "Visão Geral",
            "Extrato",
            "Contas",
            "Pagamentos",
            "Projeções",
            "Catalogação",
            "Completude",
            "Busca Global",
            "Grafo + Obsidian",
            "Categorias",
            "Análise",
            "IRPF",
            "Metas",
        }
        assert set(drilldown.MAPA_ABA_PARA_CLUSTER.keys()) == esperadas

    def test_mapa_aponta_para_clusters_validos(self) -> None:
        """Invariante: nenhum valor do mapa fora de CLUSTERS_VALIDOS."""
        for aba, cluster in drilldown.MAPA_ABA_PARA_CLUSTER.items():
            assert cluster in drilldown.CLUSTERS_VALIDOS, (
                f"Aba '{aba}' mapeada para cluster desconhecido '{cluster}'"
            )

    def test_chave_session_cluster_nao_colide_com_namespaces_existentes(self) -> None:
        """Padrão BRIEF §137: filtro_* / avancado_* / seletor_* são reservados."""
        chave = drilldown.CHAVE_SESSION_CLUSTER_ATIVO
        assert not chave.startswith("filtro_")
        assert not chave.startswith("avancado_")
        assert not chave.startswith("seletor_")
        assert chave == "cluster_ativo"


# ============================================================================
# Fake streamlit para testar ler_filtros_da_url com cluster
# ============================================================================


class _FakeStCluster:
    def __init__(self, qp: dict[str, Any]) -> None:
        self.session_state: dict = {}
        self.query_params = qp


# ============================================================================
# URL antiga: ?tab=Extrato (sem cluster) -> infere Dinheiro
# ============================================================================


class TestBackwardCompatibilityUrlAntiga:
    def test_tab_extrato_infere_cluster_dinheiro(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Acceptance: URL antiga ?tab=Extrato -> cluster_ativo='Dinheiro'."""
        fake = _FakeStCluster({"tab": "Extrato"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Dinheiro"
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extrato"

    def test_tab_visao_geral_infere_cluster_hoje(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStCluster({"tab": "Visão Geral"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Hoje"

    def test_tab_irpf_infere_cluster_analise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStCluster({"tab": "IRPF"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Análise"

    def test_tab_metas_infere_cluster_metas(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeStCluster({"tab": "Metas"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Metas"

    def test_tab_catalogacao_infere_cluster_documentos(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeStCluster({"tab": "Catalogação"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Documentos"

    def test_tab_desconhecida_nao_seta_cluster(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Defensivo: tab fora do mapa não corrompe session_state."""
        fake = _FakeStCluster({"tab": "Aba Inexistente"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert drilldown.CHAVE_SESSION_CLUSTER_ATIVO not in fake.session_state


# ============================================================================
# URL nova: ?cluster=X explícito tem prioridade
# ============================================================================


class TestUrlNovaClusterExplicito:
    def test_cluster_explicito_valido_seta_session_state(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeStCluster({"cluster": "Documentos"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Documentos"

    def test_cluster_explicito_invalido_nao_seta(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Defensivo: cluster fora de CLUSTERS_VALIDOS é ignorado."""
        fake = _FakeStCluster({"cluster": "Hacker"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert drilldown.CHAVE_SESSION_CLUSTER_ATIVO not in fake.session_state

    def test_cluster_explicito_tem_prioridade_sobre_inferido(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """URL `?cluster=Análise&tab=Extrato` -> cluster explícito vence."""
        fake = _FakeStCluster({"cluster": "Análise", "tab": "Extrato"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Análise"
        # tab_ativa ainda é setada independentemente
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extrato"

    def test_cluster_com_filtro_e_tab_combinados(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """URL completa com cluster + tab + filtro, todos os três gravados."""
        fake = _FakeStCluster({"cluster": "Dinheiro", "tab": "Extrato", "categoria": "Farmácia"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Dinheiro"
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Extrato"
        assert fake.session_state["filtro_categoria"] == "Farmácia"

    def test_cluster_como_lista_na_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Alguns proxies retornam lista para duplicatas; pega primeiro."""
        fake = _FakeStCluster({"cluster": ["Dinheiro", "Metas"]})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Dinheiro"


# ============================================================================
# Smoke test de importação de app.py (acceptance #5: radio existe)
# ============================================================================


class TestSmokeApp:
    """Smoke do módulo app: importa (com streamlit real) e expõe símbolos novos."""

    def test_app_module_importa_com_streamlit_real(self) -> None:
        """Acceptance: import de app.py não levanta e expõe main() +
        _selecionar_cluster (função auxiliar nova da Sprint 92b)."""
        # streamlit real precisa estar em sys.modules porque src.dashboard.dados
        # usa @st.cache_data no módulo-level. Como o pytest suite já importa
        # streamlit em outros testes, o import aqui é trivial.
        from src.dashboard import app

        assert callable(app.main)
        assert callable(app._selecionar_cluster)

    def test_app_importa_constantes_de_cluster(self) -> None:
        from src.dashboard import app

        assert app.CLUSTERS_VALIDOS == drilldown.CLUSTERS_VALIDOS
        assert app.CHAVE_SESSION_CLUSTER_ATIVO == (drilldown.CHAVE_SESSION_CLUSTER_ATIVO)


# "Hierarquia não é opressão, é clareza." -- princípio de arquitetura da informação
