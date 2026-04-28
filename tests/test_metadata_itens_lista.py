"""Testes Sprint AUDIT2-METADATA-ITENS-LISTA.

Cobre:
  - ingerir_documento_fiscal grava metadata.itens a partir de argumento
    `itens` (caminho NFC-e/DANFE).
  - Caller pode pre-preencher documento["itens"] (caminho holerite, sem
    upsert_item por não ter código) e o ingestor preserva.
  - _parse_g4f e _parse_infobase devolvem campo `itens` no dict.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal


@pytest.fixture()
def grafo_temp(tmp_path: Path):
    destino = tmp_path / "grafo.sqlite"
    db = GrafoDB(destino)
    db.criar_schema()
    yield db
    db.fechar()


def _ler_metadata_doc(grafo_db_path: Path, doc_id: int) -> dict:
    conn = sqlite3.connect(grafo_db_path)
    try:
        row = conn.execute("SELECT metadata FROM node WHERE id=?", (doc_id,)).fetchone()
    finally:
        conn.close()
    return json.loads(row[0])


def test_metadata_itens_populada_a_partir_de_argumento_itens(
    grafo_temp: GrafoDB, tmp_path: Path
) -> None:
    """NFC-e/DANFE: caller passa lista no argumento `itens`."""
    documento = {
        "chave_44": "X" * 44,
        "cnpj_emitente": "12345678000100",
        "data_emissao": "2026-01-15",
        "tipo_documento": "nfce_modelo_65",
        "razao_social": "LOJA TESTE LTDA",
        "total": 100.0,
    }
    itens = [
        {
            "codigo": "001",
            "descricao": "Produto A",
            "qtde": 1,
            "valor_unit": 50.0,
            "valor_total": 50.0,
        },
        {
            "codigo": "002",
            "descricao": "Produto B",
            "qtde": 2,
            "valor_unit": 25.0,
            "valor_total": 50.0,
        },
    ]
    doc_id = ingerir_documento_fiscal(grafo_temp, documento, itens=itens)
    meta = _ler_metadata_doc(tmp_path / "grafo.sqlite", doc_id)
    assert isinstance(meta["itens"], list)
    assert len(meta["itens"]) == 2
    descricoes = {it["descricao"] for it in meta["itens"]}
    assert descricoes == {"Produto A", "Produto B"}


def test_metadata_itens_preservada_quando_caller_pre_preenche(
    grafo_temp: GrafoDB, tmp_path: Path
) -> None:
    """Holerite: caller grava `documento['itens']` direto (sem upsert_item)."""
    itens_holerite = [
        {
            "descricao": "SALARIO BRUTO",
            "valor_total": 5000.0,
            "qtde": 1,
            "codigo": "",
            "tipo": "provento",
        },
        {
            "descricao": "INSS",
            "valor_total": 500.0,
            "qtde": 1,
            "codigo": "",
            "tipo": "desconto",
        },
    ]
    documento = {
        "chave_44": "HOLERITE|G4F|2026-01",
        "cnpj_emitente": "HOLERITE|abc123",
        "data_emissao": "2026-01-01",
        "tipo_documento": "holerite",
        "razao_social": "G4F SOLUCOES CORPORATIVAS LTDA",
        "total": 5000.0,
        "itens": itens_holerite,
    }
    doc_id = ingerir_documento_fiscal(grafo_temp, documento, itens=[])
    meta = _ler_metadata_doc(tmp_path / "grafo.sqlite", doc_id)
    assert len(meta["itens"]) == 2
    tipos = {it["tipo"] for it in meta["itens"]}
    assert tipos == {"provento", "desconto"}


def test_parse_g4f_devolve_campo_itens() -> None:
    from src.extractors.contracheque_pdf import _parse_g4f

    # Texto sintético casando os regex existentes (provento e desconto cada).
    texto = (
        "Demonstrativo de Pagamento de Salário: 05/25 Seg: 533\n"
        "G4F SOLUCOES CORPORATIVAS\n"
        "+   Salario Base                                 30.0    R$ 5.000,00\n"
        "-   I.N.S.S.                                     8,0   (R$ 400,00)\n"
        "Valor liquido a receber: R$ 4.600,00\n"
    )
    resultado = _parse_g4f(texto)
    assert resultado is not None
    assert "itens" in resultado
    # Pelo menos 1 provento e 1 desconto extraidos
    tipos = {it["tipo"] for it in resultado["itens"]}
    assert "provento" in tipos
    assert "desconto" in tipos


def test_parse_infobase_devolve_campo_itens() -> None:
    from src.extractors.contracheque_pdf import _parse_infobase

    # INFOBASE OCR: estrutura agregada (bruto/inss como pseudo-itens).
    # CODIGOS_INFOBASE mapeia "001" -> bruto e "100" -> inss.
    texto = (
        "INFOBASE CONSULTORIA E INFORMATICA LTDA\n"
        "Mensalista Junho de 2025\n"
        "001 SALARIO  30 10000,00\n"
        "100 INSS  8,0 1000,00\n"
    )
    resultado = _parse_infobase(texto)
    assert resultado is not None
    assert "itens" in resultado
    # Quando bruto e inss > 0, gera dois pseudo-itens
    descricoes = {it["descricao"] for it in resultado["itens"]}
    if resultado.get("bruto", 0) > 0:
        assert "SALARIO BRUTO" in descricoes


# "Item granular eh insumo de auditoria; agregado eh resumo." -- princípio AUDIT2-B2
