"""Testes regressivos da Sprint UX-121: rename do cluster 'Hoje' para 'Home'.

Cobre as quatro garantias mínimas do AC:

1. Novo nome 'Home' aparece como primeiro item canônico no selectbox Área.
2. Backward-compat: query_param ?cluster=Hoje resolve para 'Home' via alias.
3. Conteúdo da página Visão Geral inalterado (mapeamento aba->cluster ainda
   aponta para o cluster correto, agora com nome novo).
4. Drill-down via ?tab=Visão Geral continua funcional após o rename.

Spec: docs/sprints/producao/sprint_UX_121_rename_hoje_home.md
"""

from __future__ import annotations

import sys
from typing import Any

import pytest

from src.dashboard import app as app_mod
from src.dashboard.componentes import drilldown


class _FakeStCluster:
    """Mock minimalista para `ler_filtros_da_url`."""

    def __init__(self, qp: dict[str, Any]) -> None:
        self.session_state: dict = {}
        self.query_params = qp


# ============================================================================
# AC 1: 'Home' é o primeiro item canônico em CLUSTERS_VALIDOS e ABAS_POR_CLUSTER
# ============================================================================


class TestNovoNomeCanonico:
    def test_clusters_validos_comeca_com_home(self) -> None:
        """AC #1: 'Home' é o primeiro cluster (substitui 'Hoje')."""
        assert drilldown.CLUSTERS_VALIDOS[0] == "Home"
        assert "Hoje" not in drilldown.CLUSTERS_VALIDOS

    def test_abas_por_cluster_tem_chave_home(self) -> None:
        """AC #1: ABAS_POR_CLUSTER usa 'Home' como chave.

        Sprint UX-121 introduziu a chave 'Home' (antes 'Hoje').
        Sprint UX-123 expandiu para 5 abas (Visão Geral + 4 mini-views
        cross-area). Visão Geral permanece em índice 0 (default da URL antiga).
        Sprint UX-125 renomeou as 4 mini-views para espelhar clusters-irmãos
        (Finanças/Documentos/Análise/Metas) -- sem sufixo 'hoje'.
        """
        assert "Home" in app_mod.ABAS_POR_CLUSTER
        assert "Hoje" not in app_mod.ABAS_POR_CLUSTER
        assert app_mod.ABAS_POR_CLUSTER["Home"][0] == "Visão Geral"
        # UX-125: mini-view de finanças agora se chama "Finanças" (não "Dinheiro hoje").
        assert "Finanças" in app_mod.ABAS_POR_CLUSTER["Home"]
        assert "Dinheiro hoje" not in app_mod.ABAS_POR_CLUSTER["Home"]

    def test_mapa_aba_para_cluster_visao_geral_aponta_home(self) -> None:
        """AC #3: Visão Geral continua mapeada para cluster correto, com nome 'Home'."""
        assert drilldown.MAPA_ABA_PARA_CLUSTER["Visão Geral"] == "Home"


# ============================================================================
# AC 2: Backward-compat: ?cluster=Hoje resolve para 'Home' via CLUSTER_ALIASES
# ============================================================================


class TestBackwardCompatAlias:
    def test_cluster_aliases_existe_e_mapeia_hoje_para_home(self) -> None:
        """AC #2: dict CLUSTER_ALIASES preserva URLs antigas."""
        assert hasattr(drilldown, "CLUSTER_ALIASES")
        assert drilldown.CLUSTER_ALIASES.get("Hoje") == "Home"

    def test_query_param_cluster_hoje_resolve_para_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC #2: ?cluster=Hoje (URL antiga) -> session_state recebe 'Home'.

        Garante que bookmarks/links externos antigos continuam funcionando
        sem 404 nem reset para o default.
        """
        fake = _FakeStCluster({"cluster": "Hoje"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Home"

    def test_query_param_cluster_home_canonico_resolve_para_home(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC #2: ?cluster=Home (URL nova) -> session_state recebe 'Home' direto."""
        fake = _FakeStCluster({"cluster": "Home"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Home"

    def test_query_param_cluster_invalido_apos_alias_e_ignorado(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Defesa: cluster fora de CLUSTERS_VALIDOS e sem alias é silenciosamente
        ignorado (mantém comportamento Sprint 92b)."""
        fake = _FakeStCluster({"cluster": "ClusterInexistente"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert drilldown.CHAVE_SESSION_CLUSTER_ATIVO not in fake.session_state


# ============================================================================
# AC 4: Drill-down via ?tab=Visão Geral continua funcional
# ============================================================================


class TestDrillDownVisaoGeralIntacto:
    def test_tab_visao_geral_continua_inferindo_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC #4: ?tab=Visão Geral (sem cluster) -> infere cluster 'Home'.

        Regressão do mecanismo de inferência da Sprint 92b após rename.
        """
        fake = _FakeStCluster({"tab": "Visão Geral"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Visão Geral"
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Home"


# "Nome do ponto de entrada define mental model. Home eh universal."
# -- principio do default semantico
