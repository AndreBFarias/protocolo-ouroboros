"""Testes dedicados de ExtratorNubankCartao (Sprint F 2026-04-23).

Cobre: parse básico do layout Nubank cartão (date,title,amount), corner cases
(estorno com valor negativo, IOF com valor baixo), robustez com entrada inválida
(arquivo vazio, CSV sem cabeçalho esperado).

Não substitui test_deduplicator nem test_pipeline_*; este é parse-unit.
"""

from datetime import date
from pathlib import Path

import pytest

from src.extractors.nubank_cartao import ExtratorNubankCartao

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "bancos" / "nubank_cartao"
FIXTURE_SAMPLE = FIXTURE_DIR / "sample.csv"


def _copiar_fixture_com_nome(destino_dir: Path, nome: str = "nubank_sintetico.csv") -> Path:
    """Copia fixture com prefixo 'nubank' exigido por pode_processar."""
    alvo = destino_dir / nome
    alvo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return alvo


class TestParseBasico:
    def test_3_transacoes_sao_parseadas(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        assert len(transacoes) == 3

    def test_valores_convertidos_para_float_absoluto(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        for tx in transacoes:
            assert isinstance(tx.valor, float)
            assert tx.valor >= 0.0, "Cartão: extrator usa abs() -- sinal vai para tipo"

    def test_datas_convertidas_para_date(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        for tx in transacoes:
            assert isinstance(tx.data, date)
        assert transacoes[0].data == date(2026, 2, 10)
        assert transacoes[-1].data == date(2026, 2, 14)

    def test_banco_origem_e_forma_pagamento(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        for tx in transacoes:
            assert tx.banco_origem == "Nubank"
            assert tx.forma_pagamento == "Crédito"

    def test_cartao_pj_detecta_subtipo_via_path(self, tmp_path: Path) -> None:
        """Sprint 93c: cartão PJ da Vitória produz banco_origem=Nubank (PJ).

        Regressão para a família C da auditoria 2026-04-23: sem este rótulo,
        transações do cartão MEI ficam invisíveis no XLSX consolidado (as
        agregações por banco não diferenciam PJ do PF do André).
        """
        pasta_pj = tmp_path / "vitoria" / "nubank_pj_cartao"
        pasta_pj.mkdir(parents=True)
        alvo = pasta_pj / "nubank_pj_sintetico.csv"
        alvo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorNubankCartao(alvo).extrair()

        assert len(transacoes) >= 1
        assert all(tx.banco_origem == "Nubank (PJ)" for tx in transacoes)

    def test_cartao_sem_pj_no_path_mantem_rotulo_nubank(self, tmp_path: Path) -> None:
        """Cartão do André (path sem nubank_pj) continua como ``Nubank``."""
        pasta_pf = tmp_path / "andre" / "nubank_cartao"
        pasta_pf.mkdir(parents=True)
        alvo = pasta_pf / "nubank_pf_sintetico.csv"
        alvo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorNubankCartao(alvo).extrair()

        assert len(transacoes) >= 1
        assert all(tx.banco_origem == "Nubank" for tx in transacoes)


class TestCornerCases:
    def test_estorno_vira_receita(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        estorno = [t for t in transacoes if "Estorno" in t.descricao]
        assert len(estorno) == 1
        assert estorno[0].tipo == "Receita"
        assert estorno[0].valor == 120.00

    def test_iof_e_compra_sao_despesa(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_com_nome(tmp_path)
        extrator = ExtratorNubankCartao(arquivo)

        transacoes = extrator.extrair()

        nao_estorno = [t for t in transacoes if "Estorno" not in t.descricao]
        assert len(nao_estorno) == 2
        for tx in nao_estorno:
            assert tx.tipo == "Despesa"

    def test_hash_identificador_deterministico(self, tmp_path: Path) -> None:
        arquivo1 = _copiar_fixture_com_nome(tmp_path, "nubank_rodada_1.csv")
        arquivo2 = _copiar_fixture_com_nome(tmp_path, "nubank_rodada_2.csv")

        txs1 = ExtratorNubankCartao(arquivo1).extrair()
        txs2 = ExtratorNubankCartao(arquivo2).extrair()

        assert [t.identificador for t in txs1] == [t.identificador for t in txs2]


class TestEntradaInvalida:
    def test_arquivo_vazio_retorna_lista_vazia(self, tmp_path: Path) -> None:
        vazio = tmp_path / "nubank_vazio.csv"
        vazio.write_text("date,title,amount\n", encoding="utf-8")

        extrator = ExtratorNubankCartao(vazio)
        transacoes = extrator.extrair()

        assert transacoes == []

    def test_csv_com_cabecalho_errado_e_rejeitado(self, tmp_path: Path) -> None:
        errado = tmp_path / "nubank_errado.csv"
        errado.write_text("foo,bar,baz\n1,2,3\n", encoding="utf-8")

        extrator = ExtratorNubankCartao(errado)

        assert extrator.pode_processar(errado) is False

    def test_linha_com_data_invalida_e_ignorada(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "nubank_ruido.csv"
        arquivo.write_text(
            "date,title,amount\n"
            "2026-02-10,Valida,10.00\n"
            "NAO-E-DATA,Ruido,5.00\n"
            "2026-02-12,Outra valida,20.00\n",
            encoding="utf-8",
        )

        extrator = ExtratorNubankCartao(arquivo)
        transacoes = extrator.extrair()

        assert len(transacoes) == 2
        assert all("Ruido" not in t.descricao for t in transacoes)


@pytest.mark.parametrize(
    "cabecalho,esperado",
    [
        ("date,title,amount", True),
        ("Data,Valor,Identificador,Descrição", False),
        ("foo,bar", False),
    ],
)
def test_pode_processar_detecta_cabecalho(tmp_path: Path, cabecalho: str, esperado: bool) -> None:
    arquivo = tmp_path / "nubank_check.csv"
    arquivo.write_text(f"{cabecalho}\n", encoding="utf-8")
    extrator = ExtratorNubankCartao(arquivo)
    assert extrator.pode_processar(arquivo) is esperado


# "A riqueza verdadeira consiste em distinguir o essencial do supérfluo." -- Sêneca
