"""Testes do src.intake.glyph_tolerant.

Fixtures reproduzem trechos REAIS extraídos via pdfplumber do
`inbox/pdf_notas.pdf` (cupom de garantia Americanas com fonte ToUnicode
quebrada). Manter os textos exatamente como saem do `extract_text()` --
qualquer "limpeza" estética anula o teste.
"""

from __future__ import annotations

import re

import pytest

from src.intake.glyph_tolerant import (
    GLYPH_J,
    GLYPH_S_MAIUSCULO,
    casa_padroes,
    compilar_regex_tolerante,
    extrair_chave_nfe44,
    extrair_cnpj,
    extrair_cnpjs,
    extrair_cpf,
    extrair_data_br,
    normalizar_ps5_p55,
)

# ============================================================================
# Fixtures: trechos reais com glyphs corrompidos
# ============================================================================

TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO = """\
americanas sa - 0337 CNP): 00.776.574/0160-79
SCC, LTS 01 05 E D6, PISO TERREO LJS 01 E 02 MODE ESLO1 - GAMA
- BRASILIA
19/04/2026 17:06 | NSU TEF: 0304000022973 | NumCupom: 86
CUPOM DE SERVIÇO - VIA DO CLIENTE
CUPOM BILHETE DE SEGURO
SEGURO DE GARANTIA ESTENDIDA ORIGINAL
Processo SUSEP No. 15414 .900147/2014-11
DADOS DO SEGURADO
NOME:
NOME SOCIAL.
CPF: 051.273.731-22
DADOS DA SEGURADORA
Razão Social: MAPFRE Seguros Gerais 5.A.
CNP): 61.074.175/0001-38 Cod SUSEP: 06238
Q BILHETE DE SEGURO PODE SER
"""

TEXTO_CPF_COM_ESPACO = "CPF: 051.273. 731-22"  # variante glyph (espaço extra)
TEXTO_CPF_OUTRA_VARIANTE = "CPF: 051.273.2731-22"  # dígito a mais por glyph (não normalizamos)

TEXTO_NFCE_AMERICANAS = """\
CNPJ: 00.776.574/0160-79  americanas sa - 0337
SCC, LTS 01 05 E D6, PISO TERREO LJS 01 E 02 MODE E SL 01
GAMA - BRASILIA - DF
Documento Auxiliar da Nota Fiscal de Consumidor Eletronica
NFCe nº 43280 Serie 304 19/04/2026 17:12:10
Consulte pela chave de acesso em
www.fazenda.df.gov.br/nfce/consulta
5326 0400 7765 7401 8079 6530 4000 0432 8010 5868 2510
"""


# ============================================================================
# Constantes nomeadas
# ============================================================================


def test_glyph_j_aceita_parentese_e_letra():
    padrao = re.compile("CNP" + GLYPH_J)
    assert padrao.search("CNPJ:")
    assert padrao.search("CNP):")
    assert not padrao.search("CNPK")  # K não está na classe


def test_glyph_s_maiusculo_aceita_5():
    padrao = re.compile(GLYPH_S_MAIUSCULO + r"\.A\.")
    assert padrao.search("S.A.")
    assert padrao.search("5.A.")  # como aparece na razão social MAPFRE no PDF


# ============================================================================
# casa_padroes
# ============================================================================


def test_casa_padroes_modo_any_basta_um():
    padroes = ["INEXISTENTE", "CUPOM BILHETE"]
    assert casa_padroes(padroes, TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO, modo="any")


def test_casa_padroes_modo_all_exige_todos():
    padroes = ["CUPOM BILHETE", "GARANTIA ESTENDIDA", "Processo " + GLYPH_S_MAIUSCULO + "USEP"]
    assert casa_padroes(padroes, TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO, modo="all")


def test_casa_padroes_modo_all_falha_se_um_nao_casa():
    padroes = ["CUPOM BILHETE", "INEXISTENTE_NESSE_TEXTO"]
    assert not casa_padroes(padroes, TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO, modo="all")


def test_casa_padroes_aceita_pattern_compilado_e_string_misturados():
    pre = compilar_regex_tolerante(r"CUPOM\s+BILHETE")
    padroes = [pre, "GARANTIA ESTENDIDA"]
    assert casa_padroes(padroes, TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO, modo="all")


def test_casa_padroes_modo_invalido_levanta():
    with pytest.raises(ValueError, match="modo inválido"):
        casa_padroes(["x"], "y", modo="maybe")  # type: ignore[arg-type]


# ============================================================================
# extrair_cnpj
# ============================================================================


def test_extrair_cnpj_do_cupom_garantia_glyph_quebrado():
    # Trecho tem 2 CNPJs (varejo + seguradora), ambos com rótulo "CNP)" quebrado.
    # extrair_cnpj devolve o PRIMEIRO encontrado (varejo, no topo).
    cnpj = extrair_cnpj(TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO)
    assert cnpj == "00.776.574/0160-79"


def test_extrair_cnpj_do_nfce_normal():
    cnpj = extrair_cnpj(TEXTO_NFCE_AMERICANAS)
    assert cnpj == "00.776.574/0160-79"


def test_extrair_cnpj_solto_sem_rotulo():
    cnpj = extrair_cnpj("Empresa qualquer 12.345.678/0001-90 mais texto")
    assert cnpj == "12.345.678/0001-90"


def test_extrair_cnpj_devolve_none_quando_ausente():
    assert extrair_cnpj("texto sem CNPJ algum") is None


# ============================================================================
# extrair_cnpjs (plural)
# ============================================================================


def test_extrair_cnpjs_devolve_dois_em_cupom_garantia():
    cnpjs = extrair_cnpjs(TEXTO_CUPOM_GARANTIA_GLYPH_QUEBRADO)
    assert cnpjs == ["00.776.574/0160-79", "61.074.175/0001-38"]


def test_extrair_cnpjs_deduplica_quando_mesmo_cnpj_aparece_duas_vezes():
    texto = "CNPJ: 12.345.678/0001-90 e mais tarde 12.345.678/0001-90 de novo"
    assert extrair_cnpjs(texto) == ["12.345.678/0001-90"]


def test_extrair_cnpjs_devolve_lista_vazia_quando_ausente():
    assert extrair_cnpjs("documento sem CNPJ") == []


# ============================================================================
# compilar_regex_tolerante (comportamento MULTILINE)
# ============================================================================


def test_compilar_regex_multiline_caret_casa_inicio_de_linha():
    # Com MULTILINE (default), ^ casa início de QUALQUER linha, não só do texto
    padrao = compilar_regex_tolerante(r"^DANFE")
    texto = "Algo no topo\nDANFE -- Documento Auxiliar..."
    assert padrao.search(texto) is not None


def test_compilar_regex_ignorecase_default():
    padrao = compilar_regex_tolerante(r"danfe")
    assert padrao.search("DANFE no topo") is not None


# ============================================================================
# extrair_cpf
# ============================================================================


def test_extrair_cpf_normal():
    assert extrair_cpf("CPF: 051.273.731-22") == "051.273.731-22"


def test_extrair_cpf_com_espaco_glyph_quebrado():
    # No pdf_notas.pgs 1-2 aparece "051.273. 731-22" (espaço inserido).
    assert extrair_cpf(TEXTO_CPF_COM_ESPACO) == "051.273.731-22"


def test_extrair_cpf_devolve_none_quando_ausente():
    assert extrair_cpf("documento sem CPF") is None


# ============================================================================
# extrair_data_br
# ============================================================================


def test_extrair_data_br_devolve_iso():
    assert extrair_data_br("19/04/2026 17:06") == "2026-04-19"


def test_extrair_data_br_pega_primeira_plausivel():
    texto = "Algo com 99/99/9999 inválido e depois 19/04/2026 válido"
    assert extrair_data_br(texto) == "2026-04-19"


def test_extrair_data_br_devolve_none_quando_invalida_unica():
    assert extrair_data_br("99/99/9999 só essa") is None


def test_extrair_data_br_devolve_none_quando_ausente():
    assert extrair_data_br("texto sem data") is None


# ============================================================================
# extrair_chave_nfe44
# ============================================================================


def test_extrair_chave_44_do_nfce_americanas():
    chave = extrair_chave_nfe44(TEXTO_NFCE_AMERICANAS)
    # Texto traz "5326 0400 7765 7401 8079 6530 4000 0432 8010 5868 2510"
    assert chave == "53260400776574018079653040000432801058682510"
    assert len(chave) == 44


def test_extrair_chave_44_devolve_none_quando_ausente():
    assert extrair_chave_nfe44("documento sem chave NFe") is None


def test_extrair_chave_44_ignora_grupos_de_4_que_nao_somam_44():
    # 10 grupos de 4 dígitos = 40, regex pede exatamente 11 grupos de 4
    texto_curto = "1234 5678 9012 3456 7890 1234 5678 9012 3456 7890"
    assert extrair_chave_nfe44(texto_curto) is None


# ============================================================================
# normalizar_ps5_p55 (Sprint INFRA-NFCE-FIX-PS5-P55 -- bug 2026-05-12)
# ============================================================================


def test_normalizar_ps5_p55_corrige_base_carregamento():
    # Bug real: cupom NFCe Americanas trouxe "CONTROLE P55" via pdfplumber.
    entrada = "BASE DE CARREGAMENTO DO CONTROLE P55"
    assert normalizar_ps5_p55(entrada) == "BASE DE CARREGAMENTO DO CONTROLE PS5"


def test_normalizar_ps5_p55_preserva_controle_ps5_correto():
    # Item que já veio correto não pode ser tocado (idempotência).
    entrada = "CONTROLE PS5 DUALSENSE GALACTIC PURPLE"
    assert normalizar_ps5_p55(entrada) == entrada


def test_normalizar_ps5_p55_nao_afeta_produto_nao_relacionado():
    # "P55" sem contexto PlayStation deve ficar como veio (poderia ser
    # bateria P55, parafuso P55, etc.).
    entrada = "BATERIA P55 INDUSTRIAL 12V"
    assert normalizar_ps5_p55(entrada) == entrada


def test_normalizar_ps5_p55_corrige_com_dualsense_no_contexto():
    # Contexto DUALSENSE na mesma linha (janela 40 chars) prova PS5.
    entrada = "CARREGADOR P55 PARA DUALSENSE BRANCO"
    assert normalizar_ps5_p55(entrada) == "CARREGADOR PS5 PARA DUALSENSE BRANCO"


def test_normalizar_ps5_p55_corrige_com_playstation_no_contexto():
    entrada = "JOGO P55 PLAYSTATION DIGITAL"
    assert normalizar_ps5_p55(entrada) == "JOGO PS5 PLAYSTATION DIGITAL"


def test_normalizar_ps5_p55_idempotente():
    # Rodar duas vezes não gera "PSS5" nem corrompe a string.
    entrada = "CONTROLE P55 DUALSENSE"
    saida_1 = normalizar_ps5_p55(entrada)
    saida_2 = normalizar_ps5_p55(saida_1)
    assert saida_1 == saida_2 == "CONTROLE PS5 DUALSENSE"


def test_normalizar_ps5_p55_nao_atravessa_quebra_de_linha():
    # P55 em uma linha, CONTROLE em outra -- não normaliza (linhas distintas).
    entrada = "BATERIA P55\nCONTROLE PARA TV"
    assert normalizar_ps5_p55(entrada) == entrada


def test_normalizar_ps5_p55_texto_vazio_ou_sem_p55():
    assert normalizar_ps5_p55("") == ""
    assert normalizar_ps5_p55("texto qualquer sem token") == "texto qualquer sem token"


# "Quem mede com vara torta ergue parede torta." -- ditado popular brasileiro
