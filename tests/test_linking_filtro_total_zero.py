"""Sprint INFRA-LINKING-DIRPF-TOTAL-ZERO (2026-05-13).

Garante que documentos com `total` ausente, nulo ou abaixo de R$ 0,01
NÃO entram na heurística de linking por valor.

Origem: auditoria pós `./run.sh --tudo` em 2026-05-13 -- 3 propostas
conflito (007462, 007583, 007768) para `DIRPF|05127373122|2025_RETIF`
com `total=0.0` casando transações aleatórias de R$ 0,01 (diff_valor
proporcional zera por divisão indefinida).

Cobertura:
  1. helper `_total_vazio_ou_minimo` em isolamento (valores limite).
  2. `candidatas_para_documento` retorna [] quando total é 0.0/0.005/None.
  3. `candidatas_para_documento` retorna candidatas reais quando total > 0.01.
  4. `linkar_documentos_a_transacoes` contabiliza `total_vazio` e NÃO cria
     proposta nem aresta para o documento sem valor declarado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.graph import linking
from src.graph.db import GrafoDB

# ============================================================================
# Helper unitário: _total_vazio_ou_minimo
# ============================================================================


class TestTotalVazioOuMinimo:
    """Valores limite do helper que classifica `total` como elegível ou não."""

    def test_none_e_vazio(self) -> None:
        assert linking._total_vazio_ou_minimo(None) is True

    def test_zero_exato_e_vazio(self) -> None:
        assert linking._total_vazio_ou_minimo(0.0) is True

    def test_meio_centavo_e_vazio(self) -> None:
        assert linking._total_vazio_ou_minimo(0.005) is True

    def test_um_centavo_e_vazio_por_inclusao(self) -> None:
        # O limite é "<=" 0.01: a borda inferior conta como sem valor real.
        assert linking._total_vazio_ou_minimo(0.01) is True

    def test_dois_centavos_e_elegivel(self) -> None:
        assert linking._total_vazio_ou_minimo(0.02) is False

    def test_valor_negativo_pequeno_e_vazio(self) -> None:
        # Comparação em módulo (alguns extratores assinam total).
        assert linking._total_vazio_ou_minimo(-0.005) is True

    def test_valor_negativo_grande_e_elegivel(self) -> None:
        assert linking._total_vazio_ou_minimo(-100.0) is False

    def test_string_nao_numerica_e_vazio(self) -> None:
        assert linking._total_vazio_ou_minimo("invalido") is True

    def test_valor_grande_e_elegivel(self) -> None:
        assert linking._total_vazio_ou_minimo(1234.56) is False


# ============================================================================
# Fixture: grafo com 1 transação compatível por data (mas valores quaisquer)
# ============================================================================


@pytest.fixture
def grafo_com_transacao_pequena(tmp_path: Path):
    """Grafo com 1 transação de R$ 0,01 — alvo natural de matching falso
    quando o documento tem total=0.0 e a heurística proporcional indefine.
    """
    db = GrafoDB(tmp_path / "filtro_total_zero.sqlite")
    db.criar_schema()

    tx_id = db.upsert_node(
        tipo="transacao",
        nome_canonico="tx-pequena-ruido",
        metadata={
            "data": "2026-04-30",
            "valor": -0.01,
            "local": "movimento ruido",  # noqa: accent
            "banco_origem": "c6",
        },
    )
    return db, tx_id


def _adicionar_documento(db: GrafoDB, *, nome: str, total: object) -> int:
    """Cria documento dirpf_retif com total parametrizável."""
    return db.upsert_node(
        tipo="documento",
        nome_canonico=nome,
        metadata={
            "tipo_documento": "dirpf_retif",
            "data_emissao": "2026-04-30",
            "total": total,
            "fornecedor": "Receita Federal",
        },
    )


# ============================================================================
# candidatas_para_documento -- filtragem cedo
# ============================================================================


class TestCandidatasFiltroTotalVazio:
    def test_total_zero_nao_gera_candidatas(self, grafo_com_transacao_pequena) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        doc_id = _adicionar_documento(db, nome="dirpf-total-zero", total=0.0)
        doc = db.buscar_node_por_id(doc_id)
        assert doc is not None

        candidatas = linking.candidatas_para_documento(db, doc)
        assert candidatas == [], (
            "documento com total=0.0 NÃO deve gerar candidatas "
            "(heurística proporcional indefinida)"
        )

    def test_total_meio_centavo_nao_gera_candidatas(
        self, grafo_com_transacao_pequena
    ) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        doc_id = _adicionar_documento(db, nome="dirpf-meio-centavo", total=0.005)
        doc = db.buscar_node_por_id(doc_id)
        assert doc is not None

        candidatas = linking.candidatas_para_documento(db, doc)
        assert candidatas == []

    def test_total_none_nao_gera_candidatas(self, grafo_com_transacao_pequena) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        doc_id = _adicionar_documento(db, nome="dirpf-total-null", total=None)
        doc = db.buscar_node_por_id(doc_id)
        assert doc is not None

        candidatas = linking.candidatas_para_documento(db, doc)
        assert candidatas == []

    def test_total_dois_centavos_entra_no_funil(
        self, grafo_com_transacao_pequena
    ) -> None:
        """Acima do limiar o documento entra normalmente no funil; pode ou
        não casar (depende da janela), mas o filtro de total não barra."""
        db, _tx_id = grafo_com_transacao_pequena
        # Transação extra para garantir match acima do limiar.
        db.upsert_node(
            tipo="transacao",
            nome_canonico="tx-dois-centavos",
            metadata={
                "data": "2026-04-30",
                "valor": -0.02,
                "local": "movimento alvo dois centavos",  # noqa: accent
                "banco_origem": "c6",
            },
        )
        doc_id = _adicionar_documento(db, nome="dirpf-dois-centavos", total=0.02)
        doc = db.buscar_node_por_id(doc_id)
        assert doc is not None

        candidatas = linking.candidatas_para_documento(db, doc)
        assert candidatas, (
            "documento com total=0.02 (acima do mínimo elegível) DEVE entrar "
            "no funil heurístico"
        )


# ============================================================================
# linkar_documentos_a_transacoes -- contador total_vazio + zero propostas
# ============================================================================


class TestLinkagemFiltraTotalVazio:
    def test_documento_total_zero_conta_em_total_vazio(
        self, grafo_com_transacao_pequena, tmp_path: Path
    ) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        _adicionar_documento(db, nome="dirpf-total-zero-stats", total=0.0)

        propostas = tmp_path / "propostas"
        stats = linking.linkar_documentos_a_transacoes(
            db, caminho_propostas=propostas
        )

        assert stats["total_vazio"] == 1
        assert stats["conflitos"] == 0
        assert stats["linkados"] == 0
        # Nenhum arquivo de proposta deve ser escrito.
        assert not propostas.exists() or not list(propostas.glob("*.md"))

    def test_documento_total_none_conta_em_total_vazio(
        self, grafo_com_transacao_pequena, tmp_path: Path
    ) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        _adicionar_documento(db, nome="dirpf-null-stats", total=None)

        propostas = tmp_path / "propostas"
        stats = linking.linkar_documentos_a_transacoes(
            db, caminho_propostas=propostas
        )

        assert stats["total_vazio"] == 1
        assert stats["conflitos"] == 0

    def test_documento_total_valido_nao_conta_em_total_vazio(
        self, grafo_com_transacao_pequena, tmp_path: Path
    ) -> None:
        db, _tx_id = grafo_com_transacao_pequena
        db.upsert_node(
            tipo="transacao",
            nome_canonico="tx-pareada-real",
            metadata={
                "data": "2026-04-30",
                "valor": -123.45,
                "local": "movimento real",  # noqa: accent
                "banco_origem": "c6",
            },
        )
        _adicionar_documento(db, nome="dirpf-com-valor", total=123.45)

        propostas = tmp_path / "propostas"
        stats = linking.linkar_documentos_a_transacoes(
            db, caminho_propostas=propostas
        )

        assert stats["total_vazio"] == 0


# "Vazio não casa com cheio; presumir o contrário é magia, não método." -- princípio do arquivista
