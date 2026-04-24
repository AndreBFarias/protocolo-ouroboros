"""Testes dedicados de ExtratorNubankCC (Sprint F 2026-04-23).

Cobre: parse do layout CSV Data,Valor,Identificador,Descrição, corner cases
(Pix recebido/enviado, boleto, DAS Simples como Imposto), entrada inválida
(cabeçalho errado, linha malformada).

Armadilha CLAUDE.md #3: este layout é incompatível com o layout do cartão
(date,title,amount). Testes próprios para evitar regressão cruzada.
"""

from datetime import date
from pathlib import Path

from src.extractors.nubank_cc import ExtratorNubankCC

FIXTURE_SAMPLE = (
    Path(__file__).parent / "fixtures" / "bancos" / "nubank_cc" / "sample.csv"
)


def _copiar_fixture_como(destino_dir: Path, nome: str = "nubank_cc_sintetico.csv") -> Path:
    """Copia fixture para tmp_path com nome arbitrário (pode_processar não exige 'nubank')."""
    alvo = destino_dir / nome
    alvo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return alvo


class TestParseBasico:
    def test_3_transacoes_sao_parseadas(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert len(transacoes) == 3

    def test_datas_parseadas_formato_br(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert transacoes[0].data == date(2026, 2, 10)
        assert transacoes[1].data == date(2026, 2, 11)
        assert transacoes[2].data == date(2026, 2, 12)

    def test_valor_preserva_sinal(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert transacoes[0].valor == 1500.00
        assert transacoes[1].valor == -350.00
        assert transacoes[2].valor == -89.90

    def test_identificador_do_csv_preservado(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert transacoes[0].identificador == "id-fic-001"
        assert transacoes[1].identificador == "id-fic-002"


class TestCornerCases:
    def test_pix_recebido_classifica_como_receita(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        pix_receb = [t for t in transacoes if "Transferência Recebida" in t.descricao]
        assert len(pix_receb) == 1
        assert pix_receb[0].tipo == "Receita"
        assert pix_receb[0].forma_pagamento == "Pix"

    def test_boleto_vira_despesa_com_forma_boleto(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        boleto = [t for t in transacoes if "boleto" in t.descricao.lower()]
        assert len(boleto) == 1
        assert boleto[0].tipo == "Despesa"
        assert boleto[0].forma_pagamento == "Boleto"

    def test_debito_automatico_vira_despesa_forma_debito(self, tmp_path: Path) -> None:
        arquivo = _copiar_fixture_como(tmp_path)
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        debito = [t for t in transacoes if "Débito" in t.descricao]
        assert len(debito) == 1
        assert debito[0].tipo == "Despesa"
        assert debito[0].forma_pagamento == "Débito"

    def test_das_simples_reconhecido_como_imposto(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "nubank_imposto.csv"
        arquivo.write_text(
            "Data,Valor,Identificador,Descrição\n"
            "15/02/2026,-245.80,id-imp-001,DAS Simples Nacional - Periodo 01/2026\n",
            encoding="utf-8",
        )
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert len(transacoes) == 1
        assert transacoes[0].tipo == "Imposto"

    def test_deteccao_conta_pj_vs_pf_pelo_caminho(self, tmp_path: Path) -> None:
        pasta_pj = tmp_path / "vitoria" / "nubank_pj_cc"
        pasta_pj.mkdir(parents=True)
        arquivo = pasta_pj / "fatura_sintetica.csv"
        arquivo.write_text(FIXTURE_SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

        transacoes = ExtratorNubankCC(arquivo).extrair()

        assert all(t.banco_origem == "Nubank (PJ)" for t in transacoes)


class TestEntradaInvalida:
    def test_arquivo_vazio_retorna_lista_vazia(self, tmp_path: Path) -> None:
        vazio = tmp_path / "nubank_cc_vazio.csv"
        vazio.write_text(
            "Data,Valor,Identificador,Descrição\n", encoding="utf-8"
        )

        extrator = ExtratorNubankCC(vazio)
        transacoes = extrator.extrair()

        assert transacoes == []

    def test_cabecalho_de_cartao_e_rejeitado(self, tmp_path: Path) -> None:
        """Layout do cartão (date,title,amount) não deve casar com CC."""
        arquivo_cartao = tmp_path / "misturado.csv"
        arquivo_cartao.write_text(
            "date,title,amount\n2026-02-10,Compra,50.00\n", encoding="utf-8"
        )

        extrator = ExtratorNubankCC(arquivo_cartao)

        assert extrator.pode_processar(arquivo_cartao) is False

    def test_linha_com_valor_nao_numerico_e_ignorada(self, tmp_path: Path) -> None:
        arquivo = tmp_path / "nubank_ruido.csv"
        arquivo.write_text(
            "Data,Valor,Identificador,Descrição\n"
            "10/02/2026,100.00,id-01,Valida\n"
            "11/02/2026,NAO_NUMERO,id-02,Ruido\n"
            "12/02/2026,50.00,id-03,Outra valida\n",
            encoding="utf-8",
        )
        extrator = ExtratorNubankCC(arquivo)

        transacoes = extrator.extrair()

        assert len(transacoes) == 2
        assert all("Ruido" not in t.descricao for t in transacoes)


def test_pode_processar_reconhece_cabecalho_com_acento(tmp_path: Path) -> None:
    """Cabeçalho oficial usa 'Descrição' com acento -- caracter UTF-8."""
    arquivo = tmp_path / "nubank_cc_check.csv"
    arquivo.write_text(
        "Data,Valor,Identificador,Descrição\n", encoding="utf-8"
    )

    extrator = ExtratorNubankCC(arquivo)

    assert extrator.pode_processar(arquivo) is True


# "A liberdade é a capacidade de agir conforme a razão." -- Spinoza
