"""Testes da Sprint UX-124 -- Busca renderiza tabela inline.

Cobre:

- `construir_dataframe_fornecedor`: filtragem case-insensitive, colunas
  canônicas, ordenação por data DESC, mascaramento PII.
- Filtros sidebar (mes_ref/quem/forma_pagamento) impactam dados antes
  da tabela ser construída.
- Refactor em `paginas.busca`: ausência do botão "Ir para Catalogacao
  filtrada", presença de `st.dataframe(construir_dataframe_fornecedor(...))`.
- Integração com export CSV.
"""

from __future__ import annotations

import inspect
import re

import pandas as pd
import pytest

from src.dashboard.componentes import busca_resultado_inline as bri
from src.dashboard.paginas import busca as pag

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def df_extrato_amostra() -> pd.DataFrame:
    """DataFrame amostra com transações de 3 fornecedores em 2 meses."""
    return pd.DataFrame(
        [
            {
                "data": "2026-04-15",
                "valor": 234.50,
                "local": "Padaria Ki-Sabor",
                "categoria": "Alimentação",
                "banco_origem": "Itau",
                "quem": "Andre",  # anonimato-allow: fixture de matcher
                "mes_ref": "2026-04",
                "forma_pagamento": "Crédito",
                "tag_irpf": "",
            },
            {
                "data": "2026-03-12",
                "valor": 850.00,
                "local": "PADARIA KI-SABOR",
                "categoria": "Aluguel",
                "banco_origem": "Itau",
                "quem": "casal",
                "mes_ref": "2026-03",
                "forma_pagamento": "Pix",
                "tag_irpf": "",
            },
            {
                "data": "2026-04-05",
                "valor": 42.10,
                "local": "Padaria Ki-Sabor Filial Lago",
                "categoria": "Alimentação",
                "banco_origem": "Nubank",
                "quem": "Vitoria",  # anonimato-allow: fixture de matcher
                "mes_ref": "2026-04",
                "forma_pagamento": "Débito",
                "tag_irpf": "",
            },
            {
                "data": "2026-04-20",
                "valor": 99.99,
                "local": "Outro Fornecedor X",
                "categoria": "Outros",
                "banco_origem": "C6",
                "quem": "Andre",  # anonimato-allow: fixture de matcher
                "mes_ref": "2026-04",
                "forma_pagamento": "Crédito",
                "tag_irpf": "",
            },
        ]
    )


# ---------------------------------------------------------------------------
# 1. Tabela com 0 / 1 / N linhas
# ---------------------------------------------------------------------------


def test_dataframe_zero_linhas_para_fornecedor_inexistente(
    df_extrato_amostra: pd.DataFrame,
) -> None:
    """Fornecedor que não existe no extrato -> DataFrame vazio com colunas."""
    df = bri.construir_dataframe_fornecedor("Inexistente", df_extrato_amostra)
    assert len(df) == 0
    assert list(df.columns) == [
        "Data",
        "Valor",
        "Local",
        "Categoria",
        "Banco",
        "Documento",
    ]


def test_dataframe_uma_linha_match_exato(
    df_extrato_amostra: pd.DataFrame,
) -> None:
    """Termo casando 1 fornecedor único -> 1 linha."""
    df = bri.construir_dataframe_fornecedor("Outro Fornecedor X", df_extrato_amostra)
    assert len(df) == 1
    assert df.iloc[0]["Banco"] == "C6"


def test_dataframe_n_linhas_para_fornecedor_recorrente(
    df_extrato_amostra: pd.DataFrame,
) -> None:
    """Padaria Ki-Sabor aparece em 3 transações (case-insensitive)."""
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_extrato_amostra)
    assert len(df) == 3
    # Todos os valores na coluna Local contêm o nome (após mascaramento).
    for v in df["Local"]:
        assert "padaria" in v.lower()


# ---------------------------------------------------------------------------
# 2. Mascaramento PII
# ---------------------------------------------------------------------------


def test_mascaramento_pii_ativo_por_default() -> None:
    """CPF e CNPJ na coluna Local devem virar mascarados."""
    df_pii = pd.DataFrame(
        [
            {
                "data": "2026-04-01",
                "valor": 100.0,
                "local": "Fulano CPF 123.456.789-01",
                "categoria": "X",
                "banco_origem": "Itau",
                "tag_irpf": "",
            },
            {
                "data": "2026-04-02",
                "valor": 200.0,
                "local": "Empresa CNPJ 12.345.678/0001-90",
                "categoria": "Y",
                "banco_origem": "C6",
                "tag_irpf": "",
            },
        ]
    )
    df = bri.construir_dataframe_fornecedor("Fulano", df_pii, mascarar_pii=True)
    assert "123.456.789-01" not in " ".join(df["Local"].astype(str))
    assert "***.***.***-**" in df.iloc[0]["Local"]


def test_mascaramento_pii_pode_ser_desativado() -> None:
    """Flag mascarar_pii=False preserva conteúdo original."""
    df_pii = pd.DataFrame(
        [
            {
                "data": "2026-04-01",
                "valor": 100.0,
                "local": "Fulano CPF 123.456.789-01",
                "categoria": "X",
                "banco_origem": "Itau",
                "tag_irpf": "",
            }
        ]
    )
    df = bri.construir_dataframe_fornecedor("Fulano", df_pii, mascarar_pii=False)
    assert "123.456.789-01" in df.iloc[0]["Local"]


# ---------------------------------------------------------------------------
# 3. Filtros sidebar (mes / pessoa / forma) impactam tabela
# ---------------------------------------------------------------------------


def test_filtro_por_mes_impacta_tabela(df_extrato_amostra: pd.DataFrame) -> None:
    """Filtro mes_ref aplicado antes da chamada deve reduzir linhas."""
    df_abril = df_extrato_amostra[df_extrato_amostra["mes_ref"] == "2026-04"]
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_abril)
    assert len(df) == 2  # 2 de abril, sem o de março


def test_filtro_por_pessoa_impacta_tabela(
    df_extrato_amostra: pd.DataFrame,
) -> None:
    """Filtrar por quem='Andre' antes -> só transações do Andre."""  # anonimato-allow
    df_andre = df_extrato_amostra[df_extrato_amostra["quem"] == "Andre"]  # anonimato-allow
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_andre)
    assert len(df) == 1
    assert df.iloc[0]["Banco"] == "Itau"


def test_filtro_por_forma_pagamento_impacta_tabela(
    df_extrato_amostra: pd.DataFrame,
) -> None:
    """Filtrar por forma_pagamento='Pix' antes -> só Pix."""
    df_pix = df_extrato_amostra[df_extrato_amostra["forma_pagamento"] == "Pix"]
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_pix)
    assert len(df) == 1
    assert df.iloc[0]["Categoria"] == "Aluguel"


# ---------------------------------------------------------------------------
# 4. Ordenação por data DESC
# ---------------------------------------------------------------------------


def test_ordenacao_por_data_decrescente(df_extrato_amostra: pd.DataFrame) -> None:
    """Tabela inline deve ordenar por data DESC (mais recente primeiro)."""
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_extrato_amostra)
    datas = list(df["Data"])
    # Esperado: 2026-04-15, 2026-04-05, 2026-03-12 (ordem DESC).
    assert datas == ["2026-04-15", "2026-04-05", "2026-03-12"]


# ---------------------------------------------------------------------------
# 5. Integração com export CSV
# ---------------------------------------------------------------------------


def test_dataframe_serializa_para_csv(df_extrato_amostra: pd.DataFrame) -> None:
    """DataFrame inline deve serializar para CSV utf-8 sem erro."""
    df = bri.construir_dataframe_fornecedor("Padaria Ki-Sabor", df_extrato_amostra)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    assert b"Data,Valor,Local,Categoria,Banco,Documento" in csv_bytes
    assert b"Padaria" in csv_bytes


# ---------------------------------------------------------------------------
# 6. Refactor em paginas.busca: ausencia do botao + presenca de st.dataframe
# ---------------------------------------------------------------------------


def test_botao_ir_para_catalogacao_removido() -> None:
    """Sprint UX-124: a chamada `st.button("Ir para Catalogacao filtrada")` foi removida.

    Apenas docstrings/comentários podem mencionar o nome (explicando o
    refactor), nunca uma chamada real `st.button(...)`.
    """
    fonte = inspect.getsource(pag)
    # Procura padrão de chamada de função: st.button(...) com string casando.
    padrao = re.compile(r"st\.button\s*\(\s*['\"]Ir para Catalog\w+ filtrada['\"]")
    assert padrao.search(fonte) is None, (
        "st.button('Ir para Catalogacao filtrada') deveria ter sido removido"
    )


def test_pagina_busca_chama_construir_dataframe_fornecedor() -> None:
    """Sprint UX-124: paginas.busca renderiza tabela via componente novo."""
    fonte = inspect.getsource(pag)
    assert "construir_dataframe_fornecedor" in fonte
    assert "st.dataframe" in fonte


def test_pagina_busca_preserva_mensagem_de_resumo() -> None:
    """Mensagem 'casa o fornecedor X. N transações encontradas' permanece."""
    fonte = inspect.getsource(pag)
    assert "casa o fornecedor" in fonte
    assert "transações encontradas" in fonte


# ---------------------------------------------------------------------------
# 7. Robustez defensiva
# ---------------------------------------------------------------------------


def test_dataframe_vazio_quando_extrato_sem_coluna_local() -> None:
    """Se `df_extrato` não tem coluna `local`, devolve DataFrame vazio."""
    df_sem_local = pd.DataFrame([{"data": "2026-04-01", "valor": 100.0}])
    df = bri.construir_dataframe_fornecedor("X", df_sem_local)
    assert len(df) == 0


def test_dataframe_vazio_quando_nome_fornecedor_falso() -> None:
    """Nome vazio -> retorno vazio (sem erro)."""
    df = bri.construir_dataframe_fornecedor(
        "", pd.DataFrame([{"local": "X", "data": "2026-04-01", "valor": 1.0}])
    )
    assert len(df) == 0


def test_formatar_valor_brl() -> None:
    """Helper interno deve formatar com separador BR."""
    assert bri._formatar_valor_brl(1234.56) == "R$ 1.234,56"
    assert bri._formatar_valor_brl(-50.0) == "-R$ 50,00"
    assert bri._formatar_valor_brl(None) == "--"


# "Cada teste é uma promessa cumprida ao usuário." -- Aristóteles (parafraseado)
