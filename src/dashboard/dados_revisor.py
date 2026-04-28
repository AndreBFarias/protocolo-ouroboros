"""Listagem de pendências do Revisor Visual (Sprint D2).

Extraído de ``src/dashboard/dados.py`` na Sprint INFRA-D2a para respeitar o
limite de 800 linhas por arquivo (CLAUDE.md regra 6). Refactor puro -- zero
mudança de comportamento. As funções aqui podem ser importadas via
``src.dashboard.dados`` (re-export preservado para compat com mocks de teste).
"""

import json
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[2]

CAMINHO_GRAFO: Path = _RAIZ / "data" / "output" / "grafo.sqlite"
CAMINHO_RAW_CLASSIFICAR: Path = _RAIZ / "data" / "raw" / "_classificar"
CAMINHO_RAW_CONFERIR: Path = _RAIZ / "data" / "raw" / "_conferir"


def listar_pendencias_revisao(
    caminho_grafo: Path | None = None,
    caminho_classificar: Path | None = None,
    caminho_conferir: Path | None = None,
    limite_confidence: float = 0.8,
) -> list[dict]:
    """Lista pendências para o Revisor Visual (Sprint D2).

    Critérios de inclusão (em ordem de prioridade):
      1. Arquivos em ``data/raw/_classificar/`` (não-classificados pelo
         pipeline -- prioridade máxima).
      2. Arquivos/diretórios em ``data/raw/_conferir/`` (fallback do
         supervisor com recall < limiar -- prioridade alta).
      3. Nodes ``documento`` do grafo com ``metadata.confidence``
         abaixo de ``limite_confidence``.
      4. Nodes ``documento`` sem aresta ``documento_de`` saindo
         (achado P0 da auditoria 2026-04-26: 0% docs vinculados).

    Parâmetros opcionais permitem injetar paths em testes (sem precisar
    monkeypatchear constantes globais).

    Cada pendência é um dict com:
      - ``item_id``: identificador estável (caminho relativo ou ``node_<id>``).
      - ``tipo``: ``raw_classificar`` | ``raw_conferir`` |
        ``grafo_low_confidence`` | ``grafo_sem_link``.
      - ``caminho``: Path absoluto do arquivo original (str) quando aplicável.
      - ``metadata``: dict com campos extras (tipo_documento, razao_social, etc.).
      - ``prioridade``: int 1 (mais alto) a 4.

    Read-only no grafo. Não toca em ``data/raw/``.
    """
    grafo = caminho_grafo if caminho_grafo is not None else CAMINHO_GRAFO
    raw_classificar = (
        caminho_classificar if caminho_classificar is not None else CAMINHO_RAW_CLASSIFICAR
    )
    raw_conferir = caminho_conferir if caminho_conferir is not None else CAMINHO_RAW_CONFERIR

    pendencias: list[dict] = []

    if raw_classificar.exists() and raw_classificar.is_dir():
        for arquivo in sorted(raw_classificar.iterdir()):
            if arquivo.is_file():
                pendencias.append(
                    {
                        "item_id": str(arquivo.relative_to(raw_classificar.parents[1])),
                        "tipo": "raw_classificar",
                        "caminho": str(arquivo),
                        "metadata": {"nome": arquivo.name},
                        "prioridade": 1,
                    }
                )

    if raw_conferir.exists() and raw_conferir.is_dir():
        for entrada in sorted(raw_conferir.iterdir()):
            pendencias.append(
                {
                    "item_id": str(entrada.relative_to(raw_conferir.parents[1])),
                    "tipo": "raw_conferir",
                    "caminho": str(entrada),
                    "metadata": {"nome": entrada.name, "eh_diretorio": entrada.is_dir()},
                    "prioridade": 2,
                }
            )

    if grafo.exists():
        import sqlite3

        conn = sqlite3.connect(f"file:{grafo}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            ids_vinculados: set[int] = set()
            for row in conn.execute("SELECT DISTINCT src_id FROM edge WHERE tipo = 'documento_de'"):
                ids_vinculados.add(int(row["src_id"]))

            for row in conn.execute(
                "SELECT id, nome_canonico, metadata FROM node WHERE tipo = 'documento'"
            ):
                node_id = int(row["id"])
                meta_raw = row["metadata"] or "{}"
                try:
                    meta = json.loads(meta_raw)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
                confidence = meta.get("confidence")
                arquivo_origem = meta.get("arquivo_origem", "")

                if isinstance(confidence, (int, float)) and confidence < limite_confidence:
                    pendencias.append(
                        {
                            "item_id": f"node_{node_id}",
                            "tipo": "grafo_low_confidence",
                            "caminho": arquivo_origem,
                            "metadata": {
                                "nome_canonico": row["nome_canonico"],
                                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                                "confidence": float(confidence),
                                "razao_social": meta.get("razao_social", ""),
                                "data_emissao": meta.get("data_emissao", ""),
                                "total": float(meta.get("total", 0.0) or 0.0),
                            },
                            "prioridade": 3,
                        }
                    )
                    continue

                if node_id not in ids_vinculados:
                    pendencias.append(
                        {
                            "item_id": f"node_{node_id}",
                            "tipo": "grafo_sem_link",
                            "caminho": arquivo_origem,
                            "metadata": {
                                "nome_canonico": row["nome_canonico"],
                                "tipo_documento": meta.get("tipo_documento", "desconhecido"),
                                "razao_social": meta.get("razao_social", ""),
                                "data_emissao": meta.get("data_emissao", ""),
                                "total": float(meta.get("total", 0.0) or 0.0),
                            },
                            "prioridade": 4,
                        }
                    )
        finally:
            conn.close()

    pendencias.sort(key=lambda p: (p["prioridade"], p["item_id"]))
    return pendencias


# "Não basta saber, é preciso também aplicar; não basta querer, é preciso também fazer." -- Goethe
