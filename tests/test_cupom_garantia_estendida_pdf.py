"""Testes do extrator de Cupom Bilhete de Seguro -- Garantia Estendida (Sprint 47c).

As fixtures `.txt` em `tests/fixtures/garantias_estendidas/` reproduzem o texto
extraído de PDFs reais com CPF anonimizado. O extrator aceita `texto_override`
para viabilizar testes sem dependência de binários PDF/imagem.

Cobertura por tipo de fixture:

- `bilhete_nativo_base_p55.txt`     -- PDF nativo com glyphs ruins (CNP), Q BILHETE, 5.À.)
- `bilhete_nativo_controle_p55.txt` -- PDF nativo com glyphs parciais (CNP), D6238)
- `bilhete_scan_controle_p55.txt`   -- Scan OCR (CNPJ], Kazão Sacial)
- `bilhete_scan_base_p55.txt`       -- Scan OCR (CNPJ:, 00,776.574, SEC, Riaco)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.extractors.cupom_garantia_estendida_pdf import (
    ExtratorCupomGarantiaEstendida,
    _carregar_seguradoras,
    e_cupom_garantia_estendida,
)
from src.graph.db import GrafoDB

FIXTURES = Path(__file__).parent / "fixtures" / "garantias_estendidas"


# ============================================================================
# Utilitários
# ============================================================================


def _carregar_fixture(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


@pytest.fixture()
def extrator(tmp_path: Path) -> ExtratorCupomGarantiaEstendida:
    arquivo_fantasma = tmp_path / "placeholder.pdf"
    arquivo_fantasma.write_bytes(b"%PDF-1.4\n")
    return ExtratorCupomGarantiaEstendida(arquivo_fantasma)


@pytest.fixture()
def grafo_temp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


# ============================================================================
# Detector
# ============================================================================


class TestDetector:
    def test_detecta_bilhete_pdf_native(self):
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        assert e_cupom_garantia_estendida(texto) is True

    def test_detecta_bilhete_scan_via_ocr(self):
        texto = _carregar_fixture("bilhete_scan_controle_p55.txt")
        assert e_cupom_garantia_estendida(texto) is True

    def test_detecta_mesmo_com_marcador_quebrado(self):
        # Fixture 1 tem `Q BILHETE` em vez de `O BILHETE`; detector aceita glyph.
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        assert "Q BILHETE" in texto  # sanity
        assert e_cupom_garantia_estendida(texto) is True

    def test_rejeita_texto_sem_marcadores(self):
        assert e_cupom_garantia_estendida("Nota fiscal comum, sem SUSEP.") is False

    def test_rejeita_texto_com_apenas_1_marcador(self):
        # Apenas "GARANTIA ESTENDIDA" sem os outros 2 -- não é suficiente.
        assert (
            e_cupom_garantia_estendida(
                "Produto com GARANTIA ESTENDIDA de 12 meses sem cupom SUSEP."
            )
            is False
        )


# ============================================================================
# Parser -- campos canônicos
# ============================================================================


class TestExtracaoCamposCanonicos:
    @pytest.mark.parametrize(
        "fixture",
        [
            "bilhete_nativo_base_p55.txt",
            "bilhete_nativo_controle_p55.txt",
            "bilhete_scan_controle_p55.txt",
            "bilhete_scan_base_p55.txt",
        ],
    )
    def test_todos_campos_criticos_preenchidos(
        self,
        extrator: ExtratorCupomGarantiaEstendida,
        fixture: str,
    ):
        texto = _carregar_fixture(fixture)
        bilhetes = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)
        assert len(bilhetes) == 1
        b = bilhetes[0]
        criticos = [
            "numero_bilhete",
            "processo_susep",
            "cpf_segurado",
            "bem_segurado",
            "premio_total",
            "vigencia_inicio",
            "vigencia_fim",
            "seguradora_cnpj",
            "varejo_cnpj",
            "data_emissao",
        ]
        faltando = [campo for campo in criticos if not b.get(campo)]
        assert not faltando, f"campos críticos faltando: {faltando}"

    def test_extrai_15_digitos_bilhete_individual(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["numero_bilhete"] == "781000129322124"
        assert len(bilhete["numero_bilhete"]) == 15
        assert bilhete["numero_bilhete"].isdigit()

    def test_extrai_processo_susep_formato_canonico(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        # Nativo tem `15414 .900147/2014-11` (espaço extra); normalizador deve
        # produzir `XXXXX.XXXXXX/XXXX-XX`.
        assert bilhete["processo_susep"] == "15414.900147/2014-11"

    def test_vigencia_e_cobertura_extraidas_como_iso(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["vigencia_inicio"] == "2026-04-19"
        assert bilhete["vigencia_fim"] == "2029-04-19"
        assert bilhete["cobertura_inicio"] == "2027-04-19"
        assert bilhete["cobertura_fim"] == "2029-04-19"

    def test_valores_numericos_parseados_em_float(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["premio_liquido"] == pytest.approx(50.27)
        assert bilhete["iof"] == pytest.approx(3.71)
        assert bilhete["premio_total"] == pytest.approx(53.98)
        assert bilhete["valor_bem"] == pytest.approx(179.99)
        # Invariante contábil: prêmio total = líquido + IOF (com tolerância de 1 cent).
        assert (
            abs(bilhete["premio_total"] - bilhete["premio_liquido"] - bilhete["iof"])
            <= 0.01
        )


# ============================================================================
# Glyph-tolerance específica
# ============================================================================


class TestGlyphTolerance:
    def test_glyph_tolerante_cnpj_corrompido_no_pdf_native(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Fixture 1 tem `CNP):` (glyph J->\\)) -- extrator deve extrair CNPJ do varejo."""
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        assert "CNP)" in texto and "CNPJ" not in texto.split("DADOS DA SEGURADORA")[0]
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["varejo_cnpj"] == "00.776.574/0160-79"
        assert bilhete["seguradora_cnpj"] == "61.074.175/0001-38"

    def test_glyph_tolerante_cnpj_scan_com_bracket(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Fixture 3 tem `CNPJ]:` (OCR de scan inseriu ]) -- regex CNP+GLYPH_J+ resolve."""
        texto = _carregar_fixture("bilhete_scan_controle_p55.txt")
        assert "CNPJ]" in texto
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["varejo_cnpj"] == "00.776.574/0160-79"

    def test_glyph_tolerante_separador_virgula_ocr(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Fixture 4 tem `00,776.574` (OCR trocou `.` por `,`) -- separador tolerante."""
        texto = _carregar_fixture("bilhete_scan_base_p55.txt")
        assert "00,776.574" in texto
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        assert bilhete["varejo_cnpj"] == "00.776.574/0160-79"

    def test_codigo_susep_normalizado_via_yaml_quando_glyph_d_em_zero(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Fixture 2 tem `D6238` (glyph 0->D) -- enrich por CNPJ do YAML corrige."""
        texto = _carregar_fixture("bilhete_nativo_controle_p55.txt")
        assert "D6238" in texto
        bilhete = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto)[0]
        # O YAML define SUSEP canônico 06238 para o CNPJ da MAPFRE; enrich sobrescreve.
        assert bilhete["seguradora_codigo_susep"] == "06238"

    def test_ri_asz_co_cobre_todas_variantes_ocr(
        self, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Fixture 4 tem `Riaco`, fixture 1 tem `Rizco`, fixture 3 tem `Risco`."""
        for nome in [
            "bilhete_scan_base_p55.txt",
            "bilhete_nativo_base_p55.txt",
            "bilhete_scan_controle_p55.txt",
        ]:
            bilhete = extrator.extrair_bilhetes(
                extrator.caminho, texto_override=_carregar_fixture(nome)
            )[0]
            assert bilhete["cobertura_inicio"] is not None, f"cobertura None em {nome}"


# ============================================================================
# Seguradora + YAML
# ============================================================================


class TestSeguradoraYaml:
    def test_seguradora_mapfre_resolvida_via_yaml(self):
        seguradoras = _carregar_seguradoras()
        assert "61.074.175/0001-38" in seguradoras
        mapfre = seguradoras["61.074.175/0001-38"]
        assert mapfre["razao_social"].startswith("MAPFRE")
        assert mapfre["codigo_susep"] == "06238"

    def test_cardif_tambem_cadastrada(self):
        seguradoras = _carregar_seguradoras()
        cnpjs = set(seguradoras.keys())
        assert any("CARDIF" in seguradoras[c]["razao_social"].upper() for c in cnpjs)

    def test_cnpj_desconhecido_gera_proposta(
        self,
        extrator: ExtratorCupomGarantiaEstendida,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Quando seguradora.cnpj não está no YAML, extrator registra proposta."""
        monkeypatch.setattr(
            "src.extractors.cupom_garantia_estendida_pdf.PATH_PROPOSTAS",
            tmp_path / "propostas",
        )
        ext_vazio = ExtratorCupomGarantiaEstendida(
            extrator.caminho, seguradoras_cfg={}
        )
        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        ext_vazio.extrair_bilhetes(ext_vazio.caminho, texto_override=texto)
        propostas_criadas = list((tmp_path / "propostas").glob("*.md"))
        assert len(propostas_criadas) == 1
        assert "MAPFRE" in propostas_criadas[0].read_text(encoding="utf-8")


# ============================================================================
# Grafo -- ingestão completa
# ============================================================================


class TestIngestaoGrafo:
    def test_grafo_recebe_apolice_seguradora_varejo(
        self,
        grafo_temp: GrafoDB,
        extrator: ExtratorCupomGarantiaEstendida,
    ):
        from src.graph.ingestor_documento import ingerir_apolice

        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(
            extrator.caminho, texto_override=texto
        )[0]
        ingerir_apolice(grafo_temp, bilhete, caminho_arquivo=extrator.caminho)

        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"].get("apolice") == 1
        assert stats["nodes_por_tipo"].get("seguradora") == 1
        assert stats["nodes_por_tipo"].get("fornecedor") == 1
        assert stats["nodes_por_tipo"].get("periodo") == 1

        assert stats["edges_por_tipo"].get("emitida_por") == 1
        assert stats["edges_por_tipo"].get("vendida_em") == 1
        assert stats["edges_por_tipo"].get("ocorre_em") == 1
        # Aresta `assegura` não existe porque nenhum item foi pré-inserido.
        assert "assegura" not in stats["edges_por_tipo"]

    def test_apolice_chaveada_por_numero_bilhete(
        self, grafo_temp: GrafoDB, extrator: ExtratorCupomGarantiaEstendida
    ):
        from src.graph.ingestor_documento import ingerir_apolice

        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(
            extrator.caminho, texto_override=texto
        )[0]
        ingerir_apolice(grafo_temp, bilhete, caminho_arquivo=extrator.caminho)
        nodes_apolice = grafo_temp.listar_nodes("apolice")
        assert len(nodes_apolice) == 1
        assert nodes_apolice[0].nome_canonico == "781000129322124"

    def test_pdf_notas_pg1_e_pg2_geram_mesmo_bilhete_id(
        self, grafo_temp: GrafoDB, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Páginas 1 e 2 do pdf_notas.pdf têm o mesmo bilhete 781000129322124.

        Se a duplicata escapar do filtro de envelopes da Sprint 41 e chegar ao
        ingestor, o upsert por `numero_bilhete` tem que evitar duplicar o nó
        apolice e as arestas associadas (idempotência da Sprint 42).
        """
        from src.graph.ingestor_documento import ingerir_apolice

        texto_pg1 = _carregar_fixture("bilhete_nativo_base_p55.txt")
        texto_pg2 = _carregar_fixture("bilhete_scan_base_p55.txt")
        b1 = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto_pg1)[0]
        b2 = extrator.extrair_bilhetes(extrator.caminho, texto_override=texto_pg2)[0]
        assert b1["numero_bilhete"] == b2["numero_bilhete"]

        id1 = ingerir_apolice(grafo_temp, b1, caminho_arquivo=extrator.caminho)
        id2 = ingerir_apolice(grafo_temp, b2, caminho_arquivo=extrator.caminho)
        assert id1 == id2
        stats = grafo_temp.estatisticas()
        assert stats["nodes_por_tipo"]["apolice"] == 1
        # Cada tipo de aresta permanece único entre o mesmo par de nós
        assert stats["edges_por_tipo"]["emitida_por"] == 1
        assert stats["edges_por_tipo"]["vendida_em"] == 1

    def test_aresta_assegura_criada_quando_item_ja_existe_no_grafo(
        self, grafo_temp: GrafoDB, extrator: ExtratorCupomGarantiaEstendida
    ):
        """Se Sprint 44/44b já tiver inserido o Item da NFC-e, aresta `assegura` aparece."""
        from src.graph.ingestor_documento import ingerir_apolice

        # Simula NFC-e previamente inserida
        grafo_temp.upsert_node(
            "item",
            "item_base_p55_2026-04-19",
            metadata={
                "descricao": "BASE DE CARREGAMENTO DO CONTROLE P55",
                "cnpj_varejo": "00.776.574/0160-79",
                "data_compra": "2026-04-19",
            },
        )

        texto = _carregar_fixture("bilhete_nativo_base_p55.txt")
        bilhete = extrator.extrair_bilhetes(
            extrator.caminho, texto_override=texto
        )[0]
        ingerir_apolice(grafo_temp, bilhete, caminho_arquivo=extrator.caminho)

        edges = grafo_temp.listar_edges(tipo="assegura")
        assert len(edges) == 1


# ============================================================================
# Pipeline + pode_processar
# ============================================================================


class TestPodeProcessar:
    def test_pode_processar_por_caminho(
        self, extrator: ExtratorCupomGarantiaEstendida, tmp_path: Path
    ):
        arq = tmp_path / "andre" / "garantias_estendidas" / "GARANTIA_EST_x.pdf"
        arq.parent.mkdir(parents=True)
        arq.write_bytes(b"%PDF-1.4\n")
        assert extrator.pode_processar(arq) is True

    def test_rejeita_extensao_incompativel(
        self, extrator: ExtratorCupomGarantiaEstendida, tmp_path: Path
    ):
        arq = tmp_path / "garantias_estendidas" / "bilhete.xml"
        arq.parent.mkdir(parents=True)
        arq.write_text("xml", encoding="utf-8")
        assert extrator.pode_processar(arq) is False

    def test_extrair_retorna_lista_vazia_de_transacao(
        self,
        extrator: ExtratorCupomGarantiaEstendida,
        grafo_temp: GrafoDB,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """`extrair()` devolve [] (prêmio não duplica transação bancária)."""
        # Stubs: `_ler_paginas` devolve fixture; grafo é o temporário.
        monkeypatch.setattr(
            extrator,
            "_ler_paginas",
            lambda caminho: [_carregar_fixture("bilhete_nativo_base_p55.txt")],
        )
        monkeypatch.setattr(extrator, "_grafo", grafo_temp)
        resultado = extrator.extrair()
        assert resultado == []
        # Side-effect: apolice no grafo
        assert grafo_temp.estatisticas()["nodes_por_tipo"].get("apolice") == 1


# "Quem promete cobertura assume o futuro alheio." -- princípio atuarial
