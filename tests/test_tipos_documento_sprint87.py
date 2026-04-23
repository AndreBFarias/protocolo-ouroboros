"""Testes da Sprint 87.4 -- regras documentais novas em tipos_documento.yaml.

Acrescenta 3 tipos `especifico` que antes caíam em skip_nao_identificado do
adapter do vault (Sprint 70):

- irpf_parcela      : DARF de parcelamento IRPF
- das_mei           : DAS do Simples Nacional MEI
- comprovante_cpf   : Comprovante de Situação Cadastral CPF (Receita)

Cada teste cria um arquivo PDF fictício em tmp_path e chama
`src.intake.classifier.classificar` com um preview textual que casa as
âncoras regex da regra correspondente. Validamos:

  1. decisao.tipo == id esperado
  2. decisao.prioridade == "especifico"
  3. pasta_destino cai no template declarado
  4. não há colisão com `boleto_servico` (regra normal com `Linha digitável`)

Referência canônica: `mappings/tipos_documento.yaml` atualizado nesta sprint.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import classifier as clf


@pytest.fixture
def arquivo_temp(tmp_path: Path):
    """Factory que cria PDF fictício -- só precisamos de bytes reais para SHA8."""

    def _factory(nome: str = "doc.pdf", conteudo: bytes = b"%PDF-1.4 fake") -> Path:
        caminho = tmp_path / nome
        caminho.write_bytes(conteudo)
        return caminho

    return _factory


@pytest.fixture(autouse=True)
def reset_cache():
    """Garante que o YAML de produção é recarregado antes de cada teste."""
    clf.recarregar_tipos()
    yield


# ============================================================================
# Previews textuais sintéticos -- refletem conteúdo real dos PDFs legados
# ============================================================================

PREVIEW_IRPF_PARCELA = """\
Documento de Arrecadação de Receitas Federais
DARF
Ministério da Fazenda -- Secretaria da Receita Federal do Brasil
Período de Apuração: 12/2024
Data de Vencimento: 30/04/2026
Código da Receita: 2904 -- IRPF -- QUOTAS
3ª PARCELA
Valor total do documento: R$ 456,78
"""

PREVIEW_DAS_MEI = """\
Documento de Arrecadação
do Simples Nacional
CNPJ: 52.488.753/0001-00
DAS de MEI (Versão: 2.0.0)
Período de Apuração: 03/2026
Vencimento: 20/04/2026
Valor Total: R$ 71,40
Linha digitável: 85850000000-0 71408562026-7 04205032026-3 10123456789-0
"""

PREVIEW_COMPROVANTE_CPF = """\
Receita Federal do Brasil
Comprovante de Situação Cadastral no CPF
Nome: ANDRÉ FARIAS
CPF: 051.273.731-22
Data de Nascimento: 10/01/1990
Situação Cadastral: REGULAR
Data da inscrição: 15/03/2005
"""


# ============================================================================
# Previews Sprint 88 -- volume real do inbox/
# ============================================================================

PREVIEW_DAS_PARCSN = """\
Documento de Arrecadação
do Simples Nacional
CNPJ Razão Social
45.850.636/0001-60 ANDRE DA SILVA BATISTA DE FARIAS
Período de Apuração Data de Vencimento Número do Documento Pagar este documento até
Agosto/2025 29/08/2025 07.18.25233.7376200-4
Observações
DAS de PARCSN (Versão: 2.0.0)
Valor Total do Documento
Número do Parcelamento: 1
338,48
Parcela: 10/25
"""

PREVIEW_CERTIDAO_RECEITA = """\
MINISTÉRIO DA FAZENDA Por meio do e-CAC
SECRETARIA ESPECIAL DA RECEITA FEDERAL DO BRASIL
PROCURADORIA-GERAL DA FAZENDA NACIONAL
INFORMAÇÕES DE APOIO PARA EMISSÃO DE CERTIDÃO
CNPJ: 45.850.636/0001-60 - ANDRE DA SILVA BATISTA DE FARIAS
Dados Cadastrais da Matriz
Natureza Jurídica: 213-5 - EMPRESARIO (INDIVIDUAL)
"""

PREVIEW_EXTRATO_C6_PDF = """\
Extrato exportado no dia 21 de abril de 2026 às 15:35
ANDRE DA SILVA BATISTA DE FARIAS 051.273.731-22
Agência: 1 Conta: 182795446
Extrato Período 21 de abril de 2025 até 21 de abril de 2026
Saldo do dia 21 de abril de 2026 R$ 2.846,82
24/04 Pagamento PGTO FAT CARTAO C6 -R$ 132,61
28/04 Entradas CDB C6 LIM. GARANT. R$ 10,74
"""

PREVIEW_CUPOM_WHATSAPP_OCR = """\
LM CU LOTE 04 DAE 08 SNL OM
Documento fue ii da Mota isca re
enstnbóue Etrinios
Tributos
7896006555017 ARNO TPI
7896102115712 IOGURTE POTE
SNCOLA MENU DF 59180
Total de tam
"""


# ============================================================================
# Testes (um por tipo novo)
# ============================================================================


def test_classifica_irpf_parcela_como_especifico(arquivo_temp):
    arq = arquivo_temp("parcela_irpf.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_IRPF_PARCELA, pessoa="andre")
    assert decisao.tipo == "irpf_parcela"
    assert decisao.prioridade == "especifico"
    assert decisao.match_mode == "all"
    assert "impostos/irpf_parcelas" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("IRPF_PARCELA_")
    # A presença de 'Linha digitável' em DARFs não pode fazer cair em boleto_servico
    assert decisao.tipo != "boleto_servico"


def test_classifica_das_mei_como_especifico(arquivo_temp):
    arq = arquivo_temp("das_mei.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DAS_MEI, pessoa="andre")
    assert decisao.tipo == "das_mei"
    assert decisao.prioridade == "especifico"
    assert decisao.match_mode == "all"
    assert "impostos/das" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("DAS_")
    # DAS também tem linha digitável -- precisa vir antes de boleto_servico
    assert decisao.tipo != "boleto_servico"


def test_classifica_comprovante_cpf_como_especifico(arquivo_temp):
    arq = arquivo_temp("cpf_cadastral.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_COMPROVANTE_CPF, pessoa="andre")
    assert decisao.tipo == "comprovante_cpf"
    assert decisao.prioridade == "especifico"
    assert decisao.match_mode == "all"
    assert "documentos_pessoais" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("CPF_CAD_")


# ============================================================================
# Testes Sprint 88 -- regras calibradas em volume real do inbox/
# ============================================================================


def test_classifica_das_parcsn_texto_real(arquivo_temp):
    """Sprint 88: DAS do parcelamento do Simples Nacional (MEI desativado)."""
    arq = arquivo_temp("10a_parcela.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DAS_PARCSN, pessoa="andre")
    assert decisao.tipo == "das_parcsn"
    assert decisao.prioridade == "especifico"
    assert "impostos/das_parcsn" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("DAS_PARCSN_")


def test_das_parcsn_nao_cai_em_das_mei(arquivo_temp):
    """Regression: PARCSN tem 'DAS de PARCSN' que NÃO deve casar 'DAS de MEI'."""
    arq = arquivo_temp("parcsn.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DAS_PARCSN, pessoa="andre")
    assert decisao.tipo != "das_mei"
    assert decisao.tipo != "irpf_parcela"


def test_das_mei_ativo_nao_cai_em_parcsn(arquivo_temp):
    """Regression: MEI ativo tem 'DAS de MEI' que NÃO deve casar 'PARCSN'."""
    arq = arquivo_temp("das_mei.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DAS_MEI, pessoa="vitoria")
    assert decisao.tipo == "das_mei"
    assert decisao.tipo != "das_parcsn"


def test_classifica_certidao_receita_cnpj(arquivo_temp):
    """Sprint 88: Informações de apoio para emissão de certidão (Receita + PGFN)."""
    arq = arquivo_temp("certidao.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_CERTIDAO_RECEITA, pessoa="andre")
    assert decisao.tipo == "certidao_receita_cnpj"
    assert decisao.prioridade == "especifico"
    assert "certidoes_receita" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("CERT_RF_")


def test_classifica_extrato_c6_pdf(arquivo_temp):
    """Sprint 88: extrato C6 em PDF (distinto do extrator CSV/XLS)."""
    arq = arquivo_temp("extrato_c6.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_EXTRATO_C6_PDF, pessoa="andre")
    assert decisao.tipo == "extrato_c6_pdf"
    assert decisao.prioridade == "especifico"
    assert "c6_cc" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("EXTRATO_C6_")


def test_cupom_fiscal_foto_aceita_ocr_sujo_com_ean(arquivo_temp):
    """Sprint 88: OCR de WhatsApp photo é sujo; códigos EAN 78\\d{11,12} são âncora forte."""
    arq = arquivo_temp("cupom.jpeg")
    decisao = clf.classificar(arq, "image/jpeg", PREVIEW_CUPOM_WHATSAPP_OCR, pessoa="casal")
    assert decisao.tipo == "cupom_fiscal_foto"
    assert decisao.prioridade == "fallback"


# "Quem classifica corretamente já resolveu metade do problema." -- princípio do intake
