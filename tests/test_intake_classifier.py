"""Testes do src.intake.classifier.

Cobre:
- Resolução de prioridade (especifico > normal > fallback)
- match_mode all vs any
- Templates com_data e sem_data
- Fallback "_classificar" sem exceção
- recarregar_tipos para isolamento entre testes

Fixtures-âncora reproduzem trechos REAIS extraídos via pdfplumber dos PDFs
da inbox de 2026-04-19 -- garante que o classifier roteia o que vimos na
Conferência Artesanal Opus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import classifier as clf

# ============================================================================
# Fixtures de texto-âncora (trechos reais ou sintéticos plausíveis)
# ============================================================================

PREVIEW_CUPOM_GARANTIA = """\
americanas sa - 0337 CNP): 00.776.574/0160-79
SCC, LTS 01 05 E D6, PISO TERREO LJS 01 E 02 MODE ESLO1 - GAMA - BRASILIA
19/04/2026 17:06 | NSU TEF: 0304000022973 | NumCupom: 86
CUPOM DE SERVIÇO - VIA DO CLIENTE
CUPOM BILHETE DE SEGURO
SEGURO DE GARANTIA ESTENDIDA ORIGINAL
Processo SUSEP No. 15414.900147/2014-11
"""

PREVIEW_NFCE_AMERICANAS = """\
CNPJ: 00.776.574/0160-79  americanas sa - 0337
GAMA - BRASILIA - DF
Documento Auxiliar da Nota Fiscal de Consumidor Eletronica
NFCe nº 43280 Serie 304 19/04/2026 17:12:10
Consulte pela chave de acesso em www.fazenda.df.gov.br/nfce/consulta
5326 0400 7765 7401 8079 6530 4000 0432 8010 5868 2510
"""

PREVIEW_DANFE_NFE55 = """\
DANFE - DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRÔNICA
0 - ENTRADA / 1 - SAÍDA
DESTINATÁRIO/REMETENTE
Razão Social: ANDRÉ FARIAS  CPF: 051.273.731-22
Data de emissão: 15/03/2026
"""

PREVIEW_HOLERITE_INFOBASE = """\
INFOBASE TECNOLOGIA LTDA
Demonstrativo de Pagamento de Salário
Funcionário: ANDRÉ FARIAS
Mês de referência: 03/2026
Vencimentos       Descontos
"""

PREVIEW_FATURA_CARTAO = """\
SANTANDER -- Fatura do Cartão Elite Visa
Limite do cartão: R$ 15.000,00
Total da fatura: R$ 2.345,67
Vencimento da fatura: 10/04/2026
"""

PREVIEW_EXTRATO = """\
SANTANDER
EXTRATO DE CONTA -- período 01/03/2026 a 31/03/2026
Saldo Anterior: R$ 1.234,56
"""

PREVIEW_CONTRATO_LOCACAO = """\
INSTRUMENTO PARTICULAR
Pelo presente, CONTRATANTE: João da Silva, e CONTRATADO: Imobiliária ABC,
ajustam locação de imóvel residencial, datado de 01/02/2026.
"""

PREVIEW_DESCONHECIDO = "Texto qualquer sem assinatura de tipo nenhum nada nem disso."


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture
def arquivo_temp(tmp_path: Path):
    """Devolve factory que cria arquivo com conteúdo bruto opcional."""

    def _factory(nome: str = "doc.pdf", conteudo: bytes = b"%PDF-1.4 fake") -> Path:
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
# Carregamento e cache
# ============================================================================


def test_recarregar_tipos_devolve_lista_nao_vazia():
    tipos = clf.recarregar_tipos()
    assert isinstance(tipos, list) and len(tipos) >= 14


def test_tipos_estao_ordenados_por_prioridade():
    tipos = clf.recarregar_tipos()
    niveis = [clf._ORDEM_PRIORIDADE[t["prioridade"]] for t in tipos]
    assert niveis == sorted(niveis), "ordem de prioridade não foi aplicada"


def test_recarregar_yaml_inexistente_levanta(tmp_path):
    inexistente = tmp_path / "nao_existe.yaml"
    with pytest.raises(FileNotFoundError):
        clf.recarregar_tipos(inexistente)


def test_recarregar_yaml_sem_chave_tipos_levanta(tmp_path):
    arquivo = tmp_path / "vazio.yaml"
    arquivo.write_text("outras_coisas: 1\n")
    with pytest.raises(ValueError, match="sem chave raiz 'tipos'"):
        clf.recarregar_tipos(arquivo)


# ============================================================================
# Validação de schema do YAML (falha-cedo no import)
# ============================================================================


def _yaml_minimo(tmp_path: Path, conteudo: str) -> Path:
    arquivo = tmp_path / "tipos.yaml"
    arquivo.write_text(conteudo, encoding="utf-8")
    return arquivo


def test_validacao_falta_campo_obrigatorio(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: tipo_quebrado
    prioridade: normal
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: ["X"]
    pasta_destino_template: "data/raw/{pessoa}/x/"
    # falta renomear_template
""",
    )
    with pytest.raises(ValueError, match="faltando campo obrigatório 'renomear_template'"):
        clf.recarregar_tipos(arquivo)


def test_validacao_prioridade_invalida(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: t1
    prioridade: super_alta
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: ["X"]
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      com_data: "X_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "X_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError, match="prioridade 'super_alta' inválida"):
        clf.recarregar_tipos(arquivo)


def test_validacao_match_mode_invalido(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: t1
    prioridade: normal
    match_mode: maybe
    mimes: [application/pdf]
    regex_conteudo: ["X"]
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      com_data: "X_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "X_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError, match="match_mode 'maybe' inválido"):
        clf.recarregar_tipos(arquivo)


def test_validacao_regex_conteudo_vazio(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: t1
    prioridade: normal
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: []
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      com_data: "X_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "X_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError, match="regex_conteudo deve ser lista não vazia"):
        clf.recarregar_tipos(arquivo)


def test_validacao_id_duplicado(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: duplicado
    prioridade: normal
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: ["A"]
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      com_data: "A_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "A_{sha8}.pdf"
  - id: duplicado
    prioridade: normal
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: ["B"]
    pasta_destino_template: "data/raw/{pessoa}/y/"
    renomear_template:
      com_data: "B_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "B_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError, match="id duplicado"):
        clf.recarregar_tipos(arquivo)


def test_validacao_renomear_template_sem_chaves_obrigatorias(tmp_path):
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: t1
    prioridade: normal
    match_mode: any
    mimes: [application/pdf]
    regex_conteudo: ["X"]
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      so_com_data: "X_{data:%Y-%m-%d}_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError, match="renomear_template deve ter chaves"):
        clf.recarregar_tipos(arquivo)


def test_validacao_acumula_multiplos_erros(tmp_path):
    """Validador devolve TODOS os erros num só raise, não para no primeiro."""
    arquivo = _yaml_minimo(
        tmp_path,
        """\
tipos:
  - id: t1
    prioridade: super
    match_mode: maybe
    mimes: []
    regex_conteudo: []
    pasta_destino_template: "data/raw/{pessoa}/x/"
    renomear_template:
      com_data: "X_{data:%Y-%m-%d}_{sha8}.pdf"
      sem_data: "X_{sha8}.pdf"
""",
    )
    with pytest.raises(ValueError) as exc_info:
        clf.recarregar_tipos(arquivo)
    msg = str(exc_info.value)
    assert "prioridade" in msg
    assert "match_mode" in msg
    assert "mimes" in msg
    assert "regex_conteudo" in msg


def test_yaml_real_passa_validacao():
    """O mappings/tipos_documento.yaml de produção passa a validação."""
    tipos = clf.recarregar_tipos()  # sem path -> usa o de produção
    assert len(tipos) == 15
    for tipo in tipos:
        assert tipo["prioridade"] in clf._PRIORIDADES_VALIDAS
        assert tipo["match_mode"] in clf._MATCH_MODES_VALIDOS


# ============================================================================
# Roteamento por tipo (casos do mundo real)
# ============================================================================


def test_classifica_cupom_garantia_estendida_no_pdf_notas(arquivo_temp):
    arq = arquivo_temp("pdf_notas.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_CUPOM_GARANTIA, pessoa="andre")
    assert decisao.tipo == "cupom_garantia_estendida"
    assert decisao.prioridade == "especifico"
    assert decisao.match_mode == "all"
    assert "garantias_estendidas" in str(decisao.pasta_destino)
    assert decisao.data_detectada_iso == "2026-04-19"
    assert decisao.nome_canonico.startswith("GARANTIA_EST_2026-04-19_")
    assert decisao.nome_canonico.endswith(".pdf")


def test_classifica_nfce_americanas_pg1_do_scan(arquivo_temp):
    arq = arquivo_temp("notas_pg1.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_NFCE_AMERICANAS, pessoa="andre")
    assert decisao.tipo == "nfce_consumidor_eletronica"
    assert decisao.extrator_modulo == "src.extractors.nfce_pdf"
    assert "nfs_fiscais/nfce" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("NFCE_2026-04-19_")


def test_classifica_danfe_nfe55_quando_tem_destinatario(arquivo_temp):
    arq = arquivo_temp("danfe.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DANFE_NFE55, pessoa="andre")
    assert decisao.tipo == "danfe_nfe55"
    assert decisao.match_mode == "all"
    assert "nfs_fiscais/danfe55" in str(decisao.pasta_destino)


def test_nfce_nao_e_classificada_como_danfe_porque_falta_destinatario(arquivo_temp):
    """NFC-e tem 'Documento Auxiliar...' mas NÃO tem 'DESTINATÁRIO' --
    o `match_mode: all` da regra danfe_nfe55 exige todos os 3 e portanto recusa."""
    arq = arquivo_temp("nfce.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_NFCE_AMERICANAS, pessoa="andre")
    assert decisao.tipo == "nfce_consumidor_eletronica"
    assert decisao.tipo != "danfe_nfe55"


def test_classifica_holerite_infobase(arquivo_temp):
    arq = arquivo_temp("holerite.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_HOLERITE_INFOBASE, pessoa="andre")
    assert decisao.tipo == "holerite"
    assert decisao.extrator_modulo == "src.extractors.contracheque_pdf"


def test_classifica_fatura_cartao_antes_de_extrato(arquivo_temp):
    """fatura_cartao está declarada ANTES de extrato_bancario no YAML --
    'Limite do cartão' é fingerprint forte e ganha o roteamento."""
    arq = arquivo_temp("fatura.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_FATURA_CARTAO, pessoa="andre")
    assert decisao.tipo == "fatura_cartao"


def test_classifica_extrato_quando_nao_e_fatura(arquivo_temp):
    arq = arquivo_temp("extrato.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_EXTRATO, pessoa="andre")
    assert decisao.tipo == "extrato_bancario"


def test_classifica_contrato_quando_tem_contratante_E_contratado(arquivo_temp):
    arq = arquivo_temp("contrato.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_CONTRATO_LOCACAO, pessoa="andre")
    assert decisao.tipo == "contrato"


def test_nao_classifica_contrato_quando_falta_uma_das_ancoras(arquivo_temp):
    """match_mode: all -- só CONTRATANTE sem CONTRATADO não basta."""
    arq = arquivo_temp("doc.pdf")
    texto = "Aviso ao CONTRATANTE -- prezado cliente, segue documentação."
    decisao = clf.classificar(arq, "application/pdf", texto, pessoa="andre")
    assert decisao.tipo != "contrato"


# ============================================================================
# Fallback "não classificado" -- sem exceção
# ============================================================================


def test_arquivo_sem_match_vai_para_classificar(arquivo_temp):
    arq = arquivo_temp("misterio.pdf")
    decisao = clf.classificar(arq, "application/pdf", PREVIEW_DESCONHECIDO, pessoa="andre")
    assert decisao.tipo is None
    assert decisao.prioridade is None
    assert "_classificar" in str(decisao.pasta_destino)
    assert decisao.nome_canonico.startswith("_CLASSIFICAR_")
    assert decisao.motivo_fallback is not None


def test_mime_incompativel_pula_tipo(arquivo_temp):
    """XML NFe tem mime application/xml -- PDF do mesmo conteúdo não casa."""
    arq = arquivo_temp("doc.pdf")
    decisao = clf.classificar(arq, "application/pdf", "<infNFe>conteudo</infNFe>", pessoa="andre")
    assert decisao.tipo != "xml_nfe"


def test_fallback_quando_arquivo_nao_existe_levanta(tmp_path):
    """Único caso onde levantamos exceção -- precisamos do SHA8 dos bytes."""
    inexistente = tmp_path / "nao_existe.pdf"
    with pytest.raises(FileNotFoundError):
        clf.classificar(inexistente, "application/pdf", "qualquer", pessoa="andre")


# ============================================================================
# Templates de nome
# ============================================================================


def test_template_sem_data_quando_preview_nao_traz_data(arquivo_temp):
    arq = arquivo_temp("sem_data.pdf")
    texto = "CUPOM BILHETE DE SEGURO GARANTIA ESTENDIDA Processo SUSEP 1234"
    decisao = clf.classificar(arq, "application/pdf", texto, pessoa="andre")
    assert decisao.tipo == "cupom_garantia_estendida"
    assert decisao.data_detectada_iso is None
    assert decisao.nome_canonico.startswith("GARANTIA_EST_")
    assert "2026" not in decisao.nome_canonico  # sem data


def test_pasta_destino_resolve_pessoa_no_template(arquivo_temp):
    arq = arquivo_temp("doc.pdf")
    decisao_andre = clf.classificar(
        arq, "application/pdf", PREVIEW_HOLERITE_INFOBASE, pessoa="andre"
    )
    decisao_vit = clf.classificar(
        arq, "application/pdf", PREVIEW_HOLERITE_INFOBASE, pessoa="vitoria"
    )
    assert "/andre/" in str(decisao_andre.pasta_destino)
    assert "/vitoria/" in str(decisao_vit.pasta_destino)


def test_sha8_estavel_para_mesmo_arquivo(arquivo_temp):
    arq = arquivo_temp("doc.pdf", conteudo="%PDF-1.4 conteúdo determinístico".encode("utf-8"))
    decisao_a = clf.classificar(arq, "application/pdf", PREVIEW_DESCONHECIDO, pessoa="andre")
    decisao_b = clf.classificar(arq, "application/pdf", PREVIEW_DESCONHECIDO, pessoa="andre")
    assert decisao_a.nome_canonico == decisao_b.nome_canonico


# "O detalhe que não se mede vira armadilha." -- princípio do supervisor artesanal
