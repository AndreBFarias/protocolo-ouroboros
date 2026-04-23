"""Testes do drill-down aplicado a gráficos extras (Sprint 87.1, R73-1).

Cobre os 2 novos pontos de drill-down:

1. `visao_geral._grafico_barras_historico` — barras Receita/Despesa com
   `customdata=mes_ref` e `aplicar_drilldown` chamado (scatter Saldo fica
   sem drill porque é linha).
2. `grafo_obsidian._bar_chart` quando invocado com `drilldown_campo` —
   pipe do "Top Fornecedores" roteia clique para aba Extrato. Charts sem
   `drilldown_campo` continuam usando `st.plotly_chart` direto.

Limitação documentada: "Top 10 Categorias" em `categorias._ranking_com_variacao`
é tabela HTML, não gráfico Plotly; drill-down via clique não se aplica
(Streamlit não suporta `on_select` em tabelas). Essa limitação está escrita
como docstring da função e coberta pelo teste
`test_top10_categorias_limitacao_registrada`.
"""

from __future__ import annotations

import sys
from typing import Any

import pandas as pd
import pytest

from src.dashboard.paginas import categorias, grafo_obsidian, visao_geral

# ---------------------------------------------------------------------------
# Fakes compartilhados
# ---------------------------------------------------------------------------


class _FakeSt:
    """Mock mínimo de `streamlit` para capturar chamadas a plotly_chart."""

    def __init__(self) -> None:
        self.session_state: dict = {}
        self.query_params: dict = {}
        self.plot_calls: list[dict[str, Any]] = []

    def plotly_chart(self, fig: Any, **kwargs: Any) -> dict:
        # Guarda a fig para inspeção e finge que ninguém clicou
        # (selection vazio força `aplicar_drilldown` a não disparar rerun).
        self.plot_calls.append({"fig": fig, "kwargs": kwargs})
        return {"selection": {"points": []}}

    def rerun(self) -> None:  # pragma: no cover — nunca chamado com selection vazio
        raise AssertionError("rerun não deveria disparar com selection vazio")

    def markdown(self, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, *args: Any, **kwargs: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# 87.1 — visao_geral: Receita vs Despesa
# ---------------------------------------------------------------------------


def _extrato_sintetico_3_meses() -> pd.DataFrame:
    """Gera extrato mínimo com 3 meses para alimentar `_grafico_barras_historico`."""
    return pd.DataFrame(
        [
            {"mes_ref": "2026-01", "tipo": "Receita", "valor": 1000.0},
            {"mes_ref": "2026-01", "tipo": "Despesa", "valor": 400.0},
            {"mes_ref": "2026-02", "tipo": "Receita", "valor": 1200.0},
            {"mes_ref": "2026-02", "tipo": "Despesa", "valor": 700.0},
            {"mes_ref": "2026-03", "tipo": "Receita", "valor": 900.0},
            {"mes_ref": "2026-03", "tipo": "Despesa", "valor": 500.0},
        ]
    )


class TestVisaoGeralDrillDown:
    def test_grafico_barras_historico_aplica_customdata_e_drilldown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Os 2 traces Bar devem ter customdata = meses_sel; Scatter saldo, não."""
        fake = _FakeSt()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        # O módulo já importou `st` no topo; patch também o atributo.
        monkeypatch.setattr(visao_geral, "st", fake)
        # `aplicar_drilldown` lê streamlit internamente — já patchado via sys.modules.

        extrato = _extrato_sintetico_3_meses()
        visao_geral._grafico_barras_historico(extrato, "2026-03")

        assert len(fake.plot_calls) == 1, (
            "aplicar_drilldown chama plotly_chart exatamente uma vez"
        )
        chamada = fake.plot_calls[0]
        fig = chamada["fig"]

        # 3 traces: 2 Bar (receita, despesa) + 1 Scatter (saldo)
        assert len(fig.data) == 3
        # Trace 0 (Receita) e 1 (Despesa) têm customdata com os meses
        meses_esperados = ("2026-01", "2026-02", "2026-03")
        cd0 = tuple(fig.data[0].customdata)
        cd1 = tuple(fig.data[1].customdata)
        assert cd0 == meses_esperados
        assert cd1 == meses_esperados
        # Trace 2 (Scatter saldo) NÃO deve receber customdata
        cd2 = fig.data[2].customdata
        assert cd2 is None, "Scatter saldo não deve ter customdata (sem drill)"

        # `aplicar_drilldown` passa `key=...` e `on_select="rerun"` no plotly_chart
        assert chamada["kwargs"].get("key") == "bar_receita_despesa"
        assert chamada["kwargs"].get("on_select") == "rerun"


# ---------------------------------------------------------------------------
# 87.1 — grafo_obsidian: _bar_chart com drilldown_campo
# ---------------------------------------------------------------------------


class TestBarChartGrafoObsidianDrillDown:
    def test_bar_chart_sem_drill_usa_plotly_chart_direto(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quando `drilldown_campo=None`, preserva comportamento original."""
        fake = _FakeSt()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        monkeypatch.setattr(grafo_obsidian, "st", fake)

        itens = [
            {"rotulo": "Salário", "valor": 5000.0},
            {"rotulo": "Bonus", "valor": 1000.0},
        ]
        grafo_obsidian._bar_chart(
            itens, titulo="Receita por fonte", cor="#50fa7b", key="bar_receita"
        )

        assert len(fake.plot_calls) == 1
        kwargs = fake.plot_calls[0]["kwargs"]
        # Chart estático: SEM on_select (só use_container_width + key)
        assert "on_select" not in kwargs
        assert kwargs.get("key") == "bar_receita"

    def test_bar_chart_com_drill_aplica_aplicar_drilldown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Quando `drilldown_campo="fornecedor"`, roteia por `aplicar_drilldown`."""
        fake = _FakeSt()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        monkeypatch.setattr(grafo_obsidian, "st", fake)

        itens = [
            {"rotulo": "Neoenergia", "valor": 450.0},
            {"rotulo": "CAESB", "valor": 180.0},
        ]
        grafo_obsidian._bar_chart(
            itens,
            titulo="Top 10 fornecedores",
            cor="#ff79c6",
            key="bar_fornecedor",
            drilldown_campo="fornecedor",
        )

        assert len(fake.plot_calls) == 1
        chamada = fake.plot_calls[0]
        fig = chamada["fig"]
        # O `_bar_chart` já seta `customdata=rotulos_completos` no único trace.
        assert fig.data[0].customdata is not None
        assert tuple(fig.data[0].customdata) == ("Neoenergia", "CAESB")
        # `aplicar_drilldown` carrega on_select="rerun" + key
        kwargs = chamada["kwargs"]
        assert kwargs.get("on_select") == "rerun"
        assert kwargs.get("key") == "bar_fornecedor"

    def test_bar_chart_vazio_nao_chama_plotly_chart(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lista vazia: aviso em markdown, sem plotly_chart."""
        fake = _FakeSt()
        monkeypatch.setitem(sys.modules, "streamlit", fake)
        monkeypatch.setattr(grafo_obsidian, "st", fake)

        grafo_obsidian._bar_chart(
            [], titulo="Top 10 fornecedores", cor="#ff79c6", key="bar_fornecedor",
            drilldown_campo="fornecedor",
        )
        assert fake.plot_calls == []


# ---------------------------------------------------------------------------
# 87.1 — categorias: Top 10 é tabela HTML (limitação registrada)
# ---------------------------------------------------------------------------


class TestTop10CategoriasLimitacao:
    def test_top10_categorias_limitacao_registrada(self) -> None:
        """A docstring do ranking documenta a limitação Sprint 87.1 / R73-1."""
        doc = categorias._ranking_com_variacao.__doc__ or ""
        assert "Sprint 87.1" in doc
        assert "R73-1" in doc
        assert "tabela HTML" in doc or "tabela" in doc
        # Apontando para o fallback (treemap) preservado
        assert "treemap" in doc.lower()


# ---------------------------------------------------------------------------
# Acceptance — presença de `aplicar_drilldown` nos 4 arquivos
# ---------------------------------------------------------------------------


class TestAcceptanceCritico871:
    def test_aplicar_drilldown_em_4_paginas(self) -> None:
        """Acceptance explícito: >=4 páginas em src/dashboard/paginas/ com drill."""
        from pathlib import Path

        paginas = Path(__file__).resolve().parents[1] / "src/dashboard/paginas"
        com_drill = [
            p for p in paginas.glob("*.py") if "aplicar_drilldown" in p.read_text()
        ]
        nomes = sorted(p.name for p in com_drill)
        assert len(com_drill) >= 4, (
            f"Sprint 87.1 exige >=4 páginas com drill-down. Hoje: {nomes}"
        )
        # Garantia explícita dos 4 arquivos-alvo do spec
        assert "extrato.py" in nomes
        assert "categorias.py" in nomes
        assert "visao_geral.py" in nomes
        assert "grafo_obsidian.py" in nomes


# "Clicar no número e cair na transação: o dashboard vira ferramenta." -- Andre, 2026-04-22
