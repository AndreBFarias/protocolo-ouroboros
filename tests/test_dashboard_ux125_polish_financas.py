"""Testes regressivos da Sprint UX-125: polish final pós cluster v2.

Cobre os 5 ACs:

1. AC1 -- body 100% horizontal: `.main .block-container` e
   `[data-testid="stMainBlockContainer"]` ganham `max-width: 100%` em
   `css_global()`.
2. AC2 -- rename Dinheiro -> Finanças: CLUSTERS_VALIDOS, MAPA_ABA_PARA_CLUSTER,
   CLUSTER_ALIASES atualizados. Backward-compat via alias preserva URL antiga
   `?cluster=Dinheiro`.
3. AC3 -- tabs do Home espelham clusters: ABAS_POR_CLUSTER["Home"] = ["Visão
   Geral", "Finanças", "Documentos", "Análise", "Metas"]. Roteador em app.py
   chama as funções home_*.renderizar dos arquivos físicos (mantêm nome).
4. AC4 -- sidebar busca: label "Busca Global", placeholder vazio,
   label_visibility="visible".
5. AC5 -- input busca altura 44px (mesma dos selectboxes).

Spec: docs/sprints/producao/sprint_UX_125_polish_final_financas.md.

Padrão BRIEF §161: testes que tocam streamlit usam `monkeypatch.setitem`
para injetar fakes em `sys.modules`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from src.dashboard import app as app_mod
from src.dashboard import tema as tema_mod
from src.dashboard.componentes import busca_global_sidebar, drilldown

RAIZ = Path(__file__).resolve().parents[1]


# ============================================================================
# AC1 -- body 100% horizontal
# ============================================================================


class TestAc1BodyHorizontal:
    def test_css_global_aplica_max_width_100_no_block_container(self) -> None:
        """CSS deve declarar max-width: 100% em .main .block-container."""
        css = tema_mod.css_global()
        # A regra nova combina os dois seletores; o CSS precisa conter
        # a string 'max-width: 100%' associada a .main .block-container.
        assert ".main .block-container" in css
        assert "max-width: 100% !important" in css

    def test_css_global_cobre_testid_moderno(self) -> None:
        """Streamlit >=1.32 usa data-testid='stMainBlockContainer'.
        Regra UX-125 cobre ambos seletores."""
        css = tema_mod.css_global()
        assert '[data-testid="stMainBlockContainer"]' in css
        # No bloco da regra, width: 100% também aparece (defesa em
        # profundidade contra temas customizados que reimplementam max-width).
        assert "width: 100% !important" in css


# ============================================================================
# AC2 -- rename Dinheiro -> Finanças
# ============================================================================


class _FakeStAlias:
    def __init__(self, qp: dict[str, Any]) -> None:
        self.session_state: dict = {}
        self.query_params = qp


class TestAc2RenameFinancas:
    def test_clusters_validos_contem_financas(self) -> None:
        """CLUSTERS_VALIDOS substitui 'Dinheiro' por 'Finanças'."""
        assert "Finanças" in drilldown.CLUSTERS_VALIDOS
        assert "Dinheiro" not in drilldown.CLUSTERS_VALIDOS

    def test_clusters_validos_ordem_canonica(self) -> None:
        """Ordem fixa Home/Finanças/Documentos/Análise/Metas."""
        assert drilldown.CLUSTERS_VALIDOS == (
            "Home",
            "Finanças",
            "Documentos",
            "Análise",
            "Metas",
        )

    def test_mapa_aba_para_cluster_aponta_para_financas(self) -> None:
        """4 abas que antes apontavam para 'Dinheiro' agora apontam para 'Finanças'."""
        for aba in ("Extrato", "Contas", "Pagamentos", "Projeções"):
            assert drilldown.MAPA_ABA_PARA_CLUSTER[aba] == "Finanças", (
                f"Aba '{aba}' deveria mapear para 'Finanças', está em "
                f"'{drilldown.MAPA_ABA_PARA_CLUSTER[aba]}'"
            )

    def test_mapa_nao_tem_mais_dinheiro_como_valor(self) -> None:
        """Nenhuma entrada do MAPA pode apontar para 'Dinheiro' (cluster sumiu)."""
        for aba, cluster in drilldown.MAPA_ABA_PARA_CLUSTER.items():
            assert cluster != "Dinheiro", (
                f"Aba '{aba}' ainda mapeia para 'Dinheiro' (renomeado p/ Finanças)"
            )

    def test_cluster_aliases_dinheiro_resolve_para_financas(self) -> None:
        """Backward-compat: ?cluster=Dinheiro -> 'Finanças' via alias."""
        assert drilldown.CLUSTER_ALIASES.get("Dinheiro") == "Finanças"

    def test_query_param_dinheiro_resolve_para_financas(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """URL antiga ?cluster=Dinheiro -> session_state recebe 'Finanças'."""
        fake = _FakeStAlias({"cluster": "Dinheiro"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Finanças"

    def test_app_abas_por_cluster_tem_chave_financas(self) -> None:
        """ABAS_POR_CLUSTER usa 'Finanças' como chave (não 'Dinheiro')."""
        assert "Finanças" in app_mod.ABAS_POR_CLUSTER
        assert "Dinheiro" not in app_mod.ABAS_POR_CLUSTER
        assert app_mod.ABAS_POR_CLUSTER["Finanças"] == [
            "Extrato",
            "Contas",
            "Pagamentos",
            "Projeções",
        ]


# ============================================================================
# AC3 -- tabs do Home espelham clusters
# ============================================================================


class TestAc3TabsHomeEspelhamClusters:
    def test_abas_por_cluster_home_tem_5_tabs_canonicas(self) -> None:
        """ABAS_POR_CLUSTER['Home'] = ['Visão Geral','Finanças','Documentos','Análise','Metas']."""
        assert app_mod.ABAS_POR_CLUSTER["Home"] == [
            "Visão Geral",
            "Finanças",
            "Documentos",
            "Análise",
            "Metas",
        ]

    def test_tabs_home_nao_tem_sufixo_hoje(self) -> None:
        """Sprint UX-125: tabs do Home NÃO têm 'hoje' no label."""
        for aba in app_mod.ABAS_POR_CLUSTER["Home"]:
            assert "hoje" not in aba.lower(), (
                f"Aba '{aba}' do Home não pode mais ter 'hoje' (UX-125)"
            )

    def test_app_py_dispatcha_para_home_dinheiro_via_tab_financas(self) -> None:
        """Inspeção textual: roteador em main() chama home_dinheiro.renderizar
        no bloco da tab 'Finanças' do cluster Home (arquivo físico mantém nome)."""
        texto = (RAIZ / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
        # tab 'Finanças' aparece no st.tabs(...) do cluster Home
        assert '"Finanças"' in texto
        # As 4 mini-views ainda são chamadas pelo nome físico
        assert "home_dinheiro.renderizar" in texto
        assert "home_docs.renderizar" in texto
        assert "home_analise.renderizar" in texto
        assert "home_metas.renderizar" in texto

    def test_abas_home_homonimas_documentadas(self) -> None:
        """Sprint UX-125: ABAS_HOME_HOMONIMAS lista as 4 tabs do Home com
        nome igual a clusters próprios (Finanças/Documentos/Análise/Metas).
        Constante usada em invariantes de teste."""
        assert drilldown.ABAS_HOME_HOMONIMAS == frozenset(
            {"Finanças", "Documentos", "Análise", "Metas"}
        )

    def test_tab_visao_geral_ainda_indice_0_no_home(self) -> None:
        """Default do cluster Home permanece 'Visão Geral' (compat URL antiga
        ?cluster=Home cai em índice 0)."""
        assert app_mod.ABAS_POR_CLUSTER["Home"][0] == "Visão Geral"


# ============================================================================
# AC4 -- sidebar busca refinada
# ============================================================================


class _FakeStBusca:
    """Mock para capturar chamada `st.text_input` em `renderizar_input_busca`."""

    def __init__(self) -> None:
        self.session_state: dict = {}
        self.query_params: dict = {}
        self.text_input_calls: list[dict] = []
        self.markdown_calls: list[str] = []

    def text_input(self, label: str = "", **kwargs: Any) -> str:
        self.text_input_calls.append({"label": label, **kwargs})
        return ""

    def markdown(self, body: str = "", **_: Any) -> None:
        self.markdown_calls.append(body)


class TestAc4SidebarBusca:
    def test_label_busca_global_visivel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sprint UX-125 AC4: label='Busca Global' com label_visibility='visible'."""
        fake = _FakeStBusca()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()

        chamada = fake.text_input_calls[0]
        assert chamada["label"] == "Busca Global"
        assert chamada.get("label_visibility") == "visible"

    def test_placeholder_vazio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sprint UX-125 AC4: placeholder='' (sem texto duplicado)."""
        fake = _FakeStBusca()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()

        chamada = fake.text_input_calls[0]
        assert chamada.get("placeholder") == ""

    def test_label_nao_e_mais_buscar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reverte UX-119 que usava label='Buscar' colapsado.
        UX-125: label='Busca Global' visível."""
        fake = _FakeStBusca()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        busca_global_sidebar.renderizar_input_busca()

        chamada = fake.text_input_calls[0]
        assert chamada["label"] != "Buscar"
        assert chamada.get("label_visibility") != "collapsed"


# ============================================================================
# AC5 -- input de busca da sidebar com altura 44px
# ============================================================================


class TestAc5InputAltura44px:
    def test_css_global_define_min_height_44px_no_input_da_sidebar(self) -> None:
        """Sprint UX-125 AC5: input da sidebar ganha min-height: 44px (mesma
        regra dos selectboxes)."""
        css = tema_mod.css_global()
        # Confere que a regra existe e bate o seletor escopado na sidebar.
        assert '[data-testid="stSidebar"] [data-testid="stTextInput"]' in css
        # min-height 44px aparece na regra do input da sidebar.
        # Para evitar acoplar com whitespace, conferimos a presença substring.
        # (a regra dos selectboxes globais também usa 44px; aqui basta
        # garantir que o seletor da sidebar+textinput está presente no css)
        # Recortamos um trecho ao redor para validar valor numérico.
        idx = css.find('[data-testid="stSidebar"] [data-testid="stTextInput"]')
        assert idx >= 0
        bloco = css[idx : idx + 200]
        assert "min-height: 44px" in bloco


# ============================================================================
# Regressivos sprints anteriores
# ============================================================================


class TestRegressoesPreservadas:
    def test_alias_hoje_para_home_da_ux121_preservado(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regressão UX-121: ?cluster=Hoje continua resolvendo para 'Home'."""
        fake = _FakeStAlias({"cluster": "Hoje"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Home"

    def test_alias_dinheiro_para_financas_da_ux125_funciona(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sprint UX-125: ?cluster=Dinheiro continua resolvendo (alias)."""
        fake = _FakeStAlias({"cluster": "Dinheiro"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Finanças"

    def test_tab_extrato_ainda_infere_cluster_apos_rename(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """URL antiga ?tab=Extrato infere cluster (agora 'Finanças', era
        'Dinheiro'). Mecanismo de inferência preservado."""
        fake = _FakeStAlias({"tab": "Extrato"})
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        drilldown.ler_filtros_da_url()
        assert fake.session_state[drilldown.CHAVE_SESSION_CLUSTER_ATIVO] == "Finanças"

    def test_padding_interno_preservado_no_block_container(self) -> None:
        """Regressão UX-116: padding-{top,right,bottom,left} interno permanece
        no .main .block-container. UX-125 adicionou max-width sem remover
        os 4 paddings."""
        css = tema_mod.css_global()
        for direcao in ("top", "right", "bottom", "left"):
            assert f"padding-{direcao}: " in css, f"padding-{direcao} sumiu (regressão UX-116)"


# "Espelho do filtro: tabs do Home igualam clusters. Coerência mental." -- UX-125
