"""Testes do backup automatico do grafo SQLite.

Cobre Sprint INFRA-BACKUP-GRAFO-AUTOMATIZADO (2026-05-14):

1. `_executar_backup_grafo` cria copia + .sha256
2. Skip silencioso quando grafo origem não existe (pipeline inicial)
3. Retencao mantem ultimos 7 dias completos
4. Retencao mantem 1 backup por semana das 4 semanas anteriores aos 7 dias
5. Retencao remove backups alem de 7d+4semanas (5 semanas total)
6. `_restaurar_grafo_de_backup` valida sha256 antes de sobrescrever
7. Restore rejeita backup com checksum inválido
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src import pipeline


@pytest.fixture
def grafo_origem(tmp_path: Path) -> Path:
    """Cria um arquivo SQLite mínimo para servir de grafo origem."""
    p = tmp_path / "grafo.sqlite"
    p.write_bytes(b"SQLite format 3\x00" + b"\x00" * 100)
    return p


@pytest.fixture
def dir_backup(tmp_path: Path) -> Path:
    d = tmp_path / "backup"
    d.mkdir()
    return d


def test_executar_backup_grafo_cria_arquivo_e_sha(
    grafo_origem: Path, dir_backup: Path
) -> None:
    backup = pipeline._executar_backup_grafo(grafo_origem, dir_backup)
    assert backup is not None
    assert backup.exists()
    assert backup.name.startswith(pipeline.PREFIXO_BACKUP_GRAFO)
    assert backup.suffix == ".sqlite"
    # Arquivo .sha256 ao lado
    sha_path = backup.with_suffix(backup.suffix + ".sha256")
    assert sha_path.exists()
    conteudo = sha_path.read_text(encoding="utf-8")
    assert backup.name in conteudo
    # SHA hex válido (64 chars)
    sha_hex = conteudo.split()[0]
    assert len(sha_hex) == 64
    assert all(c in "0123456789abcdef" for c in sha_hex)


def test_executar_backup_grafo_skip_quando_origem_ausente(
    tmp_path: Path, dir_backup: Path
) -> None:
    """Pipeline em estado inicial (sem grafo) -- backup eh no-op silencioso."""
    sem_grafo = tmp_path / "nao_existe.sqlite"
    r = pipeline._executar_backup_grafo(sem_grafo, dir_backup)
    assert r is None


def _criar_backup_fake(dir_backup: Path, ts: datetime) -> Path:
    """Helper: cria um par backup+sha com timestamp dado."""
    nome = f"{pipeline.PREFIXO_BACKUP_GRAFO}{ts.strftime('%Y-%m-%d_%H%M%S')}.sqlite"
    p = dir_backup / nome
    p.write_bytes(b"SQLite format 3\x00" + ts.isoformat().encode())
    sha = pipeline._sha256_arquivo(p)
    sha_path = p.with_suffix(p.suffix + ".sha256")
    sha_path.write_text(f"{sha}  {p.name}\n", encoding="utf-8")
    return p


def test_retencao_mantem_todos_dentro_de_7_dias(dir_backup: Path) -> None:
    agora = datetime.now()
    paths = []
    for h in range(0, 6 * 24, 6):  # backups a cada 6h por 6 dias
        paths.append(_criar_backup_fake(dir_backup, agora - timedelta(hours=h)))
    deletados = pipeline._aplicar_retencao_backups_grafo(dir_backup)
    assert deletados == []
    for p in paths:
        assert p.exists()


def test_retencao_mantem_1_por_semana_alem_dos_7_dias(dir_backup: Path) -> None:
    agora = datetime.now()
    # 3 backups dentro dos 7 dias (devem todos sobreviver)
    for d in range(3):
        _criar_backup_fake(dir_backup, agora - timedelta(days=d))
    # 5 backups na primeira semana ALEM dos 7 dias (8-13 dias) -- 1 deve sobreviver
    semana1: list[Path] = []
    for d in range(8, 13):
        semana1.append(_criar_backup_fake(dir_backup, agora - timedelta(days=d)))
    # 3 backups na segunda semana alem (15-17 dias) -- 1 deve sobreviver
    semana2: list[Path] = []
    for d in range(15, 18):
        semana2.append(_criar_backup_fake(dir_backup, agora - timedelta(days=d)))
    deletados = pipeline._aplicar_retencao_backups_grafo(dir_backup)
    # Sobreviventes na semana1: 1 (o mais recente, índice 0 por estar mais perto do limite)
    vivos_s1 = [p for p in semana1 if p.exists()]
    vivos_s2 = [p for p in semana2 if p.exists()]
    assert len(vivos_s1) == 1, f"Esperado 1 sobrevivente s1, achei {len(vivos_s1)}"
    assert len(vivos_s2) == 1, f"Esperado 1 sobrevivente s2, achei {len(vivos_s2)}"
    # Os deletados são os outros 4 + 2 = 6
    assert len(deletados) >= 6


def test_retencao_remove_alem_de_5_semanas(dir_backup: Path) -> None:
    agora = datetime.now()
    # 1 backup recente (sobrevive)
    recente = _criar_backup_fake(dir_backup, agora - timedelta(days=1))
    # 1 backup com 40 dias (alem de 7 + 4*7 = 35 dias) -- deve ser deletado
    velho = _criar_backup_fake(dir_backup, agora - timedelta(days=40))
    deletados = pipeline._aplicar_retencao_backups_grafo(dir_backup)
    assert recente.exists()
    assert not velho.exists()
    assert velho in deletados


def test_retencao_apaga_sha_junto(dir_backup: Path) -> None:
    agora = datetime.now()
    velho = _criar_backup_fake(dir_backup, agora - timedelta(days=50))
    sha_path = velho.with_suffix(velho.suffix + ".sha256")
    assert sha_path.exists()
    pipeline._aplicar_retencao_backups_grafo(dir_backup)
    assert not velho.exists()
    assert not sha_path.exists()


def test_restaurar_grafo_de_backup_valido(
    grafo_origem: Path, dir_backup: Path
) -> None:
    backup = pipeline._executar_backup_grafo(grafo_origem, dir_backup)
    assert backup is not None
    ts = backup.stem[len(pipeline.PREFIXO_BACKUP_GRAFO):]

    # Modifica o grafo apos backup
    grafo_origem.write_bytes(b"ALTERADO")
    conteudo_alterado = grafo_origem.read_bytes()

    rc = pipeline._restaurar_grafo_de_backup(ts, grafo_origem, dir_backup)
    assert rc == 0
    # Grafo restaurado bate com o backup
    assert grafo_origem.read_bytes() == backup.read_bytes()
    assert grafo_origem.read_bytes() != conteudo_alterado
    # Backup original preservado
    assert backup.exists()
    # Recuo (pre_restore) criado
    recuos = list(grafo_origem.parent.glob("grafo.sqlite.pre_restore_*"))
    assert len(recuos) == 1


def test_restaurar_rejeita_backup_inexistente(
    grafo_origem: Path, dir_backup: Path
) -> None:
    rc = pipeline._restaurar_grafo_de_backup(
        "2000-01-01_000000", grafo_origem, dir_backup
    )
    assert rc == 1


def test_restaurar_rejeita_checksum_invalido(
    grafo_origem: Path, dir_backup: Path
) -> None:
    backup = pipeline._executar_backup_grafo(grafo_origem, dir_backup)
    assert backup is not None
    ts = backup.stem[len(pipeline.PREFIXO_BACKUP_GRAFO):]
    # Corrompe o backup mantendo sha antigo
    backup.write_bytes(b"CORROMPIDO")
    rc = pipeline._restaurar_grafo_de_backup(ts, grafo_origem, dir_backup)
    assert rc == 1
    # Grafo origem não foi sobrescrito
    assert grafo_origem.read_bytes().startswith(b"SQLite format 3")


def test_restaurar_rejeita_sha_ausente(
    grafo_origem: Path, dir_backup: Path
) -> None:
    backup = pipeline._executar_backup_grafo(grafo_origem, dir_backup)
    assert backup is not None
    ts = backup.stem[len(pipeline.PREFIXO_BACKUP_GRAFO):]
    # Deleta o sha
    backup.with_suffix(backup.suffix + ".sha256").unlink()
    rc = pipeline._restaurar_grafo_de_backup(ts, grafo_origem, dir_backup)
    assert rc == 1


# "Backup eh o futuro guardando o passado contra o presente." -- principio do arquivista pragmatico
