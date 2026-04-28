"""Testes dos parsers de contracheque G4F e Infobase.

Usa texto sintético que imita o output de pdfplumber/tesseract, permitindo
testar a lógica de parsing sem depender de PDFs reais (dados privados).
"""

import json
from pathlib import Path

from src.extractors.contracheque_pdf import (
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


# "Quem tem a coragem de começar tem a coragem de vencer." -- David Viscott
