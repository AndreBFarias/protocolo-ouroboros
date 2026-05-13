"""Testes da infraestrutura ao redor do extrator de cupom fiscal fotografado.

Sprint INFRA-EXTRATOR-CUPOM-FOTO. Cobertura específica desta sprint
(complementar a ``tests/test_cupom_termico_foto.py``):

1. Caches canônicos Opus em ``data/output/opus_ocr_cache/`` para as 4
   amostras reais em ``data/raw/casal/nfs_fiscais/cupom_foto/`` validam
   contra ``mappings/schema_opus_ocr.json``.
2. Função ``ingerir_cupom_foto`` em ``src.graph.ingestor_documento``
   adapta o payload Opus canônico para o ingestor do grafo, criando o
   conjunto correto de nós e arestas.
3. Idempotência: reprocessar o mesmo cupom não duplica nós nem arestas.
4. ``aguardando_supervisor=True`` é rejeitado com ``ValueError``.

Não testa o pipeline ``cupom_termico_foto.py`` em si (refatorado pela
sprint paralela INFRA-EXTRATORES-USAR-OPUS); apenas a infraestrutura
ao redor.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import jsonschema
import pytest

from src.extractors.opus_visao import calcular_sha256, extrair_via_opus
from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    CAMPOS_OBRIGATORIOS_PAYLOAD_OPUS,
    ingerir_cupom_foto,
)

RAIZ = Path(__file__).resolve().parents[1]
DIR_AMOSTRAS = RAIZ / "data" / "raw" / "casal" / "nfs_fiscais" / "cupom_foto"
DIR_CACHE = RAIZ / "data" / "output" / "opus_ocr_cache"
PATH_SCHEMA = RAIZ / "mappings" / "schema_opus_ocr.json"


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def grafo_temp(tmp_path: Path) -> GrafoDB:
    db = GrafoDB(tmp_path / "grafo_teste.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


@pytest.fixture(scope="module")
def schema_opus() -> dict:
    return json.loads(PATH_SCHEMA.read_text(encoding="utf-8"))


def _amostras_jpeg() -> list[Path]:
    if not DIR_AMOSTRAS.exists():
        return []
    return sorted(DIR_AMOSTRAS.glob("CUPOM_*.jpeg"))


def _payload_canonico_minimo() -> dict:
    """Payload mínimo para testes que não dependem de imagem real."""
    return {
        "sha256": "a" * 64,
        "tipo_documento": "cupom_fiscal_foto",
        "estabelecimento": {
            "razao_social": "Mercado Teste LTDA",
            "cnpj": "11.222.333/0001-44",
            "endereco": "Rua Teste 1, Brasilia-DF",
        },
        "data_emissao": "2026-04-15",
        "horario": "10:30:00",
        "operador": "OPERADOR TESTE",
        "itens": [
            {
                "codigo": "7891234567890",
                "descricao": "ARROZ TIPO 1 5KG",
                "qtd": 1,
                "unidade": "UN",
                "valor_unit": 24.90,
                "valor_total": 24.90,
            },
            {
                "codigo": None,
                "descricao": "BANANA PRATA kg",
                "qtd": None,
                "unidade": "kg",
                "valor_unit": None,
                "valor_total": 5.65,
            },
        ],
        "total": 30.55,
        "forma_pagamento": "pix",
        "extraido_via": "opus_supervisor_artesanal",
        "confianca_global": 0.92,
        "ts_extraido": "2026-05-08T13:00:00+00:00",
    }


# ============================================================================
# Caches canônicos: validação contra schema
# ============================================================================


class TestCacheCanonico:
    """Os 4 caches gerados pela sprint validam contra o schema Opus."""

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists(),
        reason="data/raw/casal/nfs_fiscais/cupom_foto/ ausente (gitignore)",
    )
    def test_existem_pelo_menos_3_caches(self):
        if not DIR_CACHE.exists():
            pytest.skip("data/output/opus_ocr_cache/ ainda não seedado")
        caches = list(DIR_CACHE.glob("*.json"))
        # Filtra somente os caches dos cupons reais (sha256 dos 4 jpegs)
        shas_reais = {calcular_sha256(p) for p in _amostras_jpeg()}
        caches_reais = [c for c in caches if c.stem in shas_reais]
        assert len(caches_reais) >= 3, (
            f"INFRA-EXTRATOR-CUPOM-FOTO: gate D7 exige >=3 amostras, "
            f"encontrei {len(caches_reais)} caches reais em {DIR_CACHE}"
        )

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists() or not DIR_CACHE.exists(),
        reason="data ausente",
    )
    def test_caches_validam_contra_schema(self, schema_opus: dict):
        shas_reais = {calcular_sha256(p) for p in _amostras_jpeg()}
        caches_reais = [DIR_CACHE / f"{sha}.json" for sha in shas_reais]
        existentes = [c for c in caches_reais if c.exists()]
        assert existentes, "nenhum cache real encontrado"
        for cache in existentes:
            payload = json.loads(cache.read_text(encoding="utf-8"))
            jsonschema.validate(payload, schema_opus)
            assert payload["tipo_documento"] == "cupom_fiscal_foto"
            assert payload["estabelecimento"]["cnpj"], "CNPJ obrigatório"
            assert payload["total"] > 0
            assert len(payload["itens"]) >= 1

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists() or not DIR_CACHE.exists(),
        reason="data ausente",
    )
    def test_cupom_nsp_grande_tem_52_itens_513_31(self):
        # Confronto multimodal com CUPOM_2e43640d.jpeg (2026-05-13):
        # razão_social na foto é em CAIXA ALTA "COMERCIAL NSP LTDA".
        # soma(valor_total dos itens) não bate com total declarado: cupom fiscal
        # aplica descontos IBPT por item (coluna ITEM R$ < VLR R$). Validar
        # contratualmente o total declarado e a qtd de itens, não a identidade
        # aritmética soma == total (que é empiricamente falsa neste cupom real).
        sha_grande = "2e43640dde52352439716cb7854af244effa3cc0f9d2c9d7f2aa31454b37f73e"
        cache = DIR_CACHE / f"{sha_grande}.json"
        if not cache.exists():
            pytest.skip("cache 2e43640d ausente")
        payload = json.loads(cache.read_text(encoding="utf-8"))
        assert len(payload["itens"]) == 52
        assert payload["total"] == pytest.approx(513.31)
        assert payload["estabelecimento"]["razao_social"].upper() == "COMERCIAL NSP LTDA"
        assert payload["estabelecimento"]["cnpj"] == "56.525.495/0004-70"

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists() or not DIR_CACHE.exists(),
        reason="data ausente",
    )
    def test_cupom_nsp_pequeno_tem_22_itens_254_91(self):
        # Confronto multimodal com CUPOM_67a3104a.jpeg (2026-05-13):
        # cupom mostra 2 colunas (VLR R$ = bruto = 254.91, ITEM R$ = líquido pós-IBPT = 254.44).
        # soma(valor_total) = 254.44 (coluna ITEM); total declarado = 254.91 (Valor a Pagar).
        # Validar contratualmente o total declarado, não a identidade soma == total.
        sha_pequeno = "67a3104a1ebb397c224320869edb6533fda760c9afecee1df02141d40f110405"
        cache = DIR_CACHE / f"{sha_pequeno}.json"
        if not cache.exists():
            pytest.skip("cache 67a3104a ausente")
        payload = json.loads(cache.read_text(encoding="utf-8"))
        assert len(payload["itens"]) == 22
        assert payload["total"] == pytest.approx(254.91)


# ============================================================================
# extrair_via_opus: cache hit canonico
# ============================================================================


class TestExtrairViaOpusComCacheReal:
    """Quando o cache canonico existe, extrair_via_opus devolve schema completo."""

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists(),
        reason="data ausente",
    )
    def test_cache_hit_devolve_payload_completo(self, tmp_path: Path):
        # Replica um cache canonico em tmp_path para isolar do producao  # noqa: accent
        amostras = _amostras_jpeg()
        if not amostras:
            pytest.skip("nenhuma amostra real")
        img = amostras[0]
        sha = calcular_sha256(img)
        cache_origem = DIR_CACHE / f"{sha}.json"
        if not cache_origem.exists():
            pytest.skip(f"cache {sha[:8]} ausente; rode a sprint primeiro")

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache_dir.joinpath(f"{sha}.json").write_bytes(cache_origem.read_bytes())

        resultado = extrair_via_opus(
            img,
            dir_cache=cache_dir,
            dir_pendentes=tmp_path / "pendentes",
        )
        assert resultado["sha256"] == sha
        assert resultado["tipo_documento"] == "cupom_fiscal_foto"
        assert "aguardando_supervisor" not in resultado
        assert len(resultado["itens"]) >= 1


# ============================================================================
# ingerir_cupom_foto: contratos de adapter
# ============================================================================


class TestIngerirCupomFoto:
    def test_payload_minimo_cria_documento_fornecedor_periodo_e_itens(
        self,
        grafo_temp: GrafoDB,
    ):
        payload = _payload_canonico_minimo()
        doc_id = ingerir_cupom_foto(grafo_temp, payload)
        assert doc_id > 0

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0]
            n_item = con.execute("SELECT COUNT(*) FROM node WHERE tipo='item'").fetchone()[0]
            n_forn = con.execute("SELECT COUNT(*) FROM node WHERE tipo='fornecedor'").fetchone()[0]
            n_per = con.execute("SELECT COUNT(*) FROM node WHERE tipo='periodo'").fetchone()[0]
            n_contem = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='contem_item'"
            ).fetchone()[0]
            n_forn_edge = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='fornecido_por'"
            ).fetchone()[0]
            n_periodo_edge = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='ocorre_em'"
            ).fetchone()[0]
        finally:
            con.close()

        assert n_doc == 1
        assert n_item == 2  # ARROZ + BANANA
        assert n_forn == 1
        assert n_per == 1
        assert n_contem == 2
        assert n_forn_edge == 1
        assert n_periodo_edge == 1

    def test_chave_documento_usa_sha256(self, grafo_temp: GrafoDB):
        payload = _payload_canonico_minimo()
        ingerir_cupom_foto(grafo_temp, payload)
        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT nome_canonico FROM node WHERE tipo='documento'"
            ).fetchone()
        finally:
            con.close()
        # GrafoDB.upsert_node uppercase nome_canonico (consistencia entre buscas).
        assert row[0].lower() == f"CUPOMFOTO|{payload['sha256']}".lower()

    def test_idempotencia_reprocessar_nao_duplica(self, grafo_temp: GrafoDB):
        payload = _payload_canonico_minimo()
        doc_id_1 = ingerir_cupom_foto(grafo_temp, payload)
        doc_id_2 = ingerir_cupom_foto(grafo_temp, payload)
        assert doc_id_1 == doc_id_2

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0]
            n_contem = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='contem_item'"
            ).fetchone()[0]
        finally:
            con.close()
        assert n_doc == 1
        assert n_contem == 2  # não duplicou

    def test_aguardando_supervisor_levanta_value_error(self, grafo_temp: GrafoDB):
        payload = {
            "sha256": "b" * 64,
            "tipo_documento": "pendente",
            "aguardando_supervisor": True,
            "caminho_imagem": "/tmp/pendente.jpeg",
            "extraido_via": "opus_supervisor_artesanal",
            "ts_extraido": "2026-05-08T13:00:00+00:00",
        }
        with pytest.raises(ValueError, match="aguardando_supervisor"):
            ingerir_cupom_foto(grafo_temp, payload)

    @pytest.mark.parametrize("campo", CAMPOS_OBRIGATORIOS_PAYLOAD_OPUS)
    def test_campo_obrigatorio_ausente_levanta(self, grafo_temp: GrafoDB, campo: str):
        payload = _payload_canonico_minimo()
        # Apaga o campo (None não basta porque get retorna None então 'not None' é False;
        # vazio explícito também rejeita pelo guard)
        payload[campo] = None
        with pytest.raises(ValueError, match=campo):
            ingerir_cupom_foto(grafo_temp, payload)

    def test_estabelecimento_sem_cnpj_levanta(self, grafo_temp: GrafoDB):
        payload = _payload_canonico_minimo()
        payload["estabelecimento"] = {"razao_social": "Loja Sem CNPJ"}
        with pytest.raises(ValueError, match="cnpj"):
            ingerir_cupom_foto(grafo_temp, payload)

    def test_itens_sem_codigo_recebem_codigo_sintetico(self, grafo_temp: GrafoDB):
        """Items sem codigo_barras (frutas a granel) ganham SEMCOD<NNNN>."""
        payload = _payload_canonico_minimo()
        # Os 2 itens canonicos: o segundo (BANANA) tem codigo None  # noqa: accent
        ingerir_cupom_foto(grafo_temp, payload)
        con = sqlite3.connect(grafo_temp.caminho)
        try:
            rows = con.execute(
                "SELECT nome_canonico FROM node WHERE tipo='item'"
            ).fetchall()
        finally:
            con.close()
        nomes = [r[0] for r in rows]
        assert any("SEMCOD" in n for n in nomes), f"esperava SEMCOD em {nomes}"

    def test_metadata_documento_preserva_extraido_via_e_sha(
        self,
        grafo_temp: GrafoDB,
    ):
        payload = _payload_canonico_minimo()
        ingerir_cupom_foto(grafo_temp, payload)
        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT metadata FROM node WHERE tipo='documento'"
            ).fetchone()
        finally:
            con.close()
        meta = json.loads(row[0])
        assert meta["extraido_via"] == "opus_supervisor_artesanal"
        assert meta["sha256_imagem"] == payload["sha256"]
        assert meta["tipo_documento"] == "cupom_fiscal_foto"


# ============================================================================
# Integracao: 4 amostras reais via cache  # noqa: accent
# ============================================================================


class TestIntegracaoAmostrasReais:
    """Pipeline ponta-a-ponta com as 4 fotos reais (depende de data/ local)."""

    @pytest.mark.skipif(
        not DIR_AMOSTRAS.exists() or not DIR_CACHE.exists(),
        reason="data/raw + data/output/opus_ocr_cache ausentes",
    )
    def test_4_amostras_ingeridas_em_grafo_temporario(self, grafo_temp: GrafoDB):
        amostras = _amostras_jpeg()
        if len(amostras) < 3:
            pytest.skip(f"sprint exige >=3 amostras, achei {len(amostras)}")

        ingeridas = 0
        total_itens = 0
        for img in amostras:
            sha = calcular_sha256(img)
            cache = DIR_CACHE / f"{sha}.json"
            if not cache.exists():
                continue
            payload = json.loads(cache.read_text(encoding="utf-8"))
            ingerir_cupom_foto(grafo_temp, payload, caminho_arquivo=img)
            ingeridas += 1
            total_itens += len(payload["itens"])
        assert ingeridas >= 3, f"INFRA-EXTRATOR-CUPOM-FOTO: ingeri {ingeridas} amostras"

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0]
            n_item = con.execute("SELECT COUNT(*) FROM node WHERE tipo='item'").fetchone()[0]
        finally:
            con.close()
        assert n_doc == ingeridas
        assert n_item >= 1


# "Cupom fotografado e cupom estruturado tem o mesmo destino: virar nó."
# -- princípio INFRA-EXTRATOR-CUPOM-FOTO
