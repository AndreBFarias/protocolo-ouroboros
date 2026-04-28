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
    """Sprint 106a: texto longo só passa se também tiver palavras PT-BR."""
    cfg = _config_default()
    cfg.setdefault("min_palavras_conhecidas_por_tipo", {"default": 5})
    cfg.setdefault("max_ratio_non_letras_por_tipo", {"default": 0.45})
    coerente = (
        "este texto longo tem palavras conhecidas como total de valor para pagamento "
        "data emissao em loja com cnpj e produto comprado por R$ 100,00"
    )
    assert _ocr_e_ilegivel(coerente, "cupom_fiscal_foto", cfg) is False


def test_sprint_106a_garbage_2000_chars_e_ilegivel():
    """Garbage do Tesseract com 2000+ chars mas zero palavras PT-BR -> ilegivel."""
    from src.intake.ocr_fallback_similar import _carregar_config

    cfg = _carregar_config()  # carrega YAML real
    garbage = "CI Ma Fat 6 A UND imbacia usb toa LM CU LOTE 04 DAE 08 SNL OM 0H Sp TUR MAE " * 30
    assert _ocr_e_ilegivel(garbage, "cupom_fiscal_foto", cfg) is True


def test_sprint_106a_texto_coerente_pt_br_e_legivel():
    from src.intake.ocr_fallback_similar import _carregar_config

    cfg = _carregar_config()
    coerente = (
        "Documento Auxiliar da Nota Fiscal de Consumidor "
        "VALOR TOTAL: R$ 100,00 PAGAMENTO PIX CNPJ 00.776.574/0160-79 "
        "Data de emissao 19/04/2026 forma de pagamento credito"
    )
    assert _ocr_e_ilegivel(coerente, "cupom_fiscal_foto", cfg) is False


def test_sprint_106a_zero_palavras_conhecidas_e_ilegivel():
    """Texto com chars uteis suficientes mas zero palavras PT-BR -> ilegivel."""
    from src.intake.ocr_fallback_similar import _carregar_config

    cfg = _carregar_config()
    sem_pt = "abcde fghij klmno pqrst uvwxy zabcd efghi jklmn opqrs tuvwx " * 5
    # Tem chars uteis muitos, mas nenhuma palavra conhecida -> ilegivel
    assert _ocr_e_ilegivel(sem_pt, "cupom_fiscal_foto", cfg) is True


def test_sprint_106a_ratio_non_letras_alto_e_ilegivel():
    """Texto com ratio non-letras > 0.40 -> ilegivel."""
    from src.intake.ocr_fallback_similar import _carregar_config

    cfg = _carregar_config()
    # Muitos non-letras, mas tem palavras PT-BR (passa criterio 2)
    pontuado = "valor total " + "1234567890.|/|().*&^%$#@!" * 30 + " data nota cnpj cpf forma"
    # Ratio de non-letras acima de 0.40 -> ilegivel
    assert _ocr_e_ilegivel(pontuado, "cupom_fiscal_foto", cfg) is True


def test_score_temporal_dentro_da_janela():
    agora = datetime(2026, 4, 19).timestamp()
    score = _score_temporal(agora, "2026-04-19", janela_dias=7)
    assert score == 1.0


def test_audit_timezone_arquivo_2355_mesmo_dia_score_1():
    """AUDIT-TIMEZONE-OCR: arquivo gerado as 23:55 vs candidato data=hoje
    retorna score 1.0 (sem flutuacao de TZ porque so compara .date()).
    """
    mtime_tarde = datetime(2026, 4, 19, 23, 55, 0).timestamp()
    score = _score_temporal(mtime_tarde, "2026-04-19", janela_dias=7)
    assert score == 1.0


def test_audit_timezone_arquivo_0005_dia_seguinte_distancia_correta():
    """Arquivo gerado as 00:05 do dia seguinte vs candidato hoje -> 1 dia."""
    mtime_madrugada = datetime(2026, 4, 20, 0, 5, 0).timestamp()
    score = _score_temporal(mtime_madrugada, "2026-04-19", janela_dias=7)
    # 1 dia de delta numa janela de 7 -> 6/7 = ~0.857
    assert abs(score - 6 / 7) < 0.01


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


def test_audit_score_textual_banco_generico_nao_casa():
    """AUDIT-SCORE-TEXTUAL: fornecedor 'BANCO BRADESCO SA' não casa apenas
    pela palavra generica 'BANCO' em arquivo não relacionado.
    """
    meta = {"razao_social": "BANCO BRADESCO SA", "cnpj_emitente": "60746948000112"}
    # Cupom Visa generico que MENCIONA 'BANCO' mas não 'BRADESCO' nem CNPJ
    score = _score_textual("cupom_visa.pdf", "BANCO emitente x cupom", meta)
    # 'BRADESCO' eh especifica e não aparece -> matches = 0
    assert score == 0.0


def test_audit_score_textual_palavra_especifica_casa():
    """Palavra especifica ('BRADESCO') no texto do falho -> matches >= 1."""
    meta = {"razao_social": "BANCO BRADESCO SA", "cnpj_emitente": "60746948000112"}
    score = _score_textual("cupom_bradesco.pdf", "boleto BRADESCO referente", meta)
    assert score > 0.0


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
