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
DAS - Documento de Arrecadação do Simples Nacional
Período de Apuração: 03/2026
CNPJ: 12.345.678/0001-00
Simples Nacional -- Microempreendedor Individual (MEI)
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


# "Quem classifica corretamente já resolveu metade do problema." -- princípio do intake
