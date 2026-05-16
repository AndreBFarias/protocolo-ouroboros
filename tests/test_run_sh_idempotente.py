"""Sprint ANTI-MIGUE-09: testes regressivos de idempotência do
reprocessamento de documentos (`./run.sh --reextrair-tudo`, alias
de `python -m scripts.reprocessar_documentos --forcar-reextracao`).

Cobre 3 cenários:

1. **Sem --forcar-reextracao**: rodar 2x sobre o mesmo input não duplica
   nodes nem edges (INSERT OR IGNORE garante idempotência).
2. **Com --forcar-reextracao**: limpa docs antes de reingerir; estado
   final converge para o mesmo do passo 1.
3. **Misto**: rodar normal -> rodar com --forcar -> contagens iguais ao
   passo 1 (reextração não cria lixo).

Usa fixture XML NFe sintética (`tests/fixtures/nfe_xml/nfe_varejo_3itens.xml`)
que não depende de OCR/pdfplumber, tornando o teste rápido e determinístico.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.reprocessar_documentos import main as reprocessar_main
from src.graph.db import GrafoDB

FIXTURE_NFE = Path(__file__).parent / "fixtures" / "nfe_xml" / "nfe_varejo_3itens.xml"


def _contagens(grafo_path: Path) -> dict[str, int]:
    """Captura contagem de nodes por tipo + total de edges."""
    db = GrafoDB(grafo_path)
    cur = db._conn.cursor()  # noqa: SLF001 -- inspeção interna determinística
    nodes_por_tipo = dict(cur.execute("SELECT tipo, COUNT(*) FROM node GROUP BY tipo").fetchall())
    total_edges = cur.execute("SELECT COUNT(*) FROM edge").fetchone()[0]
    db.fechar()
    return {"nodes": nodes_por_tipo, "edges": total_edges}


@pytest.fixture
def ambiente_isolado(tmp_path: Path) -> tuple[Path, Path]:
    """Prepara raw/_indefinida/ com 1 XML NFe + grafo vazio em tmp_path."""
    raw = tmp_path / "raw" / "_indefinida"
    raw.mkdir(parents=True)
    shutil.copy(FIXTURE_NFE, raw / "nfe_teste.xml")
    grafo = tmp_path / "grafo.sqlite"
    return tmp_path / "raw", grafo


def test_reprocessamento_sem_forcar_e_idempotente(ambiente_isolado: tuple[Path, Path]):
    """Rodar 2x sem --forcar-reextracao não duplica nodes nem edges."""
    raw, grafo = ambiente_isolado

    rc_a = reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo)])
    assert rc_a == 0
    snapshot_apos_1 = _contagens(grafo)

    rc_b = reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo)])
    assert rc_b == 0
    snapshot_apos_2 = _contagens(grafo)

    assert snapshot_apos_2 == snapshot_apos_1, (
        f"reprocessamento sem --forcar deveria ser idempotente.\n"
        f"  rodada 1: {snapshot_apos_1}\n"
        f"  rodada 2: {snapshot_apos_2}"
    )


def test_reprocessamento_com_forcar_converge(ambiente_isolado: tuple[Path, Path]):
    """Com --forcar-reextracao: estado final = estado de uma única rodada limpa."""
    raw, grafo = ambiente_isolado

    rc_a = reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo)])
    assert rc_a == 0
    snapshot_apos_1 = _contagens(grafo)

    rc_b = reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo), "--forcar-reextracao"])
    assert rc_b == 0
    snapshot_apos_forcar = _contagens(grafo)

    assert snapshot_apos_forcar == snapshot_apos_1, (
        f"--forcar-reextracao deveria reconstruir o mesmo estado.\n"
        f"  apos 1a rodada: {snapshot_apos_1}\n"
        f"  apos --forcar: {snapshot_apos_forcar}"
    )


def test_reprocessamento_dupla_forcar_e_idempotente(ambiente_isolado: tuple[Path, Path]):
    """Rodar `--forcar-reextracao` 2x sobre o mesmo input não diverge."""
    raw, grafo = ambiente_isolado

    reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo), "--forcar-reextracao"])
    snapshot_a = _contagens(grafo)

    reprocessar_main(["--raiz", str(raw), "--grafo", str(grafo), "--forcar-reextracao"])
    snapshot_b = _contagens(grafo)

    assert snapshot_b == snapshot_a, (
        f"--forcar-reextracao em sequência deveria convergir para o mesmo estado.\n"
        f"  rodada 1: {snapshot_a}\n"
        f"  rodada 2: {snapshot_b}"
    )


# "Quem tem ânimo, encontra caminho." -- Sêneca
