"""Sprint INFRA-DEDUP-CLASSIFICAR: testes regressivos do dedup automático.

Cobre:
  1. 3 PDFs bit-a-bit -> 1 sobra (canônico).
  2. 2 PDFs com sufixos `_1`, `_2` mas sem canônico -> mantém o `_1`.
  3. PDFs com hashes distintos NÃO são tocados.
  4. dry_run não remove nada.
  5. Idempotência: rodar 2x devolve 0 removidos na segunda.
  6. Pasta vazia ou inexistente.
"""

from __future__ import annotations

from pathlib import Path

from src.intake.dedup_classificar import (
    _eh_canonico,
    _escolher_canonico,
    deduplicar_classificar,
)


def test_eh_canonico_distingue_sufixo_numerico():
    assert _eh_canonico("doc.pdf") is True
    assert _eh_canonico("doc_1.pdf") is False
    assert _eh_canonico("doc_2.pdf") is False
    assert _eh_canonico("CLASSIFICAR_abc123.pdf") is True
    assert _eh_canonico("CLASSIFICAR_abc123_1.pdf") is False
    # Sufixo na palavra (não _<N> antes de .ext) NÃO conta:
    assert _eh_canonico("relatorio2026.pdf") is True


def test_escolher_canonico_prefere_sem_sufixo(tmp_path: Path):
    a = tmp_path / "doc.pdf"
    b = tmp_path / "doc_1.pdf"
    c = tmp_path / "doc_2.pdf"
    for p in (a, b, c):
        p.write_bytes(b"X")
    assert _escolher_canonico([a, b, c]) == a


def test_escolher_canonico_fallback_lexicografico(tmp_path: Path):
    """Sem canônico, mantém o de menor lexicografia (estável)."""
    b = tmp_path / "doc_2.pdf"
    a = tmp_path / "doc_1.pdf"
    for p in (a, b):
        p.write_bytes(b"X")
    assert _escolher_canonico([b, a]) == a


def test_dedup_3_copias_bitaabit_mantem_canonico(tmp_path: Path):
    conteudo = b"PDF FAKE bit-a-bit"
    a = tmp_path / "_CLASSIFICAR_abc.pdf"
    b = tmp_path / "_CLASSIFICAR_abc_1.pdf"
    c = tmp_path / "_CLASSIFICAR_abc_2.pdf"
    for p in (a, b, c):
        p.write_bytes(conteudo)

    rel = deduplicar_classificar(tmp_path, dry_run=False)
    assert rel["removidos"] == 2
    assert rel["preservados"] == 1
    assert a.exists()
    assert not b.exists()
    assert not c.exists()


def test_dedup_dry_run_nao_remove(tmp_path: Path):
    conteudo = b"X"
    a = tmp_path / "doc.pdf"
    b = tmp_path / "doc_1.pdf"
    a.write_bytes(conteudo)
    b.write_bytes(conteudo)

    rel = deduplicar_classificar(tmp_path, dry_run=True)
    assert rel["removidos"] == 1  # quantos SERIAM removidos
    assert a.exists()
    assert b.exists()  # não foi removido em dry-run


def test_dedup_hashes_distintos_preserva_todos(tmp_path: Path):
    a = tmp_path / "doc1.pdf"
    b = tmp_path / "doc2.pdf"
    c = tmp_path / "doc3.pdf"
    a.write_bytes(b"X")
    b.write_bytes(b"Y")
    c.write_bytes(b"Z")

    rel = deduplicar_classificar(tmp_path, dry_run=False)
    assert rel["removidos"] == 0
    assert rel["preservados"] == 3
    for p in (a, b, c):
        assert p.exists()


def test_dedup_idempotente(tmp_path: Path):
    a = tmp_path / "doc.pdf"
    b = tmp_path / "doc_1.pdf"
    a.write_bytes(b"X")
    b.write_bytes(b"X")

    r1 = deduplicar_classificar(tmp_path, dry_run=False)
    assert r1["removidos"] == 1

    r2 = deduplicar_classificar(tmp_path, dry_run=False)
    assert r2["removidos"] == 0
    assert r2["preservados"] == 1


def test_dedup_pasta_vazia(tmp_path: Path):
    rel = deduplicar_classificar(tmp_path, dry_run=False)
    assert rel == {"removidos": 0, "preservados": 0, "grupos": []}


def test_dedup_pasta_inexistente(tmp_path: Path):
    rel = deduplicar_classificar(tmp_path / "nao_existe", dry_run=False)
    assert rel == {"removidos": 0, "preservados": 0, "grupos": []}


def test_dedup_grupos_no_relatorio(tmp_path: Path):
    a = tmp_path / "doc.pdf"
    b = tmp_path / "doc_1.pdf"
    a.write_bytes(b"X")
    b.write_bytes(b"X")

    rel = deduplicar_classificar(tmp_path, dry_run=True)
    assert len(rel["grupos"]) == 1
    g = rel["grupos"][0]
    assert g["canonico"].endswith("doc.pdf")
    assert any(d.endswith("doc_1.pdf") for d in g["descartados"])


# "A repeticao do mesmo nada não se promove a herança." -- princípio anti-acumulacao
