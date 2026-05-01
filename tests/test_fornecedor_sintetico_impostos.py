"""Sprint 107: testes regressivos do fornecedor sintetico para impostos.

Cobre:
  1. Helper _resolver_fornecedor_sintetico devolve sintetico para tipos
     mapeados (das_parcsn_andre -> RECEITA_FEDERAL).
  2. Tipos não-fiscais (nfce_modelo_65, holerite, etc.) devolvem None.
  3. ingerir_documento_fiscal grava fornecedor=RECEITA_FEDERAL no grafo
     quando documento e DAS PARCSN.
  4. Contribuinte original preservado em metadata.contribuinte.
  5. NFCe (não-fiscal) preserva fornecedor real (Americanas).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    _carregar_fornecedores_sinteticos,
    _resetar_cache_sinteticos,
    _resolver_fornecedor_sintetico,
    ingerir_documento_fiscal,
)


def setup_function():
    """Reseta cache antes de cada teste para garantir isolamento."""
    _resetar_cache_sinteticos()


def test_carrega_yaml_fornecedores_sinteticos():
    # AUDIT-CACHE-THREADSAFE: agora retorna tuple-of-tuples (lru_cache friendly).
    sinteticos = dict(_carregar_fornecedores_sinteticos())
    assert "das_parcsn_andre" in sinteticos
    rf = sinteticos["das_parcsn_andre"]
    assert rf["nome_canonico"] == "RECEITA_FEDERAL"
    assert rf["cnpj"] == "00394460000141"
    assert "Receita Federal" in rf["razao_social"]


def test_resolver_sintetico_das_parcsn():
    sintetico = _resolver_fornecedor_sintetico("das_parcsn_andre")
    assert sintetico is not None
    assert sintetico["nome_canonico"] == "RECEITA_FEDERAL"


def test_resolver_sintetico_dirpf():
    sintetico = _resolver_fornecedor_sintetico("dirpf_retif")
    assert sintetico is not None
    assert sintetico["nome_canonico"] == "RECEITA_FEDERAL"


def test_resolver_sintetico_tipo_nao_fiscal_devolve_none():
    assert _resolver_fornecedor_sintetico("nfce_modelo_65") is None
    assert _resolver_fornecedor_sintetico("holerite") is None
    assert _resolver_fornecedor_sintetico("boleto_servico") is None


def test_resolver_sintetico_tipo_vazio_devolve_none():
    assert _resolver_fornecedor_sintetico("") is None
    assert _resolver_fornecedor_sintetico(None) is None  # type: ignore[arg-type]


def test_ingerir_das_parcsn_aponta_para_receita_federal(tmp_path: Path):
    """DAS PARCSN ingerido deve criar aresta documento -> RECEITA_FEDERAL."""
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    documento = {
        "chave_44": "07182516307670455",
        "cnpj_emitente": "45850636000160",  # CNPJ do contribuinte (MEI Andre)  # anonimato-allow
        "data_emissao": "2025-06-30",
        "tipo_documento": "das_parcsn_andre",
        "total": 331.12,
        "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
        "numero": "07182516307670455",
        "vencimento": "2025-06-30",
    }

    ingerir_documento_fiscal(db, documento, itens=[])

    # Confirma node fornecedor RECEITA_FEDERAL
    cur = db._conn.execute(
        "SELECT nome_canonico, metadata FROM node WHERE tipo='fornecedor'"
    )
    fornecedores = list(cur.fetchall())
    nomes = {f[0] for f in fornecedores}
    # nome_canonico de fornecedor é o CNPJ canônico (com leading zeros, 14 dígitos)
    assert "00394460000141" in nomes


def test_ingerir_das_parcsn_preserva_contribuinte_em_metadata(tmp_path: Path):
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    documento = {
        "chave_44": "07182523373762004",
        "cnpj_emitente": "45850636000160",
        "data_emissao": "2025-08-29",
        "tipo_documento": "das_parcsn_andre",
        "total": 338.48,
        "razao_social": "ANDRE DA SILVA BATISTA DE FARIAS",
        "numero": "07182523373762004",
        "vencimento": "2025-08-29",
    }
    ingerir_documento_fiscal(db, documento, itens=[])

    cur = db._conn.execute("SELECT metadata FROM node WHERE tipo='documento'")
    meta = json.loads(cur.fetchone()[0])
    assert meta["contribuinte"] == "ANDRE DA SILVA BATISTA DE FARIAS"
    # Razao social do fornecedor passou para Receita Federal
    assert "Receita Federal" in meta["razao_social"]


def test_audit_contribuinte_sempre_gravado_mesmo_vazio(tmp_path: Path):
    """AUDIT-CONTRIBUINTE-METADATA: doc sintético sem razao_social grava
    metadata.contribuinte='' (sinaliza aplicação do sintético para auditoria).
    """
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    documento = {
        "chave_44": "07182516307670456",
        "cnpj_emitente": "45850636000160",
        "data_emissao": "2025-06-30",
        "tipo_documento": "das_parcsn_andre",
        "total": 100.0,
        "numero": "07182516307670456",
        # razao_social AUSENTE
    }
    ingerir_documento_fiscal(db, documento, itens=[])

    cur = db._conn.execute("SELECT metadata FROM node WHERE tipo='documento'")
    meta = json.loads(cur.fetchone()[0])
    # Sintético aplicado: contribuinte sempre presente (mesmo vazio).
    assert "contribuinte" in meta
    assert meta["contribuinte"] == ""
    assert "Receita Federal" in meta["razao_social"]


def test_ingerir_nfce_preserva_fornecedor_real(tmp_path: Path):
    """NFCe Americanas NÃO casa com nenhum sintético -- preserva fornecedor."""
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    documento = {
        "chave_44": "53260400776574016079653040000432",
        "cnpj_emitente": "00776574016079",
        "data_emissao": "2026-04-19",
        "tipo_documento": "nfce_modelo_65",
        "total": 629.98,
        "razao_social": "AMERICANAS SA - 0337",
        "numero": "43260",
    }
    ingerir_documento_fiscal(db, documento, itens=[])

    cur = db._conn.execute("SELECT metadata FROM node WHERE tipo='documento'")
    meta = json.loads(cur.fetchone()[0])
    # Sem contribuinte (não passou pelo sintético)
    assert "contribuinte" not in meta
    # Razao social preservada
    assert meta["razao_social"] == "AMERICANAS SA - 0337"


# "Quem recebe o pagamento e o fornecedor; quem paga e o cliente."
# -- principio do flow real de fornecimento
