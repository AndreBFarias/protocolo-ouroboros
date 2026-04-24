"""Testes da página Contas (Sprint 64).

Cobre:
- Helper `renderizar_dataframe` substitui NaN por traço e não devolve
  células com a string literal "nan".
- Seções Dívidas Ativas, Inventário e Prazos exibem banner
  `st.warning` com mensagem de snapshot histórico de 2023.
- Obs nula (NaN) renderiza como "—" no HTML da tabela, nunca como
  "nan".
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from src.dashboard import dados as dashboard_dados
from src.dashboard.dados import renderizar_dataframe
from src.dashboard.paginas import contas as pagina_contas


def test_renderizar_dataframe_substitui_nan_por_traco() -> None:
    df = pd.DataFrame(
        {
            "a": [1, np.nan, 3],
            "obs": ["ok", np.nan, "fim"],
        }
    )
    df_render = renderizar_dataframe(df)

    assert "nan" not in df_render["obs"].astype(str).tolist()
    assert df_render["obs"].iloc[1] == "—"
    assert df_render["a"].iloc[1] == "—"
    # Dataframe original intacto
    assert pd.isna(df["obs"].iloc[1])


def test_renderizar_dataframe_aceita_na_rep_customizado() -> None:
    df = pd.DataFrame({"x": [np.nan, 1.0]})
    df_render = renderizar_dataframe(df, na_rep="vazio")

    assert df_render["x"].iloc[0] == "vazio"


def test_renderizar_dataframe_df_vazio_nao_explode() -> None:
    df = pd.DataFrame(columns=["a", "b"])
    df_render = renderizar_dataframe(df)

    assert df_render.empty
    assert list(df_render.columns) == ["a", "b"]


def test_renderizar_dataframe_sem_nulos_preserva_valores() -> None:
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    df_render = renderizar_dataframe(df)

    assert df_render["a"].tolist() == [1, 2]
    assert df_render["b"].tolist() == ["x", "y"]


# ----------------------------------------------------------------------
# Banner de snapshot histórico em cada seção
# ----------------------------------------------------------------------


@pytest.fixture()
def dados_minimos() -> dict[str, pd.DataFrame]:
    """Fixture com DataFrames mínimos para cada aba snapshot."""
    return {
        "dividas_ativas": pd.DataFrame(
            {
                "mes_ref": ["2026-04"],
                "custo": ["Aluguel"],
                "valor": [1500.0],
                "status": ["Não Pago"],
                "vencimento": [10],
                "quem": ["André"],
                "recorrente": [True],
                "obs": [np.nan],
            }
        ),
        "inventario": pd.DataFrame(
            {
                "bem": ["Geladeira"],
                "valor_aquisicao": [3000.0],
                "vida_util_anos": [10],
                "depreciacao_anual": [300.0],
                "perda_mensal": [25.0],
            }
        ),
        "prazos": pd.DataFrame(
            {
                "conta": ["Energia"],
                "dia_vencimento": [15],
                "banco_pagamento": ["Itaú"],
                "auto_debito": [True],
            }
        ),
    }


def _coletar_warnings(mock_st: MagicMock) -> list[str]:
    """Sprint 92c: callout_html passou a ser renderizado via st.markdown com
    HTML Dracula; coletamos strings de ambas origens (st.warning legado +
    st.markdown novo) para o teste funcionar em qualquer fase da migração.
    """
    mensagens: list[str] = []
    for c in mock_st.warning.call_args_list:
        if c.args:
            mensagens.append(str(c.args[0]))
    for c in mock_st.markdown.call_args_list:
        if c.args:
            mensagens.append(str(c.args[0]))
    return mensagens


def test_secao_dividas_exibe_banner_snapshot(dados_minimos: dict[str, pd.DataFrame]) -> None:
    with patch.object(pagina_contas, "st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
        pagina_contas._secao_dividas(dados_minimos["dividas_ativas"], "2026-04", "Todos")

    mensagens = _coletar_warnings(mock_st)
    assert any("snapshot" in m.lower() for m in mensagens), mensagens
    assert any("2023" in m for m in mensagens), mensagens


def test_secao_inventario_exibe_banner_snapshot(dados_minimos: dict[str, pd.DataFrame]) -> None:
    with patch.object(pagina_contas, "st") as mock_st:
        pagina_contas._secao_inventario(dados_minimos["inventario"])

    mensagens = _coletar_warnings(mock_st)
    assert any("snapshot" in m.lower() for m in mensagens), mensagens


def test_secao_prazos_exibe_banner_snapshot(dados_minimos: dict[str, pd.DataFrame]) -> None:
    with patch.object(pagina_contas, "st") as mock_st:
        pagina_contas._secao_prazos(dados_minimos["prazos"])

    mensagens = _coletar_warnings(mock_st)
    assert any("snapshot" in m.lower() for m in mensagens), mensagens


def test_renderizar_pagina_completa_banner_em_todas_tres_secoes(
    dados_minimos: dict[str, pd.DataFrame],
) -> None:
    with patch.object(pagina_contas, "st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
        pagina_contas.renderizar(dados_minimos, "2026-04", "Todos")

    mensagens = _coletar_warnings(mock_st)
    assert len(mensagens) >= 3, (
        f"esperado >=3 banners (Dívidas, Inventário, Prazos); obtido {len(mensagens)}: {mensagens}"
    )


# ----------------------------------------------------------------------
# Coluna Obs com NaN não vira "nan"
# ----------------------------------------------------------------------


def test_dividas_obs_nan_renderiza_como_traco(dados_minimos: dict[str, pd.DataFrame]) -> None:
    df = dados_minimos["dividas_ativas"]
    with patch.object(pagina_contas, "st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
        pagina_contas._secao_dividas(df, "2026-04", "Todos")

    html_calls = [
        c for c in mock_st.markdown.call_args_list if c.args and "<table" in str(c.args[0])
    ]
    html_tabela = str(html_calls[-1].args[0]) if html_calls else ""
    assert "nan" not in html_tabela.lower().split(">")[0] or ">nan<" not in html_tabela.lower()
    assert "—" in html_tabela or "&mdash;" in html_tabela


def test_constante_aviso_snapshot_menciona_xlsx_real() -> None:
    """O texto do aviso deve apontar para o XLSX real usado pelo dashboard."""
    assert "2023" in pagina_contas.AVISO_SNAPSHOT
    assert "snapshot" in pagina_contas.AVISO_SNAPSHOT.lower()
    assert dashboard_dados.CAMINHO_XLSX.name in pagina_contas.AVISO_SNAPSHOT


# "Vazio não é nulo: é espaço para o que ainda virá." -- Lao Tzu
