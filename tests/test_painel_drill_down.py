"""Testes unitários do painel de drill-down (INFRA-DRILL-DOWN-ITEM).

Cobre as funções puras de ``src.dashboard.componentes.painel_drill_down``:
header, documento vinculado, itens, cruzamentos, sem-vínculo e a função
pública ``renderizar_painel_drill_down``. Persistência em
``revisao_humana.sqlite`` é coberta com tmp_path.

Não exercita Streamlit -- esse caminho é coberto pelo smoke runtime do
proof-of-work da sprint.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.dashboard.componentes.painel_drill_down import (
    persistir_revisao,
    renderizar_painel_drill_down,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def transacao_drogasil() -> dict:
    return {
        "data": "2021-04-07",
        "valor": -73.35,
        "local": "DROGASIL",
        "banco_origem": "Itaú",
        "identificador": "abc12345deadbeef" * 4,  # sha256 fictício
    }


@pytest.fixture
def documento_nfce() -> dict:
    return {
        "nome_canonico": "9f8e7d6c5b4a3210" * 4,
        "tipo_documento": "nfce_modelo_65",
        "data_emissao": "2021-04-07",
        "razao_social": "DROGASIL S/A",
        "arquivo_origem": "inbox/2021-04/nfce_drogasil.xml",
    }


@pytest.fixture
def itens_drogasil() -> list[dict]:
    return [
        {
            "codigo": "EAN-7891234",
            "descricao": "DIPIRONA SODICA 500MG 20CP",
            "quantidade": 2,
            "valor_unitario": 12.50,
            "valor_total": 25.00,
        },
        {
            "codigo": "EAN-7899999",
            "descricao": "PARACETAMOL 750MG 30CP",
            "quantidade": 1.0,
            "valor_unitario": 18.35,
            "valor_total": 18.35,
        },
    ]


# ---------------------------------------------------------------------------
# Testes de blocos
# ---------------------------------------------------------------------------


def test_header_mostra_data_valor_local_sha8(transacao_drogasil: dict) -> None:
    html = renderizar_painel_drill_down(transacao_drogasil)
    assert "2021-04-07" in html
    assert "DROGASIL" in html
    assert "Itaú" in html
    # valor formatado PT-BR
    assert "73,35" in html
    # sha8 = 8 chars do identificador
    assert "abc12345" in html
    assert "drill-down" in html.lower() or "DRILL-DOWN" in html


def test_painel_sem_vinculo_mostra_callout(transacao_drogasil: dict) -> None:
    html = renderizar_painel_drill_down(transacao_drogasil, documento=None)
    # Bloco de itens NÃO deve aparecer quando não há vínculo
    assert "Sem documento vinculado" in html
    assert "INFRA-LINKING-NFE-TRANSACAO" in html
    # Não pode haver tabela de itens
    assert "<table class=\"painel-drill-itens\">" not in html


def test_painel_com_documento_e_itens_renderiza_tabela(
    transacao_drogasil: dict, documento_nfce: dict, itens_drogasil: list[dict]
) -> None:
    html = renderizar_painel_drill_down(
        transacao_drogasil, documento=documento_nfce, itens=itens_drogasil
    )
    # bloco documento
    assert "DOCUMENTO VINCULADO" in html
    assert "nfce_modelo_65" in html
    assert "DROGASIL S/A" in html
    # bloco itens
    assert "DIPIRONA SODICA" in html
    assert "PARACETAMOL" in html
    assert "EAN-7891234" in html
    # valores formatados
    assert "25,00" in html
    assert "18,35" in html


def test_painel_documento_sem_itens_emite_mensagem(
    transacao_drogasil: dict, documento_nfce: dict
) -> None:
    html = renderizar_painel_drill_down(
        transacao_drogasil, documento=documento_nfce, itens=[]
    )
    assert "DOCUMENTO VINCULADO" in html
    assert "nfce_modelo_65" in html
    # mensagem de itens vazios
    assert "não tem itens granulares" in html or "Documento vinculado" in html


def test_cruzamentos_renderiza_quando_passado(
    transacao_drogasil: dict, documento_nfce: dict, itens_drogasil: list[dict]
) -> None:
    cruzamentos = [
        {
            "data": "2021-05-03",
            "local": "DROGASIL",
            "valor": -25.00,
            "sha8_transacao": "deadc0de",
            "produto_canonico": "DIPIRONA-500MG",
        }
    ]
    html = renderizar_painel_drill_down(
        transacao_drogasil,
        documento=documento_nfce,
        itens=itens_drogasil,
        cruzamentos=cruzamentos,
    )
    assert "CRUZAMENTOS" in html
    assert "DIPIRONA-500MG" in html
    assert "deadc0de" in html


def test_cruzamentos_vazio_nao_renderiza_bloco(
    transacao_drogasil: dict, documento_nfce: dict, itens_drogasil: list[dict]
) -> None:
    html = renderizar_painel_drill_down(
        transacao_drogasil,
        documento=documento_nfce,
        itens=itens_drogasil,
        cruzamentos=[],
    )
    assert "CRUZAMENTOS" not in html


def test_html_escape_protege_contra_injecao(transacao_drogasil: dict) -> None:
    transacao = dict(transacao_drogasil)
    transacao["local"] = "<script>alert(1)</script>"
    html = renderizar_painel_drill_down(transacao)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_painel_html_e_aside_com_role_dialog(transacao_drogasil: dict) -> None:
    html = renderizar_painel_drill_down(transacao_drogasil)
    assert "<aside" in html
    assert 'role="dialog"' in html
    assert "painel-drill-down" in html


def test_valor_zero_formata_sem_quebrar() -> None:
    transacao = {
        "data": "2026-05-01",
        "valor": 0.0,
        "local": "Ajuste",
        "identificador": "00000000",
    }
    html = renderizar_painel_drill_down(transacao)
    assert "0,00" in html


# ---------------------------------------------------------------------------
# Persistência opcional
# ---------------------------------------------------------------------------


def test_persistir_revisao_no_op_quando_arquivo_inexistente(tmp_path: Path) -> None:
    db = tmp_path / "nao_existe.sqlite"
    assert persistir_revisao(transacao_id=42, db_path=db) is False
    # Arquivo nunca deve ser criado pela função (graceful degradation).
    assert not db.exists()


def test_persistir_revisao_grava_quando_arquivo_existe(tmp_path: Path) -> None:
    db = tmp_path / "revisao_humana.sqlite"
    # Simula arquivo existente (mesmo que vazio).
    db.touch()
    assert persistir_revisao(transacao_id=99, db_path=db) is True
    # Verifica linha gravada.
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.execute(
            "SELECT transacao_id, marcado_em FROM revisao_drill_down WHERE transacao_id=?",
            (99,),
        )
        row = cur.fetchone()
        assert row is not None
        assert row[0] == 99
        assert row[1] and row[1].endswith("Z")
    finally:
        conn.close()


def test_persistir_revisao_idempotente(tmp_path: Path) -> None:
    db = tmp_path / "revisao_humana.sqlite"
    db.touch()
    assert persistir_revisao(transacao_id=7, db_path=db) is True
    assert persistir_revisao(transacao_id=7, db_path=db) is True
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.execute(
            "SELECT COUNT(*) FROM revisao_drill_down WHERE transacao_id=?", (7,)
        )
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()


# "O teste é a forma honesta de saber se a função existe." -- princípio do TDD
