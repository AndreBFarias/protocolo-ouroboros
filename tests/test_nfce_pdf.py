"""Testes do extrator NFC-e modelo 65 (Sprint 44b).

Fixtures `.txt` em `tests/fixtures/nfces/` reproduzem o texto extraído via
pdfplumber de NFC-e reais da Americanas Gama/DF, com CPF anonimizado e
chave 44 sintética válida (DV SEFAZ). O extrator aceita `texto_override`
para viabilizar testes sem dependência de binários PDF.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractors.nfce_pdf import (
    ExtratorNfcePDF,
    _parse_cabecalho_nfce,
    _parse_itens_nfce,
    e_nfce,
    normalizar_forma_pagamento,
)
from src.graph.db import GrafoDB
from src.utils.chave_nfe import (
    extrair_cnpj_emitente,
    extrair_modelo,
    extrair_uf_ibge,
    valida_digito_verificador,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nfces"


def _carregar(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorNfcePDF:
    placeholder = tmp_path / "placeholder.pdf"
    placeholder.write_bytes(b"%PDF-1.4\n")
    return ExtratorNfcePDF(placeholder)


@pytest.fixture()
def grafo_temp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


# ============================================================================
# Validador de chave 44 dígitos
# ============================================================================


class TestChave44:
    def test_chave_sintetica_valida(self):
        # Chave usada nas fixtures (NFC-e compra Americanas)
        chave = "53260400776574016079653040000432601123456788"
        assert valida_digito_verificador(chave) is True
        assert extrair_modelo(chave) == "65"
        assert extrair_cnpj_emitente(chave) == "00.776.574/0160-79"
        assert extrair_uf_ibge(chave) == "53"

    def test_chave_corrompida_falha_dv(self):
        # Trocar 1 dígito invalida o DV
        chave_ruim = "53260400776574016079653040000432601123456789"
        assert valida_digito_verificador(chave_ruim) is False

    def test_chave_com_formatacao_aceita(self):
        # Espaços a cada 4 dígitos (como impressa nos cupons)
        formatada = "5326 0400 7765 7401 6079 6530 4000 0432 6011 2345 6788"
        assert valida_digito_verificador(formatada) is True

    def test_chave_curta_rejeitada(self):
        assert valida_digito_verificador("12345") is False

    def test_modelo_55_distinto_de_65(self):
        # Mesma base mas dígitos 21-22 == "55" -> NFe modelo 55, não NFC-e
        base_55 = "53260400776574016079" + "55" + "001000000001" + "012345671"
        # ajustar DV se necessário; aqui só precisamos verificar o modelo
        assert extrair_modelo(base_55 + "0") == "55"


# ============================================================================
# Detector
# ============================================================================


class TestDetector:
    def test_e_nfce_aceita_americanas_compra(self):
        assert e_nfce(_carregar("nfce_americanas_compra.txt")) is True

    def test_e_nfce_aceita_supermercado(self):
        assert e_nfce(_carregar("nfce_americanas_supermercado.txt")) is True

    def test_e_nfce_rejeita_danfe_modelo55(self):
        """DANFE tem cabeçalho 'DANFE' + 'DESTINATÁRIO' e modelo 55 na chave."""
        texto_danfe = (
            "DANFE\n"
            "DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA\n"
            "DESTINATÁRIO/REMETENTE\n"
            "CNPJ: 11.222.333/0001-44\n"
            "Chave de acesso: 5326 0400 1122 2333 0001 4455 0030 0000 0001 0000 001X\n"
        )
        assert e_nfce(texto_danfe) is False

    def test_e_nfce_exige_pelo_menos_2_marcadores(self):
        texto_minimo = "Lista de compras do supermercado.\nBananas R$ 5,00"
        assert e_nfce(texto_minimo) is False

    def test_e_nfce_rejeita_chave_modelo_55_mesmo_com_cabecalho_nfce(self):
        """Cabeçalho sugere NFC-e mas chave tem modelo 55 -> rejeita (layout misto suspeito)."""
        texto = (
            "Documento Auxiliar da Nota Fiscal de Consumidor Eletrônica\n"
            "NFCe nº 1 Serie 1\n"
            "fazenda.df.gov.br/nfce\n"
            # chave sintética válida com modelo 55 na posição 21-22
            "5326 0400 7765 7401 6079 5500 1000 0000 0111 1111 1114\n"
        )
        assert e_nfce(texto) is False


# ============================================================================
# Parser de cabeçalho
# ============================================================================


class TestParserCabecalho:
    def test_parse_cabecalho_compra_completo(self):
        doc = _parse_cabecalho_nfce(_carregar("nfce_americanas_compra.txt"))
        assert doc is not None
        assert doc["chave_44"] == "53260400776574016079653040000432601123456788"
        assert doc["tipo_documento"] == "nfce_modelo_65"
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"
        assert "americanas" in (doc["razao_social"] or "").lower()
        assert doc["numero"] == "43260"
        assert doc["serie"] == "304"
        assert doc["data_emissao"] == "2026-04-19"
        assert doc["total"] == pytest.approx(629.98)
        assert doc["forma_pagamento"] == "PIX"
        assert doc["cpf_consumidor"] == "000.000.000-00"

    def test_parse_cabecalho_supermercado_sem_cpf(self):
        doc = _parse_cabecalho_nfce(_carregar("nfce_americanas_supermercado.txt"))
        assert doc is not None
        assert doc["numero"] == "43259"
        assert doc["total"] == pytest.approx(595.52)
        assert doc["cpf_consumidor"] is None  # "NÃO IDENTIFICADO" -> None

    def test_parse_cabecalho_endereco_colapsado(self):
        doc = _parse_cabecalho_nfce(_carregar("nfce_americanas_compra.txt"))
        assert doc is not None
        assert doc["endereco"] is not None
        assert "GAMA" in doc["endereco"].upper()
        assert "BRASILIA" in doc["endereco"].upper()


# ============================================================================
# Parser de itens + recall
# ============================================================================


class TestParserItens:
    def test_parse_2_itens_compra(self):
        itens = _parse_itens_nfce(_carregar("nfce_americanas_compra.txt"))
        assert len(itens) == 2
        codigos = {it["codigo"] for it in itens}
        assert "000004300823" in codigos  # Controle P55
        assert "000004298119" in codigos  # Base de carregamento
        # Sanity de um item
        controle = next(it for it in itens if it["codigo"] == "000004300823")
        assert "CONTROLE P55" in controle["descricao"].upper()
        assert controle["qtde"] == pytest.approx(1.0)
        assert controle["unidade"] == "PCE"
        assert controle["valor_unit"] == pytest.approx(449.99)
        assert controle["valor_total"] == pytest.approx(449.99)

    def test_parse_itens_recall_supermercado(self):
        """Recall >= 90% (spec aceita perda por OCR; aqui fixture limpa deve dar 100%)."""
        itens = _parse_itens_nfce(_carregar("nfce_americanas_supermercado.txt"))
        total_esperado_no_cupom = 31  # da linha "QTD. TOTAL DE ITENS 31"
        recall = len(itens) / total_esperado_no_cupom
        assert recall >= 0.90, f"recall {recall:.0%} abaixo de 90%"
        assert len(itens) == 31

    def test_itens_tem_campos_obrigatorios(self):
        itens = _parse_itens_nfce(_carregar("nfce_americanas_supermercado.txt"))
        for it in itens:
            assert it["codigo"]
            assert it["descricao"]
            assert it["qtde"] is not None and it["qtde"] > 0
            assert it["valor_unit"] is not None and it["valor_unit"] > 0
            assert it["valor_total"] is not None and it["valor_total"] > 0

    def test_layout_sem_destinatario_nao_causa_erro(self):
        """NFC-e sem 'DESTINATÁRIO' (que é NFe55) deve parsear normalmente."""
        doc = _parse_cabecalho_nfce(_carregar("nfce_americanas_supermercado.txt"))
        assert doc is not None  # não crasha


# ============================================================================
# Normalização de forma de pagamento
# ============================================================================


class TestFormaPagamento:
    @pytest.mark.parametrize(
        "entrada, esperado",
        [
            ("Pagamento Instantâneo (PIX) - Dinâmica 629,98", "PIX"),
            ("PIX", "PIX"),
            ("QR Pix 100,00", "PIX"),
            ("Cartão de Crédito - Visa", "Crédito"),
            ("Cartão Crédito", "Crédito"),
            ("Cartão de Débito - Mastercard", "Débito"),
            ("Cartão Débito", "Débito"),
            ("Dinheiro", "Dinheiro"),
            ("Espécie", "Dinheiro"),
            ("Vale Refeição", "Vale"),
            ("Vale Alimentação Ticket", "Vale"),
            ("Transferência bancária", None),
            ("", None),
            (None, None),
        ],
    )
    def test_normalizacao(self, entrada: str, esperado: str | None):
        assert normalizar_forma_pagamento(entrada) == esperado

    def test_forma_pagamento_extraida_e_normalizada_do_texto(self):
        doc = _parse_cabecalho_nfce(_carregar("nfce_americanas_compra.txt"))
        assert doc is not None
        # A string bruta é "Pagamento Instantâneo (PIX) - Dinâmica 629,98"
        # mas o parser normaliza para "PIX"
        assert doc["forma_pagamento"] == "PIX"


# ============================================================================
# Glyph tolerance
# ============================================================================


class TestGlyphTolerance:
    def test_glyph_tolerante_cnpj_com_parentese(self):
        """Layout com CNP) em vez de CNPJ (glyph ToUnicode, Armadilha #20)."""
        texto = _carregar("nfce_americanas_compra.txt").replace("CNPJ:", "CNP):")
        doc = _parse_cabecalho_nfce(texto)
        assert doc is not None
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"

    def test_glyph_tolerante_separador_virgula_em_cnpj(self):
        """OCR troca `.` por `,` em `00,776.574`. Deve casar mesmo assim."""
        texto = _carregar("nfce_americanas_compra.txt").replace(
            "00.776.574/0160-79", "00,776.574/0160-79"
        )
        doc = _parse_cabecalho_nfce(texto)
        assert doc is not None
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"


# ============================================================================
# Integração com grafo
# ============================================================================


class TestGrafoNfce:
    def test_grafo_recebe_documento_fornecedor_itens(
        self,
        extrator: ExtratorNfcePDF,
        grafo_temp: GrafoDB,
    ):
        nfces = extrator.extrair_nfces(
            extrator.caminho,
            texto_override=_carregar("nfce_americanas_compra.txt"),
        )
        assert len(nfces) == 1
        doc, itens = nfces[0]

        from src.graph.ingestor_documento import ingerir_documento_fiscal

        doc_id = ingerir_documento_fiscal(
            grafo_temp, doc, itens, caminho_arquivo=extrator.caminho
        )
        assert doc_id > 0

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento") == 1
        assert stats["nodes_por_tipo"].get("fornecedor") == 1
        assert stats["nodes_por_tipo"].get("item") == 2
        assert stats["nodes_por_tipo"].get("periodo") == 1

        assert stats["edges_por_tipo"].get("fornecido_por") == 1
        assert stats["edges_por_tipo"].get("ocorre_em") == 1
        assert stats["edges_por_tipo"].get("contem_item") == 2

    def test_ingestao_idempotente(
        self, extrator: ExtratorNfcePDF, grafo_temp: GrafoDB
    ):
        """Rodar a mesma NFC-e 2x não duplica nós nem arestas."""
        from src.graph.ingestor_documento import ingerir_documento_fiscal

        nfces = extrator.extrair_nfces(
            extrator.caminho,
            texto_override=_carregar("nfce_americanas_compra.txt"),
        )
        doc, itens = nfces[0]
        id1 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        id2 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        assert id1 == id2

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["documento"] == 1
        assert stats["nodes_por_tipo"]["item"] == 2
        assert stats["edges_por_tipo"]["contem_item"] == 2

    def test_supermercado_gera_31_itens(
        self, extrator: ExtratorNfcePDF, grafo_temp: GrafoDB
    ):
        from src.graph.ingestor_documento import ingerir_documento_fiscal

        doc, itens = extrator.extrair_nfces(
            extrator.caminho,
            texto_override=_carregar("nfce_americanas_supermercado.txt"),
        )[0]
        ingerir_documento_fiscal(grafo_temp, doc, itens)
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["item"] == 31
        assert stats["edges_por_tipo"]["contem_item"] == 31


# ============================================================================
# Contrato ExtratorBase
# ============================================================================


class TestPodeProcessar:
    def test_pode_processar_por_path_nfce(
        self, extrator: ExtratorNfcePDF, tmp_path: Path
    ):
        arq = tmp_path / "andre" / "nfs_fiscais" / "nfce" / "NFCE_123.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"%PDF-1.4\n")
        assert extrator.pode_processar(arq) is True

    def test_rejeita_extensao_incompativel(
        self, extrator: ExtratorNfcePDF, tmp_path: Path
    ):
        arq = tmp_path / "nfce" / "NFCE_123.png"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"\x89PNG")
        # Spec: NFC-e assume PDF nativo; imagem é Sprint 45
        assert extrator.pode_processar(arq) is False

    def test_extrair_retorna_lista_vazia_de_transacao(
        self,
        extrator: ExtratorNfcePDF,
        grafo_temp: GrafoDB,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """`extrair()` devolve [] (total não vira transação; duplicaria extrato)."""
        monkeypatch.setattr(
            extrator,
            "_ler_paginas",
            lambda caminho: [_carregar("nfce_americanas_compra.txt")],
        )
        monkeypatch.setattr(extrator, "_grafo", grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        assert grafo_temp.estatisticas()["nodes_por_tipo"].get("documento") == 1


# "Quem despreza o pequeno cupom não merece a grande nota." -- Provérbios adaptado
