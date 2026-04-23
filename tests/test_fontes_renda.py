"""Testes do filtro src/utils/fontes_renda.py.

Origem: auditoria de fidelidade 2026-04-23 detectou 459 linhas na aba renda
vs ~24 reais. Contaminação por reembolsos PIX, cashback, PIX entre pessoas
e transferências bancárias falsamente classificadas como "Receita".

Whitelist em mappings/fontes_renda.yaml cobre: salário CLT, MEI do André
(Paim/Suno/F2/Supa/etc.), bolsa Vitória NEES/UFAL, rendimentos de aplicação.
Blacklist bloqueia reembolsos, estornos, cashback, devoluções, PIX recebido.
"""

from __future__ import annotations

import pytest

from src.utils.fontes_renda import eh_fonte_real_de_renda


class TestFontesReaisDeRenda:
    """Whitelist reconhece fontes reais."""

    @pytest.mark.parametrize(
        "descricao",
        [
            "PAGTO SALARIO",
            "PAGAMENTO DE SALÁRIO",
            "PAIM E ASSOCIADOS Comunicação",
            "SUNOPAIM",
            "SUNO Comunicação INTEGRADA LTD",
            "SUPA Comunicação E PUBLICIDADE LTDA",
            "F2 MARKETING LTDA",
            "SOCIAL Agência DIGITAL LTDA",
            "REND PAGO APLIC AUT MAIS",
            "RENDIMENTO RDB",
            "JCP RECEBIDO",
            "Bolsa NEES UFAL",
        ],
    )
    def test_reconhece_renda_real(self, descricao: str) -> None:
        assert eh_fonte_real_de_renda(descricao) is True


class TestBlacklistBloqueia:
    """Blacklist bloqueia quando whitelist NÃO casa (ordem: whitelist vence)."""

    @pytest.mark.parametrize(
        "descricao",
        [
            "Reembolso recebido pelo Pix - iFood",
            "Estorno - Transferência enviada pelo Pix - ADELSON",
            "Cashback Átomos",
            "Devol recebida pix de PIX Marketplace",
            "Transferência recebida pelo Pix - AMANDA ELISA",
            "Pix recebido de GRUPO COMUM",
            "CRED CANC SUSP MOTO CARTAO",
        ],
    )
    def test_blacklist_bloqueia(self, descricao: str) -> None:
        assert eh_fonte_real_de_renda(descricao) is False


class TestWhitelistTemPrioridadeSobreBlacklist:
    """Quando ambas casam, whitelist prevalece (caso MEI via Pix recebido)."""

    @pytest.mark.parametrize(
        "descricao",
        [
            "Transferência recebida pelo Pix - F2 MARKETING LTDA - 18.420",
            "Transferência recebida pelo Pix - PAIM E ASSOCIADOS Comunicação",
            "Transferência recebida pelo Pix - SUNOPAIM",
            "Pix recebido de GRUPO COMUM CONSULTORIA",
        ],
    )
    def test_whitelist_prevalece(self, descricao: str) -> None:
        assert eh_fonte_real_de_renda(descricao) is True


class TestCasosAmbiguosFicaFora:
    """Por padrão, descrições não-reconhecidas ficam FORA da aba renda."""

    @pytest.mark.parametrize(
        "descricao",
        [
            "NU PAGAMENTOS S/A",  # genérico, não identifica fonte
            "Transação OFX sem descrição",
            "Crédito em conta",
            "Depósito Recebido por Boleto",  # ambíguo (poderia ser MEI ou aluguel)
            "",  # vazio
            "Andre",  # placeholder
        ],
    )
    def test_ambiguo_rejeitado(self, descricao: str) -> None:
        assert eh_fonte_real_de_renda(descricao) is False


class TestAbaRendaFiltradaPelaWhitelist:
    """Integração: simula _criar_aba_renda usando o filtro."""

    def test_contaminacao_pix_filtrada(self) -> None:
        transacoes = [
            {
                "tipo": "Receita",
                "local": "PAGTO SALARIO",
                "valor": 7442.38,
                "mes_ref": "2026-02",
                "banco_origem": "Itaú",
            },
            {
                "tipo": "Receita",
                "local": "Reembolso recebido pelo Pix - iFood",
                "valor": 35.00,
                "mes_ref": "2026-02",
                "banco_origem": "Nubank (PF)",
            },
            {
                "tipo": "Receita",
                "local": "Cashback Átomos",
                "valor": 5.50,
                "mes_ref": "2026-02",
                "banco_origem": "Nubank",
            },
            {
                "tipo": "Receita",
                "local": "SUNOPAIM",
                "valor": 2500.00,
                "mes_ref": "2026-02",
                "banco_origem": "C6",
            },
        ]

        receitas_reais = [t for t in transacoes if eh_fonte_real_de_renda(t["local"])]
        assert len(receitas_reais) == 2
        locais = {t["local"] for t in receitas_reais}
        assert locais == {"PAGTO SALARIO", "SUNOPAIM"}
