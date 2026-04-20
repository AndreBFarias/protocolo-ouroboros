"""Testes do src.intake.router.

Cobre:
- arquivar_original: copia para _envelopes/originais/<sha8>.<ext> sem perder original
- rotear_artefato: shutil.move + mkdir atomicamente, fallback _classificar/ em falha
- rotear_artefato: desambiguação de colisão de nome canônico no destino
- descartar_da_inbox: só remove em sucesso total
- rotear_lote: cleanup do envelope conforme sucesso, relatório consolidado
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.intake import router
from src.intake.classifier import Decisao

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def isolar_paths(tmp_path, monkeypatch):
    """Aponta as constantes de caminho do router e do envelope para tmp_path."""
    raiz_falsa = tmp_path / "repo"
    raiz_falsa.mkdir()
    monkeypatch.setattr(router, "_RAIZ_REPO", raiz_falsa)
    monkeypatch.setattr(
        router, "_ORIGINAIS_BASE", raiz_falsa / "data" / "raw" / "_envelopes" / "originais"
    )
    # envelope module também precisa apontar pro tmp porque cleanup_envelope mexe lá
    from src.intake import extractors_envelope as env

    monkeypatch.setattr(env, "_ENVELOPES_BASE", raiz_falsa / "data" / "raw" / "_envelopes")
    yield raiz_falsa


def _decisao_canonica(pasta: Path, nome: str = "DOC_2026-04-19_abc12345.pdf") -> Decisao:
    return Decisao(
        tipo="cupom_garantia_estendida",
        prioridade="especifico",
        match_mode="all",
        extrator_modulo=None,
        origem_sprint=41,
        pasta_destino=pasta,
        nome_canonico=nome,
        data_detectada_iso="2026-04-19",
        regras_avaliadas=1,
    )


def _decisao_fallback(pasta: Path) -> Decisao:
    return Decisao(
        tipo=None,
        prioridade=None,
        match_mode=None,
        extrator_modulo=None,
        origem_sprint=None,
        pasta_destino=pasta,
        nome_canonico="_CLASSIFICAR_abcdef01.pdf",
        data_detectada_iso=None,
        regras_avaliadas=15,
        motivo_fallback="nenhum tipo casou (mime='application/pdf')",
    )


def _arquivo(tmp_path: Path, nome: str = "x.pdf", conteudo: bytes = b"%PDF-1.4 x") -> Path:
    p = tmp_path / nome
    p.write_bytes(conteudo)
    return p


# ============================================================================
# arquivar_original
# ============================================================================


def test_arquivar_original_copia_e_preserva_inbox(tmp_path, isolar_paths):
    inbox_arq = _arquivo(tmp_path, "inbox.pdf", b"conteudo-x")
    copia = router.arquivar_original(inbox_arq)
    assert copia.exists()
    assert copia.parent.name == "originais"
    assert copia.suffix == ".pdf"
    assert inbox_arq.exists(), "inbox NÃO deve ser apagada na cópia"
    assert copia.read_bytes() == b"conteudo-x"


def test_arquivar_original_idempotente_para_mesmo_arquivo(tmp_path, isolar_paths):
    inbox_arq = _arquivo(tmp_path, "x.pdf", b"id-bytes")
    copia1 = router.arquivar_original(inbox_arq)
    copia2 = router.arquivar_original(inbox_arq)
    assert copia1 == copia2  # mesmo sha8 -> mesmo destino


def test_arquivar_original_inexistente_levanta(tmp_path, isolar_paths):
    with pytest.raises(FileNotFoundError):
        router.arquivar_original(tmp_path / "fantasma.pdf")


# ============================================================================
# rotear_artefato
# ============================================================================


def test_rotear_artefato_para_pasta_canonica(tmp_path, isolar_paths):
    artefato = _arquivo(tmp_path, "pg1.pdf", b"pg1-bytes")
    destino_pasta = isolar_paths / "data" / "raw" / "andre" / "garantias_estendidas"
    decisao = _decisao_canonica(destino_pasta)
    resultado = router.rotear_artefato(artefato, decisao)
    assert resultado.sucesso is True
    assert resultado.caminho_final.exists()
    assert resultado.caminho_final.parent == destino_pasta
    assert resultado.caminho_final.name == decisao.nome_canonico
    assert not artefato.exists(), "artefato deve ter sido movido (não copiado)"


def test_rotear_artefato_resolve_colisao_no_destino(tmp_path, isolar_paths):
    """Mesmo nome canônico no destino: segundo arquivo vira <stem>_1.pdf."""
    pasta = isolar_paths / "data" / "raw" / "andre" / "garantias_estendidas"
    decisao = _decisao_canonica(pasta, nome="GARANTIA_EST_2026-04-19_aabbccdd.pdf")
    arq1 = _arquivo(tmp_path, "split1.pdf", b"v1")
    arq2 = _arquivo(tmp_path, "split2.pdf", b"v2")
    r1 = router.rotear_artefato(arq1, decisao)
    r2 = router.rotear_artefato(arq2, decisao)
    assert r1.sucesso and r2.sucesso
    assert r1.caminho_final.name == "GARANTIA_EST_2026-04-19_aabbccdd.pdf"
    assert r2.caminho_final.name == "GARANTIA_EST_2026-04-19_aabbccdd_1.pdf"
    assert r1.caminho_final.read_bytes() == b"v1"
    assert r2.caminho_final.read_bytes() == b"v2"


def test_rotear_artefato_para_classificar_quando_decisao_e_fallback(tmp_path, isolar_paths):
    artefato = _arquivo(tmp_path, "misterio.pdf", b"x")
    pasta_classificar = isolar_paths / "data" / "raw" / "_classificar"
    decisao = _decisao_fallback(pasta_classificar)
    resultado = router.rotear_artefato(artefato, decisao)
    # Decisao com tipo=None ainda é movida para a pasta indicada (_classificar/),
    # mas marca sucesso=False porque significa "não classifiquei".
    assert resultado.caminho_final.exists()
    assert resultado.caminho_final.parent == pasta_classificar
    assert resultado.sucesso is False
    assert resultado.motivo is not None


def test_rotear_artefato_inexistente_vai_para_classificar_sem_levantar(tmp_path, isolar_paths):
    pasta = isolar_paths / "data" / "raw" / "andre" / "x"
    decisao = _decisao_canonica(pasta)
    resultado = router.rotear_artefato(tmp_path / "nao_existe.pdf", decisao)
    assert resultado.sucesso is False
    assert "inexistente" in (resultado.motivo or "")


def test_rotear_artefato_falha_no_mkdir_vai_pra_classificar(tmp_path, isolar_paths, monkeypatch):
    """Simula EACCES no mkdir do destino canônico via monkeypatch."""
    artefato = _arquivo(tmp_path, "x.pdf", b"v")
    pasta_canonica = isolar_paths / "data" / "raw" / "andre" / "garantias_estendidas"
    decisao = _decisao_canonica(pasta_canonica)

    original_mkdir = Path.mkdir

    def mkdir_falhador(self, *args, **kwargs):
        if str(self) == str(pasta_canonica):
            raise OSError("EACCES simulado")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", mkdir_falhador)
    resultado = router.rotear_artefato(artefato, decisao)
    assert resultado.sucesso is False
    assert "falha ao criar pasta destino" in (resultado.motivo or "")


# ============================================================================
# descartar_da_inbox
# ============================================================================


def test_descartar_da_inbox_remove_em_sucesso_total(tmp_path, isolar_paths):
    inbox_arq = _arquivo(tmp_path, "x.pdf", b"v")
    removido = router.descartar_da_inbox(inbox_arq, sucesso_total=True)
    assert removido is True
    assert not inbox_arq.exists()


def test_descartar_da_inbox_mantem_em_sucesso_parcial(tmp_path, isolar_paths):
    inbox_arq = _arquivo(tmp_path, "x.pdf", b"v")
    removido = router.descartar_da_inbox(inbox_arq, sucesso_total=False)
    assert removido is False
    assert inbox_arq.exists()


def test_descartar_da_inbox_inexistente_devolve_false(tmp_path, isolar_paths):
    fantasma = tmp_path / "fantasma.pdf"
    assert router.descartar_da_inbox(fantasma, sucesso_total=True) is False


# ============================================================================
# rotear_lote
# ============================================================================


def test_rotear_lote_sucesso_total_faz_cleanup_do_envelope(tmp_path, isolar_paths):
    """3 artefatos, todos casam tipo canônico -> envelope removido."""
    inbox_arq = _arquivo(tmp_path, "compilado.pdf", b"%PDF-1.4 fake")
    cop = router.arquivar_original(inbox_arq)
    sha8 = cop.stem

    diretorio_split = isolar_paths / "data" / "raw" / "_envelopes" / "pdf_split" / sha8
    diretorio_split.mkdir(parents=True)
    pares = []
    pasta_destino = isolar_paths / "data" / "raw" / "andre" / "garantias_estendidas"
    for i in range(1, 4):
        artefato = diretorio_split / f"pg{i}.pdf"
        artefato.write_bytes(f"pg{i}-bytes".encode())
        decisao = _decisao_canonica(pasta_destino, nome=f"GARANTIA_EST_pg{i}.pdf")
        pares.append((artefato, decisao))

    relatorio = router.rotear_lote(
        arquivo_inbox=inbox_arq,
        sha8_envelope=sha8,
        diretorio_envelope=diretorio_split,
        pares_artefato_decisao=pares,
    )
    assert relatorio.sucesso_total is True
    assert len(relatorio.artefatos) == 3
    assert all(a.sucesso for a in relatorio.artefatos)
    assert not diretorio_split.exists(), "envelope deveria ter sido removido (sucesso total)"


def test_rotear_lote_sucesso_parcial_mantem_envelope(tmp_path, isolar_paths):
    """Artefato 2 não classifica (decisão fallback) -> envelope mantido para auditoria."""
    inbox_arq = _arquivo(tmp_path, "compilado.pdf", b"%PDF-1.4 mix")
    cop = router.arquivar_original(inbox_arq)
    sha8 = cop.stem

    diretorio_split = isolar_paths / "data" / "raw" / "_envelopes" / "pdf_split" / sha8
    diretorio_split.mkdir(parents=True)
    pasta_canonica = isolar_paths / "data" / "raw" / "andre" / "garantias_estendidas"
    pasta_classificar = isolar_paths / "data" / "raw" / "_classificar"

    arq1 = diretorio_split / "pg1.pdf"
    arq1.write_bytes(b"pg1")
    arq2 = diretorio_split / "pg2.pdf"
    arq2.write_bytes(b"pg2")

    pares = [
        (arq1, _decisao_canonica(pasta_canonica, nome="OK_pg1.pdf")),
        (arq2, _decisao_fallback(pasta_classificar)),
    ]
    relatorio = router.rotear_lote(
        arquivo_inbox=inbox_arq,
        sha8_envelope=sha8,
        diretorio_envelope=diretorio_split,
        pares_artefato_decisao=pares,
    )
    assert relatorio.sucesso_total is False
    assert relatorio.artefatos[0].sucesso is True
    assert relatorio.artefatos[1].sucesso is False
    assert diretorio_split.exists(), "envelope deve permanecer para auditoria"


def test_rotear_lote_propaga_erros_do_envelope(tmp_path, isolar_paths):
    """Erros do envelope (zip-slip, etc.) entram no relatório e impedem sucesso_total."""
    inbox_arq = _arquivo(tmp_path, "x.zip", b"PK fake")
    cop = router.arquivar_original(inbox_arq)
    sha8 = cop.stem
    diretorio_split = isolar_paths / "data" / "raw" / "_envelopes" / "zip" / sha8
    diretorio_split.mkdir(parents=True)
    arq1 = diretorio_split / "ok.pdf"
    arq1.write_bytes(b"x")
    pasta_canonica = isolar_paths / "data" / "raw" / "andre" / "extratos"
    pares = [
        (
            arq1,
            Decisao(
                tipo="extrato_bancario",
                prioridade="normal",
                match_mode="any",
                extrator_modulo=None,
                origem_sprint=41,
                pasta_destino=pasta_canonica,
                nome_canonico="EXTRATO_aaaa.pdf",
                data_detectada_iso=None,
                regras_avaliadas=4,
            ),
        )
    ]
    relatorio = router.rotear_lote(
        arquivo_inbox=inbox_arq,
        sha8_envelope=sha8,
        diretorio_envelope=diretorio_split,
        pares_artefato_decisao=pares,
        erros_envelope=["zip-slip recusado: '/etc/passwd'"],
    )
    assert relatorio.sucesso_total is False  # erros no envelope vetam sucesso
    assert relatorio.artefatos[0].sucesso is True  # mas o artefato individual foi OK
    assert "zip-slip" in relatorio.erros[0]


# "Cada coisa em seu lugar e um lugar para cada coisa." -- Benjamin Franklin
