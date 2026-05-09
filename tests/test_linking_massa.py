"""Testes do wrapper `scripts/linking_nfe_transacao_massa.py` -- Sprint
INFRA-LINKING-NFE-TRANSACAO.

Cobre:

  1. Caso ouro -- top-1 sozinho acima do `confidence_minimo` -> edge
     `documento_de` criada com `peso = top_score`.
  2. Caso ambíguo -- top-1 e top-2 dentro da `margem_empate` ->
     edge criada com `peso = 0.5` e `revisar_humano = true` na evidência.
  3. Filtro de tipos -- DAS PARCSN é ignorado por default (não está
     na lista NF-like). Apenas `--tipos all` ou explicitação processa.
  4. Idempotência -- segunda execução não duplica nem altera edges.
  5. Modo `--dry-run` (via `processar(..., dry_run=True)`) NÃO grava
     edges no grafo.
  6. Documento sem candidata -> nenhuma edge criada (não inventa
     vínculo).

Acentuação: identificadores técnicos N-para-N com o grafo (`transacao`,  # noqa: accent
`documento_de`) seguem sem acento por consistência com `src/graph/linking.py`.
Texto humano em docstrings e asserts usa acentuação completa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.linking_nfe_transacao_massa import (
    PESO_AMBIGUO,
    TIPOS_NF_LIKE_PADRAO,
    contar_edges_documento_de,
    processar,
)
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.graph.linking import EDGE_TIPO_DOCUMENTO_DE


@pytest.fixture
def db(tmp_path: Path):
    grafo = GrafoDB(tmp_path / "grafo.sqlite")
    grafo.criar_schema()
    yield grafo
    grafo.fechar()


def _ingerir_nfce(
    db: GrafoDB,
    *,
    chave_44: str,
    cnpj: str,
    data_emissao: str,
    total: float,
    razao: str = "AMERICANAS S A",
) -> int:
    doc = {
        "chave_44": chave_44,
        "cnpj_emitente": cnpj,
        "data_emissao": data_emissao,
        "tipo_documento": "nfce_modelo_65",
        "total": total,
        "razao_social": razao,
        "numero": chave_44,
    }
    return ingerir_documento_fiscal(db, doc, itens=[])


def _ingerir_das(
    db: GrafoDB,
    *,
    chave_44: str,
    cnpj: str,
    data_emissao: str,
    total: float,
    vencimento: str,
) -> int:
    doc = {
        "chave_44": chave_44,
        "cnpj_emitente": cnpj,
        "data_emissao": data_emissao,
        "tipo_documento": "das_parcsn_andre",
        "total": total,
        "razao_social": "ANDRE DA SILVA",
        "numero": chave_44,
        "vencimento": vencimento,
        "parcela_atual": 1,
        "parcela_total": 12,
        "periodo_apuracao": data_emissao[:7],
    }
    return ingerir_documento_fiscal(db, doc, itens=[])


def _criar_tx(
    db: GrafoDB,
    *,
    nome: str,
    data_iso: str,
    valor: float,
    local: str = "AMERICANAS",
) -> int:
    return db.upsert_node(
        "transacao",
        nome,
        metadata={
            "data": data_iso,
            "valor": valor,
            "local": local,
            "banco": "Itau",
            "tipo": "Despesa",
            "forma_pagamento": "Cartao",
        },
    )


def test_caso_ouro_linka_unico_com_peso_top_score(db: GrafoDB):
    """NFCe Americanas R$ 595,52 com transação no mesmo dia + valor exato
    deve gerar 1 edge `documento_de` única, sem flag de revisão."""
    _ingerir_nfce(
        db,
        chave_44="53260400776574016079653040000432591876543210",
        cnpj="00.776.574/0160-79",
        data_emissao="2026-04-19",
        total=595.52,
    )
    tx_id = _criar_tx(
        db,
        nome="TX_AMERICANAS_595",
        data_iso="2026-04-19",
        valor=595.52,
        local="AMERICANAS",
    )

    stats = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)

    assert stats["linkados_unico"] == 1, stats
    assert stats["linkados_ambiguo"] == 0
    arestas = db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE)
    assert len(arestas) == 1
    aresta = arestas[0]
    assert aresta.peso > 0.7, f"esperado score alto, got {aresta.peso}"
    assert "revisar_humano" not in aresta.evidencia
    assert aresta.evidencia.get("tipo_documento") == "nfce_modelo_65"


def test_caso_ambiguo_linka_com_peso_0_5_e_flag_revisar(db: GrafoDB):
    """Duas transações de R$ 595,52 no mesmo dia geram empate top-1/top-2.
    Edge deve ser criada com peso=0.5 e `revisar_humano=true`."""
    _ingerir_nfce(
        db,
        chave_44="53260400776574016079653040000432591876543210",
        cnpj="00.776.574/0160-79",
        data_emissao="2026-04-19",
        total=595.52,
    )
    tx_a = _criar_tx(
        db,
        nome="TX_AMERICANAS_A",
        data_iso="2026-04-19",
        valor=595.52,
        local="AMERICANAS LOJA 01",
    )
    tx_b = _criar_tx(
        db,
        nome="TX_AMERICANAS_B",
        data_iso="2026-04-19",
        valor=595.52,
        local="AMERICANAS LOJA 02",
    )

    stats = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)

    assert stats["linkados_ambiguo"] == 1, stats
    assert stats["linkados_unico"] == 0
    arestas_a = db.listar_edges(dst_id=tx_a, tipo=EDGE_TIPO_DOCUMENTO_DE)
    arestas_b = db.listar_edges(dst_id=tx_b, tipo=EDGE_TIPO_DOCUMENTO_DE)
    arestas = arestas_a + arestas_b
    assert len(arestas) == 1, "esperava 1 edge ambígua entre as duas tx"
    aresta = arestas[0]
    assert aresta.peso == PESO_AMBIGUO
    assert aresta.evidencia.get("revisar_humano") is True
    assert aresta.evidencia.get("motivo_revisao") == "empate_top1_top2"
    assert "top1_score" in aresta.evidencia
    assert "top2_score" in aresta.evidencia


def test_filtro_tipos_padrao_ignora_das_parcsn(db: GrafoDB):
    """Filtro NF-like padrão NÃO processa DAS PARCSN (motor existente
    cuida via proposta MD)."""
    _ingerir_das(
        db,
        chave_44="07182510572313828",
        cnpj="45.850.636/0001-60",
        data_emissao="2025-02-28",
        total=324.31,
        vencimento="2025-04-30",
    )
    _criar_tx(
        db,
        nome="TX_RECEITA_FEDERAL",
        data_iso="2025-04-16",
        valor=324.31,
        local="RECEITA FEDERAL",
    )

    stats = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)

    assert stats["linkados_unico"] == 0
    assert stats["linkados_ambiguo"] == 0
    assert stats["ignorado_tipo"] == 1


def test_filtro_tipos_all_processa_qualquer_tipo(db: GrafoDB):
    """Com `tipos_documento=None` (equivalente a --tipos all) o DAS é
    processado e gera edge."""
    _ingerir_das(
        db,
        chave_44="07182510572313828",
        cnpj="45.850.636/0001-60",
        data_emissao="2025-02-28",
        total=324.31,
        vencimento="2025-04-30",
    )
    _criar_tx(
        db,
        nome="TX_RECEITA_FEDERAL",
        data_iso="2025-04-16",
        valor=324.31,
        local="RECEITA FEDERAL",
    )

    stats = processar(db, tipos_documento=None, dry_run=False)

    assert stats["ignorado_tipo"] == 0
    # DAS pode linkar ou virar baixa_confianca dependendo da config; o
    # ponto deste teste é apenas garantir que NÃO foi ignorado por filtro.
    assert stats["total_documentos"] == 1


def test_idempotencia_segunda_execucao_zero_novos(db: GrafoDB):
    """Rerodar o matcher não duplica edges nem altera o estado."""
    _ingerir_nfce(
        db,
        chave_44="53260400776574016079653040000432591876543210",
        cnpj="00.776.574/0160-79",
        data_emissao="2026-04-19",
        total=595.52,
    )
    _criar_tx(
        db,
        nome="TX_AMERICANAS_595",
        data_iso="2026-04-19",
        valor=595.52,
    )

    primeira = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)
    edges_apos_primeira = contar_edges_documento_de(db)

    segunda = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)
    edges_apos_segunda = contar_edges_documento_de(db)

    assert primeira["linkados_unico"] == 1
    assert segunda["linkados_unico"] == 0
    assert segunda["ja_linkado_motor"] == 1
    assert edges_apos_primeira == edges_apos_segunda


def test_dry_run_nao_grava_edges(db: GrafoDB):
    """`dry_run=True` calcula candidatas e contadores sem persistir."""
    _ingerir_nfce(
        db,
        chave_44="53260400776574016079653040000432591876543210",
        cnpj="00.776.574/0160-79",
        data_emissao="2026-04-19",
        total=595.52,
    )
    _criar_tx(
        db,
        nome="TX_AMERICANAS_595",
        data_iso="2026-04-19",
        valor=595.52,
    )

    edges_antes = contar_edges_documento_de(db)
    stats = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=True)
    edges_depois = contar_edges_documento_de(db)

    assert stats["linkados_unico"] == 1, "contador deve refletir o que linkaria"
    assert edges_antes == edges_depois, "dry-run não pode gravar"


def test_documento_sem_candidata_nao_inventa_vinculo(db: GrafoDB):
    """NFCe sem nenhuma transação compatível em data/valor não vira edge."""
    _ingerir_nfce(
        db,
        chave_44="53260400776574016079653040000432591876543210",
        cnpj="00.776.574/0160-79",
        data_emissao="2026-04-19",
        total=595.52,
    )
    # Cria transação distante em data e valor -- não compatível.
    _criar_tx(
        db,
        nome="TX_DISTANTE",
        data_iso="2024-01-01",
        valor=1234.56,
    )

    stats = processar(db, tipos_documento=TIPOS_NF_LIKE_PADRAO, dry_run=False)

    assert stats["sem_candidato"] == 1, stats
    assert stats["linkados_unico"] == 0
    assert stats["linkados_ambiguo"] == 0
    assert contar_edges_documento_de(db) == 0


# "Match sem dado é heurística; match com dado é ouro."
# -- princípio INFRA-LINKING-NFE-TRANSACAO  # noqa: accent
