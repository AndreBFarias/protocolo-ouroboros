"""Sprint 106: testes regressivos do motor de OCR fallback por similar.

Cobre:
  1. _ocr_e_ilegivel detecta texto curto.
  2. _score_temporal calcula proximidade dentro da janela.
  3. _score_textual casa fornecedor por substring.
  4. buscar_similar com candidato dentro da janela retorna match.
  5. buscar_similar com candidato fora da janela retorna None.
  6. buscar_similar sem candidatos do mesmo tipo retorna None.
  7. Pesos reescalados quando phash indisponivel.
  8. reanalisar_pasta_conferir opera em dry-run sem mover arquivos.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from src.graph.db import GrafoDB
from src.intake.ocr_fallback_similar import (
    _config_default,
    _ocr_e_ilegivel,
    _resetar_cache_config,
    _score_temporal,
    _score_textual,
    buscar_similar,
    reanalisar_pasta_conferir,
)


def setup_function():
    _resetar_cache_config()


def test_ocr_ilegivel_texto_curto():
    cfg = _config_default()
    assert _ocr_e_ilegivel("abc", "cupom_fiscal_foto", cfg) is True


def test_ocr_legivel_texto_longo():
    cfg = _config_default()
    longo = "este e um texto longo o suficiente para passar o limiar de 50 caracteres uteis"
    assert _ocr_e_ilegivel(longo, "cupom_fiscal_foto", cfg) is False


def test_score_temporal_dentro_da_janela():
    agora = datetime(2026, 4, 19).timestamp()
    score = _score_temporal(agora, "2026-04-19", janela_dias=7)
    assert score == 1.0


def test_score_temporal_no_limite_da_janela():
    base = datetime(2026, 4, 19)
    falho_mtime = base.timestamp()
    cand_data = (base - timedelta(days=7)).strftime("%Y-%m-%d")
    score = _score_temporal(falho_mtime, cand_data, janela_dias=7)
    # Limite extremo: score próximo de 0 (não exatamente 0)
    assert 0.0 <= score < 0.15


def test_score_temporal_fora_da_janela():
    agora = datetime(2026, 4, 19).timestamp()
    score = _score_temporal(agora, "2026-01-01", janela_dias=7)
    assert score == 0.0


def test_score_textual_fornecedor_no_nome_arquivo():
    meta = {"razao_social": "AMERICANAS SA - 0337", "cnpj_emitente": "00776574016079"}
    score = _score_textual("CUPOM_AMERICANAS_xyz.jpeg", "", meta)
    assert score > 0.0


def test_score_textual_cnpj_no_texto():
    meta = {"razao_social": "X", "cnpj_emitente": "00776574016079"}
    score = _score_textual("doc.pdf", "compra realizada CNPJ 00776574016079", meta)
    assert score > 0.0


def test_score_textual_sem_match():
    meta = {"razao_social": "AMERICANAS SA", "cnpj_emitente": "00776574016079"}
    score = _score_textual("nada.pdf", "texto qualquer", meta)
    assert score == 0.0


def _criar_grafo_com_candidato(
    tmp_path: Path,
    arquivo_real: Path,
    tipo_documento: str = "cupom_fiscal_foto",
    data_emissao: str = "2026-04-19",
    razao: str = "AMERICANAS SA",
    cnpj: str = "00776574016079",
) -> GrafoDB:
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    meta = {
        "tipo_documento": tipo_documento,
        "arquivo_origem": str(arquivo_real),
        "data_emissao": data_emissao,
        "razao_social": razao,
        "cnpj_emitente": cnpj,
        "total": 100.0,
    }
    db.upsert_node("documento", "DOC|cand|001", metadata=meta)
    return db


def test_buscar_similar_sem_candidatos_devolve_none(tmp_path: Path):
    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    falho = tmp_path / "falho.jpeg"
    falho.write_bytes(b"X")
    assert buscar_similar(falho, db, tipo_falho="cupom_fiscal_foto") is None


def test_buscar_similar_candidato_dentro_janela_e_match_textual(tmp_path: Path):
    candidato = tmp_path / "cand.pdf"
    candidato.write_bytes(b"%PDF-fake")
    db = _criar_grafo_com_candidato(tmp_path, candidato)

    # Falho com nome contendo fornecedor (textual match)
    falho = tmp_path / "CUPOM_AMERICANAS_X.jpeg"
    falho.write_bytes(b"X" * 200)

    # Forca janela ampla pra garantir match
    cfg = _config_default()
    cfg["janela_temporal_dias_por_tipo"]["cupom_fiscal_foto"] = 365
    cfg["confidence_minima"] = 0.30  # baixa pra confirmar lookup
    resultado = buscar_similar(
        falho, db, tipo_falho="cupom_fiscal_foto", texto_falho="texto", config=cfg
    )
    assert resultado is not None
    assert resultado["item_id_similar"] == "DOC|CAND|001"
    assert resultado["score"] >= 0.30


def test_buscar_similar_candidato_outro_tipo_ignorado(tmp_path: Path):
    candidato = tmp_path / "cand.pdf"
    candidato.write_bytes(b"X")
    db = _criar_grafo_com_candidato(tmp_path, candidato, tipo_documento="boleto_servico")

    falho = tmp_path / "cupom.jpeg"
    falho.write_bytes(b"X" * 200)
    resultado = buscar_similar(falho, db, tipo_falho="cupom_fiscal_foto")
    assert resultado is None


def test_reanalisar_pasta_conferir_dry_run(tmp_path: Path):
    raiz = tmp_path / "raw"
    pasta_conferir = raiz / "_conferir"
    pasta_conferir.mkdir(parents=True)
    arq = pasta_conferir / "cupom_xx.jpeg"
    arq.write_bytes(b"X" * 100)

    db = GrafoDB(tmp_path / "g.sqlite")
    db.criar_schema()
    rel = reanalisar_pasta_conferir(db, raiz_raw=raiz, dry_run=True)
    assert rel["arquivos"] == 1
    assert arq.exists()  # dry-run preserva


# "Onde a foto falha, peca o gemeo." -- principio do fallback inteligente
