"""Testes regressivos da Sprint 90a: holerite vence detector bancário legado.

Cenário do problema (auditoria 2026-04-26):
  13 PDFs em data/raw/andre/itau_cc/ (3) e data/raw/andre/santander_cartao/ (10)
  são contracheques G4F mal classificados. file_detector.py casa pelo regex
  frouxo "ITAÚ UNIBANCO" / "SANTANDER" no texto, mesmo quando o documento é
  na verdade um holerite que apenas menciona o banco no rodapé de dados
  bancários do funcionário.

Solução (Sprint 90a):
  1) holerite promovido para `prioridade: especifico` em tipos_documento.yaml
     com regex endurecido (Demonstrativo de Pagamento, G4F, INFOBASE).
  2) registry.detectar_tipo faz pre-check no preview antes do legado: se
     contém assinatura forte de holerite, pula o legado e delega ao YAML.

Testes mínimos exigidos pela spec:
  - holerite G4F sintético → tipo == "holerite"
  - holerite Infobase sintético → tipo == "holerite"
  - extrato Itaú real (cabeçalho ITAÚ UNIBANCO + agência 6450) → bancario_itau_cc
  - fatura Santander real (cartão 4220 XXXX XXXX 7342) → bancario_santander_cartao

Também cobrimos:
  - holerite com menção SANTANDER no rodapé (caso real do problema) ainda vai
    para holerite, NÃO para bancario_santander_cartao.
  - holerite com menção ITAÚ UNIBANCO no rodapé idem.
  - prioridade `especifico` é respeitada no YAML carregado.
"""

from __future__ import annotations

import pytest
from reportlab.pdfgen import canvas

from src.intake import classifier as clf
from src.intake import registry as reg

# ============================================================================
# Fixtures de isolamento
# ============================================================================


@pytest.fixture(autouse=True)
def isolar_paths(tmp_path, monkeypatch):
    """Aponta _PATH_DATA_RAW de registry+classifier para tmp_path."""
    raiz = tmp_path / "repo"
    raiz.mkdir()
    monkeypatch.setattr(reg, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(reg, "_PATH_DATA_RAW", raiz / "data" / "raw")
    monkeypatch.setattr(clf, "_RAIZ_REPO", raiz)
    monkeypatch.setattr(clf, "_PATH_DATA_RAW", raiz / "data" / "raw")
    clf.recarregar_tipos()
    yield raiz


def _pdf_com_linhas(arq, linhas):
    """Gera um PDF mínimo com as linhas fornecidas (uma por linha vertical)."""
    c = canvas.Canvas(str(arq))
    y = 800
    for linha in linhas:
        c.drawString(50, y, linha)
        y -= 14
    c.showPage()
    c.save()


# ============================================================================
# Testes principais (4 obrigatórios pela spec)
# ============================================================================


def test_holerite_g4f_classifica_como_holerite(tmp_path):
    """PDF com assinatura G4F vai para holerite, não para bancario_*."""
    arq = tmp_path / "g4f.pdf"
    linhas = [
        "G4F SOLUCOES CORPORATIVAS LTDA",
        "CNPJ: 07.094.346/0002-26",
        "Demonstrativo de Pagamento de Salario",
        "Funcionario: ANDRE FARIAS",
        "Competencia: 04/2026",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "\n".join(linhas)
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "holerite"
    assert decisao.prioridade == "especifico"
    assert "holerites" in str(decisao.pasta_destino)


def test_holerite_infobase_classifica_como_holerite(tmp_path):
    """PDF com assinatura Infobase vai para holerite."""
    arq = tmp_path / "infobase.pdf"
    linhas = [
        "INFOBASE TECNOLOGIA LTDA",
        "Recibo de Pagamento de Salario",
        "Funcionario: ANDRE FARIAS",
        "Competencia: 03/2026",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "\n".join(linhas)
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "holerite"
    assert decisao.prioridade == "especifico"


def test_extrato_itau_real_continua_bancario_itau_cc(tmp_path):
    """Regression: extrato Itaú real (sem assinatura de holerite) ainda vai
    pelo legado e classifica como bancario_itau_cc."""
    arq = tmp_path / "itau_extrato.pdf"
    linhas = [
        "ITAU UNIBANCO S.A.",
        "agência: 6450",
        "EXTRATO DE CONTA CORRENTE",
        "Saldo Anterior: 100,00",
        "Período: 01/04/2026 a 30/04/2026",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "ITAÚ UNIBANCO\nagência: 6450\nEXTRATO DE CONTA CORRENTE\n"
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "bancario_itau_cc"
    assert decisao.extrator_modulo == "src.extractors.itau_pdf"


def test_fatura_santander_real_continua_bancario_santander_cartao(tmp_path):
    """Regression: fatura Santander real (cartão 4220 XXXX XXXX 7342) ainda vai
    pelo legado e classifica como bancario_santander_cartao."""
    arq = tmp_path / "santander_fatura.pdf"
    linhas = [
        "SANTANDER",
        "Cartao Black Way Elite",
        "Número: 4220 XXXX XXXX 7342",
        "Vencimento: 15/04/2026",
        "Total da fatura: 500,00",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "SANTANDER\nCartao Black Way\n4220 XXXX XXXX 7342\n"
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "bancario_santander_cartao"
    assert decisao.extrator_modulo == "src.extractors.santander_pdf"


# ============================================================================
# Testes complementares: cenário real do bug (auditoria 2026-04-26)
# ============================================================================


def test_holerite_com_mencao_santander_no_rodape_vai_para_holerite(tmp_path):
    """Cenário real do bug: holerite G4F que menciona SANTANDER no rodapé
    (banco do funcionário). Antes da Sprint 90a caía em
    bancario_santander_cartao. Agora vai corretamente para holerite."""
    arq = tmp_path / "g4f_com_santander.pdf"
    linhas = [
        "G4F SOLUCOES CORPORATIVAS LTDA",
        "Demonstrativo de Pagamento de Salario",
        "Competencia: 04/2026",
        "Vencimentos: 5000,00",
        "Descontos: 800,00",
        "Liquido a Receber: 4200,00",
        "Conta para credito: SANTANDER",
        "Agencia: 1234 Conta: 56789-0",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "\n".join(linhas)
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "holerite"
    assert "holerites" in str(decisao.pasta_destino)


def test_holerite_com_mencao_itau_no_rodape_vai_para_holerite(tmp_path):
    """Cenário real do bug: holerite Infobase mencionando ITAÚ UNIBANCO no
    rodapé. Antes da Sprint 90a caía em bancario_itau_cc. Agora vai para
    holerite."""
    arq = tmp_path / "infobase_com_itau.pdf"
    linhas = [
        "INFOBASE TECNOLOGIA LTDA",
        "Recibo de Pagamento de Salario",
        "Competencia: 03/2026",
        "Vencimentos: 6000,00",
        "Liquido: 5100,00",
        "Conta credito: ITAU UNIBANCO",
        "agencia: 6450 conta: 1234-5",
    ]
    _pdf_com_linhas(arq, linhas)
    preview = "\n".join(linhas)
    decisao = reg.detectar_tipo(arq, "application/pdf", preview=preview, pessoa="andre")
    assert decisao.tipo == "holerite"


def test_yaml_holerite_tem_prioridade_especifico():
    """Garante que a regra holerite no YAML está em `especifico`. Esse é o
    invariante estrutural da Sprint 90a e protege contra reverter a
    promoção em PRs futuras."""
    tipos = clf._carregar_se_preciso()
    holerites = [t for t in tipos if t.get("id") == "holerite"]
    assert len(holerites) == 1, "deve existir exatamente uma regra holerite no YAML"
    assert holerites[0]["prioridade"] == "especifico"


def test_pre_check_holerite_funcao_helper():
    """Smoke do helper _tem_assinatura_holerite: positivo + negativo."""
    assert reg._tem_assinatura_holerite("Demonstrativo de Pagamento de Salário")
    assert reg._tem_assinatura_holerite("xxx G4F SOLUCOES CORPORATIVAS yyy")
    assert reg._tem_assinatura_holerite("INFOBASE TECNOLOGIA LTDA")
    # case-insensitive
    assert reg._tem_assinatura_holerite("recibo de pagamento de salario")
    # negativos
    assert not reg._tem_assinatura_holerite("ITAÚ UNIBANCO\nEXTRATO DE CONTA")
    assert not reg._tem_assinatura_holerite("")
    assert not reg._tem_assinatura_holerite("SANTANDER fatura")


# "Holerite tem cara de holerite, não importa o nome do download." -- match-pelo-conteúdo
