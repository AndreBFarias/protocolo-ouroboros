"""Sprint 105: testes regressivos da migração casal->pessoa via CPF.

Cobre:
  1. Helper _calcular_destino preserva subpastas relativas.
  2. Arquivo com CPF do Andre -> pessoa retorna 'andre' (mock pessoa_detector).  # anonimato-allow
  3. Arquivo sem CPF claro -> pessoa permanece 'casal' (não migra).
  4. dry_run não move arquivos.
  5. Idempotência: rodar 2x não duplica.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from scripts.migrar_pessoa_via_cpf import _calcular_destino, migrar_pessoa_via_cpf


def test_calcular_destino_preserva_subpastas(tmp_path: Path):
    raiz = tmp_path / "raw"
    arquivo = raiz / "casal" / "nfs_fiscais" / "nfce" / "doc.pdf"
    destino = _calcular_destino(arquivo, raiz, "andre")
    assert destino == raiz / "andre" / "nfs_fiscais" / "nfce" / "doc.pdf"


def test_migrar_arquivo_andre_via_cpf_executar(tmp_path: Path):
    raiz = tmp_path / "raw"
    pasta = raiz / "casal" / "nfs_fiscais" / "nfce"
    pasta.mkdir(parents=True)
    arq = pasta / "nfce_xyz.pdf"
    arq.write_bytes(b"%PDF-1.4 fake content")

    # Mock detectar_pessoa: retorna 'andre'
    with patch("scripts.migrar_pessoa_via_cpf.detectar_pessoa", return_value=("andre", "CPF X")):
        rel = migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=False)

    assert rel["total_em_casal"] == 1
    assert rel["migrados"] == 1
    destino = raiz / "andre" / "nfs_fiscais" / "nfce" / "nfce_xyz.pdf"
    assert destino.exists()
    assert not arq.exists()


def test_migrar_arquivo_casal_preserva(tmp_path: Path):
    raiz = tmp_path / "raw"
    pasta = raiz / "casal" / "nfs_fiscais" / "nfce"
    pasta.mkdir(parents=True)
    arq = pasta / "nfce_xyz.pdf"
    arq.write_bytes(b"%PDF-1.4 fake")

    # Mock: pessoa_detector retorna 'casal'
    with patch("scripts.migrar_pessoa_via_cpf.detectar_pessoa", return_value=("casal", "fallback")):
        rel = migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=False)

    assert rel["total_em_casal"] == 1
    assert rel["migrados"] == 0
    assert rel["preservados"] == 1
    assert arq.exists()  # não foi movido


def test_dry_run_nao_move_arquivo(tmp_path: Path):
    raiz = tmp_path / "raw"
    pasta = raiz / "casal" / "boletos"
    pasta.mkdir(parents=True)
    arq = pasta / "boleto.pdf"
    arq.write_bytes(b"%PDF-1.4 fake")

    with patch("scripts.migrar_pessoa_via_cpf.detectar_pessoa", return_value=("andre", "CPF Y")):
        rel = migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=True)

    assert rel["migrados"] == 1  # contagem
    assert arq.exists()  # mas não moveu


def test_idempotente_apos_migracao(tmp_path: Path):
    raiz = tmp_path / "raw"
    pasta = raiz / "casal" / "nfs_fiscais" / "nfce"
    pasta.mkdir(parents=True)
    arq = pasta / "doc.pdf"
    arq.write_bytes(b"%PDF-1.4 fake")

    with patch("scripts.migrar_pessoa_via_cpf.detectar_pessoa", return_value=("andre", "CPF X")):
        r1 = migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=False)
        r2 = migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=False)

    assert r1["migrados"] == 1
    assert r2["total_em_casal"] == 0  # casal/ esta vazio agora
    assert r2["migrados"] == 0


def test_destino_existente_nao_sobrescreve(tmp_path: Path):
    raiz = tmp_path / "raw"
    casal_dir = raiz / "casal" / "nfs_fiscais" / "nfce"
    andre_dir = raiz / "andre" / "nfs_fiscais" / "nfce"
    casal_dir.mkdir(parents=True)
    andre_dir.mkdir(parents=True)
    arq_casal = casal_dir / "doc.pdf"
    arq_andre = andre_dir / "doc.pdf"  # ja existe no destino
    arq_casal.write_bytes(b"X")
    arq_andre.write_bytes(b"Y")

    with patch("scripts.migrar_pessoa_via_cpf.detectar_pessoa", return_value=("andre", "X")):
        migrar_pessoa_via_cpf(raiz_raw=raiz, dry_run=False)

    # Quando destino existe, não sobrescreve
    assert arq_casal.exists()  # preservado
    assert arq_andre.exists()
    assert arq_andre.read_bytes() == b"Y"  # não tocado


# "Cada doc tem dono certo; o que duvidar pertence ao casal."
# -- principio do roteamento honesto
