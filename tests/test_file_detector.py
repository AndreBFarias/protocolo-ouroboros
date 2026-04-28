"""Testes regressivos da Sprint 90a-1: endurecer file_detector._detectar_pdf.

Antes da Sprint 90a-1, _detectar_pdf casava qualquer PDF com substring
'ITAÚ UNIBANCO' ou 'SANTANDER' como extrato bancário -- inclusive holerites
e recibos que mencionavam o banco no rodapé. A defesa Sprint 90a no
registry.py mascarava o sintoma; esta sprint endurece a causa raiz.

Regras pós-fix:
  - Itaú casa apenas se >= 2 das ancoras: nome do banco, agência canônica,
    'Saldo Anterior', 'Extrato de Conta', 'itau.com.br'.
  - Santander casa apenas se >= 2 das ancoras: nome, cartão final 7342,
    'Fatura' ou 'Extrato', 'Cartão de Crédito', vencimento+pagamento mínimo,
    'Banco Santander'.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas

from src.utils.file_detector import _detectar_pdf


def _pdf_com_linhas(arq: Path, linhas: list[str]) -> None:
    """Gera PDF mínimo com as linhas fornecidas (uma por linha vertical)."""
    c = canvas.Canvas(str(arq))
    y = 800
    for linha in linhas:
        c.drawString(50, y, linha)
        y -= 14
    c.showPage()
    c.save()


# ============================================================================
# Itaú: extrato real casa, holerite/recibo NÃO casa
# ============================================================================


def test_extrato_itau_real_com_multiplas_ancoras_casa(tmp_path: Path):
    """Extrato Itaú real tem 4+ âncoras: nome, agência, Saldo Anterior, Extrato."""
    arq = tmp_path / "itau_extrato_real.pdf"
    _pdf_com_linhas(
        arq,
        [
            "ITAÚ UNIBANCO S.A.",
            "Agência: 6450 Conta: 12345-6",
            "EXTRATO DE CONTA CORRENTE",
            "SALDO ANTERIOR  100,00",
            "Período: 01/04/2026 a 30/04/2026",
            "Movimentação:",
        ],
    )
    deteccao = _detectar_pdf(arq)
    assert deteccao is not None
    assert deteccao.banco == "itau"
    assert deteccao.tipo == "cc"


def test_holerite_com_mencao_itau_no_rodape_nao_casa(tmp_path: Path):
    """Holerite que apenas menciona 'ITAU UNIBANCO' no rodapé (1 ancora) NÃO casa.

    Cenário real do bug: G4F holerite mencionava 'Conta credito: ITAU UNIBANCO
    agencia 6450' e o detector legado casava como bancario_itau_cc.
    Após Sprint 90a-1, isso retorna None (delega ao classifier YAML).
    """
    arq = tmp_path / "holerite_g4f_itau_rodape.pdf"
    _pdf_com_linhas(
        arq,
        [
            "G4F SOLUCOES CORPORATIVAS LTDA",
            "Demonstrativo de Pagamento de Salario",
            "Competencia: 04/2026",
            "Vencimentos: 5000,00",
            "Liquido: 4200,00",
            "Conta credito: ITAU UNIBANCO",
            "agencia: 6450",
        ],
    )
    deteccao = _detectar_pdf(arq)
    # Tem 'agência: 6450' (formato exato exigido pelo detector eh com til em
    # 'agência:'). Sem o nome 'ITAÚ UNIBANCO' (so 'ITAU' sem til), o detector
    # tem no máximo 1 âncora -- não deve casar.
    assert deteccao is None or deteccao.banco != "itau", (
        f"holerite com mencao Itau no rodape não deveria casar como extrato; "
        f"deteccao={deteccao}"
    )


def test_recibo_ted_itau_nao_casa(tmp_path: Path):
    """Recibo simples 'Transferência via Itaú UNIBANCO' (1 ancora apenas) NÃO casa."""
    arq = tmp_path / "recibo_ted_itau.pdf"
    _pdf_com_linhas(
        arq,
        [
            "Recibo de Transferencia",
            "Origem: ITAÚ UNIBANCO",
            "Destino: outro banco",
            "Valor: 1000,00",
        ],
    )
    deteccao = _detectar_pdf(arq)
    assert deteccao is None, (
        f"Recibo TED com so o nome do banco não deveria casar como extrato; "
        f"deteccao={deteccao}"
    )


# ============================================================================
# Santander: fatura real casa, holerite NÃO casa
# ============================================================================


def test_fatura_santander_real_com_multiplas_ancoras_casa(tmp_path: Path):
    """Fatura Santander real tem 3+ âncoras: nome, cartão 7342, Fatura, vencimento."""
    arq = tmp_path / "santander_fatura_real.pdf"
    _pdf_com_linhas(
        arq,
        [
            "BANCO SANTANDER",
            "FATURA DO CARTÃO DE CRÉDITO",
            "Cartão Black Way Elite",
            "Final: 4220 XXXX XXXX 7342",
            "Vencimento: 15/04/2026",
            "PAGAMENTO MÍNIMO: 100,00",
        ],
    )
    deteccao = _detectar_pdf(arq)
    assert deteccao is not None
    assert deteccao.banco == "santander"


def test_holerite_com_mencao_santander_no_rodape_nao_casa(tmp_path: Path):
    """Holerite que menciona 'SANTANDER' no rodapé (1 ancora apenas) NÃO casa.

    Cenário real do bug: 10 holerites G4F caíam em santander_cartao porque
    mencionavam 'Conta para credito: SANTANDER' sem nenhuma outra âncora de
    fatura.
    """
    arq = tmp_path / "holerite_g4f_santander_rodape.pdf"
    _pdf_com_linhas(
        arq,
        [
            "G4F SOLUCOES CORPORATIVAS LTDA",
            "Demonstrativo de Pagamento de Salario",
            "Competencia: 04/2026",
            "Vencimentos: 5000,00",
            "Liquido a Receber: 4200,00",
            "Conta para credito: SANTANDER",
            "Agencia: 1234 Conta: 56789-0",
        ],
    )
    deteccao = _detectar_pdf(arq)
    assert deteccao is None or deteccao.banco != "santander", (
        f"holerite com mencao Santander no rodape não deveria casar como fatura; "
        f"deteccao={deteccao}"
    )


def test_pdf_so_com_nome_santander_nao_casa(tmp_path: Path):
    """PDF arbitrário com apenas o nome SANTANDER (sem outras âncoras) NÃO casa.

    Texto neutro: sem 'fatura', 'extrato', 'vencimento', 'pagamento mínimo'
    -- garante que 'SANTANDER' sozinho como 1 ancora não casa como fatura.
    """
    arq = tmp_path / "doc_qualquer.pdf"
    _pdf_com_linhas(
        arq,
        [
            "DOCUMENTO COMERCIAL DIVERSO",
            "Mencao: SANTANDER",
            "Texto livre sem palavras-chave de cobranca.",
        ],
    )
    deteccao = _detectar_pdf(arq)
    assert deteccao is None, (
        f"unica ancora SANTANDER (sem outras palavras-chave) não deveria casar; "
        f"deteccao={deteccao}"
    )


# "A causa raiz é mais durável que o sintoma; defenda-a primeiro." -- Marco Aurélio
