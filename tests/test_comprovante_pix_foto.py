"""Testes da infraestrutura do extrator de comprovante PIX foto (Sprint DOC-27).

Cobertura:

1. Entrada YAML ``comprovante_pix_foto`` em ``mappings/tipos_documento.yaml``
   tem campos canônicos (mimes, regex_conteudo, extrator_modulo, pasta).
2. Classifier reconhece os 3 layouts (Itaú/C6/Nubank) via regex tolerante.
3. Extrator ``ExtratorComprovantePixFoto`` aceita/recusa caminhos pela
   estrutura de pastas e nome.
4. Caches canônicos das 3 amostras inbox/ validam contra
   ``mappings/schema_opus_ocr.json``.
5. ``extrair(caminho)`` devolve cache hit quando o JSON canônico existe.
6. ``extrair(caminho)`` devolve stub ``aguardando_supervisor=True`` quando
   o cache não existe (modo supervisor artesanal, ADR-13).
7. ``ExtratorComprovantePixFoto.extrair()`` devolve lista vazia de
   ``Transacao`` mesmo com cache hit (efeito colateral fica para  # noqa: accent
   sprint ``INFRA-LINKAR-PIX-TRANSACAO``).  # noqa: accent

Sprint DOC-27 (2026-05-13).
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from src.extractors.comprovante_pix_foto import (
    ExtratorComprovantePixFoto,
    extrair,
)

RAIZ = Path(__file__).resolve().parents[1]
DIR_INBOX = RAIZ / "inbox"
DIR_CACHE = RAIZ / "data" / "output" / "opus_ocr_cache"
PATH_SCHEMA = RAIZ / "mappings" / "schema_opus_ocr.json"
PATH_YAML = RAIZ / "mappings" / "tipos_documento.yaml"

# SHAs dos 3 caches reais transcritos artesanalmente em 2026-05-13
SHA_ITAU = "2a0d6ee773d773580c56ceef5b8b16be7507d8cbe28cfd7d1918e1066c6e44ce"
SHA_C6 = "3d82d81c6e9d8d5cf0e607dd5c1b4793f9e2f24bde12b8122fdbbb31dc501010"
SHA_NUBANK = "bb6abe1ca9ddf575530016b4966cf3ebb7e89aebdadb396c67af1e9789531a2b"


@pytest.fixture(scope="module")
def schema_opus() -> dict:
    return json.loads(PATH_SCHEMA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def yaml_tipos() -> dict:
    return yaml.safe_load(PATH_YAML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def entrada_pix(yaml_tipos: dict) -> dict:
    for tipo in yaml_tipos["tipos"]:
        if tipo["id"] == "comprovante_pix_foto":
            return tipo
    raise AssertionError("entrada comprovante_pix_foto ausente no YAML")


# ============================================================================
# 1. Entrada YAML canônica
# ============================================================================


class TestEntradaYAML:
    def test_entrada_existe(self, entrada_pix: dict) -> None:
        assert entrada_pix["id"] == "comprovante_pix_foto"
        assert entrada_pix["prioridade"] == "especifico"
        assert entrada_pix["extrator_modulo"] == "src.extractors.comprovante_pix_foto"

    def test_mimes_aceitam_jpeg_png_pdf(self, entrada_pix: dict) -> None:
        mimes = set(entrada_pix["mimes"])
        assert {"image/jpeg", "image/png", "application/pdf"}.issubset(mimes)

    def test_pasta_destino_canonica(self, entrada_pix: dict) -> None:
        assert "comprovantes_pix" in entrada_pix["pasta_destino_template"]
        assert "{pessoa}" in entrada_pix["pasta_destino_template"]

    def test_regex_reconhece_itau(self, entrada_pix: dict) -> None:
        import re

        texto_itau = "Comprovante de Pix\nR$ 900,00\nRealizado em 09/05/2026\nID da transação: ABC"
        regexes = entrada_pix["regex_conteudo"]
        match_count = sum(1 for r in regexes if re.search(r, texto_itau))
        assert match_count >= 2, f"Apenas {match_count} regex casa Itaú (esperado >= 2)"

    def test_regex_reconhece_c6(self, entrada_pix: dict) -> None:
        import re

        texto_c6 = "C6 BANK\nPix realizado!\nID da transação: E318\nChave Pix: +55"
        regexes = entrada_pix["regex_conteudo"]
        match_count = sum(1 for r in regexes if re.search(r, texto_c6))
        assert match_count >= 2

    def test_regex_reconhece_nubank(self, entrada_pix: dict) -> None:
        import re

        texto_nu = "Comprovante de transferência\nTipo de transferência: Pix\nID da transação: E182"
        regexes = entrada_pix["regex_conteudo"]
        match_count = sum(1 for r in regexes if re.search(r, texto_nu))
        assert match_count >= 2


# ============================================================================
# 2. Caches reais validam contra schema canônico
# ============================================================================


class TestCachesReais:
    @pytest.mark.parametrize(
        "sha,nome_destinatario,total",
        [
            (SHA_ITAU, "PANIFICADORA KI-SABOR", 900.0),
            (SHA_C6, "Wesley Ramon Castro Santana", 50.0),
            (SHA_NUBANK, "Vitória Maria Silva dos Santos", 367.65),
        ],
    )
    def test_cache_valida_contra_schema(
        self,
        sha: str,
        nome_destinatario: str,
        total: float,
        schema_opus: dict,
    ) -> None:
        cache = DIR_CACHE / f"{sha}.json"
        if not cache.exists():
            pytest.skip(f"cache {sha[:12]} ausente")
        payload = json.loads(cache.read_text(encoding="utf-8"))
        jsonschema.validate(payload, schema_opus)
        assert payload["tipo_documento"] == "comprovante_pix_foto"
        assert payload["estabelecimento"]["razao_social"] == nome_destinatario
        assert payload["total"] == pytest.approx(total)
        assert payload["forma_pagamento"] == "pix"


# ============================================================================
# 3. Extrator: pode_processar
# ============================================================================


class TestPodeProcessar:
    def test_aceita_jpeg_em_comprovantes_pix(self, tmp_path: Path) -> None:
        p = tmp_path / "pessoa_a" / "comprovantes_pix" / "PIX_2026-05-09_abc12345.jpeg"
        p.parent.mkdir(parents=True)
        p.touch()
        extrator = ExtratorComprovantePixFoto(p)
        assert extrator.pode_processar(p) is True

    def test_aceita_pdf_em_inbox(self, tmp_path: Path) -> None:
        p = tmp_path / "inbox" / "comprovante.pdf"
        p.parent.mkdir(parents=True)
        p.touch()
        extrator = ExtratorComprovantePixFoto(p)
        assert extrator.pode_processar(p) is True

    def test_recusa_extensao_estranha(self, tmp_path: Path) -> None:
        p = tmp_path / "comprovantes_pix" / "doc.xlsx"
        p.parent.mkdir(parents=True)
        p.touch()
        extrator = ExtratorComprovantePixFoto(p)
        assert extrator.pode_processar(p) is False

    def test_recusa_jpeg_em_pasta_neutra(self, tmp_path: Path) -> None:
        p = tmp_path / "fotos_aleatorias" / "ferias.jpeg"
        p.parent.mkdir(parents=True)
        p.touch()
        extrator = ExtratorComprovantePixFoto(p)
        assert extrator.pode_processar(p) is False


# ============================================================================
# 4. extrair() devolve cache hit ou stub aguardando
# ============================================================================


class TestExtrairFuncional:
    def test_cache_hit_devolve_payload_completo(self) -> None:
        foto = DIR_INBOX / "WhatsApp Image 2026-05-13 at 09.32.30.jpeg"
        if not foto.exists():
            pytest.skip("amostra inbox ausente")
        payload = extrair(foto)
        assert payload["sha256"] == SHA_ITAU
        assert payload["tipo_documento"] == "comprovante_pix_foto"
        assert payload["total"] == pytest.approx(900.0)
        assert payload.get("aguardando_supervisor") is not True

    def test_cache_miss_registra_pendente_e_devolve_stub(
        self,
        tmp_path: Path,
    ) -> None:
        # Imagem dummy nova (não tem cache pre-existente)
        imagem_nova = tmp_path / "pix_nova.jpeg"
        imagem_nova.write_bytes(b"fake-jpeg-bytes-para-sha-unico")
        cache_dir = tmp_path / "cache"
        pendentes_dir = tmp_path / "pendentes"
        cache_dir.mkdir()
        pendentes_dir.mkdir()

        from src.extractors.opus_visao import extrair_via_opus

        payload = extrair_via_opus(
            imagem_nova,
            dir_cache=cache_dir,
            dir_pendentes=pendentes_dir,
        )
        assert payload["aguardando_supervisor"] is True
        assert payload["tipo_documento"] == "pendente"
        # Pedido foi registrado
        pendentes_files = list(pendentes_dir.glob("*.txt"))
        assert len(pendentes_files) == 1


# ============================================================================
# 5. Extrator devolve [] de Transacao (efeito colateral só)  # noqa: accent
# ============================================================================


class TestExtrairClasse:
    def test_extrair_devolve_lista_vazia_com_cache_hit(self) -> None:
        foto = DIR_INBOX / "WhatsApp Image 2026-05-13 at 11.25.02.jpeg"
        if not foto.exists():
            pytest.skip("amostra inbox ausente")
        extrator = ExtratorComprovantePixFoto(foto)
        transacoes = extrator.extrair()
        assert transacoes == []

    def test_extrair_sem_cache_devolve_lista_vazia(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        imagem_nova = tmp_path / "pix_dummy.jpeg"
        imagem_nova.write_bytes(b"fake-bytes-2")

        # Redirecionar diretórios padrão para tmp_path
        monkeypatch.setattr(
            "src.extractors.opus_visao.DIR_CACHE_PADRAO", tmp_path / "cache"
        )
        monkeypatch.setattr(
            "src.extractors.opus_visao.DIR_PENDENTES_PADRAO", tmp_path / "pendentes"
        )
        (tmp_path / "cache").mkdir()
        (tmp_path / "pendentes").mkdir()

        extrator = ExtratorComprovantePixFoto(imagem_nova)
        transacoes = extrator.extrair()
        assert transacoes == []
