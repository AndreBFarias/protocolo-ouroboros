"""Testes UX-RD-13 -- Análise reescrita (3 sub-abas + drill-down).

Cobre as funções puras do módulo ``src/dashboard/paginas/analise_avancada``:

* ``calcular_kpis_fluxo``: receita/saídas/investido/saldo
* ``preparar_dados_sankey``: 3 níveis (categoria -> classificação -> pessoa)
* ``preparar_dados_comparativo``: 4 métricas por mes_ref
* ``preparar_dados_heatmap``: matriz 7x52 + customdata mes_ref

Mais testes de invariantes UX:

* Sankey: textfont explícito presente no layout (UX-03)
* Heatmap: colorscale começa em ``texto_muted`` (não fundo) -- UX-RD-12
  invariante WCAG-AA contra "cell desaparece"

Não cobre rendering Streamlit propriamente dito -- proof-of-work runtime
captura via streamlit + screenshot.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard.paginas.analise_avancada import (
    METRICAS_COMPARATIVO,
    _renderizar_aba_fluxo,
    _renderizar_aba_padroes,
    calcular_kpis_fluxo,
    preparar_dados_comparativo,
    preparar_dados_heatmap,
    preparar_dados_sankey,
)
from src.dashboard.tema import CORES

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def df_multi_mes() -> pd.DataFrame:
    """DataFrame cobrindo 3 meses, 3 categorias, 2 pessoas, 3 classificações."""
    linhas = []
    base_data = pd.Timestamp("2026-02-01")
    categorias = [
        ("Mercado", "Obrigatório", -290.0),
        ("Aluguel", "Obrigatório", -1280.0),
        ("Investimento", "N/A", -3200.0),
        ("Restaurantes", "Supérfluo", -127.0),
        ("Transporte", "Questionável", -94.0),
    ]
    pessoas = ["André", "Vitória"]

    for mes_offset in range(3):
        mes = pd.Timestamp(base_data) + pd.DateOffset(months=mes_offset)
        mes_ref = mes.strftime("%Y-%m")
        # Receita do mês
        linhas.append(
            {
                "data": mes + pd.Timedelta(days=1),
                "valor": 5000.0,
                "categoria": "Salário",
                "classificacao": "N/A",
                "tipo": "Receita",
                "quem": "André",
                "mes_ref": mes_ref,
                "forma_pagamento": "Transferência",
                "banco_origem": "Itaú",
            }
        )
        for i, (cat, cls, valor) in enumerate(categorias):
            linhas.append(
                {
                    "data": mes + pd.Timedelta(days=2 + i),
                    "valor": valor,
                    "categoria": cat,
                    "classificacao": cls,
                    "tipo": "Despesa",
                    "quem": pessoas[i % 2],
                    "mes_ref": mes_ref,
                    "forma_pagamento": "Crédito",
                    "banco_origem": "C6",
                }
            )
    return pd.DataFrame(linhas)


@pytest.fixture
def df_vazio() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["data", "valor", "categoria", "classificacao", "tipo", "quem", "mes_ref"]
    )


# ---------------------------------------------------------------------------
# Teste 1: calcular_kpis_fluxo
# ---------------------------------------------------------------------------


def test_kpis_fluxo_calcula_entradas_saidas_e_taxa_poupanca(
    df_multi_mes: pd.DataFrame,
) -> None:
    kpis = calcular_kpis_fluxo(df_multi_mes)
    # 3 meses x R$ 5000 = R$ 15.000
    assert kpis["entradas"] == pytest.approx(15000.0)
    # 3 meses x soma|despesas| (290+1280+3200+127+94) = 4991 -> total 14973
    assert kpis["saidas"] == pytest.approx(14973.0)
    # Investido = 3 x 3200 = 9600
    assert kpis["investido"] == pytest.approx(9600.0)
    # Taxa poupança = 9600 / 15000 = 0.64
    assert kpis["taxa_poupanca"] == pytest.approx(0.64)
    # Saldo = entradas - saidas
    assert kpis["saldo"] == pytest.approx(27.0)


def test_kpis_fluxo_aceita_df_vazio(df_vazio: pd.DataFrame) -> None:
    kpis = calcular_kpis_fluxo(df_vazio)
    assert kpis == {
        "entradas": 0.0,
        "saidas": 0.0,
        "investido": 0.0,
        "saldo": 0.0,
        "taxa_poupanca": 0.0,
    }


# ---------------------------------------------------------------------------
# Teste 2: preparar_dados_sankey -- 3 níveis
# ---------------------------------------------------------------------------


def test_sankey_emite_tres_niveis_categoria_classificacao_pessoa(
    df_multi_mes: pd.DataFrame,
) -> None:
    dados = preparar_dados_sankey(df_multi_mes)
    assert dados, "Sankey não pode retornar vazio para df válido"
    # Categorias top (5 únicas) + 3 classificações + 2 pessoas = 10 nós
    assert dados["n_categorias"] >= 1
    assert dados["n_classificacoes"] >= 2
    assert dados["n_pessoas"] == 2
    # Total de labels = soma dos 3 níveis
    assert len(dados["labels"]) == (
        dados["n_categorias"] + dados["n_classificacoes"] + dados["n_pessoas"]
    )
    # source/target/value mesma cardinalidade
    assert len(dados["source"]) == len(dados["target"]) == len(dados["value"])
    # Pelo menos uma aresta categoria->classificação E uma classificação->pessoa
    assert len(dados["source"]) > dados["n_categorias"]


def test_sankey_retorna_vazio_para_df_sem_despesas(df_vazio: pd.DataFrame) -> None:
    assert preparar_dados_sankey(df_vazio) == {}


# ---------------------------------------------------------------------------
# Teste 3: preparar_dados_comparativo -- 4 métricas por mes
# ---------------------------------------------------------------------------


def test_comparativo_emite_quatro_metricas_por_mes(df_multi_mes: pd.DataFrame) -> None:
    df_comp = preparar_dados_comparativo(df_multi_mes)
    # 3 meses na fixture
    assert len(df_comp) == 3
    # Colunas canônicas presentes (4 métricas + mes_ref)
    for col in ["mes_ref", *METRICAS_COMPARATIVO]:
        assert col in df_comp.columns, f"Coluna ausente: {col}"
    # Receita = 5000 em cada mês
    assert (df_comp["Receita"] == 5000.0).all()
    # Despesa positiva (valor absoluto)
    assert (df_comp["Despesa"] > 0).all()
    # % Poupança calculado e dentro de [-100, 100] (saldo pode ser negativo
    # em meses com investimento alto)
    assert df_comp["% Poupança"].abs().max() <= 100.0


def test_comparativo_aceita_df_vazio(df_vazio: pd.DataFrame) -> None:
    df_comp = preparar_dados_comparativo(df_vazio)
    assert df_comp.empty
    assert list(df_comp.columns) == ["mes_ref", *METRICAS_COMPARATIVO]


# ---------------------------------------------------------------------------
# Teste 4: preparar_dados_heatmap -- estrutura 7x52 + customdata
# ---------------------------------------------------------------------------


def test_heatmap_emite_matriz_sete_linhas(df_multi_mes: pd.DataFrame) -> None:
    dados = preparar_dados_heatmap(df_multi_mes)
    assert dados, "Heatmap não pode retornar vazio para df válido"
    # 7 dias da semana
    assert len(dados["z"]) == 7
    assert dados["y"] == ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    # Cada linha tem o mesmo número de colunas (semanas)
    n_semanas = len(dados["z"][0])
    for linha in dados["z"]:
        assert len(linha) == n_semanas
    # x labels alinhados com colunas
    assert len(dados["x"]) == n_semanas
    # customdata existe e tem mesma forma
    assert len(dados["customdata"]) == 7
    for linha in dados["customdata"]:
        assert len(linha) == n_semanas
    # Pelo menos um cell com mes_ref preenchido
    valores_mes = [v for linha in dados["customdata"] for v in linha if v]
    assert len(valores_mes) > 0
    # mes_ref segue padrão YYYY-MM
    for v in valores_mes:
        assert len(v) == 7 and v[4] == "-"


# ---------------------------------------------------------------------------
# Teste 5: invariante visual UX-03 -- Sankey textfont explícito
# ---------------------------------------------------------------------------


def test_sankey_renderizacao_aplica_textfont_visivel(
    df_multi_mes: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Captura figs renderizados via mock de st.plotly_chart -- garante que
    o layout Sankey carrega ``textfont`` com cor de texto explícita
    (invariante UX-03 contra labels apagados em viewport >=1200px)."""
    import streamlit as st

    figs_capturadas: list = []

    def fake_plotly_chart(fig, **kwargs):  # noqa: ANN001
        figs_capturadas.append(fig)

    monkeypatch.setattr(st, "plotly_chart", fake_plotly_chart)
    monkeypatch.setattr(st, "columns", lambda n: tuple(_DummyCol() for _ in range(n)))
    monkeypatch.setattr(st, "markdown", lambda *_a, **_k: None)

    _renderizar_aba_fluxo(df_multi_mes)

    # Pelo menos uma figura é Sankey
    sankey_figs = [
        f
        for f in figs_capturadas
        if f.data and f.data[0].type == "sankey"
    ]
    assert len(sankey_figs) == 1
    sankey = sankey_figs[0].data[0]
    # textfont explícito não-nulo
    assert sankey.textfont is not None
    assert sankey.textfont.color == CORES["texto"]


# ---------------------------------------------------------------------------
# Teste 6: invariante WCAG-AA -- Heatmap colorscale começa visível
# ---------------------------------------------------------------------------


def test_heatmap_colorscale_nao_comeca_no_fundo_para_evitar_cell_invisivel(
    df_multi_mes: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UX-RD-12 invariante: cell de valor zero deve permanecer visível.

    Antes da reescrita o token inicial era ``CORES['fundo']`` (#0e0f15),
    fazendo cells de valor baixo desaparecerem contra o fundo Dracula. O
    primeiro stop da colorscale agora é ``texto_muted`` (#6c6f7d), com
    contraste suficiente para distinguir ausência de dado da própria
    moldura.
    """
    import streamlit as st

    figs_capturadas: list = []

    def fake_plotly_chart(fig, **kwargs):  # noqa: ANN001
        figs_capturadas.append(fig)
        return None

    # aplicar_drilldown chama st.plotly_chart internamente
    monkeypatch.setattr(st, "plotly_chart", fake_plotly_chart)
    monkeypatch.setattr(st, "markdown", lambda *_a, **_k: None)

    _renderizar_aba_padroes(df_multi_mes)

    heatmaps = [
        f for f in figs_capturadas if f.data and f.data[0].type == "heatmap"
    ]
    assert len(heatmaps) == 1
    heatmap = heatmaps[0].data[0]
    colorscale = heatmap.colorscale
    # Primeiro stop: posição 0.0 e cor != fundo
    primeiro_stop_pos, primeiro_stop_cor = colorscale[0]
    assert primeiro_stop_pos == 0.0
    assert primeiro_stop_cor != CORES["fundo"], (
        f"colorscale[0] não pode ser CORES['fundo']={CORES['fundo']!r} -- "
        "violaria invariante UX-RD-12 (cell desaparece)"
    )
    # Confirma que é texto_muted (decisão canonizada)
    assert primeiro_stop_cor == CORES["texto_muted"]


# ---------------------------------------------------------------------------
# Helper: dummy column manager para st.columns mock
# ---------------------------------------------------------------------------


class _DummyCol:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


# "Aqueles que não conseguem lembrar o passado estão condenados a repeti-lo." -- George Santayana
