"""Testes do extrator de recibo não-fiscal (Sprint 47).

Padrão canônico do projeto (ver `test_cupom_termico_foto.py`,
`test_nfce_pdf.py`): fixtures `.txt` em `tests/fixtures/recibos/`
reproduzem texto OCR pré-decodificado. O extrator aceita
`texto_override` para rodar testes sem tesseract real.

Acceptance criteria da Sprint 47:
  - Extrai valor, data, contraparte de comprovante de Pix impresso
  - Voucher de serviço (iFood, 99) identificado pelo layout
  - Sem itens individuais (ok: documento sem `itens` no grafo)
  - Confidence < 60% manda para supervisor
  - Acentuação PT-BR correta
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.extractors.recibo_nao_fiscal import (
    LIMIAR_CONFIDENCE_OK,
    ExtratorReciboNaoFiscal,
    _aplicar_layout,
    _carregar_layouts,
    _cnpj_placeholder,
    _detectar_layout,
    _parse_data_para_iso,
    _parse_valor,
)
from src.graph.db import GrafoDB

FIXTURES = Path(__file__).parent / "fixtures" / "recibos"
PIX_NUBANK = FIXTURES / "pix_nubank.txt"
PIX_ITAU = FIXTURES / "pix_itau.txt"
VOUCHER_IFOOD = FIXTURES / "voucher_ifood.txt"
VOUCHER_99 = FIXTURES / "voucher_99.txt"
TEXTO_AMBIGUO = FIXTURES / "texto_ambiguo.txt"


def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorReciboNaoFiscal:
    """Extrator com diretórios temporários, sem OCR real."""
    placeholder = tmp_path / "recibo_stub.jpg"
    placeholder.write_bytes(b"\xff\xd8\xff")
    return ExtratorReciboNaoFiscal(
        placeholder,
        diretorio_cache=tmp_path / "cache",
        diretorio_conferir=tmp_path / "conferir",
        diretorio_propostas=tmp_path / "propostas",
    )


@pytest.fixture()
def grafo_temp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


# ============================================================================
# Carregamento de layouts
# ============================================================================


class TestCarregamentoLayouts:
    def test_carrega_pelo_menos_4_layouts(self):
        layouts = _carregar_layouts()
        ids = {layout["id"] for layout in layouts}
        assert {"pix_nubank", "pix_itau", "voucher_ifood", "voucher_99"}.issubset(ids)

    def test_layouts_tem_regex_valor_e_data_compilados(self):
        layouts = _carregar_layouts()
        for layout in layouts:
            assert layout["regex_valor"] is not None
            assert layout["regex_data"] is not None

    def test_layouts_tem_sinal_default_despesa(self):
        layouts = _carregar_layouts()
        for layout in layouts:
            assert layout["sinal"] in {"despesa", "receita"}


# ============================================================================
# Detecção de layout por identificador
# ============================================================================


class TestDetectorLayout:
    def test_detecta_pix_nubank(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        assert layout is not None
        assert layout["id"] == "pix_nubank"

    def test_detecta_pix_itau(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_ITAU), layouts)
        assert layout is not None
        assert layout["id"] == "pix_itau"

    def test_detecta_voucher_ifood(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_IFOOD), layouts)
        assert layout is not None
        assert layout["id"] == "voucher_ifood"

    def test_detecta_voucher_99(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_99), layouts)
        assert layout is not None
        assert layout["id"] == "voucher_99"

    def test_texto_sem_pista_devolve_none(self):
        layouts = _carregar_layouts()
        assert _detectar_layout(_ler(TEXTO_AMBIGUO), layouts) is None

    def test_texto_vazio_devolve_none(self):
        assert _detectar_layout("", _carregar_layouts()) is None


# ============================================================================
# Parsing de valor e data
# ============================================================================


class TestParseValor:
    def test_valor_com_virgula_decimal(self):
        assert _parse_valor("1.234,56") == pytest.approx(1234.56)

    def test_valor_simples(self):
        assert _parse_valor("50,00") == pytest.approx(50.0)

    def test_valor_invalido_devolve_none(self):
        assert _parse_valor("abc") is None

    def test_valor_none_devolve_none(self):
        assert _parse_valor(None) is None


class TestParseData:
    def test_data_numerica(self):
        assert _parse_data_para_iso("15/03/2026") == "2026-03-15"

    def test_data_com_texto_ao_redor(self):
        assert _parse_data_para_iso("foo 05/04/2026 bar") == "2026-04-05"

    def test_data_extenso(self):
        assert _parse_data_para_iso("5 de abril de 2026") == "2026-04-05"

    def test_data_extenso_com_marco_acento(self):
        assert _parse_data_para_iso("10 de março de 2026") == "2026-03-10"

    def test_data_invalida_devolve_none(self):
        assert _parse_data_para_iso("32/13/2026") is None

    def test_data_vazia_devolve_none(self):
        assert _parse_data_para_iso(None) is None
        assert _parse_data_para_iso("") is None


# ============================================================================
# Aplicação de layout (acceptance #1 e #2)
# ============================================================================


class TestAplicarLayoutPixNubank:
    def test_extrai_valor(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_NUBANK))
        assert dados["valor"] == pytest.approx(120.50, abs=0.01)

    def test_extrai_data(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_NUBANK))
        assert dados["data"] == "2026-03-15"

    def test_extrai_contraparte(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_NUBANK))
        assert dados["contraparte"] == "MARIA SILVA DOS SANTOS"

    def test_confianca_cheia_quando_tudo_casa(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_NUBANK))
        assert dados["confianca"] == pytest.approx(1.0)

    def test_sinal_despesa(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_NUBANK), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_NUBANK))
        assert dados["sinal"] == "despesa"


class TestAplicarLayoutPixItau:
    def test_extrai_valor(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_ITAU), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_ITAU))
        assert dados["valor"] == pytest.approx(350.00, abs=0.01)

    def test_extrai_data(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_ITAU), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_ITAU))
        assert dados["data"] == "2026-03-20"

    def test_extrai_contraparte(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(PIX_ITAU), layouts)
        dados = _aplicar_layout(layout, _ler(PIX_ITAU))
        assert dados["contraparte"] == "JOAO PEREIRA LIMA"


class TestAplicarLayoutVoucherIfood:
    def test_extrai_valor_total(self):
        """Voucher iFood tem Subtotal + Taxa + Total; deve capturar Total."""
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_IFOOD), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_IFOOD))
        assert dados["valor"] == pytest.approx(43.90, abs=0.01)

    def test_extrai_data_do_pedido(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_IFOOD), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_IFOOD))
        assert dados["data"] == "2026-04-05"

    def test_extrai_id_pedido_como_descricao(self):
        """Acceptance: descrição do serviço (ID do pedido) preservada."""
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_IFOOD), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_IFOOD))
        assert dados["descricao"] == "4578293"


class TestAplicarLayoutVoucher99:
    def test_extrai_valor_corrida(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_99), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_99))
        assert dados["valor"] == pytest.approx(27.45, abs=0.01)

    def test_extrai_data_corrida(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_99), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_99))
        assert dados["data"] == "2026-04-12"

    def test_extrai_id_corrida(self):
        layouts = _carregar_layouts()
        layout = _detectar_layout(_ler(VOUCHER_99), layouts)
        dados = _aplicar_layout(layout, _ler(VOUCHER_99))
        assert dados["descricao"] == "ABC12345XYZ"


# ============================================================================
# Confiança parcial: só valor, só valor+data, etc.
# ============================================================================


class TestConfiancaParcial:
    def test_apenas_valor_e_data_confianca_0_67(self):
        """Pix sem contraparte legível: confiança ~0.67."""
        layouts = _carregar_layouts()
        layout = _detectar_layout("Nubank\nValor R$ 50,00\nData: 15/03/2026", layouts)
        assert layout is not None
        dados = _aplicar_layout(layout, "Nubank\nValor R$ 50,00\nData: 15/03/2026")
        assert dados["valor"] == pytest.approx(50.0)
        assert dados["data"] == "2026-03-15"
        assert dados["confianca"] == pytest.approx(0.67, abs=0.01)

    def test_apenas_valor_confianca_0_33(self):
        """Só valor casa: confiança baixa, vai para supervisor."""
        layouts = _carregar_layouts()
        layout = _detectar_layout("Nubank\nValor R$ 50,00", layouts)
        dados = _aplicar_layout(layout, "Nubank\nValor R$ 50,00")
        assert dados["confianca"] == pytest.approx(0.33, abs=0.01)


# ============================================================================
# CNPJ placeholder e chave sintética
# ============================================================================


class TestCnpjPlaceholder:
    def test_prefixo_nao_fiscal(self):
        placeholder = _cnpj_placeholder("0123456789abcdef")
        assert placeholder.startswith("_NAO_FISCAL_")

    def test_determinismo(self):
        """Mesmo hash -> mesmo placeholder (idempotência no grafo)."""
        assert _cnpj_placeholder("abc123") == _cnpj_placeholder("abc123")

    def test_diferencia_de_cnpj_real(self):
        """Placeholder não colide com formato SEFAZ XX.XXX.XXX/XXXX-XX."""
        placeholder = _cnpj_placeholder("0123456789abcdef")
        assert "/" not in placeholder
        assert "-" not in placeholder


# ============================================================================
# Fluxo end-to-end com texto_override
# ============================================================================


class TestFluxoCompleto:
    def test_pix_nubank_via_override(self, extrator: ExtratorReciboNaoFiscal):
        resultado = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(PIX_NUBANK))
        assert resultado["layout"] == "pix_nubank"
        assert resultado["confianca"] == pytest.approx(1.0)
        assert resultado["dados"]["valor"] == pytest.approx(120.50)
        assert resultado["dados"]["contraparte"] == "MARIA SILVA DOS SANTOS"
        assert resultado["documento"]["chave_44"].startswith("RECIBO|pix_nubank|")
        assert resultado["documento"]["cnpj_emitente"].startswith("_NAO_FISCAL_")

    def test_voucher_ifood_via_override(self, extrator: ExtratorReciboNaoFiscal):
        resultado = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(VOUCHER_IFOOD))
        assert resultado["layout"] == "voucher_ifood"
        assert resultado["dados"]["valor"] == pytest.approx(43.90)
        assert resultado["dados"]["descricao"] == "4578293"

    def test_texto_ambiguo_retorna_layout_none(self, extrator: ExtratorReciboNaoFiscal):
        """Acceptance: texto sem pista de layout -> layout None, confiança 0."""
        resultado = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(TEXTO_AMBIGUO))
        assert resultado["layout"] is None
        assert resultado["confianca"] == 0.0
        assert resultado["documento"] == {}

    def test_documento_tem_tipo_recibo_nao_fiscal(self, extrator: ExtratorReciboNaoFiscal):
        resultado = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(PIX_ITAU))
        assert resultado["documento"]["tipo_documento"] == "recibo_nao_fiscal"

    def test_chave_44_sintetica_determinista(self, extrator: ExtratorReciboNaoFiscal):
        """Mesmo texto -> mesma chave (idempotente para grafo)."""
        r1 = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(PIX_NUBANK))
        r2 = extrator.extrair_recibo(extrator.caminho, texto_override=_ler(PIX_NUBANK))
        assert r1["documento"]["chave_44"] == r2["documento"]["chave_44"]


# ============================================================================
# Fallback supervisor (acceptance #4: confidence < 60%)
# ============================================================================


class TestFallbackSupervisor:
    def test_texto_ambiguo_vai_para_fallback(self, tmp_path: Path):
        """Acceptance #4: layout não detectado -> proposta + diretório conferir."""
        foto = tmp_path / "recibo.jpg"
        foto.write_bytes(b"\xff\xd8\xff stub")
        ext = ExtratorReciboNaoFiscal(
            foto,
            diretorio_cache=tmp_path / "cache",
            diretorio_conferir=tmp_path / "conferir",
            diretorio_propostas=tmp_path / "propostas",
        )
        with patch.object(
            ext,
            "_rodar_ocr_com_cache",
            return_value=(_ler(TEXTO_AMBIGUO), 95.0),
        ):
            ext.extrair()

        propostas = list((tmp_path / "propostas").glob("*.md"))
        assert len(propostas) == 1
        conteudo = propostas[0].read_text(encoding="utf-8")
        assert "Conferência manual" in conteudo
        assert "Layout detectado: (nenhum)" in conteudo

        conferidos = list((tmp_path / "conferir").iterdir())
        assert len(conferidos) == 1

    def test_confidence_ocr_baixa_vai_para_fallback(self, tmp_path: Path):
        """Acceptance #4: confidence OCR < 60% aciona fallback mesmo com layout OK."""
        foto = tmp_path / "recibo.jpg"
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(
            foto,
            diretorio_cache=tmp_path / "cache",
            diretorio_conferir=tmp_path / "conferir",
            diretorio_propostas=tmp_path / "propostas",
        )
        with patch.object(
            ext,
            "_rodar_ocr_com_cache",
            return_value=(_ler(PIX_NUBANK), 45.0),  # 45% < 60% limiar
        ):
            ext.extrair()

        propostas = list((tmp_path / "propostas").glob("*.md"))
        assert len(propostas) == 1

    def test_confianca_parse_baixa_vai_para_fallback(self, tmp_path: Path):
        """Layout detecta mas só 1 de 3 campos casa -> fallback."""
        foto = tmp_path / "recibo.jpg"
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(
            foto,
            diretorio_cache=tmp_path / "cache",
            diretorio_conferir=tmp_path / "conferir",
            diretorio_propostas=tmp_path / "propostas",
        )
        texto_incompleto = "Nubank\nValor R$ 50,00\n"  # sem data nem contraparte
        with patch.object(
            ext,
            "_rodar_ocr_com_cache",
            return_value=(texto_incompleto, 95.0),
        ):
            ext.extrair()

        propostas = list((tmp_path / "propostas").glob("*.md"))
        assert len(propostas) == 1

    def test_fallback_idempotente_por_hash_do_conteudo(self, tmp_path: Path):
        """Reprocessar mesmo recibo NÃO cria propostas duplicadas (lição Sprint 45)."""
        foto = tmp_path / "recibo.jpg"
        foto.write_bytes(b"\xff\xd8\xff repetido")
        ext = ExtratorReciboNaoFiscal(
            foto,
            diretorio_cache=tmp_path / "cache",
            diretorio_conferir=tmp_path / "conferir",
            diretorio_propostas=tmp_path / "propostas",
        )
        with patch.object(
            ext,
            "_rodar_ocr_com_cache",
            return_value=(_ler(TEXTO_AMBIGUO), 95.0),
        ):
            ext.extrair()
            ext.extrair()
            ext.extrair()

        propostas = list((tmp_path / "propostas").glob("*.md"))
        assert len(propostas) == 1  # ainda 1, não 3

    def test_limiar_confidence_ok_60_conforme_spec(self):
        """Sprint 47 acceptance: 'confidence < 60% manda para supervisor'."""
        assert LIMIAR_CONFIDENCE_OK == 60.0


# ============================================================================
# Ingestão no grafo
# ============================================================================


class TestGrafoIngestao:
    def test_recibo_aprovado_cria_documento_no_grafo(
        self,
        extrator: ExtratorReciboNaoFiscal,
        grafo_temp: GrafoDB,
    ):
        """Acceptance: documento com tipo=recibo_nao_fiscal no grafo."""
        extrator._grafo = grafo_temp
        with patch.object(
            extrator,
            "_rodar_ocr_com_cache",
            return_value=(_ler(PIX_NUBANK), 85.0),
        ):
            extrator.extrair()

        cursor = grafo_temp._conn.execute("SELECT COUNT(*) FROM node WHERE tipo = 'documento'")
        assert cursor.fetchone()[0] == 1

        cursor = grafo_temp._conn.execute("SELECT COUNT(*) FROM node WHERE tipo = 'fornecedor'")
        assert cursor.fetchone()[0] == 1  # CNPJ placeholder entra como fornecedor

    def test_recibo_sem_itens_individuais(
        self,
        extrator: ExtratorReciboNaoFiscal,
        grafo_temp: GrafoDB,
    ):
        """Acceptance: recibo NUNCA cria nodes de tipo 'item'."""
        extrator._grafo = grafo_temp
        with patch.object(
            extrator,
            "_rodar_ocr_com_cache",
            return_value=(_ler(VOUCHER_IFOOD), 85.0),
        ):
            extrator.extrair()

        cursor = grafo_temp._conn.execute("SELECT COUNT(*) FROM node WHERE tipo = 'item'")
        assert cursor.fetchone()[0] == 0

    def test_grafo_ingestao_idempotente(
        self,
        extrator: ExtratorReciboNaoFiscal,
        grafo_temp: GrafoDB,
    ):
        """Reprocessar mesmo recibo NÃO duplica nodes."""
        extrator._grafo = grafo_temp
        with patch.object(
            extrator,
            "_rodar_ocr_com_cache",
            return_value=(_ler(PIX_ITAU), 85.0),
        ):
            extrator.extrair()
            extrator.extrair()

        cursor = grafo_temp._conn.execute("SELECT COUNT(*) FROM node WHERE tipo = 'documento'")
        assert cursor.fetchone()[0] == 1


# ============================================================================
# Integração com pipeline
# ============================================================================


class TestIntegracaoPipeline:
    def test_extrator_registrado_no_pipeline(self):
        """Acceptance: registrado em _descobrir_extratores."""
        from src.pipeline import _descobrir_extratores

        classes = _descobrir_extratores()
        nomes = [cls.__name__ for cls in classes]
        assert "ExtratorReciboNaoFiscal" in nomes

    def test_extrator_registrado_por_ultimo_baixa_prioridade(self):
        """Acceptance: catch-all depois dos extratores fiscais."""
        from src.pipeline import _descobrir_extratores

        classes = _descobrir_extratores()
        nomes = [cls.__name__ for cls in classes]
        # ExtratorReciboNaoFiscal deve vir DEPOIS de cupom, NFC-e, DANFE
        for nome_fiscal in (
            "ExtratorCupomTermicoFoto",
            "ExtratorNfcePDF",
            "ExtratorDanfePDF",
        ):
            if nome_fiscal in nomes:
                assert nomes.index("ExtratorReciboNaoFiscal") > nomes.index(nome_fiscal)


class TestPodeProcessar:
    def test_aceita_jpg_em_pasta_recibos(self, tmp_path: Path):
        foto = tmp_path / "recibos" / "pix.jpg"
        foto.parent.mkdir(parents=True)
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is True

    def test_aceita_png_com_pista_pix_no_nome(self, tmp_path: Path):
        foto = tmp_path / "comprovante_pix_2026.png"
        foto.write_bytes(b"\x89PNG")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is True

    def test_aceita_pdf_em_pasta_comprovantes(self, tmp_path: Path):
        arq = tmp_path / "comprovantes" / "pix_itau.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"%PDF")
        ext = ExtratorReciboNaoFiscal(arq)
        assert ext.pode_processar(arq) is True

    def test_aceita_heic(self, tmp_path: Path):
        foto = tmp_path / "voucher" / "ifood.heic"
        foto.parent.mkdir(parents=True)
        foto.write_bytes(b"stub")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is True

    def test_nao_colide_com_energia_ocr(self, tmp_path: Path):
        foto = tmp_path / "dividas_luz" / "conta.jpg"
        foto.parent.mkdir(parents=True)
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is False

    def test_nao_colide_com_cupom_termico(self, tmp_path: Path):
        """Pasta 'cupom' é do extrator de cupom fiscal, não de recibo."""
        foto = tmp_path / "cupom" / "pix.jpg"  # mesmo com pista 'pix' no nome
        foto.parent.mkdir(parents=True)
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is False

    def test_nao_colide_com_nfce(self, tmp_path: Path):
        foto = tmp_path / "nfce" / "comprovante.jpg"
        foto.parent.mkdir(parents=True)
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is False

    def test_nao_processa_extensao_invalida(self, tmp_path: Path):
        arq = tmp_path / "recibo.xlsx"
        arq.write_bytes(b"stub")
        ext = ExtratorReciboNaoFiscal(arq)
        assert ext.pode_processar(arq) is False

    def test_nao_processa_imagem_sem_pista(self, tmp_path: Path):
        """Imagem genérica sem pista no nome nem na pasta: recusa."""
        foto = tmp_path / "foto_aleatoria.jpg"
        foto.write_bytes(b"\xff\xd8\xff")
        ext = ExtratorReciboNaoFiscal(foto)
        assert ext.pode_processar(foto) is False


# ============================================================================
# Leitura de PDF nativo (sem OCR)
# ============================================================================


class TestLeituraPdfNativo:
    def test_pdf_usa_pdfplumber_nao_ocr(self, extrator: ExtratorReciboNaoFiscal):
        """PDF nativo pula OCR; confidence sempre 100."""
        # Mock do pdfplumber em _obter_texto
        pdf_stub = extrator.caminho.with_suffix(".pdf")
        pdf_stub.write_bytes(b"%PDF-1.4 stub")

        with patch("pdfplumber.open") as mock_open:
            ctx = mock_open.return_value.__enter__.return_value
            ctx.pages = [_PaginaFake(_ler(PIX_ITAU))]
            texto, confidence = extrator._obter_texto(pdf_stub)

        assert texto.strip()
        assert confidence == 100.0


class _PaginaFake:
    """Stub de página pdfplumber para testes sem PDF real."""

    def __init__(self, texto: str) -> None:
        self._texto = texto

    def extract_text(self) -> str:
        return self._texto


# "A memória do recibo é maior que a do banco." -- princípio do registrador
