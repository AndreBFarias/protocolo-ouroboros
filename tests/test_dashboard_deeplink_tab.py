"""Testes do deep-link `?tab=X` funcional dentro de cluster -- Sprint 100.

Foco: `gerar_html_ativar_aba` produz JS correto para cada cluster (1 teste por
cluster com tab não-default), graceful degradation em entradas inválidas,
write-back de URL preservado, e integração com `app.py` (constante
`ABAS_POR_CLUSTER` casa 1:1 com `MAPA_ABA_PARA_CLUSTER`).

Padrão canônico do projeto (BRIEF §161): mock Streamlit via
`monkeypatch.setitem(sys.modules, "streamlit", fake)` para evitar subir o
servidor. Aqui o JS gerado é testado por inspeção textual (substrings
canônicas), não por execução em browser headless -- a probe runtime real do
proof-of-work cobre a parte browser.
"""

from __future__ import annotations

import pytest

from src.dashboard import app
from src.dashboard.componentes import drilldown

# ============================================================================
# Casos triviais de gerar_html_ativar_aba
# ============================================================================


class TestGerarHtmlAtivarAbaTrivial:
    def test_aba_vazia_devolve_string_vazia(self) -> None:
        """Defensivo: aba_requerida='' (sem ?tab=X na URL) é no-op."""
        assert drilldown.gerar_html_ativar_aba("", ["Extrato", "Contas"]) == ""

    def test_aba_fora_do_cluster_devolve_vazio(self) -> None:
        """Defensivo: aba não pertence ao cluster (URL inconsistente)."""
        assert drilldown.gerar_html_ativar_aba("IRPF", ["Extrato", "Contas"]) == ""

    def test_lista_de_abas_vazia_devolve_vazio(self) -> None:
        assert drilldown.gerar_html_ativar_aba("Extrato", []) == ""


# ============================================================================
# 1 teste por cluster com 1 tab não-default deep-linkavel (acceptance #4)
# ============================================================================


class TestUmaTabNaoDefaultPorCluster:
    """Cobertura mínima de 5 clusters (acceptance #4 da Sprint 100).

    "Não-default" = índice != 0 dentro do cluster. Para clusters com 1 tab
    única (Hoje, Metas), o teste valida que a aba default em si gera JS
    coerente -- não há "não-default" possível, e isso documenta a borda.
    """

    def test_cluster_dinheiro_tab_pagamentos_indice_2(self) -> None:
        """Acceptance: ?cluster=Dinheiro&tab=Pagamentos abre tab índice 2."""
        abas = app.ABAS_POR_CLUSTER["Dinheiro"]
        html = drilldown.gerar_html_ativar_aba("Pagamentos", abas)
        assert "const indiceAlvo = 2;" in html
        assert '"Pagamentos": 2' in html

    def test_cluster_documentos_tab_revisor_indice_3(self) -> None:
        """Sprint UX-110: cluster Documentos foi reordenado e Busca Global virou
        índice 0 (default). Para testar uma tab não-default, escolhemos Revisor
        que ficou no índice 3 da nova ordem."""
        abas = app.ABAS_POR_CLUSTER["Documentos"]
        html = drilldown.gerar_html_ativar_aba("Revisor", abas)
        assert "const indiceAlvo = 3;" in html
        assert '"Revisor": 3' in html
        # Default agora é Busca Global (índice 0) -- garante que não é ela.
        assert "const indiceAlvo = 0;" not in html

    def test_cluster_analise_tab_irpf_indice_2(self) -> None:
        abas = app.ABAS_POR_CLUSTER["Análise"]
        html = drilldown.gerar_html_ativar_aba("IRPF", abas)
        assert "const indiceAlvo = 2;" in html
        assert '"IRPF": 2' in html

    def test_cluster_hoje_tab_visao_geral_unica(self) -> None:
        """Cluster com 1 tab: ainda assim gera JS válido (no-op no click,
        mas write-back é instalado).
        """
        abas = app.ABAS_POR_CLUSTER["Hoje"]
        html = drilldown.gerar_html_ativar_aba("Visão Geral", abas)
        assert "const indiceAlvo = 0;" in html
        assert '"Visão Geral": 0' in html

    def test_cluster_metas_tab_metas_unica(self) -> None:
        abas = app.ABAS_POR_CLUSTER["Metas"]
        html = drilldown.gerar_html_ativar_aba("Metas", abas)
        assert "const indiceAlvo = 0;" in html
        assert '"Metas": 0' in html


# ============================================================================
# Estrutura do JS gerado: write-back + graceful degradation
# ============================================================================


class TestEstruturaDoJavaScriptGerado:
    def test_html_contem_write_back_via_replacestate(self) -> None:
        """Acceptance #3: trocar tab manualmente atualiza ?tab=X (browser back).

        Sprint UX-110: usa Revisor (não-default) em vez de Busca Global (default).
        """
        abas = app.ABAS_POR_CLUSTER["Documentos"]
        html = drilldown.gerar_html_ativar_aba("Revisor", abas)
        assert "history.replaceState" in html
        assert "searchParams.set('tab'" in html

    def test_html_usa_window_parent_para_acessar_iframe_pai(self) -> None:
        """`st.components.v1.html` renderiza em iframe; precisa de window.parent."""
        abas = app.ABAS_POR_CLUSTER["Análise"]
        html = drilldown.gerar_html_ativar_aba("Categorias", abas)
        assert "window.parent" in html

    def test_html_tem_graceful_degradation_se_dom_nao_pronto(self) -> None:
        """Se `[role="tab"]` não existe ainda, reagenda algumas vezes e
        desiste silenciosamente -- sem crash visual.
        """
        abas = app.ABAS_POR_CLUSTER["Dinheiro"]
        html = drilldown.gerar_html_ativar_aba("Contas", abas)
        # Loop de retry com limite finito (atual: 8 tentativas).
        assert "tentativa <" in html
        assert "setTimeout" in html
        # try/catch ao redor do replaceState (defesa contra cross-origin)
        assert "try {" in html and "catch (e)" in html

    def test_html_evita_re_instalar_listener(self) -> None:
        """Idempotência: rerun não acumula listeners no mesmo elemento."""
        abas = app.ABAS_POR_CLUSTER["Dinheiro"]
        html = drilldown.gerar_html_ativar_aba("Extrato", abas)
        assert "ouroborosListener" in html

    def test_html_evita_click_redundante_se_ja_ativo(self) -> None:
        """Click só dispara se aria-selected != 'true'. Evita rerun em loop
        causado pelo Streamlit re-renderizar e clicar de novo."""
        abas = app.ABAS_POR_CLUSTER["Documentos"]
        html = drilldown.gerar_html_ativar_aba("Revisor", abas)
        assert "aria-selected" in html


# ============================================================================
# Sincronia entre ABAS_POR_CLUSTER (app.py) e MAPA_ABA_PARA_CLUSTER (drilldown)
# ============================================================================


class TestSincroniaConstantes:
    def test_abas_por_cluster_cobre_5_clusters(self) -> None:
        assert set(app.ABAS_POR_CLUSTER.keys()) == set(drilldown.CLUSTERS_VALIDOS)

    def test_toda_aba_de_app_aparece_em_mapa_para_cluster(self) -> None:
        """Invariante N-para-N: o mapa de drilldown enxerga 100% das abas
        que app.py renderiza.
        """
        abas_app: set[str] = set()
        for lista in app.ABAS_POR_CLUSTER.values():
            abas_app.update(lista)
        abas_mapa = set(drilldown.MAPA_ABA_PARA_CLUSTER.keys())
        assert abas_app == abas_mapa, (
            f"Abas em app.py mas não em MAPA_ABA_PARA_CLUSTER: "
            f"{abas_app - abas_mapa}; e vice-versa: {abas_mapa - abas_app}"
        )

    def test_cada_aba_pertence_ao_cluster_correto(self) -> None:
        """Para cada aba em ABAS_POR_CLUSTER[cluster], o mapa diz `cluster`."""
        for cluster, abas in app.ABAS_POR_CLUSTER.items():
            for aba in abas:
                assert drilldown.MAPA_ABA_PARA_CLUSTER[aba] == cluster, (
                    f"Aba '{aba}' está em ABAS_POR_CLUSTER['{cluster}'] mas "
                    f"MAPA_ABA_PARA_CLUSTER aponta para "
                    f"'{drilldown.MAPA_ABA_PARA_CLUSTER[aba]}'"
                )


# ============================================================================
# Integração com ler_filtros_da_url: ?cluster=X&tab=Y popula session_state
# ============================================================================


class _FakeStCluster:
    def __init__(self, qp: dict) -> None:
        self.session_state: dict = {}
        self.query_params = qp


class TestIntegracaoComLerFiltrosDaUrl:
    """Garante que o pipeline completo URL -> session_state -> JS funciona."""

    def test_url_completa_documentos_busca_global(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Acceptance #1: ?cluster=Documentos&tab=Busca+Global popula tudo.

        Sprint UX-110: Busca Global virou índice 0 (primeira aba do cluster).
        """
        import sys

        fake = _FakeStCluster({"cluster": "Documentos", "tab": "Busca Global"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Documentos"
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Busca Global"

        # Agora simula app.py: pega a aba requerida + abas do cluster e gera JS.
        cluster = fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO]
        aba = fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA]
        html = drilldown.gerar_html_ativar_aba(aba, app.ABAS_POR_CLUSTER[cluster])
        assert "const indiceAlvo = 0;" in html  # Busca Global é índice 0 (Sprint UX-110)

    def test_url_so_com_tab_infere_cluster_e_gera_js(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Acceptance #2: ?tab=Categorias sem cluster infere Análise."""
        import sys

        fake = _FakeStCluster({"tab": "Categorias"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Análise"
        assert fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA] == "Categorias"

        cluster = fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO]
        aba = fake.session_state[drilldown.CHAVE_SESSION_ABA_ATIVA]
        html = drilldown.gerar_html_ativar_aba(aba, app.ABAS_POR_CLUSTER[cluster])
        assert "const indiceAlvo = 0;" in html  # Categorias é índice 0


# "URL é contrato. Quem clicou em link tem direito a chegar onde queria." -- Andre
