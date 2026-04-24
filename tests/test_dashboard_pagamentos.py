"""Testes da aba Pagamentos -- Sprint 92a item 4.

Valida `_formatar_boletos_para_exibicao`:
- datas datetime viram string YYYY-MM-DD (data e vencimento);
- colunas técnicas são renomeadas para rótulos humanos PT-BR.
"""

from __future__ import annotations

import pandas as pd

from src.dashboard.paginas.pagamentos import _formatar_boletos_para_exibicao

# ---------------------------------------------------------------------------
# Sprint 92a item 4 -- rename de colunas + formato data YYYY-MM-DD
# ---------------------------------------------------------------------------


def _df_sintetico_com_datetime() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "data": pd.Timestamp("2026-03-17 00:00:00"),
                "fornecedor": "SESC CONSULTORIOS",
                "valor": 103.93,
                "vencimento": pd.Timestamp("2026-03-19 00:00:00"),
                "status": "pago",
                "banco_origem": "C6",
            },
            {
                "data": pd.Timestamp("2026-04-01 00:00:00"),
                "fornecedor": "NEOENERGIA",
                "valor": 210.55,
                "vencimento": pd.Timestamp("2026-04-10 00:00:00"),
                "status": "pendente",
                "banco_origem": "Itaú",
            },
        ]
    )


def test_formatar_boletos_renomeia_colunas_para_ptbr() -> None:
    """Acceptance: tabela exibida usa 'Data', 'Fornecedor', 'Valor',
    'Vencimento', 'Status', 'Banco'."""
    df = _df_sintetico_com_datetime()
    resultado = _formatar_boletos_para_exibicao(df)

    assert list(resultado.columns) == [
        "Data",
        "Fornecedor",
        "Valor",
        "Vencimento",
        "Status",
        "Banco",
    ]


def test_formatar_boletos_formata_data_como_yyyy_mm_dd() -> None:
    """Acceptance: coluna `data` em formato 'YYYY-MM-DD' (string, sem 00:00:00)."""
    df = _df_sintetico_com_datetime()
    resultado = _formatar_boletos_para_exibicao(df)

    assert resultado.iloc[0]["Data"] == "2026-03-17"
    assert resultado.iloc[1]["Data"] == "2026-04-01"
    # Deve ser string, não Timestamp -- garante que o st.dataframe nao
    # re-formata com horário.
    assert isinstance(resultado.iloc[0]["Data"], str)


def test_formatar_boletos_formata_vencimento_como_yyyy_mm_dd() -> None:
    """Preserva comportamento P2.2 anterior (vencimento date-only)."""
    df = _df_sintetico_com_datetime()
    resultado = _formatar_boletos_para_exibicao(df)

    assert resultado.iloc[0]["Vencimento"] == "2026-03-19"
    assert resultado.iloc[1]["Vencimento"] == "2026-04-10"


def test_formatar_boletos_aceita_data_ja_como_string() -> None:
    """Se `data` já veio como string (ex.: fallback heurístico), não quebra."""
    df = pd.DataFrame(
        [
            {
                "data": "2026-03-17",
                "fornecedor": "X",
                "valor": 1.0,
                "vencimento": "2026-03-18",
                "status": "pago",
                "banco_origem": "C6",
            }
        ]
    )
    resultado = _formatar_boletos_para_exibicao(df)
    assert resultado.iloc[0]["Data"] == "2026-03-17"
    assert resultado.iloc[0]["Vencimento"] == "2026-03-18"


def test_formatar_boletos_nao_quebra_com_dataframe_parcial() -> None:
    """Contrato defensivo: se faltar coluna `status`, as demais ainda renomeiam."""
    df = pd.DataFrame(
        [
            {
                "data": pd.Timestamp("2026-03-17"),
                "fornecedor": "X",
                "valor": 1.0,
                "banco_origem": "C6",
            }
        ]
    )
    resultado = _formatar_boletos_para_exibicao(df)
    # Status ausente na origem -> ausente no resultado (não cria coluna).
    assert "Status" not in resultado.columns
    assert "Data" in resultado.columns
    assert "Fornecedor" in resultado.columns
    assert "Valor" in resultado.columns
    assert "Banco" in resultado.columns


def test_formatar_boletos_nao_muta_original() -> None:
    """Função não deve alterar o DataFrame recebido (side-effect free)."""
    df = _df_sintetico_com_datetime()
    original_colunas = list(df.columns)
    _ = _formatar_boletos_para_exibicao(df)
    assert list(df.columns) == original_colunas  # colunas preservadas
    # Timestamp original preservado em data e vencimento.
    assert pd.api.types.is_datetime64_any_dtype(df["data"])
    assert pd.api.types.is_datetime64_any_dtype(df["vencimento"])


# "Um cabeçalho humano poupa 30 segundos de interpretação mental." -- princípio UX
