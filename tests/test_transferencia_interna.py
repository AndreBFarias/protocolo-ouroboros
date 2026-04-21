"""Testes regressivos Sprint 68 e 68b -- falso-positivo de Transferência Interna.

Sprint 68 cobriu os 4 vetores iniciais:
    1. Normalizer (`inferir_tipo_transacao`) -- nomes do casal viram TI.
    2. Deduplicator (`marcar_transferencias_internas`) -- par saída/receita
       só vira TI se pelo menos um lado tem identidade do casal.
    3. Nubank CC (`_classificar_tipo`) -- PIX para terceiros não vira TI.
    4. Canonicalizer (`e_transferencia_do_casal`) -- fronteiras explícitas.

Sprint 68b estende para os extratores restantes e a rede de segurança
pós-deduplicação em `src/pipeline.py::_reclassificar_ti_orfas`:
    5. Santander PDF (`_criar_transacao`).
    6. Itaú PDF (`_classificar_tipo`).
    7. C6 CC (`_classificar_tipo`).
    8. Nubank Cartão (`_classificar_tipo`).
    9. Pipeline (`_reclassificar_ti_orfas`) -- reclassifica linhas
       importadas do histórico que estariam órfãs de canonicalizer.
"""

from datetime import date
from pathlib import Path

import pytest

from src.extractors.c6_cc import ExtratorC6CC
from src.extractors.itau_pdf import ExtratorItauPDF
from src.extractors.nubank_cartao import ExtratorNubankCartao
from src.extractors.nubank_cc import ExtratorNubankCC
from src.extractors.santander_pdf import ExtratorSantanderPDF
from src.pipeline import _reclassificar_ti_orfas
from src.transform.canonicalizer_casal import (
    e_transferencia_do_casal,
    resetar_cache,
)
from src.transform.deduplicator import marcar_transferencias_internas
from src.transform.normalizer import inferir_tipo_transacao


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    """Garante que cada teste vê a versão atual do YAML (evita vazamento entre suites)."""
    resetar_cache()
    yield
    resetar_cache()


class TestCanonicalizerCasal:
    """Matcher formal `e_transferencia_do_casal`."""

    def test_nome_completo_andre_bate(self) -> None:
        assert e_transferencia_do_casal(
            "Transferência recebida pelo Pix - ANDRE DA SILVA BATISTA DE FARIAS - 273"
        )

    def test_nome_completo_vitoria_bate(self) -> None:
        assert e_transferencia_do_casal(
            "Vitória Maria Silva dos Santos - CPF - NU PAGAMENTOS"
        )

    def test_pix_externo_deivid_nao_bate(self) -> None:
        assert not e_transferencia_do_casal(
            "Transferência enviada - DEIVID DA SILVA ALVES SANTANA - 418"
        )

    def test_pix_externo_joao_nao_bate(self) -> None:
        assert not e_transferencia_do_casal(
            "Transferência enviada - Joao Alexandre Vaz Ferreira - 995"
        )

    def test_pix_externo_jefferson_nao_bate(self) -> None:
        assert not e_transferencia_do_casal(
            "Transferência enviada - Jefferson Castro Garcia - 995.91"
        )

    def test_andre_barata_nao_bate_com_whitelist_especifica(self) -> None:
        """Nome curto genérico 'ANDRE BARATA' não deve casar quando a whitelist
        contém apenas 'ANDRE DA SILVA BATISTA' (nome composto)."""
        assert not e_transferencia_do_casal(
            "Transferência enviada - ANDRE BARATA DA COSTA - 123"
        )

    def test_descricao_vazia_nao_bate(self) -> None:
        assert not e_transferencia_do_casal("")
        assert not e_transferencia_do_casal(None)  # type: ignore[arg-type]

    def test_placeholder_cpf_no_yaml_nao_gera_match(self) -> None:
        """Garantia: placeholder `<CPF_ANDRE>` no YAML não casa com nada."""
        assert not e_transferencia_do_casal("Pagamento ref <CPF_ANDRE>")

    def test_acentuacao_normalizada(self) -> None:
        """Matcher deve ignorar acentos: 'Vitória' casa com nome do YAML."""
        assert e_transferencia_do_casal("PIX Vitória Maria Silva dos Santos")


class TestInferirTipoNormalizer:
    """`inferir_tipo_transacao` -- saída do canonicalizer integrada."""

    def test_ti_legitima_andre_para_vitoria(self) -> None:
        desc = "Transferência enviada pelo Pix - VITORIA MARIA SILVA DOS SANTOS - 475"
        assert inferir_tipo_transacao(-500.0, desc) == "Transferência Interna"

    def test_ti_legitima_vitoria_para_andre(self) -> None:
        desc = "Transferência recebida pelo Pix - ANDRE DA SILVA BATISTA DE FARIAS - 273"
        assert inferir_tipo_transacao(500.0, desc) == "Transferência Interna"

    def test_pix_externo_deivid_vira_despesa(self) -> None:
        desc = "Transferência enviada - DEIVID DA SILVA ALVES SANTANA - 418"
        assert inferir_tipo_transacao(-20.0, desc) == "Despesa"

    def test_pix_externo_joao_vira_despesa(self) -> None:
        desc = "Transferência enviada - Joao Alexandre Vaz Ferreira - 995"
        assert inferir_tipo_transacao(-50.0, desc) == "Despesa"

    def test_pagamento_fatura_cartao_ainda_e_ti(self) -> None:
        """Exceção operacional: PAGAMENTO DE FATURA continua TI."""
        assert (
            inferir_tipo_transacao(-1500.0, "PAGAMENTO DE FATURA-INTERNET")
            == "Transferência Interna"
        )

    def test_resgate_cdb_ainda_e_ti(self) -> None:
        """Exceção operacional: resgate de investimento continua TI."""
        assert (
            inferir_tipo_transacao(1000.0, "RESGATE CDB C6")
            == "Transferência Interna"
        )


class TestDeduplicatorMarcarTI:
    """`marcar_transferencias_internas` exige identidade do casal em ao menos um lado."""

    def test_par_entre_casal_com_nome_bate(self) -> None:
        transacoes = [
            {
                "data": date(2024, 5, 10),
                "valor": 500.0,
                "tipo": "Despesa",
                "quem": "André",
                "_descricao_original": (
                    "Transferência enviada pelo Pix - VITORIA MARIA SILVA DOS SANTOS"
                ),
                "local": "Vitória Maria",
            },
            {
                "data": date(2024, 5, 10),
                "valor": 500.0,
                "tipo": "Receita",
                "quem": "Vitória",
                "_descricao_original": (
                    "Transferência recebida pelo Pix - ANDRE DA SILVA BATISTA DE FARIAS"
                ),
                "local": "André da Silva",
            },
        ]
        resultado = marcar_transferencias_internas(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"
        assert resultado[1]["tipo"] == "Transferência Interna"

    def test_par_terceiro_sem_casal_nao_vira_ti(self) -> None:
        """Caso crítico: valor e data coincidem, pessoas diferentes, mas
        nenhum lado é do casal. NÃO pode virar TI."""
        transacoes = [
            {
                "data": date(2024, 5, 10),
                "valor": 20.0,
                "tipo": "Despesa",
                "quem": "André",
                "_descricao_original": "Transferência enviada - DEIVID DA SILVA ALVES SANTANA",
                "local": "Deivid",
            },
            {
                "data": date(2024, 5, 10),
                "valor": 20.0,
                "tipo": "Receita",
                "quem": "Vitória",
                "_descricao_original": "Transferência recebida de CLIENTE X LTDA",
                "local": "Cliente X",
            },
        ]
        resultado = marcar_transferencias_internas(transacoes)
        assert resultado[0]["tipo"] == "Despesa", "Saída externa NÃO deveria virar TI"
        assert resultado[1]["tipo"] == "Receita", "Entrada externa NÃO deveria virar TI"

    def test_par_com_apenas_um_lado_casal_vira_ti(self) -> None:
        """Se apenas um lado identifica o casal, ainda é TI legítima
        (o outro lado pode ser descrição genérica do banco)."""
        transacoes = [
            {
                "data": date(2024, 5, 10),
                "valor": 300.0,
                "tipo": "Despesa",
                "quem": "André",
                "_descricao_original": "TED enviada",
                "local": "TED",
            },
            {
                "data": date(2024, 5, 10),
                "valor": 300.0,
                "tipo": "Receita",
                "quem": "Vitória",
                "_descricao_original": "Transferência recebida - ANDRE DA SILVA BATISTA DE FARIAS",
                "local": "André",
            },
        ]
        resultado = marcar_transferencias_internas(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"
        assert resultado[1]["tipo"] == "Transferência Interna"


class TestNubankCCClassificarTipo:
    """`ExtratorNubankCC._classificar_tipo` deve consultar whitelist."""

    @pytest.fixture
    def extrator(self, tmp_path) -> ExtratorNubankCC:
        return ExtratorNubankCC(tmp_path)

    def test_pix_externo_deivid_negativo_vira_despesa(self, extrator) -> None:
        desc = "Transferência enviada - DEIVID DA SILVA ALVES SANTANA - 418"
        assert extrator._classificar_tipo(desc, -20.0, "Vitória") == "Despesa"

    def test_pix_para_andre_casal_vira_ti(self, extrator) -> None:
        desc = "Andre da Silva Batista de Farias - 273.731 - ITAÚ UNIBANCO"
        assert extrator._classificar_tipo(desc, -500.0, "Vitória") == "Transferência Interna"

    def test_agencia_6450_ainda_vira_ti(self, extrator) -> None:
        """Sinalizador operacional (agência do Itaú do André) preservado."""
        desc = "Transferência - Conta XYZ Agência: 6450 Conta: 123"
        assert extrator._classificar_tipo(desc, -500.0, "Vitória") == "Transferência Interna"


class TestSantanderExtratorComCanonicalizer:
    """Sprint 68b: `ExtratorSantanderPDF._criar_transacao` consulta canonicalizer."""

    @pytest.fixture
    def extrator(self, tmp_path: Path) -> ExtratorSantanderPDF:
        return ExtratorSantanderPDF(tmp_path)

    def test_pagamento_de_fatura_preservado_como_ti(self, extrator: ExtratorSantanderPDF) -> None:
        """Regra operacional legítima: pagamento da própria fatura Santander."""
        txn = extrator._criar_transacao(
            "05/01", "PAGAMENTO DE FATURA", "1.500,00", Path("fake.pdf"), date(2024, 1, 15)
        )
        assert txn is not None
        assert txn.tipo == "Transferência Interna"

    def test_descricao_com_casal_vira_ti(self, extrator: ExtratorSantanderPDF) -> None:
        """Canonicalizer captura nome do casal em descrição de fatura."""
        txn = extrator._criar_transacao(
            "05/01",
            "VITORIA MARIA SILVA DOS SANTOS",
            "50,00",
            Path("fake.pdf"),
            date(2024, 1, 15),
        )
        assert txn is not None
        assert txn.tipo == "Transferência Interna"

    def test_compra_comercial_permanece_despesa(self, extrator: ExtratorSantanderPDF) -> None:
        """Estabelecimento comum não é TI."""
        txn = extrator._criar_transacao(
            "05/01", "PADARIA KI-SABOR", "25,50", Path("fake.pdf"), date(2024, 1, 15)
        )
        assert txn is not None
        assert txn.tipo == "Despesa"

    def test_terceiro_homonimo_nao_vira_ti(self, extrator: ExtratorSantanderPDF) -> None:
        """ANDRE BARATA (nome genérico) NÃO casa com whitelist específica do casal."""
        txn = extrator._criar_transacao(
            "05/01", "ANDRE BARATA COMERCIO", "99,00", Path("fake.pdf"), date(2024, 1, 15)
        )
        assert txn is not None
        assert txn.tipo == "Despesa"


class TestItauExtratorComCanonicalizer:
    """Sprint 68b: `ExtratorItauPDF._classificar_tipo` consulta canonicalizer."""

    def test_historico_com_vitoria_bate_canonicalizer(self) -> None:
        desc = "PIX ENVIADO VITORIA MARIA SILVA DOS SANTOS"
        assert ExtratorItauPDF._classificar_tipo(desc, -500.0) == "Transferência Interna"

    def test_historico_com_andre_bate_canonicalizer(self) -> None:
        desc = "PIX RECEBIDO ANDRE DA SILVA BATISTA DE FARIAS"
        assert ExtratorItauPDF._classificar_tipo(desc, 500.0) == "Transferência Interna"

    def test_pagamento_fatura_nubank_preservado(self) -> None:
        """Regra operacional preservada: pagamento da fatura Nubank."""
        assert (
            ExtratorItauPDF._classificar_tipo("NU PAGAMENTOS SA", -1500.0)
            == "Transferência Interna"
        )

    def test_pix_terceiro_deivid_vira_despesa(self) -> None:
        """Regressão: 'VITORIA/ES' ou terceiro homônimo não vira TI."""
        desc = "PIX ENVIADO DEIVID DA SILVA ALVES SANTANA"
        assert ExtratorItauPDF._classificar_tipo(desc, -50.0) == "Despesa"

    def test_cidade_vitoria_es_nao_vira_ti(self) -> None:
        """Regressão crítica da Sprint 68: REGEX_VITORIA cru casava 'VITORIA/ES'."""
        desc = "COMPRA LOJA FILIAL VITORIA/ES"
        assert ExtratorItauPDF._classificar_tipo(desc, -100.0) == "Despesa"


class TestC6ExtratorComCanonicalizer:
    """Sprint 68b: `ExtratorC6CC._classificar_tipo` consulta canonicalizer."""

    def test_pgto_fat_cartao_preservado(self) -> None:
        """Regra operacional: pagamento de fatura do próprio cartão C6."""
        tipo = ExtratorC6CC._classificar_tipo("PGTO FAT CARTAO", "", -1200.0)
        assert tipo == "Transferência Interna"

    def test_cdb_c6_preservado(self) -> None:
        """Regra operacional: resgate/aplicação de CDB."""
        tipo = ExtratorC6CC._classificar_tipo("CDB C6", "APLICACAO", -500.0)
        assert tipo == "Transferência Interna"

    def test_vitoria_maria_bate_canonicalizer(self) -> None:
        tipo = ExtratorC6CC._classificar_tipo(
            "PIX ENVIADO", "VITORIA MARIA SILVA DOS SANTOS", -300.0
        )
        assert tipo == "Transferência Interna"

    def test_andre_silva_batista_bate_canonicalizer(self) -> None:
        tipo = ExtratorC6CC._classificar_tipo(
            "PIX RECEBIDO", "ANDRE DA SILVA BATISTA DE FARIAS", 300.0
        )
        assert tipo == "Transferência Interna"

    def test_pix_terceiro_nao_vira_ti(self) -> None:
        """Regressão: PIX para Jefferson (terceiro) não é TI."""
        tipo = ExtratorC6CC._classificar_tipo(
            "PIX ENVIADO", "JEFFERSON CASTRO GARCIA", -100.0
        )
        assert tipo == "Despesa"


class TestNubankCartaoExtratorComCanonicalizer:
    """Sprint 68b: `ExtratorNubankCartao._classificar_tipo` consulta canonicalizer."""

    @pytest.fixture
    def extrator(self, tmp_path: Path) -> ExtratorNubankCartao:
        return ExtratorNubankCartao(tmp_path)

    def test_compra_comum_vira_despesa(self, extrator: ExtratorNubankCartao) -> None:
        assert extrator._classificar_tipo("Padaria Ki-Sabor", "André") == "Despesa"

    def test_descricao_com_casal_vira_ti(self, extrator: ExtratorNubankCartao) -> None:
        """Descrição que cita nome completo do casal (raro em fatura, mas possível)."""
        assert (
            extrator._classificar_tipo("VITORIA MARIA SILVA DOS SANTOS", "André")
            == "Transferência Interna"
        )

    def test_estorno_permanece_receita(self, extrator: ExtratorNubankCartao) -> None:
        assert extrator._classificar_tipo("Estorno compra", "André") == "Receita"

    def test_terceiro_homonimo_nao_vira_ti(self, extrator: ExtratorNubankCartao) -> None:
        """Regressão: 'ANDRE BARATA' (nome curto genérico) não casa whitelist."""
        assert extrator._classificar_tipo("ANDRE BARATA COMERCIO", "Vitória") == "Despesa"


class TestReclassificarTIOrfas:
    """Sprint 68b: rede de segurança pós-dedup reclassifica TI órfã.

    Contrato: qualquer transação com `tipo=='Transferência Interna'` cuja
    descrição NÃO bate canonicalizer e NÃO bate regra operacional
    (PAGAMENTO DE FATURA, CDB, agência 6450) é degradada para Despesa/Receita.
    """

    def test_ti_falso_positivo_deivid_vira_despesa(self) -> None:
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": -100.0,
                "_descricao_original": "Transferência enviada - DEIVID DA SILVA ALVES SANTANA",
                "local": "DEIVID",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Despesa"

    def test_ti_falso_positivo_joao_vira_despesa(self) -> None:
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": -200.0,
                "_descricao_original": "Joao Alexandre Vaz Ferreira",
                "local": "Joao Alexandre",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Despesa"

    def test_ti_falso_positivo_valor_positivo_vira_receita(self) -> None:
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": 150.0,
                "_descricao_original": "CLIENTE X LTDA pagou serviço",
                "local": "Cliente X",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Receita"

    def test_ti_legitima_casal_preservada(self) -> None:
        """Descrição que casa canonicalizer permanece TI."""
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": -500.0,
                "_descricao_original": "PIX VITORIA MARIA SILVA DOS SANTOS",
                "local": "Vitória Maria",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_pagamento_fatura_preservado_como_ti(self) -> None:
        """Regra operacional legítima preservada mesmo sem casar canonicalizer."""
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": -1500.0,
                "_descricao_original": "PAGAMENTO DE FATURA",
                "local": "PAGAMENTO",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_cdb_preservado_como_ti(self) -> None:
        """Regra operacional: CDB é TI (entre conta e investimento)."""
        transacoes = [
            {
                "tipo": "Transferência Interna",
                "valor": 1000.0,
                "_descricao_original": "RESGATE CDB C6",
                "local": "CDB",
            }
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Transferência Interna"

    def test_despesa_nao_ti_intocada(self) -> None:
        """Transações que não são TI não são afetadas."""
        transacoes = [
            {
                "tipo": "Despesa",
                "valor": -50.0,
                "_descricao_original": "Qualquer coisa",
                "local": "Loja",
            },
            {
                "tipo": "Receita",
                "valor": 3000.0,
                "_descricao_original": "Salário",
                "local": "Empregador",
            },
        ]
        resultado = _reclassificar_ti_orfas(transacoes)
        assert resultado[0]["tipo"] == "Despesa"
        assert resultado[1]["tipo"] == "Receita"

    def test_historico_reclassifica_ti_falso_positivo(self) -> None:
        """Contrato direto do BRIEF: linha do histórico marcada TI com descrição
        de terceiro deve virar Despesa/Receita."""
        transacoes_simulando_historico = [
            {
                "tipo": "Transferência Interna",
                "valor": -42.0,
                "banco_origem": "Histórico",
                "_descricao_original": "Matheus Felipe Prestador",
                "local": "Matheus Felipe",
            },
            {
                "tipo": "Transferência Interna",
                "valor": -77.0,
                "banco_origem": "Histórico",
                "_descricao_original": "Nayane Laise",
                "local": "Nayane Laise",
            },
        ]
        resultado = _reclassificar_ti_orfas(transacoes_simulando_historico)
        assert resultado[0]["tipo"] == "Despesa"
        assert resultado[1]["tipo"] == "Despesa"


# "A regra sem exceção é cega; a exceção sem regra é caos." -- autor anônimo
