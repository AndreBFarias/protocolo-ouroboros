"""Testes do src.intake.heterogeneidade.

Cobre:
- PDFs reais da inbox (heterogêneos confirmados)
- PDFs sintéticos homogêneos (extrato bancário simulado)
- Casos limite (1 página, sem texto, mesmo bilhete repetido)
- Defesa contra PDF corrompido (não levanta)
- Integração com orchestrator (page-split condicional)

10 testes mínimos conforme acceptance da Sprint 41d.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import heterogeneidade as het

INBOX = Path(__file__).resolve().parents[1] / "inbox"
PDF_NOTAS = INBOX / "pdf_notas.pdf"  # 3 cupons garantia, 3 bilhetes distintos
PDF_SCAN = INBOX / "notas de garantia e compras.pdf"  # 4 pgs scan (sem texto)

SOMENTE_SE_INBOX_EXISTE = pytest.mark.skipif(
    not (PDF_NOTAS.exists() and PDF_SCAN.exists()),
    reason="PDFs reais da inbox/ não disponíveis",
)


# ============================================================================
# Helpers para sintéticos
# ============================================================================


def _criar_pdf_com_paginas(tmp_path: Path, textos_por_pagina: list[str]) -> Path:
    """Cria PDF nativo (texto extraível) com N páginas via reportlab.

    Cada string em `textos_por_pagina[i]` vira o texto da página i+1.
    Quebra de linha respeitada via split('\n').
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    caminho = tmp_path / f"sintetico_{abs(hash(tuple(textos_por_pagina))):x}.pdf"
    c = canvas.Canvas(str(caminho), pagesize=A4)
    for texto in textos_por_pagina:
        for i, linha in enumerate(texto.split("\n")):
            c.drawString(50, 800 - i * 14, linha)
        c.showPage()
    c.save()
    return caminho


# ============================================================================
# 1. PDFs reais
# ============================================================================


@SOMENTE_SE_INBOX_EXISTE
def test_pdf_notas_real_3_bilhetes_distintos_e_heterogeneo():
    """pdf_notas.pdf: pgs 1, 2 e 3 com bilhetes 781000129322124 (x2) e
    781000129322123. Pelo menos um par tem páginas distintas -> heterogêneo."""
    assert het.e_heterogeneo(PDF_NOTAS) is True


@SOMENTE_SE_INBOX_EXISTE
def test_pdf_scan_real_sem_texto_extrai_e_homogeneo():
    """notas de garantia e compras.pdf: 4 pgs scan puro. Sem OCR aqui,
    nenhum identificador é extraído -> homogêneo (assume single envelope).

    Isso é o comportamento defensivo correto: sem texto, não dá pra
    detectar heterogeneidade. Quando Sprint 45 entrar com OCR, este
    PDF passa a ser detectado como heterogêneo (2 chaves NFe + 2 bilhetes).
    """
    assert het.e_heterogeneo(PDF_SCAN) is False


# ============================================================================
# 2. Casos canônicos sintéticos
# ============================================================================


def test_pdf_uma_pagina_e_homogeneo(tmp_path):
    pdf = _criar_pdf_com_paginas(tmp_path, ["Conteúdo qualquer com CPF: 051.273.731-22"])
    assert het.e_heterogeneo(pdf) is False


def test_pdf_sem_identificadores_legiveis_e_homogeneo(tmp_path):
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        ["Texto bobo sem nada", "Mais texto bobo", "Ainda mais texto"],
    )
    assert het.e_heterogeneo(pdf) is False


def test_pdf_dois_bilhetes_em_paginas_diferentes_e_heterogeneo(tmp_path):
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        [
            "Cupom 1\nBILHETE INDIVIDUAL: 781000129322124\nMais texto",
            "Cupom 2\nBILHETE INDIVIDUAL: 781000129322125\nOutro texto",
        ],
    )
    assert het.e_heterogeneo(pdf) is True


def test_pdf_mesmo_bilhete_repetido_em_2_paginas_e_homogeneo(tmp_path):
    """Caso real: pdf_notas pgs 1-2 são duplicatas do mesmo bilhete 781000129322124.
    Vira 1 ID único -> não há divergência -> homogêneo."""
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        [
            "Cupom\nBILHETE INDIVIDUAL: 781000129322124\nemissao 19/04",
            "Cupom IDENTICO\nBILHETE INDIVIDUAL: 781000129322124\nemissao 19/04",
        ],
    )
    assert het.e_heterogeneo(pdf) is False


def test_pdf_chave_nfe_e_bilhete_em_paginas_distintas_e_heterogeneo(tmp_path):
    """Caso da inbox real: NFC-e na pg1 + cupom garantia na pg2 do mesmo PDF."""
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        [
            "NFC-e nº 12345\n5326 0400 7765 7401 8079 6530 4000 0432 8010 5868 2510",
            "Cupom\nBILHETE INDIVIDUAL: 781000129322124",
        ],
    )
    assert het.e_heterogeneo(pdf) is True


def test_pdf_extrato_bancario_simulado_mesmo_cpf_em_4_pgs_e_homogeneo(tmp_path):
    """Extrato bancário típico: cabeçalho/CPF na pg1, continuação nas pgs 2-4.
    pgs 2-4 podem nem ter o CPF impresso. Sem >1 ID distinto -> homogêneo."""
    pg1 = (
        "EXTRATO DE CONTA -- ITAU\n"
        "CPF: 051.273.731-22\n"
        "Saldo Anterior: R$ 1000,00\n"
        "Linha de transação"
    )
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        [
            pg1,
            "Continuacao do extrato\n02/04/2026 PIX recebido R$ 100,00",
            "Continuacao do extrato\n03/04/2026 PIX enviado R$ 50,00",
            "Continuacao do extrato\n04/04/2026 SALDO DO DIA R$ 1.050,00",
        ],
    )
    assert het.e_heterogeneo(pdf) is False


def test_pdf_dois_cpfs_em_paginas_diferentes_e_heterogeneo(tmp_path):
    """Dois cupons garantia para pessoas diferentes (CPFs distintos em páginas distintas)."""
    pdf = _criar_pdf_com_paginas(
        tmp_path,
        [
            "Cupom Pessoa A\nCPF: 051.273.731-22",
            "Cupom Pessoa B\nCPF: 977.370.681-00",
        ],
    )
    assert het.e_heterogeneo(pdf) is True


# ============================================================================
# 3. Defesa contra corrupção
# ============================================================================


def test_pdf_corrompido_devolve_false_sem_levantar(tmp_path):
    falso = tmp_path / "falso.pdf"
    falso.write_bytes("isto não é um PDF válido".encode("utf-8"))
    assert het.e_heterogeneo(falso) is False


def test_pdf_inexistente_devolve_false_sem_levantar(tmp_path):
    assert het.e_heterogeneo(tmp_path / "fantasma.pdf") is False


# ============================================================================
# 4. Integração com orchestrator
# ============================================================================


def test_orchestrator_pdf_heterogeneo_chama_expandir_multipage(tmp_path, monkeypatch):
    """Quando e_heterogeneo == True, orchestrator usa page-split."""
    from src.intake import classifier as clf
    from src.intake import extractors_envelope as env
    from src.intake import orchestrator as orq
    from src.intake import router

    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()

    pseudo_inbox = raiz / "inbox"
    pseudo_inbox.mkdir(parents=True, exist_ok=True)
    pdf_het = _criar_pdf_com_paginas(
        pseudo_inbox,
        [
            "BILHETE INDIVIDUAL: 781000129322124",
            "BILHETE INDIVIDUAL: 781000129322125",
        ],
    )
    relatorio = orq.processar_arquivo_inbox(pdf_het, pessoa="andre")
    # Heterogêneo -> 2 artefatos (page-split)
    assert len(relatorio.artefatos) == 2


def test_orchestrator_pdf_homogeneo_chama_envelope_single(tmp_path, monkeypatch):
    """Quando e_heterogeneo == False, orchestrator NÃO faz page-split."""
    from src.intake import classifier as clf
    from src.intake import extractors_envelope as env
    from src.intake import orchestrator as orq
    from src.intake import router

    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz / "data" / "raw" / "_envelopes")
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz / "data" / "raw" / "_envelopes" / "originais"
    )
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()

    pseudo_inbox = raiz / "inbox"
    pseudo_inbox.mkdir(parents=True, exist_ok=True)
    pdf_homo = _criar_pdf_com_paginas(
        pseudo_inbox,
        [
            "EXTRATO DE CONTA\nCPF: 051.273.731-22\nSaldo Anterior",
            "Continuacao pg2",
            "Continuacao pg3",
        ],
    )
    relatorio = orq.processar_arquivo_inbox(pdf_homo, pessoa="andre")
    # Homogêneo -> 1 artefato só (single envelope)
    assert len(relatorio.artefatos) == 1


# "Não toda multidão é desordem; nem toda página é documento à parte." -- princípio do diagnóstico
