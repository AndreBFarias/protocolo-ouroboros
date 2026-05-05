"""Testes do redesign UX-RD-08 da página de Projeções.

Cobertura mínima exigida pela spec ``sprint_ux_rd_08_projecoes.md``:

1. três cenários renderizam (Plotly traces == 3);
2. marcos verticais visíveis no gráfico (count add_vline >= 1);
3. cards laterais de marcos atualizam com texto contendo "meses";
4. deep-link ``?cluster=Finanças&tab=Projeções`` preservado (renderiza
   sem AttributeError nem mudança de assinatura).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go

from src.dashboard.paginas import projecoes


def _gerar_transacoes_fake(meses: int = 18, saldo_mensal: float = 4000.0) -> pd.DataFrame:
    """Gera DataFrame de extrato fake com receita > despesa por ``meses``.

    Garante saldo médio mensal positivo (saldo_mensal) e cobertura suficiente
    para ``calcular_ritmos`` (>= 12 meses para ritmo 12m).
    """
    hoje = datetime(2026, 5, 1)
    linhas: list[dict[str, Any]] = []
    for i in range(meses):
        data = (hoje - timedelta(days=30 * (meses - 1 - i))).date()
        mes_ref = data.strftime("%Y-%m")
        # Receita
        linhas.append(
            {
                "data": data,
                "valor": 10_000.0,
                "tipo": "Receita",
                "forma_pagamento": "Pix",
                "local": "Empregador",
                "quem": "André",
                "categoria": "Salário",
                "classificacao": "N/A",
                "banco_origem": "Itaú",
                "mes_ref": mes_ref,
            }
        )
        # Despesa
        linhas.append(
            {
                "data": data,
                "valor": 10_000.0 - saldo_mensal,
                "tipo": "Despesa",
                "forma_pagamento": "Débito",
                "local": "Mercado",
                "quem": "André",
                "categoria": "Mercado",
                "classificacao": "Obrigatório",
                "banco_origem": "Itaú",
                "mes_ref": mes_ref,
            }
        )
    return pd.DataFrame(linhas)


def _dados_fake() -> dict[str, pd.DataFrame]:
    return {"extrato": _gerar_transacoes_fake()}


# ---------------------------------------------------------------------------
# 1. três cenários renderizam (Plotly traces == 3)
# ---------------------------------------------------------------------------


def test_grafico_cenarios_tem_tres_traces() -> None:
    """O gráfico Plotly principal deve conter exatamente 3 linhas (cenários)."""
    figura_capturada: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        figura_capturada["fig"] = fig

    with patch("src.dashboard.paginas.projecoes.st") as mock_st:
        mock_st.plotly_chart = fake_plotly_chart
        # Curvas mínimas
        pess = projecoes._projetar_curva(10_000.0, 0.06, 4_000.0)
        real = projecoes._projetar_curva(10_000.0, 0.09, 4_000.0)
        otim = projecoes._projetar_curva(10_000.0, 0.13, 4_000.0)
        projecoes._grafico_cenarios(pess, real, otim, marcos=[])

    assert "fig" in figura_capturada, "plotly_chart deveria ter sido chamado"
    fig = figura_capturada["fig"]
    assert len(fig.data) == 3, (
        f"Esperado 3 traces (pessimista/realista/otimista), obtido {len(fig.data)}"
    )
    nomes = {trace.name for trace in fig.data}
    assert any("Pessimista" in n for n in nomes)
    assert any("Realista" in n for n in nomes)
    assert any("Otimista" in n for n in nomes)


# ---------------------------------------------------------------------------
# 2. marcos verticais visíveis (add_vline conta >= 1 quando há marcos)
# ---------------------------------------------------------------------------


def test_grafico_cenarios_marcos_verticais_visiveis() -> None:
    """``add_vline`` deve gerar shapes/annotations no Plotly para cada marco
    cujo índice em ``real`` exista (idx >= 1). Para uma curva que cruza
    a meta, esperamos pelo menos 1 vline.
    """
    figura_capturada: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        figura_capturada["fig"] = fig

    with patch("src.dashboard.paginas.projecoes.st") as mock_st:
        mock_st.plotly_chart = fake_plotly_chart
        pess = projecoes._projetar_curva(10_000.0, 0.06, 8_000.0)
        real = projecoes._projetar_curva(10_000.0, 0.09, 8_000.0)
        otim = projecoes._projetar_curva(10_000.0, 0.13, 8_000.0)
        # 30k é atingida em poucos meses; 100k mais à frente.
        marcos = [
            (30_000.0, "Reserva 100%", "neutro"),
            (100_000.0, "1ª centena", "destaque"),
        ]
        projecoes._grafico_cenarios(pess, real, otim, marcos)

    fig = figura_capturada["fig"]
    # ``fig.layout.shapes`` traz as linhas verticais; ``fig.layout.annotations``
    # traz os labels rotacionados.
    shapes = list(fig.layout.shapes) if fig.layout.shapes else []
    annotations = list(fig.layout.annotations) if fig.layout.annotations else []
    assert len(shapes) >= 2, f"Esperado >=2 vlines, obtido {len(shapes)}"
    assert len(annotations) >= 2, (
        f"Esperado >=2 labels de marcos, obtido {len(annotations)}"
    )
    textos = {a.text for a in annotations if a.text}
    assert "Reserva 100%" in textos
    assert "1ª centena" in textos


# ---------------------------------------------------------------------------
# 3. card lateral de marcos contém texto "meses"
# ---------------------------------------------------------------------------


def test_card_marcos_html_contem_meses() -> None:
    """O HTML do card lateral deve incluir a palavra ``meses`` quando há
    marcos atingíveis (formatados via ``_formatar_meses``).
    """
    real = projecoes._projetar_curva(10_000.0, 0.09, 8_000.0)
    marcos_realista = projecoes._calcular_marcos_realista(real)
    # Mapeia para formato esperado por _card_marcos_html
    marcos_card = [
        (label, projecoes._formatar_meses(projecoes._meses_ate_meta(real, valor)), cor)
        for valor, label, cor in marcos_realista
    ]
    # Garante que pelo menos um marco foi atingível (caso contrário, fallback)
    assert marcos_card, "Esperado pelo menos um marco atingível com aporte 8k/9%"

    html = projecoes._card_marcos_html(marcos_card)
    assert "meses" in html.lower() or "atingido" in html.lower(), (
        "Card de marcos deveria conter formatação de meses ou estado 'atingido'"
    )
    # Nenhum marco deve ter ficado sem cor
    assert "border-left:2px solid" in html


# ---------------------------------------------------------------------------
# 4. deep-link preservado: renderizar(dados, periodo, pessoa) sem ctx
# ---------------------------------------------------------------------------


def test_renderizar_assinatura_publica_sem_ctx() -> None:
    """A função pública mantém assinatura ``(dados, mes_selecionado, pessoa)``
    e não levanta exceção quando recebe dados válidos.

    Cobre o deep-link ``?cluster=Finanças&tab=Projeções``: o roteador em
    ``app.py`` chama ``projecoes.renderizar(dados, periodo, pessoa)`` e a
    página deve responder sem erro.
    """
    import inspect

    sig = inspect.signature(projecoes.renderizar)
    parametros = list(sig.parameters.keys())
    assert parametros == ["dados", "mes_selecionado", "pessoa"], (
        f"Assinatura deveria ser (dados, mes_selecionado, pessoa); obtido {parametros}"
    )

    # Smoke: chamar renderizar com dados fake + Streamlit mockado não levanta
    dados = _dados_fake()
    with patch("src.dashboard.paginas.projecoes.st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock())
        mock_st.slider.return_value = 0
        mock_st.markdown = MagicMock()
        mock_st.subheader = MagicMock()
        mock_st.plotly_chart = MagicMock()
        # context manager para st.columns(...)
        for col in mock_st.columns.return_value:
            col.__enter__ = MagicMock(return_value=col)
            col.__exit__ = MagicMock(return_value=False)
        # renderizar com 3 colunas também (st.columns([2,1]))
        def _columns(spec: Any, **_: Any) -> tuple[Any, ...]:
            n = len(spec) if isinstance(spec, list) else int(spec)
            cols = []
            for _i in range(n):
                c = MagicMock()
                c.__enter__ = MagicMock(return_value=c)
                c.__exit__ = MagicMock(return_value=False)
                cols.append(c)
            return tuple(cols)

        mock_st.columns.side_effect = _columns
        projecoes.renderizar(dados, "2026-05", "André")

    # Se chegou aqui sem exceção, deep-link está ok.


# "Antes do destino, o caminho." -- proverbio
