"""Testes da Sprint 74 — tipagem semântica e GTC-01 sintético.

Os testes do motor principal já vivem em `tests/test_linking.py` (Sprint 48).
Este arquivo cobre apenas o que a Sprint 74 introduziu:

  1. `classificar_tipo_edge` — mapeia tipo_documento em
     {pago_com, confirma, comprovante, origem} (4 valores canônicos).
  2. Injeção do `tipo_edge_semantico` em `evidencia` ao gerar candidatas
     (usa helper `candidatas_para_documento` com grafo temporário).
  3. GTC-01 sintético: fixture simulando boleto natação + transação Sesc
     C6 + confidence do motor Sprint 48 >= 0.80.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph import linking
from src.graph.db import GrafoDB

# ============================================================================
# classificar_tipo_edge
# ============================================================================


class TestClassificarTipoEdge:
    def test_boleto_e_confirma(self) -> None:
        assert linking.classificar_tipo_edge("boleto") == "confirma"
        assert linking.classificar_tipo_edge("boleto_servico") == "confirma"

    def test_fatura_cartao_e_confirma(self) -> None:
        assert linking.classificar_tipo_edge("fatura_cartao") == "confirma"

    def test_contas_sao_confirma(self) -> None:
        assert linking.classificar_tipo_edge("conta_luz") == "confirma"
        assert linking.classificar_tipo_edge("conta_agua") == "confirma"

    def test_cupons_e_recibos_sao_comprovante(self) -> None:
        assert linking.classificar_tipo_edge("cupom_termico") == "comprovante"
        assert linking.classificar_tipo_edge("cupom_fiscal_foto") == "comprovante"
        assert linking.classificar_tipo_edge("nfce") == "comprovante"
        assert linking.classificar_tipo_edge("danfe_nfe55") == "comprovante"
        assert linking.classificar_tipo_edge("recibo_nao_fiscal") == "comprovante"
        assert linking.classificar_tipo_edge("holerite") == "comprovante"

    def test_contrato_apolice_garantia_sao_origem(self) -> None:
        assert linking.classificar_tipo_edge("contrato") == "origem"
        assert linking.classificar_tipo_edge("apolice") == "origem"
        assert linking.classificar_tipo_edge("cupom_garantia_estendida") == "origem"
        assert linking.classificar_tipo_edge("receita_medica") == "origem"

    def test_extrato_bancario_e_pago_com(self) -> None:
        assert linking.classificar_tipo_edge("extrato_bancario") == "pago_com"

    def test_tipo_desconhecido_cai_em_pago_com(self) -> None:
        assert linking.classificar_tipo_edge("xyz_inexistente") == "pago_com"
        assert linking.classificar_tipo_edge(None) == "pago_com"
        assert linking.classificar_tipo_edge("") == "pago_com"

    def test_valor_retornado_em_conjunto_canonico(self) -> None:
        canonicos = {"pago_com", "confirma", "comprovante", "origem"}
        amostras = [
            "boleto",
            "fatura_cartao",
            "cupom_termico",
            "contrato",
            "extrato_bancario",
            "xyz",
            None,
        ]
        for a in amostras:
            assert linking.classificar_tipo_edge(a) in canonicos


# ============================================================================
# Injeção do tipo_edge_semantico na evidência
# ============================================================================


@pytest.fixture
def grafo_com_boleto_e_transacao(tmp_path: Path):
    """Grafo efêmero com 1 documento boleto + 1 transação casando valor+data.

    Valores calibrados para o GTC-01 (boleto natação Sesc R$ 103,93 em
    2026-03-17 + transação C6 em 2026-03-19).
    """
    caminho = tmp_path / "gtc.sqlite"
    db = GrafoDB(caminho)
    db.criar_schema()

    tx_id = db.upsert_node(
        tipo="transacao",
        nome_canonico="gtc-tx-sesc-c6-19mar",
        metadata={
            "data": "2026-03-19",
            "valor": -103.93,
            "local": "SESC - Serviço SOCIAL DO Comércio ADMINI",
            "banco_origem": "c6",
            "categoria": "Natação",
        },
    )

    doc_id = db.upsert_node(
        tipo="documento",
        nome_canonico="gtc-boleto-sesc-mar",
        metadata={
            "tipo_documento": "boleto_servico",
            "data_emissao": "2026-03-17",
            "total": 103.93,
            "fornecedor": "Sesc",
        },
    )

    return db, tx_id, doc_id


class TestEvidenciaTemTipoEdgeSemantico:
    def test_candidatas_injetam_tipo_edge_semantico(
        self, grafo_com_boleto_e_transacao
    ) -> None:
        db, _tx_id, doc_id = grafo_com_boleto_e_transacao
        doc_node = db.buscar_node_por_id(doc_id)
        assert doc_node is not None
        candidatas = linking.candidatas_para_documento(db, doc_node)
        assert candidatas, "GTC-01: esperava ao menos 1 candidata"
        _tid, evidencia = candidatas[0]
        assert evidencia["tipo_edge_semantico"] == "confirma", (
            "boleto_servico deveria gerar tipo_edge_semantico=confirma"
        )


# ============================================================================
# GTC-01 sintético — confidence >= 0.80 na melhor candidata
# ============================================================================


class TestGTC01NatacaoSesc:
    def test_confidence_alta_mesmo_sem_cnpj(
        self, grafo_com_boleto_e_transacao
    ) -> None:
        """Sem CNPJ que bate, o motor Sprint 48 deve dar pelo menos 0.80:

        score = 1.0 - |2 dias| * 0.10 - 0 * 0.50 = 0.80.

        Se o extrator de boleto preencher CNPJ no futuro e a transação
        tiver aresta contraparte->fornecedor com CNPJ igual, o score
        sobe para 1.0 (0.80 + 0.30 clampado).
        """
        db, _tx_id, doc_id = grafo_com_boleto_e_transacao
        doc_node = db.buscar_node_por_id(doc_id)
        assert doc_node is not None
        candidatas = linking.candidatas_para_documento(db, doc_node)
        assert candidatas
        top_id, top_evid = candidatas[0]
        assert top_id == _tx_id
        assert top_evid["confidence"] >= 0.80, (
            f"GTC-01: confidence={top_evid['confidence']} deveria ser >= 0.80"
        )
