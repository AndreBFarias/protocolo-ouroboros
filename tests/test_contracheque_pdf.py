"""Testes dos parsers de contracheque G4F e Infobase.

Usa texto sintético que imita o output de pdfplumber/tesseract, permitindo
testar a lógica de parsing sem depender de PDFs reais (dados privados).
"""

import json
from pathlib import Path

from src.extractors.contracheque_pdf import (
    _extrair_bases_g4f,
    _extrair_bases_infobase,
    _ingerir_holerite_no_grafo,
    _parse_g4f,
    _parse_infobase,
)
from src.graph.db import GrafoDB

TEXTO_G4F_FOLHA = """Demonstrativo de Pagamento de Salário: 03/26 Seg: 721
Empresa: G4F SOLUCOES CORPORATIVAS
CNPJ: 07.094.346/0002-26 LTDA
Colaborador: ANDRE DA SILVA BATISTA DE FARIAS
Descrição Referência Descontos Proventos
+ Horas Normais 200.00 R$ 8.657,25
- IRRF 27.50 (R$ 1.200,29)
- INSS 14.00 (R$ 988,07)
- Desc.Vale Alimentação 22.00 (R$ 96,52)
Total (R$ 2.284,88) R$ 8.657,25
Valor líquido a receber: R$ 6.372,37
"""

TEXTO_G4F_13_ADTO = """Demonstrativo de Pagamento de Salário: 10/25 Seg: 639
Empresa: G4F SOLUCOES CORPORATIVAS
+ 13o Salário Adiantado 6.00 R$ 2.164,31
Total (R$ 0,00) R$ 2.164,31
Valor líquido a receber: R$ 2.164,31
"""

TEXTO_INFOBASE_FOLHA = """INFOBASE CONSULTORIA E INFORMATICA LTDA
CNPJ: 02.800.463/0001-63 CC: GERAL Folha Mensal
Mensalista Março de 2026
Código Descrição Referência Vencimentos Descontos
8781 DIAS NORMAIS 31,00 10.000,00
998 I.N.S.S. 9,88 988,07
999 IMPOSTO DE RENDA 27,50 1.569,55
Total de Vencimentos Total de Descontos
2.557,62
Valor Líquido 7.442,38
"""


def test_g4f_folha_mensal_extrai_todos_campos():
    resultado = _parse_g4f(TEXTO_G4F_FOLHA)
    assert resultado is not None
    assert resultado["mes_ref"] == "2026-03"
    assert resultado["fonte"] == "G4F"
    assert resultado["bruto"] == 8657.25
    assert resultado["inss"] == 988.07
    assert resultado["irrf"] == 1200.29
    assert resultado["vr_va"] == 96.52
    assert resultado["liquido"] == 6372.37


def test_g4f_13o_adiantamento_marca_tipo():
    resultado = _parse_g4f(TEXTO_G4F_13_ADTO)
    assert resultado is not None
    assert resultado["fonte"] == "G4F - 13º Adiantamento"
    assert resultado["bruto"] == 2164.31
    assert resultado["inss"] == 0.0
    assert resultado["liquido"] == 2164.31


def test_g4f_sem_referencia_retorna_none():
    resultado = _parse_g4f("Texto sem referência de mês")
    assert resultado is None


def test_infobase_folha_mensal_via_codigos():
    resultado = _parse_infobase(TEXTO_INFOBASE_FOLHA)
    assert resultado is not None
    assert resultado["mes_ref"] == "2026-03"
    assert resultado["fonte"] == "Infobase"
    assert resultado["bruto"] == 10000.00
    assert resultado["inss"] == 988.07
    assert resultado["irrf"] == 1569.55
    assert resultado["liquido"] == 7442.38


def test_infobase_liquido_por_subtracao_quando_nao_extraido():
    """Se 'Valor Líquido' não aparecer (OCR ruidoso), infere via bruto - descontos."""
    texto_sem_liquido = """INFOBASE CONSULTORIA
Mensalista Fevereiro de 2026
8781 DIAS NORMAIS 28,00 10.000,00
998 I.N.S.S. 9,88 988,07
999 IMPOSTO DE RENDA 27,50 1.569,55
"""
    resultado = _parse_infobase(texto_sem_liquido)
    assert resultado is not None
    # 10000 - 988.07 - 1569.55 = 7442.38
    assert abs(resultado["liquido"] - 7442.38) < 0.01


def test_infobase_mes_invalido_retorna_none():
    resultado = _parse_infobase("INFOBASE\nMensalista Abracadabra de 2026")
    assert resultado is None


# Sprint 95a: persistencia de 'liquido' separado de 'bruto' em metadata do grafo.


def _ler_metadata_holerite(grafo: GrafoDB, mes_ref: str) -> dict:
    """Helper: localiza node holerite pelo mes_ref e retorna metadata parseado."""
    chave = "HOLERITE|G4F|" + mes_ref
    chave = chave.replace(" ", "_")
    cur = grafo._conn.execute(
        "SELECT metadata FROM node WHERE tipo='documento' AND nome_canonico=?",
        (chave,),
    )
    row = cur.fetchone()
    assert row is not None, f"node holerite com chave {chave!r} não encontrado"
    return json.loads(row[0])


def test_sprint_95a_metadata_grafo_persiste_liquido_e_bruto(tmp_path: Path):
    """Sprint 95a: holerite ingerido no grafo deve ter metadata.liquido e .bruto.

    Antes da Sprint 95a o documento dict so gravava 'total' (= bruto), perdendo
    a info do liquido. Com a fix, o metadata persiste tanto bruto (como 'total'
    e 'bruto' por compat) quanto liquido como campo dedicado, permitindo o
    linker (Sprint 95) apertar diff_valor de 0.30 para 0.05.
    """
    registro = _parse_g4f(TEXTO_G4F_FOLHA)
    assert registro is not None
    assert registro["bruto"] == 8657.25
    assert registro["liquido"] == 6372.37

    grafo = GrafoDB(tmp_path / "g.sqlite")
    grafo.criar_schema()
    arquivo_falso = tmp_path / "holerite_g4f_marco.pdf"
    arquivo_falso.write_bytes(b"%PDF-1.4 stub")
    _ingerir_holerite_no_grafo(grafo, registro, arquivo_falso)

    meta = _ler_metadata_holerite(grafo, "2026-03")
    assert meta["tipo_documento"] == "holerite"
    assert meta["total"] == 8657.25  # compat: total = bruto
    assert meta["bruto"] == 8657.25
    assert meta["liquido"] == 6372.37


def test_sprint_95a_liquido_zero_quando_registro_sem_liquido(tmp_path: Path):
    """Quando registro não traz 'liquido', metadata.liquido = 0.0 (graceful)."""
    registro = {
        "mes_ref": "2026-04",
        "fonte": "G4F",
        "bruto": 5000.0,
        # 'liquido' ausente
    }
    grafo = GrafoDB(tmp_path / "g.sqlite")
    grafo.criar_schema()
    arquivo_falso = tmp_path / "holerite_sem_liquido.pdf"
    arquivo_falso.write_bytes(b"%PDF-1.4 stub")
    _ingerir_holerite_no_grafo(grafo, registro, arquivo_falso)

    meta = _ler_metadata_holerite(grafo, "2026-04")
    assert meta["bruto"] == 5000.0
    assert meta["liquido"] == 0.0


# Sprint INFRA-CONTRACHEQUE-EXTRAIR-BASES: extração de bases fiscais omitidas.

TEXTO_G4F_REAL_FEV2026 = """Demonstrativo de Pagamento de Salário: 02/26 Seg: 695
Empresa: G4F SOLUCOES CORPORATIVAS LTDA, CNPJ: 07.094.346/0002-26
Colaborador: ANDRE DA SILVA BATISTA DE FARIAS, Matrícula: 16769, CBO: 212405
Cargo: ANALISTA DE BUSINESS INTELLIGENCE
Data de admissão: 08/05/2025
Data de pagamento: 06/03/2026
Conta: Banco 33 - Santander S.A., Agência 2327, CC 71018701-1

Descrição Referência Descontos Proventos
+ Horas Normais 200,00 R$ 8.657,25
- IRRF 27,50 (R$ 1.200,29)
- INSS 14,00 (R$ 988,07)
- Desc.Vale Alimentação 20,00 (R$ 87,75)
Total (R$ 2.276,11) R$ 8.657,25
Valor líquido a receber: R$ 6.381,14

Nº de dependentes IR: 0, Nº dependentes Salário Família: 0
Salário base: R$ 8.657,25
Base de cálculo INSS: R$ 8.475,55
Base de cálculo IR: R$ 8.657,25
Base de cálculo FGTS: R$ 8.657,25
FGTS do mês: R$ 692,58
"""

TEXTO_INFOBASE_REAL_FEV2026 = """INFOBASE CONSULTORIA E INFORMATICA LTDA
CNPJ: 02.800.463/0001-63, CC: GERAL, Folha Mensal
Mensalista Fevereiro de 2026
440 ANDRE DA SILVA BATISTA DE FARIAS (CBO 212410)
Cargo: ANALISTA DE DADOS, Admissão: 02/06/2025

Vencimentos:
 8781 DIAS NORMAIS 30,00 10.000,00
Descontos:
  998 I.N.S.S. 9,88 988,07
  999 IMPOSTO DE RENDA 27,50 1.569,55

Total vencimentos: 10.000,00, Total descontos: 2.557,62
Valor Líquido: 7.442,38

Rodapé bases:
 Sal_Base 10.000,00, Base_INSS 8.475,55, Base_IRRF 10.000,00,
 FGTS 800,00, Base_FGTS 9.011,93, Aliq_IRRF 27,50%
"""


def test_g4f_extrai_bases_fiscais_completas():
    """Parse positivo G4F fev/2026: 14+ campos no dict, incluindo bases."""
    resultado = _parse_g4f(TEXTO_G4F_REAL_FEV2026)
    assert resultado is not None
    # Campos críticos classe A preservados (retrocompat).
    assert resultado["bruto"] == 8657.25
    assert resultado["inss"] == 988.07
    assert resultado["irrf"] == 1200.29
    assert resultado["vr_va"] == 87.75
    assert resultado["liquido"] == 6381.14
    # Bases fiscais novas.
    assert resultado["base_inss"] == 8475.55
    assert resultado["base_irrf"] == 8657.25
    assert resultado["base_fgts"] == 8657.25
    assert resultado["fgts_mes"] == 692.58
    assert resultado["dependentes_ir"] == 0
    assert resultado["dependentes_salfam"] == 0
    # Metadata empresa.
    assert resultado["cnpj_empresa"] == "07.094.346/0002-26"
    assert "G4F" in resultado["razao_social"].upper()
    assert resultado["cargo"] == "ANALISTA DE BUSINESS INTELLIGENCE"
    assert resultado["data_admissao"] == "08/05/2025"
    assert resultado["data_pagamento"] == "06/03/2026"
    # Banco crédito.
    assert "Santander" in resultado["banco_credito"]
    assert "2327" in resultado["banco_credito"]


def test_infobase_extrai_bases_fiscais_completas():
    """Parse positivo Infobase fev/2026: bases extraídas do rodapé."""
    resultado = _parse_infobase(TEXTO_INFOBASE_REAL_FEV2026)
    assert resultado is not None
    # Campos classe A preservados.
    assert resultado["bruto"] == 10000.00
    assert resultado["inss"] == 988.07
    assert resultado["irrf"] == 1569.55
    assert resultado["liquido"] == 7442.38
    # Bases fiscais novas.
    assert resultado["base_inss"] == 8475.55
    assert resultado["base_irrf"] == 10000.00
    assert resultado["base_fgts"] == 9011.93
    assert resultado["fgts_mes"] == 800.00
    # Metadata empresa.
    assert resultado["cnpj_empresa"] == "02.800.463/0001-63"
    assert "INFOBASE" in resultado["razao_social"].upper()
    assert resultado["cargo"] == "ANALISTA DE DADOS"
    assert resultado["data_admissao"] == "02/06/2025"


def test_regex_base_inss_g4f_isolada():
    """Regex base_inss G4F casa formato 'Base de cálculo INSS: R$ 8.475,55'."""
    bases = _extrair_bases_g4f("Base de cálculo INSS: R$ 8.475,55")
    assert bases["base_inss"] == 8475.55


def test_regex_base_inss_infobase_isolada():
    """Regex base_inss Infobase casa formato 'Base_INSS 8.475,55'."""
    bases = _extrair_bases_infobase("Base_INSS 8.475,55, Base_IRRF 10.000,00")
    assert bases["base_inss"] == 8475.55
    assert bases["base_irrf"] == 10000.00


def test_regex_fgts_g4f_isolada():
    """Regex fgts_mes G4F casa formato 'FGTS do mês: R$ 692,58'."""
    bases = _extrair_bases_g4f("FGTS do mês: R$ 692,58")
    assert bases["fgts_mes"] == 692.58


def test_regex_cnpj_empresa_g4f_isolada():
    """Regex cnpj_empresa casa formato canônico XX.XXX.XXX/XXXX-XX."""
    bases = _extrair_bases_g4f("CNPJ: 07.094.346/0002-26")
    assert bases["cnpj_empresa"] == "07.094.346/0002-26"


def test_retrocompat_dict_g4f_tem_14_campos_minimo():
    """Dict G4F retorna ≥14 chaves preservando contratos antigos (8 antes)."""
    resultado = _parse_g4f(TEXTO_G4F_REAL_FEV2026)
    assert resultado is not None
    # 8 campos antigos (Sprint AUDIT2): mes_ref, fonte, bruto, inss, irrf,
    # vr_va, liquido, banco, itens.
    chaves_antigas = {
        "mes_ref",
        "fonte",
        "bruto",
        "inss",
        "irrf",
        "vr_va",
        "liquido",
        "banco",
        "itens",
    }
    assert chaves_antigas.issubset(set(resultado.keys()))
    # ≥14 chaves totais (bases novas).
    assert len(resultado) >= 14


def test_retrocompat_dict_infobase_tem_14_campos_minimo():
    """Dict Infobase retorna ≥14 chaves preservando contratos antigos."""
    resultado = _parse_infobase(TEXTO_INFOBASE_REAL_FEV2026)
    assert resultado is not None
    chaves_antigas = {
        "mes_ref",
        "fonte",
        "bruto",
        "inss",
        "irrf",
        "vr_va",
        "liquido",
        "banco",
        "itens",
    }
    assert chaves_antigas.issubset(set(resultado.keys()))
    assert len(resultado) >= 14


def test_grafo_persiste_bases_fiscais_g4f_em_metadata(tmp_path: Path):
    """Ingerir holerite G4F no grafo persiste bases em metadata do node documento."""
    registro = _parse_g4f(TEXTO_G4F_REAL_FEV2026)
    assert registro is not None

    grafo = GrafoDB(tmp_path / "g.sqlite")
    grafo.criar_schema()
    arquivo_falso = tmp_path / "holerite_g4f_fev.pdf"
    arquivo_falso.write_bytes(b"%PDF-1.4 stub")
    _ingerir_holerite_no_grafo(grafo, registro, arquivo_falso)

    meta = _ler_metadata_holerite(grafo, "2026-02")
    # Bases fiscais persistidas (Sprint INFRA-CONTRACHEQUE-EXTRAIR-BASES).
    assert meta["base_inss"] == 8475.55
    assert meta["base_irrf"] == 8657.25
    assert meta["base_fgts"] == 8657.25
    assert meta["fgts_mes"] == 692.58
    assert meta["cnpj_empresa"] == "07.094.346/0002-26"
    assert meta["cargo"] == "ANALISTA DE BUSINESS INTELLIGENCE"
    assert meta["data_admissao"] == "08/05/2025"
    assert meta["data_pagamento"] == "06/03/2026"
    assert "Santander" in meta["banco_credito"]


def test_g4f_sem_bases_no_texto_nao_quebra_parse():
    """Falha-soft: parse G4F sem rodapé de bases ainda retorna dict válido."""
    # Texto antigo TEXTO_G4F_FOLHA traz CNPJ na linha "CNPJ: 07.094.346/0002-26
    # LTDA" mas não o bloco de bases fiscais — confirma graceful degradation
    # quando rodapé fiscal está ausente.
    resultado = _parse_g4f(TEXTO_G4F_FOLHA)
    assert resultado is not None
    # Campos antigos OK.
    assert resultado["bruto"] == 8657.25
    # Bases viram None graciosamente quando rodapé ausente.
    assert resultado["base_inss"] is None
    assert resultado["base_irrf"] is None
    assert resultado["fgts_mes"] is None
    # CNPJ ainda casa via REGEX_G4F_CNPJ no header (esperado).
    assert resultado["cnpj_empresa"] == "07.094.346/0002-26"


# "Quem tem a coragem de começar tem a coragem de vencer." -- David Viscott
