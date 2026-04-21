"""Testes do extrator DANFE NFe modelo 55 (Sprint 44).

Fixtures `.txt` em `tests/fixtures/danfes/` reproduzem o texto extraído via
pdfplumber de DANFEs formais A4, com destinatário anonimizado e chave 44
sintética válida (DV SEFAZ, modelo 55). O extrator aceita `texto_override`
para viabilizar testes sem dependência de binários PDF.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractors.danfe_pdf import (
    ExtratorDanfePDF,
    _parse_cabecalho_danfe,
    _parse_itens_danfe,
    e_danfe,
)
from src.graph.db import GrafoDB
from src.utils.chave_nfe import (
    extrair_cnpj_emitente,
    extrair_modelo,
    valida_digito_verificador,
)

FIXTURES = Path(__file__).parent / "fixtures" / "danfes"


def _carregar(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorDanfePDF:
    placeholder = tmp_path / "placeholder.pdf"
    placeholder.write_bytes(b"%PDF-1.4\n")
    return ExtratorDanfePDF(placeholder)


@pytest.fixture()
def grafo_temp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


# ============================================================================
# Validador de chave 44 dígitos (modelo 55)
# ============================================================================


class TestChave44Modelo55:
    def test_chave_varejo_valida(self):
        # Chave da fixture danfe_varejo_5itens.txt (Americanas)
        chave = "53260400776574016079550010000123451123456786"
        assert valida_digito_verificador(chave) is True
        assert extrair_modelo(chave) == "55"
        assert extrair_cnpj_emitente(chave) == "00.776.574/0160-79"

    def test_chave_servico_valida(self):
        # Chave da fixture danfe_servico_ti_1item.txt
        chave = "53260311222333000144550010000000421876543216"
        assert valida_digito_verificador(chave) is True
        assert extrair_modelo(chave) == "55"
        assert extrair_cnpj_emitente(chave) == "11.222.333/0001-44"

    def test_chave_mercado_valida_uf_sp(self):
        # Chave da fixture danfe_mercado_20itens.txt (São Paulo)
        chave = "35260222333444000155550020000098761112233440"
        assert valida_digito_verificador(chave) is True
        assert extrair_modelo(chave) == "55"
        assert extrair_cnpj_emitente(chave) == "22.333.444/0001-55"

    def test_valida_digito_verificador_chave(self):
        """Test nomeado no spec: valida DV por modulo 11 SEFAZ."""
        chave_boa = "53260400776574016079550010000123451123456786"
        chave_corrompida = "53260400776574016079550010000123451123456789"
        assert valida_digito_verificador(chave_boa) is True
        assert valida_digito_verificador(chave_corrompida) is False


# ============================================================================
# Detector (e_danfe)
# ============================================================================


class TestDetector:
    def test_aceita_danfe_varejo(self):
        assert e_danfe(_carregar("danfe_varejo_5itens.txt")) is True

    def test_aceita_danfe_servico(self):
        assert e_danfe(_carregar("danfe_servico_ti_1item.txt")) is True

    def test_aceita_danfe_mercado(self):
        assert e_danfe(_carregar("danfe_mercado_20itens.txt")) is True

    def test_rejeita_nfce_modelo65(self):
        """NFC-e tem chave modelo 65 e não tem bloco DESTINATÁRIO/REMETENTE."""
        texto_nfce = (
            "Documento Auxiliar da Nota Fiscal de Consumidor Eletronica\n"
            "NFCe nº 43260 Serie 304\n"
            "fazenda.df.gov.br/nfce\n"
            "5326 0400 7765 7401 6079 6530 4000 0432 6011 2345 6788\n"
        )
        assert e_danfe(texto_nfce) is False

    def test_rejeita_texto_arbitrario(self):
        assert e_danfe("Lista de compras: pao, leite, ovos.") is False

    def test_rejeita_chave_modelo_65_mesmo_com_cabecalho_danfe(self):
        """Cabeçalho suspeito: diz DANFE mas chave é modelo 65 -> rejeita."""
        texto = (
            "DANFE\nDESTINATÁRIO / REMETENTE\n"
            "CNPJ: 00.776.574/0160-79\n"
            "5326 0400 7765 7401 6079 6530 4000 0432 6011 2345 6788\n"
        )
        assert e_danfe(texto) is False


# ============================================================================
# Parser de cabeçalho
# ============================================================================


class TestParserCabecalho:
    def test_extrai_chave_44_digitos(self):
        """Test nomeado no spec: extrai chave 44 da DANFE."""
        doc = _parse_cabecalho_danfe(_carregar("danfe_varejo_5itens.txt"))
        assert doc is not None
        assert doc["chave_44"] == "53260400776574016079550010000123451123456786"

    def test_parse_cabecalho_varejo_completo(self):
        doc = _parse_cabecalho_danfe(_carregar("danfe_varejo_5itens.txt"))
        assert doc is not None
        assert doc["tipo_documento"] == "nfe_modelo_55"
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"
        assert doc["razao_social"] is not None
        assert "AMERICANAS" in doc["razao_social"].upper()
        assert doc["numero"] == "12345"
        assert doc["serie"] == "1"
        assert doc["data_emissao"] == "2026-04-19"
        assert doc["total"] == pytest.approx(1748.68)
        assert doc["cfop_nota"] == "5102"
        assert doc["cancelada"] is False

    def test_parse_cabecalho_servico(self):
        doc = _parse_cabecalho_danfe(_carregar("danfe_servico_ti_1item.txt"))
        assert doc is not None
        assert doc["cnpj_emitente"] == "11.222.333/0001-44"
        assert doc["data_emissao"] == "2026-03-15"
        assert doc["total"] == pytest.approx(2500.00)
        assert doc["cfop_nota"] == "5933"

    def test_parse_cabecalho_mercado_uf_sp(self):
        doc = _parse_cabecalho_danfe(_carregar("danfe_mercado_20itens.txt"))
        assert doc is not None
        assert doc["cnpj_emitente"] == "22.333.444/0001-55"
        assert doc["data_emissao"] == "2026-02-10"
        assert doc["total"] == pytest.approx(397.17)

    def test_cancelada_detectada(self):
        texto = _carregar("danfe_varejo_5itens.txt") + "\nNFe CANCELADA\n"
        doc = _parse_cabecalho_danfe(texto)
        assert doc is not None
        assert doc["cancelada"] is True

    def test_endereco_extraido(self):
        doc = _parse_cabecalho_danfe(_carregar("danfe_varejo_5itens.txt"))
        assert doc is not None
        assert doc["endereco"] is not None
        assert "GAMA" in doc["endereco"].upper()

    def test_destinatario_extraido(self):
        doc = _parse_cabecalho_danfe(_carregar("danfe_servico_ti_1item.txt"))
        assert doc is not None
        assert doc["cpf_cnpj_destinatario"] == "55.666.777/0001-88"

    def test_cnpj_texto_vs_chave_divergente_loga_warning(self, caplog):
        import logging
        texto_divergente = (
            "DANFE\nDOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA\n"
            "DESTINATÁRIO / REMETENTE\n"
            "Emitente: EMPRESA X\nCNPJ: 99.999.999/0001-99\n"
            "CHAVE DE ACESSO\n"
            "5326 0400 7765 7401 6079 5500 1000 0123 4511 2345 6786\n"
            "DATA DE EMISSÃO: 19/04/2026\nVALOR TOTAL DA NOTA: 100,00\n"
        )
        with caplog.at_level(logging.WARNING, logger="danfe_pdf"):
            _parse_cabecalho_danfe(texto_divergente)
        assert any("CNPJ divergente" in r.message for r in caplog.records)


# ============================================================================
# Parser de itens + recall
# ============================================================================


class TestParserItens:
    def test_extrai_5_itens_corretamente(self):
        """Test nomeado no spec: recall 100% no caso varejo."""
        itens = _parse_itens_danfe(_carregar("danfe_varejo_5itens.txt"))
        assert len(itens) == 5
        codigos = {it["codigo"] for it in itens}
        assert "000004300823" in codigos
        assert "000004298119" in codigos
        assert "000004312455" in codigos

        controle = next(it for it in itens if it["codigo"] == "000004300823")
        assert "CONTROLE P55" in controle["descricao"].upper()
        assert controle["ncm"] == "95045000"
        assert controle["cfop"] == "5102"
        assert controle["qtde"] == pytest.approx(1.0)
        assert controle["unidade"] == "PCE"
        assert controle["valor_unit"] == pytest.approx(449.99)
        assert controle["valor_total"] == pytest.approx(449.99)
        assert controle["icms_valor"] == pytest.approx(80.99)

    def test_recall_mercado_20_itens(self):
        """Acceptance criterion do spec: >= 95% de recall."""
        itens = _parse_itens_danfe(_carregar("danfe_mercado_20itens.txt"))
        total_esperado = 20
        recall = len(itens) / total_esperado
        assert recall >= 0.95, f"recall {recall:.0%} abaixo de 95%"

    def test_item_servico_unico(self):
        itens = _parse_itens_danfe(_carregar("danfe_servico_ti_1item.txt"))
        assert len(itens) == 1
        servico = itens[0]
        assert servico["codigo"] == "SERV-001"
        assert "CONSULTORIA" in servico["descricao"].upper()
        assert servico["ncm"] == "00000000"
        assert servico["cfop"] == "5933"
        assert servico["valor_total"] == pytest.approx(2500.00)

    def test_itens_tem_campos_obrigatorios(self):
        itens = _parse_itens_danfe(_carregar("danfe_varejo_5itens.txt"))
        for it in itens:
            assert it["codigo"]
            assert it["descricao"]
            assert it["ncm"] and len(it["ncm"]) == 8
            assert it["cfop"] and len(it["cfop"]) == 4
            assert it["qtde"] is not None and it["qtde"] > 0
            assert it["valor_unit"] is not None and it["valor_unit"] > 0
            assert it["valor_total"] is not None and it["valor_total"] > 0

    def test_item_sem_ncm_nao_crasha(self):
        """Test nomeado no spec: item sem NCM (linha inválida) não derruba o parser."""
        texto = (
            "DANFE\nDOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA\n"
            "DESTINATÁRIO / REMETENTE\nCNPJ: 00.776.574/0160-79\n"
            "CHAVE DE ACESSO\n"
            "5326 0400 7765 7401 6079 5500 1000 0123 4511 2345 6786\n"
            "DATA DE EMISSÃO: 19/04/2026\n"
            "CÓDIGO DESCRIÇÃO NCM CFOP UN QTD V.UNIT V.TOTAL\n"
            "ABC ITEM SEM NCM VÁLIDO\n"
            "DEF OUTRO ITEM LINHA QUEBRADA\n"
            "CÁLCULO DO IMPOSTO\n"
            "VALOR TOTAL DA NOTA: 100,00\n"
        )
        itens = _parse_itens_danfe(texto)
        # Nenhum item válido -> lista vazia, sem exceção
        assert itens == []


# ============================================================================
# Fallback para layout desconhecido
# ============================================================================


class TestFallbackLayoutDesconhecido:
    def test_layout_desconhecido_retorna_fallback(
        self, extrator: ExtratorDanfePDF
    ):
        """Test nomeado no spec: layout desconhecido devolve doc com itens=[],
        NÃO crasha -- vai pra fallback supervisor."""
        texto_estranho = (
            "DANFE\nDOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA\n"
            "DESTINATÁRIO / REMETENTE\n"
            "Emitente: EXOTICA LTDA\n"
            "CNPJ: 00.776.574/0160-79\n"
            "CHAVE DE ACESSO\n"
            "5326 0400 7765 7401 6079 5500 1000 0123 4511 2345 6786\n"
            "DATA DE EMISSÃO: 19/04/2026\n"
            "VALOR TOTAL DA NOTA: 500,00\n"
            "LISTA DE PRODUTOS EM FORMATO ESTRANHO SEM TABELA CANONICA.\n"
            "PRODUTO_ESOTERICO_1 R$ 100,00\n"
            "PRODUTO_ESOTERICO_2 R$ 400,00\n"
        )
        resultado = extrator.extrair_danfes(
            extrator.caminho, texto_override=texto_estranho
        )
        assert len(resultado) == 1
        doc, itens = resultado[0]
        assert doc["chave_44"] is not None
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"
        # Layout desconhecido: itens vazios, mas sem crash
        assert itens == []
        assert doc["qtde_itens"] == 0


# ============================================================================
# Integração com grafo (1 Documento + N Itens + 1 Fornecedor + arestas)
# ============================================================================


class TestGrafoDanfe:
    def test_grafo_recebe_documento_fornecedor_itens_varejo(
        self,
        extrator: ExtratorDanfePDF,
        grafo_temp: GrafoDB,
    ):
        danfes = extrator.extrair_danfes(
            extrator.caminho,
            texto_override=_carregar("danfe_varejo_5itens.txt"),
        )
        assert len(danfes) == 1
        doc, itens = danfes[0]

        from src.graph.ingestor_documento import ingerir_documento_fiscal

        doc_id = ingerir_documento_fiscal(
            grafo_temp, doc, itens, caminho_arquivo=extrator.caminho
        )
        assert doc_id > 0

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento") == 1
        assert stats["nodes_por_tipo"].get("fornecedor") == 1
        assert stats["nodes_por_tipo"].get("item") == 5
        assert stats["nodes_por_tipo"].get("periodo") == 1

        assert stats["edges_por_tipo"].get("fornecido_por") == 1
        assert stats["edges_por_tipo"].get("ocorre_em") == 1
        assert stats["edges_por_tipo"].get("contem_item") == 5

    def test_ingestao_idempotente(
        self, extrator: ExtratorDanfePDF, grafo_temp: GrafoDB
    ):
        """Rodar a mesma DANFE 2x não duplica nós nem arestas."""
        from src.graph.ingestor_documento import ingerir_documento_fiscal

        danfes = extrator.extrair_danfes(
            extrator.caminho,
            texto_override=_carregar("danfe_varejo_5itens.txt"),
        )
        doc, itens = danfes[0]
        id1 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        id2 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        assert id1 == id2

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["documento"] == 1
        assert stats["nodes_por_tipo"]["item"] == 5
        assert stats["edges_por_tipo"]["contem_item"] == 5

    def test_tres_danfes_tres_fornecedores_distintos(
        self, extrator: ExtratorDanfePDF, grafo_temp: GrafoDB
    ):
        """Acceptance criterion do spec: 3 DANFEs de fornecedores distintos."""
        from src.graph.ingestor_documento import ingerir_documento_fiscal

        nomes = [
            "danfe_varejo_5itens.txt",
            "danfe_servico_ti_1item.txt",
            "danfe_mercado_20itens.txt",
        ]
        total_itens_grafo = 0
        for nome in nomes:
            doc, itens = extrator.extrair_danfes(
                extrator.caminho, texto_override=_carregar(nome)
            )[0]
            ingerir_documento_fiscal(grafo_temp, doc, itens)
            total_itens_grafo += len(itens)

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["documento"] == 3
        assert stats["nodes_por_tipo"]["fornecedor"] == 3
        # 5 + 1 + 20 = 26 itens
        assert stats["nodes_por_tipo"]["item"] == 26
        assert stats["edges_por_tipo"]["contem_item"] == 26
        assert stats["edges_por_tipo"]["fornecido_por"] == 3


# ============================================================================
# Armadilha A44-6: DANFE cancelada não é ingerida
# ============================================================================


class TestDanfeCancelada:
    def test_cancelada_nao_ingerida_no_grafo(
        self,
        extrator: ExtratorDanfePDF,
        grafo_temp: GrafoDB,
        monkeypatch: pytest.MonkeyPatch,
    ):
        texto_cancelado = _carregar("danfe_varejo_5itens.txt") + "\nNFe CANCELADA\n"
        monkeypatch.setattr(
            extrator, "_ler_paginas", lambda caminho: [texto_cancelado]
        )
        monkeypatch.setattr(extrator, "_grafo", grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        # Cancelada -> grafo intacto (nenhum documento criado)
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento", 0) == 0


# ============================================================================
# Contrato ExtratorBase
# ============================================================================


class TestPodeProcessar:
    def test_pode_processar_por_path_nfs_fiscais(
        self, extrator: ExtratorDanfePDF, tmp_path: Path
    ):
        arq = tmp_path / "andre" / "nfs_fiscais" / "DANFE_123.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"%PDF-1.4\n")
        assert extrator.pode_processar(arq) is True

    def test_rejeita_subpasta_nfce(self, extrator: ExtratorDanfePDF, tmp_path: Path):
        """Subpasta nfs_fiscais/nfce/ é da Sprint 44b, não desta."""
        arq = tmp_path / "andre" / "nfs_fiscais" / "nfce" / "NFCE_1.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"%PDF-1.4\n")
        assert extrator.pode_processar(arq) is False

    def test_rejeita_extensao_incompativel(
        self, extrator: ExtratorDanfePDF, tmp_path: Path
    ):
        arq = tmp_path / "nfs_fiscais" / "DANFE_1.png"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"\x89PNG")
        assert extrator.pode_processar(arq) is False

    def test_extrair_retorna_lista_vazia_de_transacao(
        self,
        extrator: ExtratorDanfePDF,
        grafo_temp: GrafoDB,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """`extrair()` devolve [] (total já aparece no extrato bancário)."""
        monkeypatch.setattr(
            extrator,
            "_ler_paginas",
            lambda caminho: [_carregar("danfe_varejo_5itens.txt")],
        )
        monkeypatch.setattr(extrator, "_grafo", grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        assert grafo_temp.estatisticas()["nodes_por_tipo"].get("documento") == 1


# "Quem mede o detalhe domina o total." -- princípio contábil
