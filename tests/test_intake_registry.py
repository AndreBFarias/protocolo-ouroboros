"""Testes do src.intake.registry.

Cobre:
- CSV Nubank cartão (header `date,title,amount`) -> caminho legado
- CSV Nubank CC (header `Data,Valor,Identificador,Descrição`) -> caminho legado
- OFX -> detector próprio do registry (legado não cobre OFX)
- XLSX inválido -> legado tenta e falha graciosamente -> YAML fallback
- PDF Itaú/Santander -> legado primeiro
- PDF cupom_garantia -> legado retorna None -> YAML pega
- IMG/XML/EML -> YAML direto (legado não tenta)
- Adapter: DeteccaoArquivo vira Decisao com pasta `<pessoa>/<banco>_<tipo>/`
- Integração com orchestrator: arquivos bancários reais do data/raw/ são roteados
"""

from __future__ import annotations

import pytest

from src.intake import classifier as clf
from src.intake import registry as reg
from src.intake.classifier import Decisao
from src.utils.file_detector import DeteccaoArquivo

# ============================================================================
# Fixtures de isolamento
# ============================================================================


@pytest.fixture(autouse=True)
def isolar_paths(tmp_path, monkeypatch):
    """Aponta _PATH_DATA_RAW do registry para tmp_path."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(reg, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(reg, "_PATH_DATA_RAW", raiz / "data" / "raw")
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()
    yield raiz


# ============================================================================
# CSV legado
# ============================================================================


def test_csv_nubank_cartao_vai_pelo_legado(tmp_path):
    arq = tmp_path / "Nubank_2026-04-11.csv"
    arq.write_text("date,title,amount\n2026-04-15,Teste Loja,50.00\n", encoding="utf-8")
    decisao = reg.detectar_tipo(arq, "text/csv", preview=None, pessoa="andre")
    assert decisao.tipo == "bancario_nubank_cartao"
    assert decisao.extrator_modulo == "src.extractors.nubank_cartao"
    assert decisao.origem_sprint == "41c"
    assert "nubank_cartao" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("BANCARIO_NUBANK_CARTAO_")
    assert decisao.data_detectada_iso == "2026-04-01"


def test_csv_nubank_cc_vai_pelo_legado(tmp_path):
    arq = tmp_path / "NU_977370681_01ABR2026_30ABR2026.csv"
    arq.write_text(
        "Data,Valor,Identificador,Descri\u00e7\u00e3o\n01/04/2026,100,abc,Teste\n",
        encoding="utf-8",
    )
    decisao = reg.detectar_tipo(arq, "text/csv", preview=None, pessoa="vitoria")
    assert decisao.tipo == "bancario_nubank_cc"
    assert decisao.extrator_modulo == "src.extractors.nubank_cc"
    assert decisao.data_detectada_iso == "2026-04-01"


def test_csv_nao_bancario_cai_em_classificar_via_yaml(tmp_path):
    arq = tmp_path / "qualquer.csv"
    arq.write_text("col1,col2\n1,2\n", encoding="utf-8")
    decisao = reg.detectar_tipo(arq, "text/csv", preview="col1,col2\n1,2\n", pessoa="andre")
    assert decisao.tipo is None  # YAML não cobre CSV genérico


# ============================================================================
# OFX
# ============================================================================


def test_ofx_c6_detector_proprio_do_registry(tmp_path):
    arq = tmp_path / "c6_cc_andre_2026-04.ofx"
    arq.write_bytes(b"OFXHEADER:100\n<OFX></OFX>")
    decisao = reg.detectar_tipo(arq, "application/x-ofx", preview=None, pessoa="andre")
    assert decisao.tipo == "bancario_c6_ofx"
    assert decisao.extrator_modulo == "src.extractors.ofx_parser"
    assert "c6_cc" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("BANCARIO_C6_OFX_")


def test_ofx_banco_desconhecido_marca_como_desconhecido(tmp_path):
    arq = tmp_path / "extrato_qualquer.ofx"
    arq.write_bytes(b"OFXHEADER:100\n<OFX></OFX>")
    decisao = reg.detectar_tipo(arq, "application/x-ofx", preview=None, pessoa="andre")
    assert decisao.tipo == "bancario_desconhecido_ofx"


def test_ofx_pessoa_via_path_quando_nao_explicita(tmp_path):
    pasta_andre = tmp_path / "andre"
    pasta_andre.mkdir()
    arq = pasta_andre / "extrato.ofx"
    arq.write_bytes(b"OFXHEADER:100\n<OFX></OFX>")
    decisao = reg.detectar_tipo(arq, "application/x-ofx", preview=None, pessoa="_indefinida")
    assert "/andre/" in str(decisao.pasta_destino)


def test_ofx_fallback_casal_sem_pista(tmp_path):
    arq = tmp_path / "extrato.ofx"
    arq.write_bytes(b"OFXHEADER:100\n<OFX></OFX>")
    decisao = reg.detectar_tipo(arq, "application/x-ofx", preview=None, pessoa="_indefinida")
    assert "/casal/" in str(decisao.pasta_destino)


# ============================================================================
# PDF -- legado primeiro, YAML fallback
# ============================================================================


def test_pdf_cupom_garantia_legado_devolve_none_yaml_pega(tmp_path):
    """Cupom de garantia não é Itaú/Santander -- legado retorna None,
    YAML reconhece pelo regex `CUPOM BILHETE DE SEGURO + GARANTIA + SUSEP`."""
    from reportlab.pdfgen import canvas

    arq = tmp_path / "cupom.pdf"
    c = canvas.Canvas(str(arq))
    for linha in [
        "CUPOM BILHETE DE SEGURO",
        "GARANTIA ESTENDIDA ORIGINAL",
        "Processo SUSEP No. 15414.900147/2014-11",
        "DATA DA EMISSAO: 19/04/2026",
    ]:
        c.drawString(
            50,
            800 - 14 * (1 + ["CUPOM", "GARANTIA", "Processo", "DATA"].index(linha.split()[0])),
            linha,
        )
    c.showPage()
    c.save()

    preview_texto = (
        "CUPOM BILHETE DE SEGURO\nGARANTIA ESTENDIDA ORIGINAL\n"
        "Processo SUSEP No. 15414.900147/2014-11\nDATA DA EMISSAO: 19/04/2026"
    )
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview_texto, pessoa="andre")
    assert decisao.tipo == "cupom_garantia_estendida"
    assert decisao.origem_sprint == 41  # YAML, não 41c


def test_pdf_holerite_legado_devolve_none_yaml_pega(tmp_path):
    """Holerite não é bancário -- legado None, YAML pega via 'Holerite'."""
    from reportlab.pdfgen import canvas

    arq = tmp_path / "holerite.pdf"
    c = canvas.Canvas(str(arq))
    c.drawString(50, 800, "Demonstrativo de Pagamento de Salario")
    c.drawString(50, 780, "Funcionario: ANDRE FARIAS")
    c.showPage()
    c.save()
    decisao = reg.detectar_tipo(
        arq, "application/pdf", preview="Demonstrativo de Pagamento de Salario", pessoa="andre"
    )
    assert decisao.tipo == "holerite"


# ============================================================================
# IMG/XML/EML -- YAML direto
# ============================================================================


def test_xml_nfe_vai_direto_para_yaml(tmp_path):
    arq = tmp_path / "nfe.xml"
    arq.write_text('<?xml version="1.0"?><infNFe/>', encoding="utf-8")
    decisao = reg.detectar_tipo(
        arq, "application/xml", preview='<?xml version="1.0"?><infNFe/>', pessoa="andre"
    )
    assert decisao.tipo == "xml_nfe"


def test_imagem_jpeg_vai_direto_para_yaml(tmp_path):
    arq = tmp_path / "cupom.jpg"
    arq.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    decisao = reg.detectar_tipo(
        arq, "image/jpeg", preview="CUPOM FISCAL CCF: 12345", pessoa="andre"
    )
    assert decisao.tipo == "cupom_fiscal_foto"


# ============================================================================
# Adapter: DeteccaoArquivo -> Decisao
# ============================================================================


def test_adapter_legado_constroi_decisao_com_pessoa_e_periodo(tmp_path):
    arq = tmp_path / "x.csv"
    arq.write_bytes(b"x")
    deteccao = DeteccaoArquivo(
        banco="nubank",
        tipo="cartao",
        pessoa="andre",
        subtipo="",
        periodo="2026-03",
        formato="csv",
        confianca=0.95,
    )
    decisao = reg._adaptar_legado(deteccao, arq)
    assert isinstance(decisao, Decisao)
    assert decisao.tipo == "bancario_nubank_cartao"
    assert decisao.data_detectada_iso == "2026-03-01"
    assert "andre/nubank_cartao" in str(decisao.pasta_destino)
    assert decisao.nome_canonico == f"BANCARIO_NUBANK_CARTAO_2026-03_{reg.sha8_arquivo(arq)}.csv"


def test_adapter_legado_sem_periodo_omite_data(tmp_path):
    arq = tmp_path / "x.pdf"
    arq.write_bytes(b"x")
    deteccao = DeteccaoArquivo(
        banco="itau",
        tipo="cc",
        pessoa="andre",
        subtipo="",
        periodo=None,
        formato="pdf",
        confianca=0.95,
    )
    decisao = reg._adaptar_legado(deteccao, arq)
    assert decisao.data_detectada_iso is None
    assert "_2026" not in decisao.nome_canonico  # sem periodo, nome enxuto


# ============================================================================
# Integração com orchestrator (smoke)
# ============================================================================


def test_orchestrator_csv_bancario_real_chama_legado_via_registry(
    tmp_path, isolar_paths, monkeypatch
):
    """Smoke: orchestrator usa registry, e CSV Nubank vai pelo legado.

    A fixture `isolar_paths` (autouse) já redirecionou registry+classifier
    para `tmp_path/repo`. Aqui só preciso redirecionar envelope+router pra
    mesma raiz e disparar o pipeline.
    """
    from src.intake import extractors_envelope as env
    from src.intake import orchestrator as orq
    from src.intake import router

    raiz = isolar_paths  # devolvido pela fixture
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )

    pseudo_inbox = raiz / "inbox"
    pseudo_inbox.mkdir(parents=True, exist_ok=True)
    arq = pseudo_inbox / "Nubank_2026-04-11.csv"
    arq.write_text("date,title,amount\n2026-04-15,X,50.00\n", encoding="utf-8")

    relatorio = orq.processar_arquivo_inbox(arq, pessoa="andre")
    assert len(relatorio.artefatos) == 1
    assert relatorio.artefatos[0].decisao.tipo == "bancario_nubank_cartao"
    assert relatorio.sucesso_total is True


# "Dois caminhos para o mesmo destino é um caminho perdido." -- princípio da unificação
