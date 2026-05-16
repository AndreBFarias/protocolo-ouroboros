"""Testes do script `scripts/diagnosticar_linking.py` (Sprint LINK-AUDIT-01).

Usa grafo sintético em memória SQLite para validar:
1. Contagem correta de linkados/órfãos por tipo.
2. Função `menor_combinacao_que_resolve` devolve a primeira janela/tolerância
   que aceita ao menos 1 candidata, em ordem crescente.
3. Documentos com `total=0.0` não geram candidatas (espelha filtro do motor).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from scripts.diagnosticar_linking import (
    encontrar_candidatas,
    gerar_diagnostico,
    menor_combinacao_que_resolve,
)


def _criar_grafo_sintetico(caminho: Path) -> None:
    """Popula SQLite com schema mínimo do grafo + 2 docs + 3 transações + 1 aresta."""
    conn = sqlite3.connect(str(caminho))
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE node (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            nome_canonico TEXT NOT NULL,
            aliases TEXT NOT NULL DEFAULT '[]',
            metadata TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE edge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_id INTEGER NOT NULL,
            dst_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            peso REAL NOT NULL DEFAULT 1.0,
            evidencia TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # 2 documentos: um holerite (linkado) e um DAS PARCSN (órfão).
    holerite_meta = {
        "tipo_documento": "holerite",
        "data_emissao": "2026-01-01",
        "total": 1000.00,
    }
    das_meta = {
        "tipo_documento": "das_parcsn_andre",
        "data_emissao": "2026-02-15",
        "vencimento": "2026-02-15",
        "total": 350.00,
    }
    # Documento com total zero (DIRPF retif simulado) -- deve ser pulado.
    dirpf_meta = {
        "tipo_documento": "dirpf_retif",
        "data_emissao": "2026-04-30",
        "total": 0.0,
    }
    cur.execute(
        "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
        ("documento", "HOLERITE|FOO|2026-01", json.dumps(holerite_meta)),
    )
    holerite_id = cur.lastrowid
    cur.execute(
        "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
        ("documento", "DAS|123|2026-02", json.dumps(das_meta)),
    )
    cur.execute(
        "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
        ("documento", "DIRPF|2025", json.dumps(dirpf_meta)),
    )

    # 3 transações: 1 casa holerite (linkada), 1 casa DAS perto da janela, 1 sem relação.
    for nome, meta in [
        ("TX-HOLERITE-MATCH", {"data": "2026-01-05", "valor": 1000.00}),
        ("TX-DAS-PROXIMO", {"data": "2026-02-13", "valor": 351.00}),
        ("TX-NAO-RELACIONADO", {"data": "2025-07-10", "valor": 50.00}),
    ]:
        cur.execute(
            "INSERT INTO node (tipo, nome_canonico, metadata) VALUES (?, ?, ?)",
            ("transacao", nome, json.dumps(meta)),
        )
    tx_holerite_id = cur.execute(
        "SELECT id FROM node WHERE nome_canonico='TX-HOLERITE-MATCH'"
    ).fetchone()[0]

    # Aresta documento_de holerite -> tx_holerite (já linkado).
    cur.execute(
        "INSERT INTO edge (src_id, dst_id, tipo, peso, evidencia) "
        "VALUES (?, ?, 'documento_de', 1.0, '{}')",
        (holerite_id, tx_holerite_id),
    )

    conn.commit()
    conn.close()


@pytest.fixture
def grafo_sintetico(tmp_path: Path) -> Path:
    """Fixture: caminho para grafo SQLite sintético reproducível."""
    caminho = tmp_path / "grafo.sqlite"
    _criar_grafo_sintetico(caminho)
    return caminho


def test_diagnostico_conta_linkados_e_orfaos(grafo_sintetico: Path) -> None:
    """gerar_diagnostico devolve 1 linkado (holerite) e 2 órfãos (DAS + dirpf)."""
    diag = gerar_diagnostico(grafo_sintetico)

    assert diag["total_documentos"] == 3
    assert diag["total_linkados"] == 1
    assert diag["total_orfaos"] == 2
    assert diag["total_transacoes"] == 3
    assert diag["linkados_por_tipo"] == {"holerite": 1}
    assert diag["orfaos_por_tipo"] == {"das_parcsn_andre": 1, "dirpf_retif": 1}

    # linking_pct (transacoes) = 1/3 = 33.33%
    assert diag["linking_pct_transacoes"] == pytest.approx(33.3333, abs=0.01)


def test_menor_combinacao_para_das_resolve_em_3d_5pct(grafo_sintetico: Path) -> None:
    """O DAS sintético (venc=2026-02-15, total=350) tem tx perto (2026-02-13, 351).

    Delta = 2d. Diff_pct = 1/350 = 0.286%. Deve resolver em janela=3d, tol=0.5%.
    """
    from scripts.diagnosticar_linking import carregar_documentos_e_transacoes

    docs, txs, linkados = carregar_documentos_e_transacoes(grafo_sintetico)
    das = next(d for d in docs if d["metadata"].get("tipo_documento") == "das_parcsn_andre")
    assert das["id"] not in linkados

    resultado = menor_combinacao_que_resolve(das, txs)
    assert resultado is not None
    assert resultado["janela_dias_minima"] == 3
    # Menor tolerância da varredura que casa 1/350 (=0.286%) é 0.005 (=0.5%).
    assert resultado["tolerancia_pct_minima"] == 0.005
    assert resultado["qtd_candidatas"] == 1


def test_documento_com_total_zero_nao_gera_candidatas(grafo_sintetico: Path) -> None:
    """`encontrar_candidatas` espelha filtro do motor: total <= R$ 0,01 não casa."""
    from scripts.diagnosticar_linking import carregar_documentos_e_transacoes

    docs, txs, _ = carregar_documentos_e_transacoes(grafo_sintetico)
    dirpf = next(d for d in docs if d["metadata"].get("tipo_documento") == "dirpf_retif")

    # Mesmo com janela e tolerância absurdas, total=0 não passa.
    candidatas = encontrar_candidatas(dirpf, txs, janela_dias=999, tolerancia_pct=0.99)
    assert candidatas == []

    # E menor_combinacao_que_resolve devolve None.
    assert menor_combinacao_que_resolve(dirpf, txs) is None


def test_ancora_temporal_das_usa_vencimento() -> None:
    """DAS_PARCSN_ANDRE deve usar `vencimento` como âncora (espelha YAML)."""
    from scripts.diagnosticar_linking import _ancora_temporal_para_tipo

    meta_das = {"data_emissao": "2026-02-01", "vencimento": "2026-02-15"}
    assert _ancora_temporal_para_tipo(meta_das, "das_parcsn_andre") == "2026-02-15"

    # Tipos não-DAS usam data_emissao.
    assert _ancora_temporal_para_tipo(meta_das, "holerite") == "2026-02-01"
    assert _ancora_temporal_para_tipo(meta_das, "cupom_fiscal") == "2026-02-01"

    # Fallback para data_emissao quando vencimento ausente em DAS.
    meta_sem_venc = {"data_emissao": "2026-02-01"}
    assert _ancora_temporal_para_tipo(meta_sem_venc, "das_parcsn_andre") == "2026-02-01"


def test_encontrar_candidatas_ordena_por_diff_pct_e_delta() -> None:
    """Saída de encontrar_candidatas vem ordenada do match mais forte ao mais fraco."""
    doc = {
        "metadata": {
            "tipo_documento": "cupom_fiscal",
            "data_emissao": "2026-04-15",
            "total": 100.00,
        }
    }
    transacoes = [
        # tx mais distante mas valor exato
        {"id": 1, "data": date(2026, 4, 20), "valor": 100.00, "metadata": {}},
        # tx no dia, valor 1% off
        {"id": 2, "data": date(2026, 4, 15), "valor": 99.00, "metadata": {}},
        # tx no dia, valor exato
        {"id": 3, "data": date(2026, 4, 15), "valor": 100.00, "metadata": {}},
    ]
    cands = encontrar_candidatas(doc, transacoes, janela_dias=7, tolerancia_pct=0.05)
    assert len(cands) == 3
    # ordenacao: (diff_pct, |delta_dias|)
    # tx 3: diff_pct=0, delta=0 -> primeira
    # tx 1: diff_pct=0, delta=5 -> segunda
    # tx 2: diff_pct=0.01, delta=0 -> terceira
    assert [c["tid"] for c in cands] == [3, 1, 2]


# "O teste é a forma honesta de admitir que ainda não confiamos no que escrevemos." -- adágio do TDD
