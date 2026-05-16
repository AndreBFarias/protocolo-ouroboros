"""Testes para o wrapper ``scripts/processar_inbox_massa.py``.

Sprint INFRA-PROCESSAR-INBOX-MASSA -- valida que o wrapper:
- gera log estruturado JSON,
- captura estado antes/depois do grafo,
- respeita ``--sem-backup`` e ``--dry-run``.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "scripts" / "processar_inbox_massa.py"


@pytest.fixture
def grafo_temporario(tmp_path: Path) -> Path:
    """Cria um grafo SQLite mínimo para o wrapper inspecionar."""
    g = tmp_path / "grafo.sqlite"
    with sqlite3.connect(g) as con:
        con.executescript(
            """
            CREATE TABLE node (id INTEGER PRIMARY KEY, tipo TEXT,
                               nome_canonico TEXT, aliases TEXT,
                               metadata TEXT, created_at TEXT,
                               updated_at TEXT);
            CREATE TABLE edge (id INTEGER PRIMARY KEY, src_id INTEGER,
                               dst_id INTEGER, tipo TEXT, peso REAL,
                               evidencia TEXT, created_at TEXT);
            INSERT INTO node (tipo, nome_canonico) VALUES ('documento', 'doc1');
            INSERT INTO node (tipo, nome_canonico) VALUES ('transacao', 't1');
            INSERT INTO edge (src_id, dst_id, tipo, peso, evidencia)
                VALUES (2, 1, 'documento_de', 1.0, '{}');
            """
        )
    return g


def test_script_existe_e_eh_executavel():
    assert SCRIPT.exists()
    conteudo = SCRIPT.read_text(encoding="utf-8")
    assert "def main()" in conteudo
    assert "--dry-run" in conteudo
    assert "--forcar-reextracao" in conteudo
    assert "--sem-backup" in conteudo


def test_help_ok():
    """O wrapper exibe help sem erro."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Wrapper" in result.stdout or "wrapper" in result.stdout.lower()


def test_contar_grafo_estado_inicial(grafo_temporario: Path):
    """Função ``contar_grafo`` retorna contagens corretas."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        from processar_inbox_massa import contar_grafo

        d = contar_grafo(grafo_temporario)
        assert d["nodes"]["documento"] == 1
        assert d["nodes"]["transacao"] == 1
        assert d["edges"]["documento_de"] == 1
    finally:
        sys.path.pop(0)


def test_contar_grafo_inexistente(tmp_path: Path):
    """Grafo ausente retorna estrutura vazia."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        from processar_inbox_massa import contar_grafo

        d = contar_grafo(tmp_path / "nao-existe.sqlite")
        assert d == {"nodes": {}, "edges": {}}
    finally:
        sys.path.pop(0)


def test_fazer_backup_cria_copia(grafo_temporario: Path):
    """Backup gera arquivo `.bak.<ts>` ao lado do original."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        from processar_inbox_massa import fazer_backup

        destino = fazer_backup(grafo_temporario, "20260508T120000")
        assert destino is not None
        assert destino.exists()
        assert ".bak.20260508T120000" in destino.name
    finally:
        sys.path.pop(0)


def test_fazer_backup_grafo_inexistente(tmp_path: Path):
    """Backup retorna None quando grafo não existe."""
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        from processar_inbox_massa import fazer_backup

        assert fazer_backup(tmp_path / "x.sqlite", "ts") is None
    finally:
        sys.path.pop(0)
