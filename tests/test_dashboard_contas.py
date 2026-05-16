"""Testes da página Contas (Sprint 64 + UX-RD-07).

Cobre:
- Helper `renderizar_dataframe` substitui NaN por traço.
- A página Contas (após UX-RD-07) exibe **um único banner** de
  snapshot histórico no topo das seções legadas, com data dinâmica
  via mtime do XLSX em vez do hardcoded "Snapshot 2023".
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
                "quem": ["pessoa_a"],
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


def test_renderizar_pagina_emite_aviso_snapshot_centralizado(
    dados_minimos: dict[str, pd.DataFrame],
) -> None:
    """UX-RD-07: aviso de snapshot é emitido UMA vez no topo das seções
    legadas (não mais por subseção). Texto deve mencionar 'snapshot' e
    'manual', sem hardcodar 2023.
    """
    with patch.object(pagina_contas, "st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
        pagina_contas.renderizar(dados_minimos, "2026-04", "Todos")

    mensagens = _coletar_warnings(mock_st)
    snapshot_msgs = [m for m in mensagens if "snapshot" in m.lower()]
    assert snapshot_msgs, f"esperava callout com 'snapshot'; mensagens: {mensagens}"
    assert all("2023" not in m for m in snapshot_msgs), (
        f"Texto não pode mais ser hardcoded em 2023: {snapshot_msgs}"
    )


def test_secoes_legadas_renderizam_sem_warnings_proprios(
    dados_minimos: dict[str, pd.DataFrame],
) -> None:
    """UX-RD-07: subseções (_secao_dividas, _inventario, _prazos) não
    emitem mais callout próprio de snapshot — quem cuida é renderizar()
    no topo. Garantia anti-regressão para evitar duplicação."""
    with patch.object(pagina_contas, "st") as mock_st:
        mock_st.columns.return_value = (MagicMock(), MagicMock(), MagicMock())
        pagina_contas._secao_dividas(dados_minimos["dividas_ativas"], "2026-04", "Todos")
        pagina_contas._secao_inventario(dados_minimos["inventario"])
        pagina_contas._secao_prazos(dados_minimos["prazos"])

    mensagens = _coletar_warnings(mock_st)
    callouts_snapshot = [m for m in mensagens if "snapshot" in m.lower() and "warning" in m.lower()]
    assert not callouts_snapshot, (
        f"Subseções não devem mais emitir callout próprio de snapshot: {callouts_snapshot}"
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


def test_aviso_snapshot_dinamico_via_mtime(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """UX-RD-07: aviso passou a ser construído por aviso_snapshot_html()
    a partir do mtime do XLSX -- não mais constante hardcoded em 2023.

    Ainda mantemos `pagina_contas.AVISO_SNAPSHOT` como texto fallback
    documentado para retrocompatibilidade de imports externos, mas o
    fluxo real chama `aviso_snapshot_html(CAMINHO_XLSX)` em runtime.
    """
    from datetime import datetime as _dt

    fake_xlsx = tmp_path / "ouroboros_2026.xlsx"
    fake_xlsx.write_text("dummy")
    ts = _dt(2025, 6, 20, 12, 0, 0).timestamp()
    import os as _os

    _os.utime(fake_xlsx, (ts, ts))

    aviso = pagina_contas.aviso_snapshot_html(fake_xlsx)
    assert "20/06/2025" in aviso
    assert "snapshot" in aviso.lower()
    assert "2023" not in aviso

    # A constante histórica continua exportada (sem 2023, já adaptada
    # em UX-RD-07) -- retrocompatibilidade de imports.
    assert "snapshot" in pagina_contas.AVISO_SNAPSHOT.lower()
    assert (
        dashboard_dados.CAMINHO_XLSX.name
        in (
            # caminho_xlsx.name aparece dentro de aviso quando XLSX existe;
            # no aviso constante, mencionamos o XLSX consolidado por nome
            # genérico ("XLSX consolidado") -- aceitamos ambos os formatos.
            pagina_contas.AVISO_SNAPSHOT + " " + aviso
        )
        or "XLSX" in pagina_contas.AVISO_SNAPSHOT
    )


# "Vazio não é nulo: é espaço para o que ainda virá." -- Lao Tzu
