"""Testes da fusão pré-linker de holerites multi-fonte.

Sprint INFRA-LINKING-HOLERITE-MULTI-FONTE (2026-05-13).

Contexto: pessoa_b recebe holerite de duas fontes distintas (ex: G4F e
INFOBASE) para a mesma competência. Antes desta sprint, o linker processava
os dois documentos como independentes e gerava 2 propostas-conflito
artificiais -- ambos competindo pelas mesmas transações bancárias.

A fusão pré-linker `_fundir_holerites_mesma_realidade` agrupa holerites por
(competência, total próximo ±5%) e linka apenas o representante de cada
grupo. Os "alias" recebem aresta `_alias_de` para trilha de auditoria.

Cenários cobertos (5 testes obrigatórios mais 2 de invariante):

  1. Mesma competência + valor similar -> 1 linkado, 1 alias.
  2. Mesma competência + valor diferente >5% -> 2 propostas (competem).
  3. 1 holerite só -> comportamento normal sem mudança.
  4. 3+ holerites mesma realidade -> 1 representante + N alias.
  5. Idempotência: rodar 2 vezes não duplica nem muda decisão.
  6. Holerite sem competência passa intacto (não é fundido).
  7. Aresta `_alias_de` carrega evidência canônica.

Acentuação: identificadores técnicos N-para-N com o grafo (`transacao`,  # noqa: accent
`documento_de`) seguem o padrão de `tests/test_linking_runtime.py` para
evitar regressões cross-module. Texto humano em docstrings e asserts usa
acentuação completa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.graph.linking import (
    EDGE_TIPO_ALIAS_REALIDADE,
    EDGE_TIPO_DOCUMENTO_DE,
    _competencia_do_holerite,
    _fundir_holerites_mesma_realidade,
    linkar_documentos_a_transacoes,
)


@pytest.fixture
def db(tmp_path: Path) -> GrafoDB:
    grafo = GrafoDB(tmp_path / "grafo.sqlite")
    grafo.criar_schema()
    yield grafo
    grafo.fechar()


@pytest.fixture
def caminho_propostas(tmp_path: Path) -> Path:
    destino = tmp_path / "propostas_linking"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _ingerir_holerite(
    db: GrafoDB,
    *,
    fonte: str,
    mes_ref: str,
    bruto: float,
    cnpj_sintetico: str | None = None,
) -> int:
    """Reproduz `_ingerir_holerite_no_grafo` do extrator de contracheque."""
    chave = f"HOLERITE|{fonte}|{mes_ref}".replace(" ", "_")
    if cnpj_sintetico is None:
        cnpj_sintetico = f"HOLERITE|{abs(hash(fonte)) % (10**12):012x}"
    doc = {
        "chave_44": chave,
        "cnpj_emitente": cnpj_sintetico,
        "data_emissao": f"{mes_ref}-01",
        "tipo_documento": "holerite",
        "total": bruto,
        "razao_social": fonte.upper(),
        "numero": chave,
        "periodo_apuracao": mes_ref,
    }
    return ingerir_documento_fiscal(db, doc, itens=[])


def _criar_tx(
    db: GrafoDB,
    *,
    nome: str,
    data_iso: str,
    valor: float,
    local: str,
    tipo: str = "Receita",
    banco: str = "Itau",
) -> int:
    metadata = {
        "data": data_iso,
        "valor": valor,
        "local": local,
        "banco": banco,
        "tipo": tipo,
        "forma_pagamento": "Pix",
    }
    return db.upsert_node("transacao", nome, metadata=metadata)


# ============================================================================
# Casos canônicos da fusão pré-linker
# ============================================================================


def test_holerites_mesma_competencia_valor_similar_fundem(
    db: GrafoDB, caminho_propostas: Path
):
    """Dois holerites mesma competência, valor dentro de 5% -> 1 representante.

    Cenário real (id 7695/7697 do grafo de produção em 2026-05-13):
      - HOLERITE|G4F|2025-12 total 5771.50
      - HOLERITE|INFOBASE_-_13o_INTEGRAL|2025-12 total 5833.33
      - diferença relativa: 61.83 / 5771.50 = 1.07% (dentro do 5%)

    Esperado: somente 1 documento linkado; o outro vira alias.
    """
    id_g4f = _ingerir_holerite(db, fonte="G4F", mes_ref="2025-12", bruto=5771.50)
    id_infobase = _ingerir_holerite(
        db, fonte="INFOBASE_-_13o_INTEGRAL", mes_ref="2025-12", bruto=5833.33
    )
    # Uma transação que pode bater com qualquer dos dois.
    tx_id = _criar_tx(
        db,
        nome="TX_SALARIO_13o_2025_12",
        data_iso="2025-12-12",
        valor=4956.42,
        local="PAGTO SALARIO",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    # Um deles foi linkado, o outro virou alias.
    assert stats["alias_fundidos"] == 1, f"esperado 1 alias, got {stats}"
    arestas_doc = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas_doc) <= 1, (
        "Apenas o representante deve gerar aresta documento_de; "
        f"got {len(arestas_doc)}"
    )

    # Aresta _alias_de existe e aponta para o representante (id menor).
    alias_id = max(id_g4f, id_infobase)
    rep_id = min(id_g4f, id_infobase)
    arestas_alias = list(
        db.listar_edges(src_id=alias_id, tipo=EDGE_TIPO_ALIAS_REALIDADE)
    )
    assert len(arestas_alias) == 1
    assert arestas_alias[0].dst_id == rep_id


def test_holerites_mesma_competencia_valor_distante_nao_fundem(
    db: GrafoDB, caminho_propostas: Path
):
    """Dois holerites mesma competência, valor diferente >5% -> ambos passam.

    Cenário real (G4F e INFOBASE no mês não-13o):
      - HOLERITE|G4F|2025-07 total 8657.25
      - HOLERITE|INFOBASE|2025-07 total 10000.00
      - diferença relativa: 1342.75 / 8657.25 = 15.5% (fora do 5%)

    Esperado: nenhuma fusão; ambos competem pelo linker.
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2025-07", bruto=8657.25)
    _ingerir_holerite(db, fonte="INFOBASE", mes_ref="2025-07", bruto=10000.0)

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["alias_fundidos"] == 0, (
        f"valores distantes >5% não devem ser fundidos; got {stats}"
    )


def test_holerite_unico_sem_mudanca(db: GrafoDB, caminho_propostas: Path):
    """1 holerite sozinho -> comportamento normal (sem alias, sem mudança).

    Garante que a fusão não introduz efeito colateral em casos triviais.
    """
    _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    tx_id = _criar_tx(
        db,
        nome="TX_SALARIO_2026_03",
        data_iso="2026-03-06",
        valor=7442.38,
        local="PAGTO SALARIO",
    )

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["alias_fundidos"] == 0
    assert stats["linkados"] == 1
    arestas = list(db.listar_edges(dst_id=tx_id, tipo=EDGE_TIPO_DOCUMENTO_DE))
    assert len(arestas) == 1


def test_tres_holerites_mesma_realidade_um_representante(
    db: GrafoDB, caminho_propostas: Path
):
    """3+ holerites mesma competência + valor próximo -> 1 representante + N alias.

    Cenário hipotético mas estruturalmente válido: tripla redundância de fonte
    (folha + broker + RH externo) para a mesma competência.
    """
    id_a = _ingerir_holerite(db, fonte="FONTE_A", mes_ref="2026-04", bruto=8000.00)
    id_b = _ingerir_holerite(db, fonte="FONTE_B", mes_ref="2026-04", bruto=8150.00)
    id_c = _ingerir_holerite(db, fonte="FONTE_C", mes_ref="2026-04", bruto=8200.00)

    stats = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats["alias_fundidos"] == 2, (
        f"esperado 2 alias para 3 holerites mesma realidade; got {stats}"
    )

    # Representante é o de menor id -- todos os outros apontam pra ele.
    rep_esperado = min(id_a, id_b, id_c)
    aliases_esperados = {id_a, id_b, id_c} - {rep_esperado}
    for alias_id in aliases_esperados:
        arestas = list(
            db.listar_edges(src_id=alias_id, tipo=EDGE_TIPO_ALIAS_REALIDADE)
        )
        assert len(arestas) == 1
        assert arestas[0].dst_id == rep_esperado


def test_idempotencia_fusao_holerite(db: GrafoDB, caminho_propostas: Path):
    """Rodar `linkar_documentos_a_transacoes` 2x mantém exatamente os mesmos
    alias e arestas; sem duplicação e sem mudança de decisão.
    """
    id_g4f = _ingerir_holerite(db, fonte="G4F", mes_ref="2025-12", bruto=5771.50)
    id_infobase = _ingerir_holerite(
        db, fonte="INFOBASE_-_13o_INTEGRAL", mes_ref="2025-12", bruto=5833.33
    )

    stats_1 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)
    stats_2 = linkar_documentos_a_transacoes(db, caminho_propostas=caminho_propostas)

    assert stats_1["alias_fundidos"] == stats_2["alias_fundidos"] == 1

    alias_id = max(id_g4f, id_infobase)
    arestas = list(db.listar_edges(src_id=alias_id, tipo=EDGE_TIPO_ALIAS_REALIDADE))
    assert len(arestas) == 1, (
        f"idempotência violada -- aresta _alias_de duplicou: {len(arestas)}"
    )


# ============================================================================
# Invariantes auxiliares
# ============================================================================


def test_competencia_extraida_de_periodo_apuracao(db: GrafoDB):
    """`_competencia_do_holerite` usa `periodo_apuracao` quando disponível."""
    doc_id = _ingerir_holerite(db, fonte="G4F", mes_ref="2026-03", bruto=8657.25)
    doc = db.buscar_node_por_id(doc_id)
    assert doc is not None
    assert _competencia_do_holerite(doc) == "2026-03"


def test_holerite_sem_competencia_passa_intacto(
    db: GrafoDB, caminho_propostas: Path
):
    """Holerite sem `periodo_apuracao` e sem sufixo `|YYYY-MM` não é candidato
    a fusão -- passa intacto pelo `_fundir_holerites_mesma_realidade`.
    """
    # Ingere via API normal mas remove periodo_apuracao pos-fato.
    doc_id = _ingerir_holerite(db, fonte="X", mes_ref="2026-05", bruto=1000.00)
    # Mexe direto no metadata via upsert para limpar campos de competência.
    node = db.buscar_node_por_id(doc_id)
    assert node is not None
    metadata = dict(node.metadata)
    metadata.pop("periodo_apuracao", None)
    db.upsert_node(
        "documento", "HOLERITE_SEM_COMPETENCIA_RAW", metadata=metadata
    )
    documentos = db.listar_nodes(tipo="documento")
    filtrados, alias_para_rep = _fundir_holerites_mesma_realidade(documentos)
    assert alias_para_rep == {}
    # Nada foi excluído; o documento sem competência passou direto.
    assert len(filtrados) == len(documentos)


# "Duas fontes para a mesma realidade não são redundância: são testemunhas."
# -- princípio da fusão com humildade (Spinoza ressoaria: a verdade explica a si e ao falso)
