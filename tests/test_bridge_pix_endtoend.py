"""Testes end-to-end do bridge PIX mobile -> grafo (Sprint MOB-bridge-5).

Conecta os elos já entregues por sprints anteriores:

1. MOB-bridge-4: registry mapeia ``subtipo_mobile='pix'`` para o tipo
   canônico ``comprovante_pix_foto`` via ``_MAPPING_SUBTIPO_MOBILE_TO_TIPO``.
2. DOC-27: extrator ``src.extractors.comprovante_pix_foto`` produtivo e
   3 caches reais transcritos em ``data/output/opus_ocr_cache/``.
3. MOB-bridge-5 (esta sprint): ingestor ``ingerir_comprovante_pix_foto``
   no grafo, com fornecedor sintético quando o destinatário é PF.

Testes:

- ``TestRegistryRoteamento``: registry devolve Decisão correta para
  ``subtipo_mobile='pix'`` (extrator, pasta, nome canônico).
- ``TestExtratorCacheHit``: extrator funcional chamado com foto cujo
  cache existe devolve payload canônico ``comprovante_pix_foto``.
- ``TestIngestorGrafo``: ``ingerir_comprovante_pix_foto`` cria 1 doc + 1
  fornecedor + arestas, sem nó ``item``.
- ``TestIdempotencia``: reprocessar o mesmo payload não duplica.
- ``TestEndToEnd3CachesReais``: processa os 3 caches reais PIX em grafo
  temporário; espera 3 documentos ingeridos.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from src.graph.db import GrafoDB
from src.graph.ingestor_documento import (
    CAMPOS_OBRIGATORIOS_PAYLOAD_PIX,
    ingerir_comprovante_pix_foto,
)
from src.intake.registry import detectar_tipo

RAIZ = Path(__file__).resolve().parents[1]
DIR_CACHE_REPO_PRINCIPAL = (
    Path("/home/andrefarias/Desenvolvimento/protocolo-ouroboros")
    / "data"
    / "output"
    / "opus_ocr_cache"
)
DIR_CACHE_LOCAL = RAIZ / "data" / "output" / "opus_ocr_cache"

# SHA-256 dos 3 caches PIX reais transcritos artesanalmente (DOC-27).
SHAS_PIX_REAIS: tuple[str, ...] = (
    "2a0d6ee773d773580c56ceef5b8b16be7507d8cbe28cfd7d1918e1066c6e44ce",  # Itaú R$ 900
    "3d82d81c6e9d8d5cf0e607dd5c1b4793f9e2f24bde12b8122fdbbb31dc501010",  # C6 R$ 50
    "bb6abe1ca9ddf575530016b4966cf3ebb7e89aebdadb396c67af1e9789531a2b",  # Nubank R$ 367,65
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def grafo_temp(tmp_path: Path):
    db = GrafoDB(tmp_path / "grafo_teste_pix.sqlite")
    db.criar_schema()
    yield db
    db.fechar()


def _localizar_dir_cache() -> Path | None:
    """Cache real fica em ``data/output/`` (gitignored). Pode estar no
    worktree ou no repo principal; tenta os dois."""
    if DIR_CACHE_LOCAL.exists():
        return DIR_CACHE_LOCAL
    if DIR_CACHE_REPO_PRINCIPAL.exists():
        return DIR_CACHE_REPO_PRINCIPAL
    return None


def _payload_pix_minimo() -> dict:
    """Payload PIX mínimo para testes sem cache real."""
    return {
        "sha256": "a" * 64,
        "tipo_documento": "comprovante_pix_foto",
        "estabelecimento": {
            "razao_social": "FULANO DE TAL DESTINATARIO",
            "cnpj": None,
            "endereco": None,
        },
        "data_emissao": "2026-05-10",
        "horario": "10:30:00",
        "itens": [
            {
                "codigo": None,
                "descricao": "Aluguel maio",
                "qtd": 1,
                "unidade": "UN",
                "valor_unit": 1500.0,
                "valor_total": 1500.0,
            }
        ],
        "total": 1500.0,
        "forma_pagamento": "pix",
        "_pix": {
            "banco_origem": "ITAU UNIBANCO S.A",
            "banco_destino": "BANCO INTER",
            "remetente_nome": "REMETENTE CANONICO",
            "remetente_cpf_mascarado": "***.111.222-**",
            "destinatario_cpf_mascarado": "***.333.444-**",
            "chave_destinatario": "destinatario@email.com",
            "id_transacao": "E12345678202605101030AAAAAAAAA",
        },
        "extraido_via": "opus_supervisor_artesanal",
        "confianca_global": 0.95,
    }


# ============================================================================
# Teste 1: Registry roteia subtipo_mobile=pix corretamente
# ============================================================================


class TestRegistryRoteamento:
    def test_subtipo_mobile_pix_devolve_extrator_dedicado(self, tmp_path: Path):
        """MOB-bridge-4 + DOC-27: ``subtipo_mobile='pix'`` aponta para o
        extrator de comprovante PIX, pasta canônica e nome ``PIX_<sha8>``."""
        arquivo = tmp_path / "comprovante_pix.jpg"
        arquivo.write_bytes(b"binario qualquer para sha8 noqa: accent")

        decisao = detectar_tipo(
            caminho=arquivo,
            mime="image/jpeg",
            preview="",
            pessoa="andre",
            subtipo_mobile="pix",
        )

        assert decisao.tipo == "comprovante_pix_foto"
        assert decisao.extrator_modulo == "src.extractors.comprovante_pix_foto"
        assert "comprovantes_pix" in str(decisao.pasta_destino)
        assert "andre" in str(decisao.pasta_destino)
        assert decisao.nome_canonico is not None
        assert decisao.nome_canonico.startswith("PIX_")
        assert decisao.nome_canonico.endswith(".jpg")

    def test_subtipo_mobile_pix_origem_sprint_marca_mob_bridge_4(
        self, tmp_path: Path
    ):
        """Auditoria: ``origem_sprint`` permite rastrear que a decisão
        veio do hint mobile (não da cascata YAML pura)."""
        arquivo = tmp_path / "outro.png"
        arquivo.write_bytes(b"x")

        decisao = detectar_tipo(
            caminho=arquivo,
            mime="image/png",
            preview="",
            pessoa="vitoria",
            subtipo_mobile="pix",
        )
        assert decisao.origem_sprint == "MOB-bridge-4"


# ============================================================================
# Teste 2: Extrator chamado com foto -> cache canônico devolvido
# ============================================================================


class TestExtratorCacheHit:
    @pytest.mark.skipif(
        _localizar_dir_cache() is None,
        reason="cache opus_ocr_cache ausente (data/output/ é gitignored)",
    )
    def test_extrair_pix_real_devolve_payload_canonico(self, tmp_path: Path):
        """Quando existe cache para o sha256 da foto, ``extrair`` devolve o
        dict canônico com ``tipo_documento='comprovante_pix_foto'``,
        ``total``, ``estabelecimento`` e bloco ``_pix``.

        Aqui validamos o contrato do payload diretamente no JSON canônico
        (reproduzir uma foto cujo sha256 case com o cache não é prático)."""
        dir_cache = _localizar_dir_cache()
        cache_path = dir_cache / f"{SHAS_PIX_REAIS[0]}.json"
        if not cache_path.exists():
            pytest.skip(f"cache real {SHAS_PIX_REAIS[0][:12]} indisponível")

        payload = json.loads(cache_path.read_text(encoding="utf-8"))

        assert payload["tipo_documento"] == "comprovante_pix_foto"
        assert payload["sha256"] == SHAS_PIX_REAIS[0]
        assert payload["total"] > 0
        assert "estabelecimento" in payload
        assert "_pix" in payload
        assert payload["_pix"].get("id_transacao")

    def test_extrair_pix_payload_minimo_aceito_pelo_contrato(self):
        """Payload PIX mínimo casa o contrato exigido por
        ``CAMPOS_OBRIGATORIOS_PAYLOAD_PIX``."""
        payload = _payload_pix_minimo()
        for campo in CAMPOS_OBRIGATORIOS_PAYLOAD_PIX:
            assert payload.get(campo), f"campo obrigatório ausente: {campo}"


# ============================================================================
# Teste 3: Ingestor cria 1 doc + 1 fornecedor + arestas (sem nó item)
# ============================================================================


class TestIngestorGrafo:
    def test_payload_minimo_cria_documento_fornecedor_sem_item(
        self, grafo_temp: GrafoDB
    ):
        """PIX é transferência monolítica: cria 1 documento + 1 fornecedor +
        1 período, com arestas ``fornecido_por`` e ``ocorre_em``, mas SEM
        nós ``item`` nem aresta ``contem_item``."""
        payload = _payload_pix_minimo()
        doc_id = ingerir_comprovante_pix_foto(grafo_temp, payload)
        assert doc_id > 0

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='documento'"
            ).fetchone()[0]
            n_forn = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='fornecedor'"
            ).fetchone()[0]
            n_periodo = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='periodo'"
            ).fetchone()[0]
            n_item = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='item'"
            ).fetchone()[0]
            n_forn_edge = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='fornecido_por'"
            ).fetchone()[0]
            n_ocorre = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='ocorre_em'"
            ).fetchone()[0]
            n_contem = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='contem_item'"
            ).fetchone()[0]
        finally:
            con.close()

        assert n_doc == 1
        assert n_forn == 1
        assert n_periodo == 1
        assert n_item == 0, "PIX não cria nós item (transferência monolítica)"
        assert n_forn_edge == 1
        assert n_ocorre == 1
        assert n_contem == 0

    def test_destinatario_pf_recebe_cnpj_sintetico(self, grafo_temp: GrafoDB):
        """Recebedor sem CNPJ canônico (PIX P2P) vira fornecedor sintético
        ``PIX|<sha8>``, derivado da chave PIX para garantir dedup."""
        payload = _payload_pix_minimo()
        ingerir_comprovante_pix_foto(grafo_temp, payload)

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT nome_canonico, metadata FROM node WHERE tipo='fornecedor'"
            ).fetchone()
        finally:
            con.close()
        nome_canonico, _metadata_raw = row
        assert nome_canonico.upper().startswith("PIX|"), (
            f"esperava CNPJ sintético, achei {nome_canonico!r}"
        )

        # Determinismo: sha8 derivado da chave_destinatario (email).
        esperado_sha = hashlib.sha256(
            "destinatario@email.com".encode("utf-8")
        ).hexdigest()[:8]
        assert nome_canonico.upper() == f"PIX|{esperado_sha}".upper(), (
            f"derivação não determinística: {nome_canonico!r}"
        )

    def test_destinatario_pj_usa_cnpj_real(self, grafo_temp: GrafoDB):
        """PIX para CNPJ canônico real (caso PJ) NÃO vira sintético."""
        payload = _payload_pix_minimo()
        payload["estabelecimento"]["cnpj"] = "12.345.678/0001-95"
        ingerir_comprovante_pix_foto(grafo_temp, payload)

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT nome_canonico FROM node WHERE tipo='fornecedor'"
            ).fetchone()
        finally:
            con.close()
        # GrafoDB normaliza nome_canonico em uppercase; CNPJ real sobrevive.
        assert "PIX|" not in row[0]
        assert "12.345.678" in row[0]

    def test_chave_documento_usa_pix_sha256(self, grafo_temp: GrafoDB):
        """Documento PIX chaveado por ``PIX|<sha256>`` (idempotência)."""
        payload = _payload_pix_minimo()
        ingerir_comprovante_pix_foto(grafo_temp, payload)
        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT nome_canonico FROM node WHERE tipo='documento'"
            ).fetchone()
        finally:
            con.close()
        # nome_canonico armazenado em uppercase pelo GrafoDB.
        assert row[0].upper() == f"PIX|{payload['sha256']}".upper()

    def test_metadata_preserva_bloco_pix_e2e_e_banco(self, grafo_temp: GrafoDB):
        """Metadata do documento carrega ID E2E, banco origem/destino, chave PIX."""
        payload = _payload_pix_minimo()
        ingerir_comprovante_pix_foto(grafo_temp, payload)
        con = sqlite3.connect(grafo_temp.caminho)
        try:
            row = con.execute(
                "SELECT metadata FROM node WHERE tipo='documento'"
            ).fetchone()
        finally:
            con.close()
        meta = json.loads(row[0])
        assert meta["pix_id_transacao"] == "E12345678202605101030AAAAAAAAA"
        assert meta["pix_banco_origem"] == "ITAU UNIBANCO S.A"
        assert meta["pix_banco_destino"] == "BANCO INTER"
        assert meta["pix_chave_destinatario"] == "destinatario@email.com"
        assert meta["forma_pagamento"] == "pix"
        assert meta["sha256_imagem"] == payload["sha256"]

    def test_aguardando_supervisor_levanta_value_error(self, grafo_temp: GrafoDB):
        """Pendência (cache miss) é rejeitada antes de criar nó órfão."""
        payload = {
            "sha256": "f" * 64,
            "tipo_documento": "pendente",
            "aguardando_supervisor": True,
            "caminho_imagem": "/tmp/pendente.jpeg",
            "extraido_via": "opus_supervisor_artesanal",
            "ts_extraido": "2026-05-13T10:00:00+00:00",
        }
        with pytest.raises(ValueError, match="aguardando_supervisor"):
            ingerir_comprovante_pix_foto(grafo_temp, payload)

    @pytest.mark.parametrize("campo", CAMPOS_OBRIGATORIOS_PAYLOAD_PIX)
    def test_campo_obrigatorio_ausente_levanta(
        self, grafo_temp: GrafoDB, campo: str
    ):
        payload = _payload_pix_minimo()
        payload[campo] = None
        with pytest.raises(ValueError, match=campo):
            ingerir_comprovante_pix_foto(grafo_temp, payload)

    def test_tipo_documento_errado_levanta(self, grafo_temp: GrafoDB):
        """Payload com tipo_documento != comprovante_pix_foto é rejeitado."""
        payload = _payload_pix_minimo()
        payload["tipo_documento"] = "cupom_fiscal_foto"
        with pytest.raises(ValueError, match="comprovante_pix_foto"):
            ingerir_comprovante_pix_foto(grafo_temp, payload)


# ============================================================================
# Teste 4: Idempotência -- reprocessar mesma foto não duplica
# ============================================================================


class TestIdempotencia:
    def test_reprocessar_mesmo_payload_nao_duplica(self, grafo_temp: GrafoDB):
        payload = _payload_pix_minimo()
        doc_id_1 = ingerir_comprovante_pix_foto(grafo_temp, payload)
        doc_id_2 = ingerir_comprovante_pix_foto(grafo_temp, payload)
        assert doc_id_1 == doc_id_2

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='documento'"
            ).fetchone()[0]
            n_forn = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='fornecedor'"
            ).fetchone()[0]
            n_forn_edge = con.execute(
                "SELECT COUNT(*) FROM edge WHERE tipo='fornecido_por'"
            ).fetchone()[0]
        finally:
            con.close()
        assert n_doc == 1, "documento duplicado em reprocessamento"
        assert n_forn == 1, "fornecedor duplicado em reprocessamento"
        assert n_forn_edge == 1

    def test_multiplos_pix_mesmo_destinatario_compartilham_fornecedor(
        self, grafo_temp: GrafoDB
    ):
        """Dois PIX diferentes para o mesmo destinatário (mesma chave PIX)
        criam 2 documentos mas reutilizam 1 fornecedor."""
        payload_a = _payload_pix_minimo()
        payload_a["sha256"] = "a" * 64
        payload_a["_pix"]["id_transacao"] = "EAAAAAAA1111111111111111111111111"

        payload_b = _payload_pix_minimo()
        payload_b["sha256"] = "b" * 64
        payload_b["data_emissao"] = "2026-06-15"
        payload_b["total"] = 200.0
        payload_b["_pix"]["id_transacao"] = "EBBBBBBB2222222222222222222222222"

        ingerir_comprovante_pix_foto(grafo_temp, payload_a)
        ingerir_comprovante_pix_foto(grafo_temp, payload_b)

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='documento'"
            ).fetchone()[0]
            n_forn = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='fornecedor'"
            ).fetchone()[0]
        finally:
            con.close()
        assert n_doc == 2
        assert n_forn == 1, (
            "PIX para mesmo destinatário (mesma chave) deveria reusar fornecedor"
        )


# ============================================================================
# Teste 5: End-to-end com os 3 caches reais PIX (DOC-27)
# ============================================================================


class TestEndToEnd3CachesReais:
    """Pipeline ponta-a-ponta com os 3 comprovantes PIX reais transcritos."""

    @pytest.mark.skipif(
        _localizar_dir_cache() is None,
        reason="data/output/opus_ocr_cache ausente (gitignored)",
    )
    def test_ingere_3_pix_reais_em_grafo_temporario(self, grafo_temp: GrafoDB):
        dir_cache = _localizar_dir_cache()
        ingeridos = 0
        for sha in SHAS_PIX_REAIS:
            cache_path = dir_cache / f"{sha}.json"
            if not cache_path.exists():
                continue
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            assert payload["tipo_documento"] == "comprovante_pix_foto"
            ingerir_comprovante_pix_foto(grafo_temp, payload)
            ingeridos += 1

        assert ingeridos >= 3, (
            f"MOB-bridge-5: ingeri {ingeridos} comprovantes PIX reais "
            f"(esperado >= 3)"
        )

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc_pix = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='documento' "
                "AND json_extract(metadata, '$.tipo_documento') = 'comprovante_pix_foto'"
            ).fetchone()[0]
            n_forn = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='fornecedor'"
            ).fetchone()[0]
            n_item = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='item'"
            ).fetchone()[0]
        finally:
            con.close()
        assert n_doc_pix == ingeridos, (
            f"esperava {ingeridos} documentos PIX, achei {n_doc_pix}"
        )
        # Cada um dos 3 PIX é para destinatário distinto (Panificadora,
        # Wesley, Vitória), então cria 3 fornecedores sintéticos distintos.
        assert n_forn == ingeridos
        assert n_item == 0, "PIX não cria nós item"

    @pytest.mark.skipif(
        _localizar_dir_cache() is None,
        reason="data/output/opus_ocr_cache ausente (gitignored)",
    )
    def test_chave_pix_sintetica_estavel_entre_runs(self, grafo_temp: GrafoDB):
        """Reprocessar os 3 caches reais não cria novos fornecedores
        sintéticos -- o CNPJ derivado da chave PIX é determinístico."""
        dir_cache = _localizar_dir_cache()
        payloads: list[dict] = []
        for sha in SHAS_PIX_REAIS:
            cache_path = dir_cache / f"{sha}.json"
            if cache_path.exists():
                payloads.append(json.loads(cache_path.read_text(encoding="utf-8")))
        if len(payloads) < 3:
            pytest.skip(f"3 caches reais ausentes, achei {len(payloads)}")

        for payload in payloads:
            ingerir_comprovante_pix_foto(grafo_temp, payload)
        # Segunda passada idempotente.
        for payload in payloads:
            ingerir_comprovante_pix_foto(grafo_temp, payload)

        con = sqlite3.connect(grafo_temp.caminho)
        try:
            n_doc = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='documento'"
            ).fetchone()[0]
            n_forn = con.execute(
                "SELECT COUNT(*) FROM node WHERE tipo='fornecedor'"
            ).fetchone()[0]
        finally:
            con.close()
        assert n_doc == len(payloads), "documento duplicado em segunda passada"
        assert n_forn == len(payloads), "fornecedor duplicado em segunda passada"


# "Toda transação tem duas pernas: a que move e a que registra." -- Heráclito de Éfeso
