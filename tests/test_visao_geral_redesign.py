"""Testes do redesign UX-RD-04 da página Visão Geral.

Validam:
1. ``_kpi_grid_html`` emite 4 cards (Receita, Despesa, Saldo, Reserva).
2. Valores formatados em moeda BRL aparecem nos cards.
3. ``_ultimos_eventos`` retorna até 5 eventos ordenados por data desc.
4. ``_cluster_grid_html`` emite 6 cluster cards com hrefs canônicos.
5. ``_estilos_locais`` injeta classes ``.vg-hero``, ``.vg-kpi``,
   ``.vg-cluster-card``, ``.vg-timeline``.
6. ``renderizar`` renderiza sem exception com extrato mínimo (AppTest).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.dashboard.paginas import visao_geral as vg

RAIZ = Path(__file__).resolve().parents[1]


# ============================================================================
# 1) KPI grid emite 4 cards
# ============================================================================


class TestKpiGridQuatroCards:
    def test_kpi_grid_renderiza_quatro_cards(self) -> None:
        html = vg._kpi_grid_html(
            receitas=5000.0,
            despesas=3200.0,
            saldo=1800.0,
            reserva_atual=22000.0,
            reserva_meta=44019.78,
            reserva_pct=50.0,
            delta_receita=12.5,
            delta_despesa=-3.0,
            delta_saldo=20.0,
        )
        # Quatro cards ``.vg-kpi <modifier>`` devem aparecer (além
        # do wrapper ``.vg-kpi-grid``).
        assert html.count('class="vg-kpi-grid"') == 1
        # 'vg-kpi ' (com espaço) só aparece no card individual seguido
        # de modificador (up/warn/bad).
        assert html.count('class="vg-kpi ') == 4

    def test_kpi_grid_inclui_labels_dos_quatro_kpis(self) -> None:
        html = vg._kpi_grid_html(
            receitas=0.0,
            despesas=0.0,
            saldo=0.0,
            reserva_atual=0.0,
            reserva_meta=44019.78,
            reserva_pct=0.0,
            delta_receita=0.0,
            delta_despesa=0.0,
            delta_saldo=0.0,
        )
        for label in ("Receita", "Despesa", "Saldo", "Reserva"):
            assert f">{label}<" in html, f"label '{label}' deve estar no KPI grid"


# ============================================================================
# 2) Valores reais formatados aparecem
# ============================================================================


class TestKpiGridValoresReais:
    def test_valores_formatados_em_brl(self) -> None:
        html = vg._kpi_grid_html(
            receitas=12_345.67,
            despesas=8_901.23,
            saldo=3_444.44,
            reserva_atual=44_019.78,
            reserva_meta=44_019.78,
            reserva_pct=100.0,
            delta_receita=5.0,
            delta_despesa=-2.0,
            delta_saldo=10.0,
        )
        # ``formatar_moeda`` retorna formato "R$ 12.345,67".
        assert "12.345,67" in html
        assert "8.901,23" in html
        assert "3.444,44" in html
        assert "44.019,78" in html
        # Reserva 100% atingida: classe ``up`` no card.
        assert "vg-kpi up" in html


# ============================================================================
# 3) Timeline com últimos 5 eventos
# ============================================================================


class TestUltimosEventos:
    def test_timeline_last_five_events_ordenados_por_data_desc(self) -> None:
        extrato = pd.DataFrame(
            {
                "data": [
                    "2026-04-01",
                    "2026-04-15",
                    "2026-04-20",
                    "2026-04-25",
                    "2026-04-28",
                    "2026-04-30",  # Sexto: deve ser o primeiro retornado.
                ],
                "valor": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
                "tipo": ["Despesa"] * 6,
                "local": ["A", "B", "C", "D", "E", "F"],
                "categoria": ["Mercado"] * 6,
                "mes_ref": ["2026-04"] * 6,
            }
        )

        eventos = vg._ultimos_eventos(extrato, n=5)

        assert len(eventos) == 5
        # Mais recente primeiro: F (30/04), E (28/04), D (25/04), ...
        assert "<strong>F</strong>" in eventos[0]["what"]
        assert "<strong>E</strong>" in eventos[1]["what"]

    def test_timeline_extrato_vazio_retorna_lista_vazia(self) -> None:
        df_vazio = pd.DataFrame({"data": [], "valor": [], "tipo": []})
        assert vg._ultimos_eventos(df_vazio) == []

    def test_timeline_html_quando_sem_eventos(self) -> None:
        html = vg._timeline_html([])
        assert "Sem eventos" in html
        assert "vg-timeline" in html


# ============================================================================
# 4) Cluster cards com 6 entradas e hrefs canônicos
# ============================================================================


class TestClusterCardsSeis:
    def test_cluster_grid_renderiza_seis_cards(self) -> None:
        dados = {
            "extrato": pd.DataFrame({"valor": [1.0, 2.0]}),
            "contas": pd.DataFrame({"banco": ["Itaú", "Nubank"]}),
            "metas": pd.DataFrame({"nome": ["m1", "m2", "m3"]}),
        }
        html = vg._cluster_grid_html(dados)
        assert html.count('class="vg-cluster-card"') == 6

    def test_cluster_grid_links_apontam_para_clusters_canonicos(self) -> None:
        html = vg._cluster_grid_html(
            {"extrato": pd.DataFrame(), "contas": pd.DataFrame(), "metas": pd.DataFrame()}
        )
        # Verifica os 6 nomes em <h3> e os hrefs querystring com cluster=.
        for nome in ("Inbox", "Finanças", "Documentos", "Análise", "Metas", "Sistema"):
            assert f"<h3>{nome}</h3>" in html
            assert f"?cluster={nome}" in html


# ============================================================================
# 5) Estilos locais com classes do redesign
# ============================================================================


class TestEstilosLocaisInjetaClasses:
    def test_estilos_locais_inclui_classes_do_redesign(self) -> None:
        css = vg._estilos_locais()
        for classe in (
            ".vg-hero",
            ".vg-kpi",
            ".vg-kpi-grid",
            ".vg-cluster-grid",
            ".vg-cluster-card",
            ".vg-timeline",
            ".vg-tl-item",
            "@keyframes ob-rotate",
            "@keyframes ob-halo",
        ):
            assert classe in css, f"classe '{classe}' deve estar nos estilos locais"


# ============================================================================
# 5b) Hero SVG inline minificado (regressão UX-RD-04 patch 2026-05-04)
# ============================================================================


class TestHeroSvgMinificadoSemVazamento:
    """Regressão do bug UX-RD-04 reprovado pelo dono.

    Sintoma original: fragmentos do SVG (``<circle cx="155" ...``,
    ``<g transform="translate(175,40)"``) apareciam como TEXTO no hero
    porque o ``st.markdown`` rotea pelo parser CommonMark antes de honrar
    ``unsafe_allow_html=True``. Linhas com 4+ espaços de indentação
    (típicas de ``<path d="M ...">`` multi-linha) eram interpretadas
    como bloco de código indentado.

    Defesa: ``_ler_svg_ouroboros`` colapsa whitespace; ``_hero_html``
    deve emitir HTML em uma única linha, sem qualquer linha indentada
    em 4+ espaços.
    """

    def test_svg_lido_sem_quebras_de_linha(self) -> None:
        svg = vg._ler_svg_ouroboros()
        assert svg, "SVG do ouroboros deve existir em assets/"
        assert "\n" not in svg, (
            "SVG inline não pode ter quebras de linha — o parser markdown "
            "do Streamlit transforma blocos indentados em <code>."
        )

    def test_svg_inline_preserva_estrutura(self) -> None:
        """Minificação não pode destruir a estrutura do SVG."""
        svg = vg._ler_svg_ouroboros()
        # Tags estruturais essenciais devem continuar presentes.
        for fragmento in (
            "<svg",
            "</svg>",
            'viewBox="0 0 320 320"',
            'class="ob-ring"',
            'class="ob-halo"',
            "<defs>",
            "</defs>",
            "OUROBOROS",
            "PROTOCOLO",
        ):
            assert fragmento in svg, f"SVG minificado perdeu fragmento essencial: {fragmento!r}"

    def test_hero_html_sem_linhas_indentadas_em_quatro_espacos(self) -> None:
        html = vg._hero_html()
        for i, linha in enumerate(html.split("\n")):
            espacos = len(linha) - len(linha.lstrip(" "))
            assert espacos < 4, (
                f"Linha {i} do hero tem indentação de {espacos} espaços; "
                f"isso vira <code> no parser markdown do Streamlit. "
                f"Linha: {linha[:80]!r}"
            )

    def test_hero_html_contem_svg_completo_em_um_unico_bloco(self) -> None:
        html = vg._hero_html()
        assert "<svg" in html and "</svg>" in html
        # O SVG deve estar inteiro entre o div .ouroboros e seu fechamento,
        # sem fragmentação que vazaria conteúdo cru.
        inicio = html.index("<svg")
        fim = html.index("</svg>") + len("</svg>")
        bloco_svg = html[inicio:fim]
        # Estruturas internas têm que estar dentro do bloco, não vazadas.
        assert "<circle" in bloco_svg
        assert 'transform="translate(175,40)"' in bloco_svg
        # Não pode haver <circle ou <path órfão FORA do bloco SVG.
        antes = html[:inicio]
        depois = html[fim:]
        for fora in (antes, depois):
            assert "<circle" not in fora, "fragmento <circle vazou fora do bloco <svg>"
            assert "<path d=" not in fora, "fragmento <path vazou fora do bloco <svg>"


# ============================================================================
# 6) renderizar() executa sem exception com extrato mínimo (AppTest)
# ============================================================================


class TestRenderizarEndToEnd:
    """Sprint UX-RD-04: integração mínima via Streamlit AppTest. Garante que
    a função ``renderizar`` não levanta exception em runtime real.
    """

    def test_renderizar_com_extrato_minimo_nao_crasha(self) -> None:
        from streamlit.testing.v1 import AppTest

        script = _script_visao_geral()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception, [str(e) for e in at.exception]

    def test_renderizar_sem_extrato_emite_warning(self) -> None:
        """ADR-10 (graceful degradation): dados vazios -> warning, não crasha."""
        from streamlit.testing.v1 import AppTest

        script = _script_visao_geral_sem_dados()
        at = AppTest.from_string(script)
        at.run()
        assert not at.exception
        textos = [m.value for m in at.markdown]
        assert any("Nenhum dado" in t for t in textos)


# ----------------------------------------------------------------------------
# Helpers de geração de script (padrão canônico do projeto)
# ----------------------------------------------------------------------------


def _script_visao_geral() -> str:
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import pandas as pd

extrato = pd.DataFrame({{
    "data": ["2026-04-01", "2026-04-15", "2026-04-20", "2026-04-28"],
    "mes_ref": ["2026-04", "2026-04", "2026-04", "2026-04"],
    "valor": [3000.0, 50.0, 30.0, 100.0],
    "tipo": ["Receita", "Despesa", "Receita", "Despesa"],
    "categoria": ["Salário", "Mercado", "Reembolso", "Combustível"],
    "classificacao": ["N/A", "Obrigatório", "N/A", "Obrigatório"],
    "local": ["Empresa Y", "Padaria X", "Empresa Y", "Posto Z"],
    "banco_origem": ["Itaú", "Itaú", "Itaú", "Nubank"],
    "quem": ["pessoa_a", "pessoa_a", "pessoa_a", "pessoa_a"],
    "forma_pagamento": ["Transferência", "Pix", "Transferência", "Crédito"],
}})
dados = {{"extrato": extrato}}

from src.dashboard.paginas import visao_geral
visao_geral.renderizar(dados, "2026-04", "Todos", None)
"""


def _script_visao_geral_sem_dados() -> str:
    return f"""
import sys
from pathlib import Path
RAIZ = Path({str(RAIZ)!r})
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

dados = {{}}

from src.dashboard.paginas import visao_geral
visao_geral.renderizar(dados, "2026-04", "Todos", None)
"""
