"""Testes de localização PT-BR dos gráficos do dashboard (Sprint 65).

Valida o helper `aplicar_locale_ptbr` e os dicionários `MESES_PTBR` /
`MESES_PTBR_COMPLETO`: tradução de rótulos de eixo x, separadores
decimais brasileiros e robustez contra entradas inválidas.

Não sobe Streamlit; inspeciona o módulo `src.dashboard.tema` e objetos
Plotly (`plotly.graph_objects.Figure`) diretamente.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.dashboard.tema import (
    MESES_PTBR,
    MESES_PTBR_COMPLETO,
    aplicar_locale_ptbr,
    formatar_mes_ptbr,
)


class TestDicionariosMeses:
    def test_meses_ptbr_cobre_12_meses(self):
        assert set(MESES_PTBR.keys()) == set(range(1, 13))

    def test_meses_ptbr_abreviados_corretos(self):
        assert MESES_PTBR[1] == "Jan"
        assert MESES_PTBR[2] == "Fev"
        assert MESES_PTBR[3] == "Mar"
        assert MESES_PTBR[4] == "Abr"
        assert MESES_PTBR[5] == "Mai"
        assert MESES_PTBR[6] == "Jun"
        assert MESES_PTBR[7] == "Jul"
        assert MESES_PTBR[8] == "Ago"
        assert MESES_PTBR[9] == "Set"
        assert MESES_PTBR[10] == "Out"
        assert MESES_PTBR[11] == "Nov"
        assert MESES_PTBR[12] == "Dez"

    def test_meses_ptbr_completo_cobre_12_meses(self):
        assert set(MESES_PTBR_COMPLETO.keys()) == set(range(1, 13))

    def test_meses_ptbr_completo_acentuados_corretamente(self):
        # "Março" tem cedilha; "Abril" não; "Fevereiro", "Setembro", "Outubro",
        # "Novembro", "Dezembro" sem acentos especiais mas com terminações
        # coerentes.
        assert MESES_PTBR_COMPLETO[3] == "Março"
        assert MESES_PTBR_COMPLETO[4] == "Abril"
        assert MESES_PTBR_COMPLETO[2] == "Fevereiro"
        assert MESES_PTBR_COMPLETO[9] == "Setembro"


class TestFormatarMesPtbr:
    def test_formato_abreviado_padrao(self):
        assert formatar_mes_ptbr("2025-11") == "Nov/25"
        assert formatar_mes_ptbr("2026-04") == "Abr/26"
        assert formatar_mes_ptbr("2019-10") == "Out/19"

    def test_formato_completo_quando_solicitado(self):
        assert formatar_mes_ptbr("2025-11", completo=True) == "Novembro 2025"
        assert formatar_mes_ptbr("2026-04", completo=True) == "Abril 2026"
        assert formatar_mes_ptbr("2022-03", completo=True) == "Março 2022"

    def test_entrada_invalida_retorna_original(self):
        # String sem hífen: retorna original.
        assert formatar_mes_ptbr("sem-hifen-valido-aqui") == "sem-hifen-valido-aqui"
        assert formatar_mes_ptbr("2025") == "2025"
        assert formatar_mes_ptbr("2025-13") == "2025-13"

    def test_entrada_nao_str_retorna_str(self):
        assert formatar_mes_ptbr(None) == "None"  # type: ignore[arg-type]
        assert formatar_mes_ptbr(12345) == "12345"  # type: ignore[arg-type]


class TestAplicarLocalePtbr:
    def test_separadores_ptbr_aplicados(self):
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["2025-11", "2025-12"], y=[100.5, 200.75]))
        aplicar_locale_ptbr(fig, valores_eixo_x=["2025-11", "2025-12"])
        assert fig.layout.separators == ",."

    def test_ticktext_traduz_para_ptbr(self):
        fig = go.Figure()
        meses = ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03", "2026-04"]
        fig.add_trace(go.Bar(x=meses, y=[10, 20, 30, 40, 50, 60]))
        aplicar_locale_ptbr(fig, valores_eixo_x=meses)
        ticktext = list(fig.layout.xaxis.ticktext)
        assert ticktext == ["Nov/25", "Dez/25", "Jan/26", "Fev/26", "Mar/26", "Abr/26"]

    def test_tickvals_preservam_valores_originais(self):
        fig = go.Figure()
        meses = ["2025-11", "2026-04"]
        fig.add_trace(go.Bar(x=meses, y=[10, 60]))
        aplicar_locale_ptbr(fig, valores_eixo_x=meses)
        tickvals = list(fig.layout.xaxis.tickvals)
        assert tickvals == ["2025-11", "2026-04"]

    def test_tickmode_array_aplicado(self):
        fig = go.Figure()
        aplicar_locale_ptbr(fig, valores_eixo_x=["2025-11"])
        assert fig.layout.xaxis.tickmode == "array"

    def test_sem_valores_eixo_x_aplica_apenas_separadores(self):
        fig = go.Figure()
        aplicar_locale_ptbr(fig)
        assert fig.layout.separators == ",."
        # ticktext não é setado, permanece None
        assert fig.layout.xaxis.ticktext is None

    def test_valores_eixo_x_vazio_nao_seta_ticks(self):
        fig = go.Figure()
        aplicar_locale_ptbr(fig, valores_eixo_x=[])
        assert fig.layout.separators == ",."
        assert fig.layout.xaxis.ticktext is None

    def test_retorno_e_mesma_figura(self):
        fig = go.Figure()
        retornado = aplicar_locale_ptbr(fig, valores_eixo_x=["2025-11"])
        assert retornado is fig


# "Idioma é parte da experiência." -- princípio de UX local
