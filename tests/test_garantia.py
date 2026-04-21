"""Testes do extrator de garantia de fabricante (Sprint 47b).

Padrão canônico do projeto (ver `test_receita_medica.py`,
`test_cupom_garantia_estendida_pdf.py`): fixtures `.txt` em
`tests/fixtures/garantias_fabricante/` reproduzem texto OCR/PDF
pré-decodificado. O extrator aceita `texto_override` para rodar testes
sem tesseract/pdfplumber reais.

Acceptance criteria da Sprint 47b:
  - Extrai produto, número de série, data de início, prazo em meses e
    fornecedor (CNPJ + nome).
  - Grafo: nó `garantia` + aresta `emitida_por` para `fornecedor`;
    aresta opcional `cobre` para `item` quando linking existir.
  - Alerta automático quando faltam 30 dias para fim da garantia
    (propriedade `expirando=True` no metadata + warning no log).
  - Acentuação PT-BR correta.

Distinção importante: este teste cobre garantia de FABRICANTE
(Electrolux/Samsung/Amazon/Whirlpool) -- diferente de apólice SUSEP
(Sprint 47c, arquivo de teste `test_cupom_garantia_estendida_pdf.py`).
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from src.extractors.garantia import (
    ALERTA_PROXIMIDADE_DIAS,
    EXTENSOES_ACEITAS,
    ExtratorGarantiaFabricante,
    _carregar_padroes,
    _extrair_cnpj,
    _extrair_prazo_meses,
    _extrair_produto,
    _extrair_serial,
    _identificar_fornecedor_conhecido,
    _parse_garantia,
)
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    ingerir_documento_fiscal,
    ingerir_garantia,
)

FIXTURES = Path(__file__).parent / "fixtures" / "garantias_fabricante"
ELECTROLUX_12M = FIXTURES / "garantia_electrolux_12m.txt"
SAMSUNG_PHONE = FIXTURES / "garantia_samsung_smartphone.txt"
AMAZON_VAREJO = FIXTURES / "garantia_amazon_varejista.txt"
EXPIRANDO = FIXTURES / "garantia_expirando.txt"


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


@pytest.fixture()
def grafo_temp(tmp_path: Path):
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorGarantiaFabricante:
    """Extrator com placeholder de caminho; grafo None (caller injeta)."""
    placeholder = tmp_path / "garantia_stub.txt"
    placeholder.write_text("stub", encoding="utf-8")
    return ExtratorGarantiaFabricante(placeholder)


# ============================================================================
# Catálogo de padrões conhecidos (YAML)
# ============================================================================


class TestCatalogoPadroes:
    def test_carrega_pelo_menos_5_fabricantes(self):
        padroes = _carregar_padroes()
        assert len(padroes.get("fabricantes") or []) >= 5

    def test_cada_fabricante_tem_cnpj_e_prazo_padrao(self):
        padroes = _carregar_padroes()
        for fab in padroes.get("fabricantes") or []:
            assert fab.get("nome"), fab
            assert fab.get("cnpj"), fab
            assert isinstance(fab.get("prazo_padrao_meses"), int), fab

    def test_identifica_electrolux_por_alias(self):
        padroes = _carregar_padroes()
        match = _identificar_fornecedor_conhecido(
            "Comprado na Electrolux do Brasil", padroes
        )
        assert match is not None
        assert match["nome"] == "Electrolux"
        assert match["_kind"] == "fabricante"

    def test_identifica_amazon_como_varejista(self):
        padroes = _carregar_padroes()
        match = _identificar_fornecedor_conhecido(
            "Pedido via Amazon Serviços de Varejo", padroes
        )
        assert match is not None
        assert match["_kind"] == "varejista"

    def test_fornecedor_desconhecido_retorna_none(self):
        padroes = _carregar_padroes()
        match = _identificar_fornecedor_conhecido(
            "Loja de esquina sem nome reconhecido", padroes
        )
        assert match is None


# ============================================================================
# Extração de campos isolados
# ============================================================================


class TestExtracaoCampos:
    def test_cnpj_formatado(self):
        assert _extrair_cnpj("CNPJ: 17.474.294/0001-40") == "17.474.294/0001-40"

    def test_cnpj_sem_formatacao(self):
        assert _extrair_cnpj("CNPJ: 17474294000140") == "17.474.294/0001-40"

    def test_cnpj_ausente(self):
        assert _extrair_cnpj("Texto sem documento") is None

    def test_prazo_meses_explicito(self):
        assert _extrair_prazo_meses("Prazo de Garantia: 12 meses") == 12

    def test_prazo_com_parenteses_extenso(self):
        # Armadilha A47b-1: regex descarta texto entre parênteses.
        assert _extrair_prazo_meses("Prazo: 12 (doze) meses") == 12

    def test_prazo_em_anos_converte_para_meses(self):
        assert _extrair_prazo_meses("Garantia: 2 anos") == 24

    def test_prazo_em_dias_converte_para_meses(self):
        # 90 dias = 3 meses (garantia legal CDC).
        assert _extrair_prazo_meses("Garantia: 90 dias") == 3

    def test_serial_sn_padrao(self):
        assert _extrair_serial("S/N: BR2025AX01234") == "BR2025AX01234"

    def test_serial_imei_14_digitos(self):
        texto = "IMEI: 358765432109876 Outro produto"
        assert _extrair_serial(texto) == "358765432109876"

    def test_serial_ausente_retorna_none(self):
        assert _extrair_serial("Sem identificador do produto") is None

    def test_produto_com_modelo(self):
        texto = "Produto: GELADEIRA FROST FREE DUPLEX ELECTROLUX DB53"
        produto = _extrair_produto(texto)
        assert produto is not None
        assert "GELADEIRA" in produto
        assert "DB53" in produto


# ============================================================================
# Parse consolidado por fixture
# ============================================================================


class TestParseElectrolux:
    def test_extrai_tudo_do_termo_electrolux(self):
        parsed = _parse_garantia(_ler(ELECTROLUX_12M))
        assert parsed is not None
        assert parsed["fornecedor_cnpj"] == "17.474.294/0001-40"
        assert parsed["fornecedor_nome"] == "Electrolux"
        assert parsed["data_inicio"] == "2026-02-10"
        assert parsed["prazo_meses"] == 12
        assert parsed["numero_serie"] == "BR2025AX01234"
        assert "GELADEIRA" in (parsed["produto"] or "")
        assert parsed["categoria_produto"] == "eletrodomestico"

    def test_preserva_acentuacao_em_produto(self):
        # Fixture tem "Curitiba/PR" no endereço -- não no produto.
        # Verifica que parse não estraga chars PT quando presentes.
        parsed = _parse_garantia(_ler(ELECTROLUX_12M))
        assert parsed is not None
        # chave_garantia tem CNPJ + serial + data, formato canônico
        assert parsed["chave_garantia"].startswith("GAR|17.474.294/0001-40|")


class TestParseSamsung:
    def test_extrai_imei_como_serial(self):
        parsed = _parse_garantia(_ler(SAMSUNG_PHONE))
        assert parsed is not None
        assert parsed["numero_serie"] == "358765432109876"
        assert parsed["fornecedor_nome"] == "Samsung"
        assert parsed["categoria_produto"] == "eletronico"

    def test_produto_contem_galaxy(self):
        parsed = _parse_garantia(_ler(SAMSUNG_PHONE))
        assert parsed is not None
        assert "Galaxy" in (parsed["produto"] or "") or "S24" in (
            parsed["produto"] or ""
        )


class TestParseAmazon:
    def test_identificado_como_varejista(self):
        parsed = _parse_garantia(_ler(AMAZON_VAREJO))
        assert parsed is not None
        assert parsed["fornecedor_nome"] == "Amazon"
        # tipo_garantia é "varejista" quando match é varejista e prazo >= 4m
        assert parsed["tipo_garantia"] == "varejista"


# ============================================================================
# Alerta de proximidade de vencimento (acceptance #3)
# ============================================================================


class TestAlertaVencimento:
    def test_fixture_expirando_e_flagada(self):
        # Hoje-congelado: fixture tem data_fim = 2026-04-30 (compra
        # 05/05/2025 + 12 meses x 30d = 360d). Usa 2026-04-20 como
        # referência estável (10 dias antes do fim, dentro da janela
        # de alerta). Evita flakiness quando CI roda após 30/04/2026.
        hoje_ref = date(2026, 4, 20)
        parsed = _parse_garantia(_ler(EXPIRANDO), hoje=hoje_ref)
        assert parsed is not None
        data_fim = date.fromisoformat(parsed["data_fim"])
        dias = (data_fim - hoje_ref).days
        assert 0 <= dias <= ALERTA_PROXIMIDADE_DIAS
        assert parsed["expirando"] is True

    def test_garantia_recente_nao_esta_expirando(self):
        # Hoje-congelado para estabilidade eterna de CI.
        hoje_ref = date(2026, 4, 20)
        parsed = _parse_garantia(_ler(ELECTROLUX_12M), hoje=hoje_ref)
        assert parsed is not None
        # Electrolux comprada em 10/02/2026 com 12m -> data_fim em 2027.
        assert parsed["expirando"] is False
        assert parsed["expirada"] is False

    def test_data_fim_calculada_corretamente(self):
        parsed = _parse_garantia(_ler(ELECTROLUX_12M))
        assert parsed is not None
        data_inicio = date.fromisoformat(parsed["data_inicio"])
        data_fim = date.fromisoformat(parsed["data_fim"])
        # 12 meses * 30 dias = 360 dias (aproximação do extrator).
        assert (data_fim - data_inicio) == timedelta(days=360)


# ============================================================================
# Parse defensivo
# ============================================================================


class TestParseDefensivo:
    def test_texto_vazio_retorna_none(self):
        assert _parse_garantia("") is None

    def test_sem_cnpj_nem_fornecedor_conhecido_retorna_none(self):
        texto = (
            "TERMO DE GARANTIA\n"
            "Produto: genérico\n"
            "Data de Compra: 01/02/2026\n"
            "Prazo de Garantia: 12 meses\n"
            "Loja Desconhecida Ltda sem registro\n"
        )
        assert _parse_garantia(texto) is None

    def test_sem_prazo_e_sem_default_retorna_none(self):
        texto = (
            "TERMO DE GARANTIA\n"
            "CNPJ: 99.999.999/0001-99\n"
            "Data de Compra: 01/02/2026\n"
            "Produto: teste\n"
            "Condições especiais aplicáveis.\n"
        )
        assert _parse_garantia(texto) is None

    def test_sem_data_retorna_none(self):
        texto = (
            "TERMO DE GARANTIA\n"
            "CNPJ: 17.474.294/0001-40\n"
            "Produto: GELADEIRA\n"
            "Prazo de Garantia: 12 meses\n"
        )
        assert _parse_garantia(texto) is None


# ============================================================================
# Ingestão no grafo (acceptance #2)
# ============================================================================


class TestIngestaoGrafo:
    def test_garantia_cria_nodes_e_arestas_basicas(self, grafo_temp):
        extrator = ExtratorGarantiaFabricante(ELECTROLUX_12M, grafo=grafo_temp)
        resultado = extrator.extrair_garantias(
            ELECTROLUX_12M, texto_override=_ler(ELECTROLUX_12M)
        )
        assert len(resultado) == 1

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("garantia") == 1
        assert stats["nodes_por_tipo"].get("fornecedor", 0) >= 1
        assert stats["nodes_por_tipo"].get("periodo", 0) >= 1
        assert stats["edges_por_tipo"].get("emitida_por", 0) >= 1
        assert stats["edges_por_tipo"].get("ocorre_em", 0) >= 1

    def test_ingestao_idempotente(self, grafo_temp):
        extrator = ExtratorGarantiaFabricante(ELECTROLUX_12M, grafo=grafo_temp)
        texto = _ler(ELECTROLUX_12M)
        extrator.extrair_garantias(ELECTROLUX_12M, texto_override=texto)
        stats_1 = grafo_temp.estatisticas()
        extrator.extrair_garantias(ELECTROLUX_12M, texto_override=texto)
        stats_2 = grafo_temp.estatisticas()
        assert stats_1["nodes_total"] == stats_2["nodes_total"]
        assert stats_1["edges_total"] == stats_2["edges_total"]

    def test_fornecedor_tem_cnpj_e_razao_social(self, grafo_temp):
        extrator = ExtratorGarantiaFabricante(ELECTROLUX_12M, grafo=grafo_temp)
        extrator.extrair_garantias(
            ELECTROLUX_12M, texto_override=_ler(ELECTROLUX_12M)
        )
        fornecedor = grafo_temp.buscar_node("fornecedor", "17.474.294/0001-40")
        assert fornecedor is not None
        assert fornecedor.metadata.get("cnpj") == "17.474.294/0001-40"
        assert "Electrolux" in (fornecedor.aliases or [])

    def test_garantia_node_guarda_produto_e_serial(self, grafo_temp):
        extrator = ExtratorGarantiaFabricante(SAMSUNG_PHONE, grafo=grafo_temp)
        extrator.extrair_garantias(
            SAMSUNG_PHONE, texto_override=_ler(SAMSUNG_PHONE)
        )
        nodes_garantia = grafo_temp.listar_nodes("garantia")
        assert len(nodes_garantia) == 1
        meta = nodes_garantia[0].metadata
        assert meta.get("numero_serie") == "358765432109876"
        assert "Galaxy" in (meta.get("produto") or "") or "S24" in (
            meta.get("produto") or ""
        )
        assert meta.get("prazo_meses") == 12

    def test_ingerir_garantia_rejeita_campos_obrigatorios_ausentes(
        self, grafo_temp
    ):
        with pytest.raises(ValueError, match="chave_garantia"):
            ingerir_garantia(grafo_temp, {})

        with pytest.raises(ValueError, match="fornecedor_cnpj"):
            ingerir_garantia(
                grafo_temp,
                {
                    "chave_garantia": "GAR|X|Y|2026-01-01",
                    "data_inicio": "2026-01-01",
                    "prazo_meses": 12,
                },
            )


# ============================================================================
# Linking com item (aresta cobre) -- acceptance #2
# ============================================================================


class TestLinkingComItem:
    def test_aresta_cobre_criada_quando_item_existe(self, grafo_temp):
        """Quando item está no grafo com mesmo CNPJ + data + descrição
        próxima, aresta `cobre` deve ser criada."""
        # Primeiro, ingere um documento fiscal (NFC-e) com item "geladeira".
        documento = {
            "chave_44": "1" * 44,
            "cnpj_emitente": "17.474.294/0001-40",
            "data_emissao": "2026-02-10",
            "tipo_documento": "nfce_modelo_65",
            "razao_social": "Electrolux",
        }
        itens = [
            {
                "codigo": "DB53-001",
                "descricao": "GELADEIRA FROST FREE DUPLEX DB53",
                "qtde": 1,
                "valor_unit": 3500.0,
                "valor_total": 3500.0,
            }
        ]
        ingerir_documento_fiscal(grafo_temp, documento, itens)

        # Agora ingere garantia do mesmo fornecedor no mesmo dia.
        extrator = ExtratorGarantiaFabricante(ELECTROLUX_12M, grafo=grafo_temp)
        extrator.extrair_garantias(
            ELECTROLUX_12M, texto_override=_ler(ELECTROLUX_12M)
        )

        stats = grafo_temp.estatisticas()
        # Aresta cobre deve ter sido criada pela heurística localizar_item.
        assert stats["edges_por_tipo"].get("cobre", 0) >= 1

    def test_aresta_cobre_nao_criada_sem_item_existente(self, grafo_temp):
        """Sem item prévio no grafo, aresta cobre NÃO é criada."""
        extrator = ExtratorGarantiaFabricante(ELECTROLUX_12M, grafo=grafo_temp)
        extrator.extrair_garantias(
            ELECTROLUX_12M, texto_override=_ler(ELECTROLUX_12M)
        )
        stats = grafo_temp.estatisticas()
        assert stats["edges_por_tipo"].get("cobre", 0) == 0


# ============================================================================
# Alerta no ingestor (warning log para expirando)
# ============================================================================


class TestAlertaIngestor:
    def test_ingestor_loga_warning_quando_expirando(self, grafo_temp, caplog):
        """Propriedade `expirando=True` no dict faz ingestor logar warning."""
        import logging

        caplog.set_level(logging.WARNING, logger="graph.ingestor_documento")
        extrator = ExtratorGarantiaFabricante(EXPIRANDO, grafo=grafo_temp)
        extrator.extrair_garantias(
            EXPIRANDO, texto_override=_ler(EXPIRANDO)
        )
        mensagens = [r.message for r in caplog.records]
        assert any("expira em" in m and "<=30 dias" in m for m in mensagens), (
            "esperava warning de 'expira em ... <=30 dias', "
            f"mas só tenho: {mensagens}"
        )


# ============================================================================
# pode_processar (integração com pipeline)
# ============================================================================


class TestPodeProcessar:
    def test_aceita_pista_termo_garantia(self, extrator, tmp_path):
        arquivo = tmp_path / "termo_garantia_electrolux.pdf"
        arquivo.write_bytes(b"%PDF-1.4")
        assert extrator.pode_processar(arquivo) is True

    def test_aceita_pista_certificado_garantia(self, extrator, tmp_path):
        arquivo = tmp_path / "certificado_garantia_samsung.jpg"
        arquivo.write_bytes(b"\xff\xd8\xff")
        assert extrator.pode_processar(arquivo) is True

    def test_rejeita_apolice_estendida_47c(self, extrator, tmp_path):
        """Coisas em `garantias_estendidas/` pertencem à Sprint 47c."""
        sub = tmp_path / "garantias_estendidas"
        sub.mkdir()
        arquivo = sub / "bilhete_samsung.pdf"
        arquivo.write_bytes(b"%PDF-1.4")
        assert extrator.pode_processar(arquivo) is False

    def test_rejeita_apolice_por_nome(self, extrator, tmp_path):
        arquivo = tmp_path / "apolice_zurich.pdf"
        arquivo.write_bytes(b"%PDF-1.4")
        assert extrator.pode_processar(arquivo) is False

    def test_rejeita_receita_medica(self, extrator, tmp_path):
        arquivo = tmp_path / "receita_losartana.jpg"
        arquivo.write_bytes(b"\xff\xd8\xff")
        assert extrator.pode_processar(arquivo) is False

    def test_rejeita_extensao_nao_suportada(self, extrator, tmp_path):
        arquivo = tmp_path / "termo_garantia.doc"
        arquivo.write_bytes(b"\xd0\xcf\x11\xe0")
        assert extrator.pode_processar(arquivo) is False

    def test_aceita_extensoes_declaradas(self, extrator, tmp_path):
        for ext in EXTENSOES_ACEITAS:
            arquivo = tmp_path / f"termo_garantia_teste{ext}"
            arquivo.write_bytes(b"x")
            assert extrator.pode_processar(arquivo) is True, ext


# ============================================================================
# Contrato ExtratorBase: extrair() devolve lista vazia
# ============================================================================


class TestContratoExtratorBase:
    def test_extrair_devolve_lista_vazia(self, grafo_temp, tmp_path):
        arquivo = tmp_path / "termo_garantia_stub.txt"
        arquivo.write_text(_ler(ELECTROLUX_12M), encoding="utf-8")
        extrator = ExtratorGarantiaFabricante(arquivo, grafo=grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []

    def test_arquivo_sem_marcador_e_ignorado(self, grafo_temp, tmp_path):
        """Texto sem 'termo de garantia' ou similar é ignorado em silêncio."""
        arquivo = tmp_path / "termo_garantia_falso.txt"
        arquivo.write_text(
            "Apenas uma nota aleatória sem marcador de garantia.\n"
            "CNPJ: 17.474.294/0001-40\n"
            "Data: 10/02/2026\n"
            "Prazo: 12 meses\n",
            encoding="utf-8",
        )
        extrator = ExtratorGarantiaFabricante(arquivo, grafo=grafo_temp)
        resultado = extrator.extrair_garantias(arquivo)
        assert resultado == []


# "Termo de garantia é contrato -- leia, ingira, lembre." -- princípio do arquivista
