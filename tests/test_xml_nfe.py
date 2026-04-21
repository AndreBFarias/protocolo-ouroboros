"""Testes do extrator XML NFe modelo 55 (Sprint 46).

Fixtures em `tests/fixtures/nfe_xml/` são XMLs sintéticos padrão SEFAZ
layout 4.0 com chave 44 válida (DV calculado via módulo 11 oficial) e
CNPJs anonimizados. Nenhum XML real de cliente foi commitado.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from src.extractors.xml_nfe import (
    NS_NFE,
    ORIGEM_FONTE,
    ExtratorXmlNFe,
    _detectar_cancelamento,
    _parse_cabecalho,
    _parse_itens,
    e_xml_nfe,
)
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal
from src.utils.chave_nfe import (
    extrair_cnpj_emitente,
    extrair_modelo,
    valida_digito_verificador,
)

FIXTURES = Path(__file__).parent / "fixtures" / "nfe_xml"

CHAVE_VAREJO = "53260400776574016079550010000432601123456782"
CHAVE_SERVICO = "53260422333444000155550020000000771999888772"
CHAVE_CANCELADA = "53260411222333000144550010000000991555444333"
CHAVE_SOBRESCRITA = "53260488999777000100550010000012341112233445"


def _carregar_bytes(nome: str) -> bytes:
    return (FIXTURES / nome).read_bytes()


def _carregar_root(nome: str) -> ET.Element:
    return ET.fromstring(_carregar_bytes(nome))


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorXmlNFe:
    placeholder = tmp_path / "placeholder.xml"
    placeholder.write_bytes(b"<?xml version='1.0'?><root/>")
    return ExtratorXmlNFe(placeholder)


@pytest.fixture()
def grafo_temp(tmp_path: Path):
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


# ============================================================================
# Chaves sinteticas -- sanity check de DV (Luna #4: empirismo antes de supor)
# ============================================================================


class TestChavesSinteticas:
    def test_chave_varejo_dv_valido(self):
        assert valida_digito_verificador(CHAVE_VAREJO) is True
        assert extrair_modelo(CHAVE_VAREJO) == "55"
        assert extrair_cnpj_emitente(CHAVE_VAREJO) == "00.776.574/0160-79"

    def test_chave_servico_dv_valido(self):
        assert valida_digito_verificador(CHAVE_SERVICO) is True

    def test_chave_cancelada_dv_valido(self):
        assert valida_digito_verificador(CHAVE_CANCELADA) is True

    def test_chave_sobrescrita_dv_valido(self):
        assert valida_digito_verificador(CHAVE_SOBRESCRITA) is True


# ============================================================================
# Detector
# ============================================================================


class TestDetector:
    def test_e_xml_nfe_aceita_varejo(self):
        assert e_xml_nfe(_carregar_root("nfe_varejo_3itens.xml")) is True

    def test_e_xml_nfe_aceita_servico(self):
        assert e_xml_nfe(_carregar_root("nfe_servico_ti_1item.xml")) is True

    def test_e_xml_nfe_aceita_envelope_de_cancelamento(self):
        """`procEventoNFe` envolve a NFe original e deve ser reconhecido."""
        assert e_xml_nfe(_carregar_root("nfe_cancelada.xml")) is True

    def test_rejeita_xml_nao_nfe(self):
        assert e_xml_nfe(_carregar_root("nao_e_nfe.xml")) is False

    def test_rejeita_xml_sem_namespace_sefaz(self):
        xml = "<?xml version='1.0'?><root><data>x</data></root>"
        assert e_xml_nfe(ET.fromstring(xml)) is False

    def test_rejeita_nfce_modelo_65(self):
        """Modelo 65 tem extrator dedicado (Sprint 44b); aqui deve rejeitar."""
        # Chave sintetica modelo 65 (NFC-e) -- extrator xml_nfe rejeita.
        xml = (
            "<?xml version='1.0'?>"
            "<nfeProc xmlns='http://www.portalfiscal.inf.br/nfe'>"
            "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'>"
            "<infNFe Id='NFe53260400776574016079653040000432601123456788'>"
            "<ide><mod>65</mod></ide>"
            "<emit><CNPJ>00776574016079</CNPJ></emit>"
            "</infNFe>"
            "</NFe>"
            "</nfeProc>"
        )
        assert e_xml_nfe(ET.fromstring(xml)) is False


# ============================================================================
# Parser de cabecalho
# ============================================================================


class TestParserCabecalho:
    def test_parse_cabecalho_varejo_completo(self):
        doc = _parse_cabecalho(_carregar_root("nfe_varejo_3itens.xml"))
        assert doc is not None
        assert doc["chave_44"] == CHAVE_VAREJO
        assert doc["tipo_documento"] == "nfe_modelo_55"
        assert doc["origem_fonte"] == ORIGEM_FONTE
        assert doc["cnpj_emitente"] == "00.776.574/0160-79"
        assert doc["razao_social"] == "LOJAS EXEMPLO COMERCIO VAREJISTA LTDA"
        assert "BRASILIA" in (doc["endereco"] or "").upper()
        assert doc["numero"] == "43260"
        assert doc["serie"] == "1"
        assert doc["data_emissao"] == "2026-04-15"
        assert doc["total"] == pytest.approx(1329.88)
        assert doc["cfop_nota"] == "5102"
        assert doc["cpf_cnpj_destinatario"] == "000.000.000-00"
        assert doc["cancelada"] is False

    def test_parse_cabecalho_servico_destinatario_cnpj(self):
        doc = _parse_cabecalho(_carregar_root("nfe_servico_ti_1item.xml"))
        assert doc is not None
        assert doc["cpf_cnpj_destinatario"] == "11.222.333/0001-44"
        assert doc["cnpj_emitente"] == "22.333.444/0001-55"
        assert doc["cfop_nota"] == "5933"
        assert doc["total"] == pytest.approx(10000.00)

    def test_extrai_chave_44_do_atributo_id_infnfe(self):
        """Armadilha A46-1: atributo Id tem prefixo 'NFe' que precisa sair."""
        root = _carregar_root("nfe_varejo_3itens.xml")
        doc = _parse_cabecalho(root)
        assert doc is not None
        # A chave deve ter exatamente 44 digitos, sem o prefixo 'NFe'.
        assert len(doc["chave_44"]) == 44
        assert doc["chave_44"].isdigit()
        assert valida_digito_verificador(doc["chave_44"]) is True

    def test_cancelada_nao_ingere_mas_parseia(self):
        doc = _parse_cabecalho(_carregar_root("nfe_cancelada.xml"))
        assert doc is not None
        assert doc["cancelada"] is True
        assert doc["chave_44"] == CHAVE_CANCELADA

    def test_rejeita_chave_dv_invalido(self, tmp_path: Path):
        xml_ruim = (
            "<?xml version='1.0'?>"
            "<NFe xmlns='http://www.portalfiscal.inf.br/nfe'>"
            "<infNFe Id='NFe53260400776574016079550010000432601123456789'>"
            "<ide><mod>55</mod></ide>"
            "<emit><CNPJ>00776574016079</CNPJ></emit>"
            "</infNFe>"
            "</NFe>"
        )
        doc = _parse_cabecalho(ET.fromstring(xml_ruim))
        assert doc is None


# ============================================================================
# Parser de itens
# ============================================================================


class TestParserItens:
    def test_extrai_todos_itens_com_tributacao_completa(self):
        itens = _parse_itens(_carregar_root("nfe_varejo_3itens.xml"))
        assert len(itens) == 3
        # Cada item tem NCM + CFOP + ICMS + PIS + COFINS (IPI varia por item).
        for item in itens:
            assert item["codigo"]
            assert item["descricao"]
            assert item["ncm"]
            assert item["cfop"]
            assert item["qtde"] is not None and item["qtde"] > 0
            assert item["valor_unit"] is not None
            assert item["valor_total"] is not None
            assert item["icms_valor"] is not None
            assert item["pis_valor"] is not None
            assert item["cofins_valor"] is not None
            assert item["origem_fonte"] == ORIGEM_FONTE

    def test_tributacao_primeiro_item_confere_com_fixture(self):
        itens = _parse_itens(_carregar_root("nfe_varejo_3itens.xml"))
        controle = next(it for it in itens if it["codigo"] == "000004300823")
        assert "CONTROLE P55" in controle["descricao"].upper()
        assert controle["ncm"] == "95045000"
        assert controle["cfop"] == "5102"
        assert controle["unidade"] == "UN"
        assert controle["qtde"] == pytest.approx(1.0)
        assert controle["valor_unit"] == pytest.approx(449.99)
        assert controle["valor_total"] == pytest.approx(449.99)
        assert controle["icms_valor"] == pytest.approx(80.99)
        assert controle["ipi_valor"] == pytest.approx(22.50)
        assert controle["pis_valor"] == pytest.approx(7.42)
        assert controle["cofins_valor"] == pytest.approx(34.20)

    def test_item_sem_ipi_devolve_none(self):
        """Item 2 do varejo não tem bloco IPI (isento)."""
        itens = _parse_itens(_carregar_root("nfe_varejo_3itens.xml"))
        base = next(it for it in itens if it["codigo"] == "000004298119")
        assert base["ipi_valor"] is None
        # Mas os outros tributos existem:
        assert base["icms_valor"] is not None
        assert base["pis_valor"] is not None

    def test_servico_simples_nacional_sem_tributos_federais(self):
        """NFe de serviço em Simples Nacional: PIS/COFINS NT -> valor None."""
        itens = _parse_itens(_carregar_root("nfe_servico_ti_1item.xml"))
        assert len(itens) == 1
        servico = itens[0]
        assert servico["codigo"] == "SVC001"
        # PISNT/COFINSNT não carregam `vPIS`/`vCOFINS` -> esperado None.
        assert servico["pis_valor"] is None
        assert servico["cofins_valor"] is None
        # Mas valor do produto/servico continua correto.
        assert servico["valor_total"] == pytest.approx(10000.00)


# ============================================================================
# Deteccao de cancelamento (Armadilha A46-2)
# ============================================================================


class TestCancelamento:
    def test_xml_cancelada_tpevento_110111_nao_linka(self):
        root = _carregar_root("nfe_cancelada.xml")
        assert _detectar_cancelamento(root) is True

    def test_xml_ativo_nao_e_cancelado(self):
        root = _carregar_root("nfe_varejo_3itens.xml")
        assert _detectar_cancelamento(root) is False


# ============================================================================
# Contrato ExtratorBase
# ============================================================================


class TestPodeProcessar:
    def test_pode_processar_aceita_extensao_xml(
        self, extrator: ExtratorXmlNFe, tmp_path: Path
    ):
        arq = tmp_path / "andre" / "nfs_fiscais" / "xml" / "NFe.xml"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(_carregar_bytes("nfe_varejo_3itens.xml"))
        assert extrator.pode_processar(arq) is True

    def test_rejeita_extensao_nao_xml(
        self, extrator: ExtratorXmlNFe, tmp_path: Path
    ):
        arq = tmp_path / "nfe.pdf"
        arq.write_bytes(b"%PDF-1.4\n")
        assert extrator.pode_processar(arq) is False

    def test_rejeita_xml_sem_namespace_sefaz(
        self, extrator: ExtratorXmlNFe, tmp_path: Path
    ):
        arq = tmp_path / "outro.xml"
        arq.write_bytes(_carregar_bytes("nao_e_nfe.xml"))
        assert extrator.pode_processar(arq) is False

    def test_rejeita_xml_malformado(
        self, extrator: ExtratorXmlNFe, tmp_path: Path
    ):
        arq = tmp_path / "quebrado.xml"
        arq.write_bytes(b"<?xml version='1.0'?><nfe><infNFe")
        # ET.ParseError eh capturado em pode_processar -> False.
        assert extrator.pode_processar(arq) is False

    def test_namespace_nfe_constante_nao_muda(self):
        """Mudanca de namespace quebraria detector e ingestao simultaneamente."""
        assert NS_NFE == "http://www.portalfiscal.inf.br/nfe"


# ============================================================================
# Integração com grafo
# ============================================================================


class TestGrafoXmlNFe:
    def test_grafo_recebe_documento_fornecedor_3_itens(
        self, extrator: ExtratorXmlNFe, grafo_temp: GrafoDB
    ):
        xmls = extrator.extrair_xmls(
            extrator.caminho,
            conteudo_override=_carregar_bytes("nfe_varejo_3itens.xml"),
        )
        assert len(xmls) == 1
        doc, itens = xmls[0]
        assert len(itens) == 3
        doc_id = ingerir_documento_fiscal(
            grafo_temp, doc, itens, caminho_arquivo=extrator.caminho
        )
        assert doc_id > 0

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento") == 1
        assert stats["nodes_por_tipo"].get("fornecedor") == 1
        assert stats["nodes_por_tipo"].get("item") == 3
        assert stats["nodes_por_tipo"].get("periodo") == 1
        assert stats["edges_por_tipo"].get("fornecido_por") == 1
        assert stats["edges_por_tipo"].get("ocorre_em") == 1
        assert stats["edges_por_tipo"].get("contem_item") == 3

    def test_ingestao_idempotente(
        self, extrator: ExtratorXmlNFe, grafo_temp: GrafoDB
    ):
        xmls = extrator.extrair_xmls(
            extrator.caminho,
            conteudo_override=_carregar_bytes("nfe_varejo_3itens.xml"),
        )
        doc, itens = xmls[0]
        id1 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        id2 = ingerir_documento_fiscal(grafo_temp, doc, itens)
        assert id1 == id2
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["documento"] == 1
        assert stats["nodes_por_tipo"]["item"] == 3
        assert stats["edges_por_tipo"]["contem_item"] == 3

    def test_metadata_documento_marca_origem_fonte_xml_nfe(
        self, extrator: ExtratorXmlNFe, grafo_temp: GrafoDB
    ):
        xmls = extrator.extrair_xmls(
            extrator.caminho,
            conteudo_override=_carregar_bytes("nfe_varejo_3itens.xml"),
        )
        doc, itens = xmls[0]
        ingerir_documento_fiscal(grafo_temp, doc, itens)
        node = grafo_temp.buscar_node("documento", CHAVE_VAREJO)
        assert node is not None
        assert node.metadata.get("origem_fonte") == ORIGEM_FONTE
        assert node.metadata.get("tipo_documento") == "nfe_modelo_55"

    def test_xml_sobrescreve_documento_existente_com_origem_fonte(
        self, extrator: ExtratorXmlNFe, grafo_temp: GrafoDB
    ):
        """DANFE PDF ingerido primeiro; XML NFe depois sobrescreve origem_fonte.

        Acceptance da Sprint 46 (Fase 2): quando a mesma chave 44 ja foi
        ingerida por outro extrator, o XML deve marcar `origem_fonte=xml_nfe`
        no grafo (via merge raso do `upsert_node`).
        """
        # Simula uma ingestao anterior via DANFE PDF com dados mais pobres.
        doc_danfe = {
            "chave_44": CHAVE_SOBRESCRITA,
            "tipo_documento": "nfe_modelo_55",
            "origem_fonte": "danfe_pdf",
            "cnpj_emitente": "88.999.777/0001-00",
            "razao_social": "ELETRO PREMIUM COMERCIO LTDA",
            "data_emissao": "2026-02-10",
            "total": 5499.00,
            # DANFE PDF não tem dados ricos de tributação federal.
        }
        item_danfe_pobre = {
            "codigo": "TV55OLED",
            "descricao": "TV OLED 55 POLEGADAS MODELO PREMIUM",
            "qtde": 1.0,
            "valor_unit": 5499.00,
            "valor_total": 5499.00,
            # Sem icms_valor, pis_valor, cofins_valor, origem_fonte.
        }
        ingerir_documento_fiscal(grafo_temp, doc_danfe, [item_danfe_pobre])

        node_antes = grafo_temp.buscar_node("documento", CHAVE_SOBRESCRITA)
        assert node_antes is not None
        assert node_antes.metadata.get("origem_fonte") == "danfe_pdf"

        # Agora ingere o XML -- deve sobrescrever origem_fonte e enriquecer.
        xmls = extrator.extrair_xmls(
            extrator.caminho,
            conteudo_override=_carregar_bytes("nfe_sobrescreve_danfe.xml"),
        )
        doc_xml, itens_xml = xmls[0]
        ingerir_documento_fiscal(grafo_temp, doc_xml, itens_xml)

        node_depois = grafo_temp.buscar_node("documento", CHAVE_SOBRESCRITA)
        assert node_depois is not None
        assert node_depois.id == node_antes.id  # mesmo id (upsert, não insert)
        assert node_depois.metadata.get("origem_fonte") == ORIGEM_FONTE

        # Item também ganhou tributação federal (via merge raso de metadata).
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["documento"] == 1  # não duplicou

    def test_xml_item_enriquecido_com_tributos_federais(
        self, extrator: ExtratorXmlNFe, grafo_temp: GrafoDB
    ):
        """Item ingerido via XML carrega ICMS/IPI/PIS/COFINS nos metadados."""
        xmls = extrator.extrair_xmls(
            extrator.caminho,
            conteudo_override=_carregar_bytes("nfe_varejo_3itens.xml"),
        )
        doc, itens = xmls[0]
        ingerir_documento_fiscal(grafo_temp, doc, itens)
        # Item persistido no grafo carrega tributos federais (acceptance  # noqa: accent
        # #2 da Sprint 46: ICMS/IPI/PIS/COFINS + NCM/CFOP + origem_fonte
        # persistidos em meta do nó `item` via propagação opcional do
        # `ingerir_documento_fiscal`).
        for item in itens:
            chave_item = (
                f"{doc['cnpj_emitente']}|{doc['data_emissao'][:10]}|{item['codigo']}"
            )
            node = grafo_temp.buscar_node("item", chave_item)
            assert node is not None
            assert node.metadata.get("icms_valor") == item["icms_valor"]
            assert node.metadata.get("pis_valor") == item["pis_valor"]
            assert node.metadata.get("cofins_valor") == item["cofins_valor"]
            assert node.metadata.get("origem_fonte") == ORIGEM_FONTE
            assert node.metadata.get("ncm") == item["ncm"]
            assert node.metadata.get("cfop") == item["cfop"]


# ============================================================================
# Integração com pipeline (_descobrir_extratores)
# ============================================================================


class TestRegistroPipeline:
    def test_extrator_registrado_no_pipeline(self):
        """Pipeline deve listar ExtratorXmlNFe entre os extratores descobertos."""
        from src.extractors.xml_nfe import ExtratorXmlNFe
        from src.pipeline import _descobrir_extratores

        classes = _descobrir_extratores()
        nomes = [c.__name__ for c in classes]
        assert "ExtratorXmlNFe" in nomes
        # Extensão .xml é disjunta de .pdf -- ordem no registro não  # noqa: accent
        # importa para roteamento. Precedência XML > DANFE é garantida
        # pelo upsert_node em sobrescrita (ver
        # test_xml_sobrescreve_documento_existente_com_origem_fonte).
        assert classes.index(ExtratorXmlNFe) >= 0


# ============================================================================
# Contrato extrair() -> [] (não gera transação -- total já está no extrato)
# ============================================================================


class TestContratoExtrair:
    def test_extrair_retorna_lista_vazia_de_transacao(
        self,
        tmp_path: Path,
        grafo_temp: GrafoDB,
    ):
        arq = tmp_path / "nfe_varejo.xml"
        arq.write_bytes(_carregar_bytes("nfe_varejo_3itens.xml"))
        extrator = ExtratorXmlNFe(arq, grafo=grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento") == 1
        assert stats["nodes_por_tipo"].get("item") == 3

    def test_extrair_cancelada_nao_ingere(
        self, tmp_path: Path, grafo_temp: GrafoDB
    ):
        arq = tmp_path / "nfe_cancelada.xml"
        arq.write_bytes(_carregar_bytes("nfe_cancelada.xml"))
        extrator = ExtratorXmlNFe(arq, grafo=grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        # NFe cancelada NÃO deve entrar no grafo (acceptance A46-2).
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("documento") is None


# "A prova do parser é o XML real; a prova do dado é o grafo." -- princípio do auditor
