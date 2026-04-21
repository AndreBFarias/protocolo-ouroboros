"""Testes do extrator de receita médica (Sprint 47a).

Padrão canônico do projeto (ver `test_recibo_nao_fiscal.py`,
`test_cupom_garantia_estendida_pdf.py`): fixtures `.txt` em
`tests/fixtures/receitas/` reproduzem texto OCR pré-decodificado. O
extrator aceita `texto_override` para rodar testes sem tesseract real.

Acceptance criteria da Sprint 47a:
  - Extrai CRM, médico, paciente, >= 1 medicamento com posologia
  - Nó `prescricao` + arestas `prescreve` para nodes `item`
  - Quando transação de farmácia casa com medicamento prescrito,
    aresta `prescreve_cobre` é criada (auditor humano valida)
  - Receita médica com mais de 6 meses gera aviso
  - Acentuação PT-BR correta
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.extractors.receita_medica import (
    EXTENSOES_ACEITAS,
    VALIDADE_CONTROLADA_MESES,
    VALIDADE_DEFAULT_MESES,
    ExtratorReceitaMedica,
    _carregar_medicamentos_dedutiveis,
    _extrair_crm,
    _extrair_medicamentos,
    _identificar_principio_ativo,
    _parse_receita,
)
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import ingerir_documento_fiscal

FIXTURES = Path(__file__).parent / "fixtures" / "receitas"
RECEITA_SIMPLES = FIXTURES / "receita_simples.txt"
RECEITA_USO_CONTINUO = FIXTURES / "receita_uso_continuo.txt"
RECEITA_SEM_CRM = FIXTURES / "receita_sem_crm.txt"
RECEITA_EXPIRADA = FIXTURES / "receita_expirada.txt"


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


@pytest.fixture()
def grafo_temp(tmp_path: Path):
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorReceitaMedica:
    """Extrator com placeholder de caminho; grafo None (in-memory no teste)."""
    placeholder = tmp_path / "receita_stub.jpg"
    placeholder.write_bytes(b"\xff\xd8\xff")
    return ExtratorReceitaMedica(placeholder)


# ============================================================================
# Catálogo de medicamentos dedutíveis
# ============================================================================


class TestCatalogoMedicamentosDedutiveis:
    def test_carrega_pelo_menos_10_medicamentos(self):
        catalogo = _carregar_medicamentos_dedutiveis()
        assert len(catalogo) >= 10

    def test_cada_entrada_tem_principio_ativo_e_classe(self):
        catalogo = _carregar_medicamentos_dedutiveis()
        for entrada in catalogo:
            assert entrada.get("principio_ativo"), entrada
            assert entrada.get("classe"), entrada

    def test_identifica_principio_via_nome_comercial(self):
        catalogo = _carregar_medicamentos_dedutiveis()
        entrada = _identificar_principio_ativo("Puran T4", catalogo)
        assert entrada is not None
        assert entrada["principio_ativo"] == "levotiroxina"

    def test_identifica_principio_via_substring(self):
        catalogo = _carregar_medicamentos_dedutiveis()
        entrada = _identificar_principio_ativo("LOSARTANA POTASSICA", catalogo)
        assert entrada is not None
        assert entrada["principio_ativo"] == "losartana"

    def test_medicamento_desconhecido_retorna_none(self):
        catalogo = _carregar_medicamentos_dedutiveis()
        entrada = _identificar_principio_ativo("Xaropinho Inventado", catalogo)
        assert entrada is None


# ============================================================================
# Extração de CRM, médico, paciente
# ============================================================================


class TestExtracaoCampos:
    def test_crm_com_barra(self):
        assert _extrair_crm("Dr. Fulano CRM/DF 12345") == "DF|12345"

    def test_crm_com_hifen(self):
        assert _extrair_crm("CRM-SP 67890 -- ortopedista") == "SP|67890"

    def test_crm_ausente(self):
        assert _extrair_crm("médico sem registro") is None

    def test_parse_receita_simples_extrai_tudo(self):
        parsed = _parse_receita(_ler(RECEITA_SIMPLES))
        assert parsed is not None
        assert parsed["crm_completo"] == "DF|12345"
        assert parsed["medico_nome"]
        assert "Paulo" in parsed["medico_nome"]
        assert parsed["paciente_nome"]
        assert "ANDRÉ" in parsed["paciente_nome"]
        assert parsed["data_emissao"] == "2026-03-15"
        assert len(parsed["medicamentos"]) == 1
        med = parsed["medicamentos"][0]
        assert "amoxicilina" in med["nome"].lower()
        assert med["dosagem"].lower().startswith("500")
        assert med["posologia"]
        assert "8 em 8" in med["posologia"] or "8/8" in med["posologia"]

    def test_parse_preserva_acentuacao(self):
        parsed = _parse_receita(_ler(RECEITA_USO_CONTINUO))
        assert parsed is not None
        # Paciente VITÓRIA ANDRADE SOARES deve manter acento.
        assert "VITÓRIA" in (parsed["paciente_nome"] or "")


# ============================================================================
# Medicamentos com posologia e uso contínuo
# ============================================================================


class TestMedicamentos:
    def test_uso_continuo_identificado_em_3_medicamentos(self):
        parsed = _parse_receita(_ler(RECEITA_USO_CONTINUO))
        assert parsed is not None
        assert len(parsed["medicamentos"]) == 3
        nomes = {m["nome"].lower() for m in parsed["medicamentos"]}
        assert any("losartana" in n for n in nomes)
        assert any("sinvastatina" in n for n in nomes)
        assert any("metformina" in n for n in nomes)
        # Todos marcados como contínuos
        for med in parsed["medicamentos"]:
            assert med["continuo"] is True

    def test_elegibilidade_dedutivel_para_uso_continuo_conhecido(self):
        parsed = _parse_receita(_ler(RECEITA_USO_CONTINUO))
        assert parsed is not None
        # Losartana, Sinvastatina e Metformina estão no YAML -- todos elegíveis.
        elegiveis = [
            m for m in parsed["medicamentos"] if m.get("elegivel_dedutivel_irpf")
        ]
        assert len(elegiveis) == 3

    def test_antibiotico_sem_uso_continuo_nao_e_dedutivel(self):
        parsed = _parse_receita(_ler(RECEITA_SIMPLES))
        assert parsed is not None
        med = parsed["medicamentos"][0]
        assert med["continuo"] is False
        assert med["elegivel_dedutivel_irpf"] is False

    def test_regex_medicamento_numerado_captura_3_itens(self):
        texto = (
            "RECEITUÁRIO\n"
            "CRM/DF 11111\n"
            "Em 01/03/2026.\n"
            "1. Omeprazol 20mg\n"
            "Tomar 1 cápsula em jejum, uso contínuo.\n"
            "2. Metformina 500mg\n"
            "Tomar 1 comprimido após o almoço, uso contínuo.\n"
            "3. Dipirona 500mg\n"
            "Tomar 1 comprimido se dor.\n"
        )
        catalogo = _carregar_medicamentos_dedutiveis()
        medicamentos = _extrair_medicamentos(texto, catalogo)
        assert len(medicamentos) == 3


# ============================================================================
# Validade / expiração
# ============================================================================


class TestValidadeExpiracao:
    def test_validade_default_6_meses(self):
        parsed = _parse_receita(_ler(RECEITA_SIMPLES))
        assert parsed is not None
        assert parsed["validade_meses"] == VALIDADE_DEFAULT_MESES

    def test_receita_antiga_e_marcada_como_expirada(self):
        parsed = _parse_receita(_ler(RECEITA_EXPIRADA))
        assert parsed is not None
        data_emissao = date.fromisoformat(parsed["data_emissao"])
        meses_desde = (date.today() - data_emissao).days / 30
        # Fixture foi emitida em 10/05/2025 -- mais de 6 meses até 2026-04.
        assert meses_desde >= 6
        assert parsed["expirada"] is True

    def test_controle_especial_reduz_validade_para_1_mes(self):
        texto = (
            "RECEITUÁRIO\n"
            "Dr. Teste Controlado CRM/DF 22222\n"
            "Brasília, 01/03/2026.\n"
            "1. Ritalina 10mg\n"
            "Tomar 1 comprimido de manhã, uso contínuo.\n"
            "Controle especial -- tarja preta.\n"
        )
        parsed = _parse_receita(texto)
        assert parsed is not None
        assert parsed["validade_meses"] == VALIDADE_CONTROLADA_MESES


# ============================================================================
# Parse defensivo
# ============================================================================


class TestParseDefensivo:
    def test_sem_crm_retorna_none(self):
        parsed = _parse_receita(_ler(RECEITA_SEM_CRM))
        assert parsed is None

    def test_texto_vazio_retorna_none(self):
        assert _parse_receita("") is None

    def test_sem_medicamento_retorna_none(self):
        texto = (
            "RECEITUÁRIO\n"
            "CRM/DF 33333\n"
            "Brasília, 05/03/2026.\n"
            "Paciente: FULANO\n"
            "Sem prescrição explícita.\n"
        )
        assert _parse_receita(texto) is None


# ============================================================================
# Ingestão no grafo
# ============================================================================


class TestIngestaoGrafo:
    def test_prescricao_simples_cria_nodes_e_arestas(self, grafo_temp):
        extrator = ExtratorReceitaMedica(RECEITA_SIMPLES, grafo=grafo_temp)
        resultado = extrator.extrair_receitas(
            RECEITA_SIMPLES, texto_override=_ler(RECEITA_SIMPLES)
        )
        assert len(resultado) == 1

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("prescricao") == 1
        # Médico vira fornecedor com categoria médico.
        assert stats["nodes_por_tipo"].get("fornecedor", 0) >= 1
        # Um medicamento ingerido.
        assert stats["nodes_por_tipo"].get("item", 0) >= 1
        # Aresta emitida_por e prescreve presentes.
        assert stats["edges_por_tipo"].get("emitida_por", 0) >= 1
        assert stats["edges_por_tipo"].get("prescreve", 0) >= 1
        assert stats["edges_por_tipo"].get("ocorre_em", 0) >= 1

    def test_uso_continuo_cria_3_arestas_prescreve(self, grafo_temp):
        extrator = ExtratorReceitaMedica(RECEITA_USO_CONTINUO, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_USO_CONTINUO, texto_override=_ler(RECEITA_USO_CONTINUO)
        )
        stats = grafo_temp.estatisticas()
        assert stats["edges_por_tipo"].get("prescreve", 0) == 3

    def test_ingestao_idempotente(self, grafo_temp):
        extrator = ExtratorReceitaMedica(RECEITA_SIMPLES, grafo=grafo_temp)
        texto = _ler(RECEITA_SIMPLES)
        extrator.extrair_receitas(RECEITA_SIMPLES, texto_override=texto)
        stats_1 = grafo_temp.estatisticas()
        extrator.extrair_receitas(RECEITA_SIMPLES, texto_override=texto)
        stats_2 = grafo_temp.estatisticas()
        assert stats_1["nodes_total"] == stats_2["nodes_total"]
        assert stats_1["edges_total"] == stats_2["edges_total"]

    def test_medico_tem_categoria_e_crm(self, grafo_temp):
        extrator = ExtratorReceitaMedica(RECEITA_SIMPLES, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_SIMPLES, texto_override=_ler(RECEITA_SIMPLES)
        )
        medico = grafo_temp.buscar_node("fornecedor", "CRM|DF|12345")
        assert medico is not None
        assert medico.metadata.get("categoria") == "medico"
        assert medico.metadata.get("crm") == "DF|12345"

    def test_medicamento_conhecido_tem_principio_ativo(self, grafo_temp):
        extrator = ExtratorReceitaMedica(
            RECEITA_USO_CONTINUO, grafo=grafo_temp
        )
        extrator.extrair_receitas(
            RECEITA_USO_CONTINUO, texto_override=_ler(RECEITA_USO_CONTINUO)
        )
        losartana_node = grafo_temp.buscar_node("item", "MED|LOSARTANA")
        assert losartana_node is not None
        assert losartana_node.metadata.get("principio_ativo") == "losartana"
        assert losartana_node.metadata.get("classe") == "anti_hipertensivo"
        assert losartana_node.metadata.get("continuo") is True
        assert losartana_node.metadata.get("elegivel_dedutivel_irpf") is True


# ============================================================================
# Linking prescrição <-> farmácia (aresta prescreve_cobre)
# ============================================================================


class TestLinkingFarmacia:
    def test_prescreve_cobre_e_criada_quando_item_farmacia_existe(self, grafo_temp):
        # Ingere primeiro um cupom de farmácia com Losartana (via documento fiscal).
        documento = {
            "chave_44": "35260401234567000100550010000012341234567890",
            "cnpj_emitente": "12.345.678/0001-00",
            "data_emissao": "2026-02-10",
            "tipo_documento": "nfce_modelo_65",
            "razao_social": "Drogaria Santa Fé",
        }
        itens = [
            {
                "codigo": "7891000100103",
                "descricao": "LOSARTANA POT 50MG CX 30 COMPR",
                "qtde": 1,
                "unidade": "UN",
                "valor_unit": 15.90,
                "valor_total": 15.90,
            }
        ]
        ingerir_documento_fiscal(grafo_temp, documento, itens)

        # Ingere a receita de uso contínuo (mesma época).
        extrator = ExtratorReceitaMedica(RECEITA_USO_CONTINUO, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_USO_CONTINUO, texto_override=_ler(RECEITA_USO_CONTINUO)
        )

        stats = grafo_temp.estatisticas()
        assert stats["edges_por_tipo"].get("prescreve_cobre", 0) >= 1

    def test_sem_item_farmacia_nao_cria_prescreve_cobre(self, grafo_temp):
        extrator = ExtratorReceitaMedica(RECEITA_USO_CONTINUO, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_USO_CONTINUO, texto_override=_ler(RECEITA_USO_CONTINUO)
        )
        stats = grafo_temp.estatisticas()
        assert stats["edges_por_tipo"].get("prescreve_cobre", 0) == 0


# ============================================================================
# Aviso de expiração
# ============================================================================


class TestAvisoExpiracao:
    def test_receita_expirada_gera_warning_no_log(self, grafo_temp, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="receita_medica")
        caplog.set_level(logging.WARNING, logger="graph.ingestor_documento")
        extrator = ExtratorReceitaMedica(RECEITA_EXPIRADA, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_EXPIRADA, texto_override=_ler(RECEITA_EXPIRADA)
        )
        # Ao menos uma mensagem com "expirada" ou "validade".
        mensagens = " ".join(rec.getMessage().lower() for rec in caplog.records)
        assert "expirada" in mensagens or "validade" in mensagens

    def test_receita_recente_nao_gera_warning_expiracao(self, grafo_temp, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="receita_medica")
        # Receita simples é de 2026-03-15; dentro de 6 meses.
        hoje = date.today()
        data_emissao = date.fromisoformat("2026-03-15")
        meses = (hoje - data_emissao).days / 30
        if meses >= 6:
            pytest.skip(
                "Fixture receita_simples ficou antiga -- teste perde sentido"
            )
        extrator = ExtratorReceitaMedica(RECEITA_SIMPLES, grafo=grafo_temp)
        extrator.extrair_receitas(
            RECEITA_SIMPLES, texto_override=_ler(RECEITA_SIMPLES)
        )
        mensagens = " ".join(rec.getMessage().lower() for rec in caplog.records)
        assert "expirada" not in mensagens


# ============================================================================
# Detecção pelo pipeline (pode_processar)
# ============================================================================


class TestPodeProcessar:
    def test_aceita_receita_em_pasta_saude_receita(self, tmp_path):
        alvo = tmp_path / "saude" / "receitas" / "receita_2026.pdf"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(b"%PDF-1.4\n")
        extrator = ExtratorReceitaMedica(alvo)
        assert extrator.pode_processar(alvo) is True

    def test_recusa_holerite(self, tmp_path):
        alvo = tmp_path / "holerites" / "janeiro.pdf"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(b"%PDF-1.4\n")
        extrator = ExtratorReceitaMedica(alvo)
        assert extrator.pode_processar(alvo) is False

    def test_recusa_cupom(self, tmp_path):
        alvo = tmp_path / "cupons" / "receita_drogaria.jpg"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_bytes(b"\xff\xd8\xff")
        extrator = ExtratorReceitaMedica(alvo)
        # Mesmo com 'receita' no nome, 'cupom' na pasta é exclusão forte.
        assert extrator.pode_processar(alvo) is False

    def test_recusa_extensao_desconhecida(self, tmp_path):
        alvo = tmp_path / "receitas" / "arquivo.txt"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text("receita")
        extrator = ExtratorReceitaMedica(alvo)
        assert extrator.pode_processar(alvo) is False

    def test_extensoes_aceitas_cobrem_pdf_jpg_png_heic(self):
        assert ".pdf" in EXTENSOES_ACEITAS
        assert ".jpg" in EXTENSOES_ACEITAS
        assert ".png" in EXTENSOES_ACEITAS
        assert ".heic" in EXTENSOES_ACEITAS


# ============================================================================
# Contrato com pipeline (registro em _descobrir_extratores)
# ============================================================================


class TestRegistroPipeline:
    def test_pipeline_registra_extrator_receita(self):
        from src.pipeline import _descobrir_extratores

        classes = _descobrir_extratores()
        nomes = [cls.__name__ for cls in classes]
        assert "ExtratorReceitaMedica" in nomes

    def test_receita_vem_antes_do_recibo_catch_all(self):
        from src.pipeline import _descobrir_extratores

        classes = _descobrir_extratores()
        nomes = [cls.__name__ for cls in classes]
        idx_receita = nomes.index("ExtratorReceitaMedica")
        idx_recibo = nomes.index("ExtratorReciboNaoFiscal")
        assert idx_receita < idx_recibo


# ============================================================================
# Extrair retorna lista vazia de Transacao (não é lançamento)  # noqa: accent
# ============================================================================


class TestExtrairNaoGeraTransacao:
    def test_extrair_devolve_lista_vazia_de_transacao(
        self, grafo_temp, tmp_path
    ):
        placeholder = tmp_path / "receita.jpg"
        placeholder.write_bytes(b"\xff\xd8\xff")
        extrator = ExtratorReceitaMedica(placeholder, grafo=grafo_temp)
        # extrair() tenta OCR e falha (bytes inválidos) mas devolve [].
        resultado = extrator.extrair()
        assert resultado == []


# "A medida do texto é o cuidado com quem o lê." -- princípio do validador
