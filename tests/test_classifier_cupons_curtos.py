"""Testes da regra OCR-curto do classifier para cupons fiscais fotografados.

Sprint 96 -- NF de cartão fotografada em estabelecimento genérico (sem âncoras
"CUPOM FISCAL"/"DANFE"/"NFC-E") deve casar `cupom_fiscal_foto` quando o OCR
extrai CNPJ + valor R$ + marcador (Nota Fiscal/cartão/débito/cupom).

Fixtures sintéticas reproduzem cenários reais observados em `inbox/1.jpeg`
(R$ 254,51, débito, shopping setor comercial sul) e variações adversárias.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import classifier as clf

# ============================================================================
# Fixtures de texto-âncora
# ============================================================================

# Cupom curto típico: CNPJ + valor + cartão débito + "Nota Fiscal".
# OCR ~400 chars, sem "CUPOM FISCAL" ou "DANFE" -- só casaria pela regra
# OCR-curto da Sprint 96.
PREVIEW_CUPOM_CURTO_OK = """\
ty 66.825.498/0004-70
Nota Fiscal
shopping - Setor Comercial Sul, Quadra 08
Sala 240 - Brasilia - DF
Valor it fe 254,51
FORMA PAGAMENTO     VALOR PAGO
Cartao Debito       254,51
TBPT
USO E SENHA PESSOAL
Documento N/A IDENTIFICADO
Data Serie 203
Protocolo 002 259260227200
"""

# Cupom curto SEM CNPJ: deve cair em _classificar (rejeitado pela regra
# OCR-curto, sem âncora forte para casar regex_conteudo plano).
PREVIEW_CUPOM_SEM_CNPJ = """\
Nota Fiscal
Estabelecimento Generico LTDA
Sala 240 - Brasilia - DF
Valor 254,51
FORMA PAGAMENTO     VALOR PAGO
Cartao Debito       254,51
USO E SENHA PESSOAL
Data Serie 203
"""

# Cupom longo com âncora forte ("CUPOM FISCAL"): casa pela regra clássica
# `regex_conteudo`. Regression test -- OCR-curto não deve "roubar" o match.
PREVIEW_CUPOM_LONGO_REGRESSION = """\
SUPERMERCADO ABC LTDA
CNPJ: 12.345.678/0001-90
Endereco: Av Brasilia 100, Brasilia - DF
EXTRATO CFe SAT
CUPOM FISCAL ELETRONICO - SAT
Item Cod Desc Qtde UN Vl Unit Vl Total
1 7891234567890 ARROZ TIPO 1 5KG 1 UN 24,90 24,90
2 7891234567891 OLEO SOJA 900ML 2 UN 8,50 17,00
3 7891234567892 LEITE INTEGRAL 1L 6 UN 5,90 35,40
4 7891234567893 PAO FORMA 500G 1 UN 7,80 7,80
Tributos: R$ 8,30 (Lei 12741/12)
Total Bruto: R$ 85,10
Desconto: R$ 0,00
Total a Pagar: R$ 85,10
Forma Pagamento: Cartao Credito
Consumidor n/identificado
Protocolo: 35200612345678901234567890123456789012345678
""" + ("Linha extra de regression " * 30)

# JPEG aleatório sem texto significativo (OCR ruído): rejeitado.
PREVIEW_JPEG_RUIDO = """\
mn lk pq r s t v
abc 123 xyz
test test test
foto qualquer sem documento
"""

# PNG legivel mas sem CNPJ ou valor R$: rejeitado.
# Tem "Nota Fiscal" como pista mas falta CNPJ formatado E valor monetario.
PREVIEW_PNG_SEM_MARCADORES = """\
Nota Fiscal de Servico
Estabelecimento sem identificacao
Endereco: Asa Norte
Linha Brasilia DF
Sem identificador formal
Cartao apresentado
"""


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture
def arquivo_temp(tmp_path: Path):
    """Devolve factory que cria JPEG/PNG falso com bytes mínimos."""

    def _factory(nome: str = "cupom.jpeg", conteudo: bytes = b"\xff\xd8\xff\xe0fake") -> Path:
        caminho = tmp_path / nome
        caminho.write_bytes(conteudo)
        return caminho

    return _factory


@pytest.fixture(autouse=True)
def reset_cache():
    """Recarrega o YAML antes de cada teste para evitar contaminação."""
    clf.recarregar_tipos()
    yield


# ============================================================================
# Casos de aceitação (5 cenários do acceptance criteria)
# ============================================================================


def test_cupom_curto_ok_casa_ocr_curto(arquivo_temp):
    """Cenario 1: CNPJ + valor + 'Nota Fiscal' + cartao -> casa OCR-curto."""
    caminho = arquivo_temp("cupom_curto.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", PREVIEW_CUPOM_CURTO_OK)
    assert decisao.tipo == "cupom_fiscal_foto"
    assert decisao.match_submodo == "ocr_curto"
    assert decisao.motivo_fallback is None


def test_cupom_curto_sem_cnpj_rejeitado(arquivo_temp):
    """Cenario 2: sem CNPJ formatado -> requer_todos falha -> _classificar."""
    caminho = arquivo_temp("cupom_sem_cnpj.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", PREVIEW_CUPOM_SEM_CNPJ)
    assert decisao.tipo is None
    assert decisao.match_submodo is None
    assert "_classificar" in str(decisao.pasta_destino)


def test_cupom_longo_com_cupom_fiscal_regression(arquivo_temp):
    """Cenario 3: 'CUPOM FISCAL' explicito -> casa regex_conteudo plano (regression)."""
    caminho = arquivo_temp("cupom_longo.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", PREVIEW_CUPOM_LONGO_REGRESSION)
    assert decisao.tipo == "cupom_fiscal_foto"
    # Submodo None significa que casou pelo regex_conteudo plano, não subregra.
    assert decisao.match_submodo is None


def test_jpeg_aleatoria_sem_texto_rejeitado(arquivo_temp):
    """Cenario 4: OCR ruido sem ancoras -> _classificar."""
    caminho = arquivo_temp("ruido.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", PREVIEW_JPEG_RUIDO)
    assert decisao.tipo is None
    assert decisao.match_submodo is None


def test_png_legivel_sem_cnpj_e_sem_valor_rejeitado(arquivo_temp):
    """Cenario 5: PNG legivel mas sem CNPJ e sem R$/valor -> _classificar."""
    caminho = arquivo_temp("png_sem_marcadores.png")
    decisao = clf.classificar(caminho, "image/png", PREVIEW_PNG_SEM_MARCADORES)
    assert decisao.tipo is None
    assert decisao.match_submodo is None


# ============================================================================
# Casos adicionais de borda (mais robustez no OCR-curto)
# ============================================================================


def test_cnpj_com_virgula_no_lugar_de_ponto_aceito(arquivo_temp):
    """OCR insere virgula no agrupamento de milhar do CNPJ. Caso real do 1.jpeg.

    Texto plausivel reproduz o OCR do shopping setor comercial sul (~530 chars,
    com lixo OCR e formato adverso de CNPJ). Tem que casar a subregra ocr_curto.
    """
    texto = (
        "ty 66,825. 498/0004-70 x\n"
        ") ae, Hy i i k SELO NESTE\n"
        "E : gu de; DE (E soa\n"
        "ai Ht 'a Nota Fiscal dp\n"
        "a uns! doi etree 7 l\n"
        "do DIO FOU G08 006 06657 ap CIA 9\n"
        "oa RICD nose TM\n"
        "Doses\n"
        "Valor it fe 254,51\n"
        "FORMA PAGAMENTO     VALOR PAGO\n"
        "Cartao Debito 254,51\n"
        "TBPT\n"
        "shopping - Setor Comercial Sul, Quadra 08\n"
        "Sala 240 - Brasilia - DF\n"
        "525.495 /0004-70\n"
        "id: 1 AUT 402500 pc: 042g\n"
        "On6b7T762, AAs ad\n"
        "DA USO E SENHA PESSOAL\n"
        "MAO IDENTIFICADO\n"
        "Dido Serie 203\n"
        "ocolo desing 002 259260227200\n"
    )
    assert 200 <= len(texto) <= 900
    caminho = arquivo_temp("real_1jpeg.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", texto)
    assert decisao.tipo == "cupom_fiscal_foto"
    assert decisao.match_submodo == "ocr_curto"


def test_ocr_acima_do_limite_nao_casa_subregra(arquivo_temp):
    """OCR > 900 chars: subregra ocr_curto não dispara. Sem outras âncoras, rejeita."""
    texto_base = (
        "ty 66.825.498/0004-70\n"
        "Nota Fiscal\n"
        "Valor 254,51\n"
        "Cartao Debito 254,51\n"
    )
    # Inflar texto para passar de 900 chars sem inserir marcadores fortes.
    texto = texto_base + ("\nlinha de ruido textual extra " * 40)
    assert len(texto) > 900
    caminho = arquivo_temp("ocr_grande.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", texto)
    # Sem "CUPOM FISCAL"/"Tributos|Consumidor"/EAN, e fora da janela ocr_curto,
    # deve cair em _classificar.
    assert decisao.tipo is None


def test_ocr_abaixo_do_minimo_nao_casa_subregra(arquivo_temp):
    """OCR < 200 chars: subregra ocr_curto não dispara mesmo com CNPJ + valor."""
    texto = (
        "66.825.498/0004-70\n"
        "Nota Fiscal\n"
        "Valor 254,51\n"
        "Cartao\n"
    )
    assert len(texto) < 200
    caminho = arquivo_temp("ocr_pequeno.jpeg")
    decisao = clf.classificar(caminho, "image/jpeg", texto)
    assert decisao.tipo is None


def test_subregra_preserva_pasta_destino_e_nome(arquivo_temp):
    """Quando OCR-curto casa, pasta_destino e nome_canonico saem do YAML normal."""
    caminho = arquivo_temp("verificacao.jpeg")
    decisao = clf.classificar(
        caminho, "image/jpeg", PREVIEW_CUPOM_CURTO_OK, pessoa="andre"
    )
    assert "nfs_fiscais/cupom_foto" in str(decisao.pasta_destino).replace("\\", "/")
    assert "andre" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("CUPOM_")
    assert decisao.nome_canonico.endswith(".jpeg")


# "Uma foto de cupom vale tanto quanto um DANFE formal." -- princípio do match-pelo-conteúdo
