"""Diagnóstico empírico do linking documento -> transação (Sprint LINK-AUDIT-01).

Lê `data/output/grafo.sqlite` (ou caminho informado), identifica documentos
sem aresta `documento_de` e tenta encontrar transação candidata afrouxando
cada critério (janela temporal, tolerância de valor, pessoa) por vez.

Saídas
------

- Tabela no stdout: contagem de órfãos por tipo + análise das candidatas que
  seriam liberadas afrouxando 1 critério.
- Quando `--export-json PATH` for informado, escreve JSON estruturado com:

  ```
  {
    "total_documentos": N,
    "total_linkados": M,
    "linking_pct": float,
    "orfaos_por_tipo": {tipo: count, ...},
    "candidatos_por_tipo": {
        tipo: [
            {"doc_id": int, "doc_nome": str, "menor_janela_que_resolve": int,
             "menor_tol_que_resolve": float, "candidatas": [...]},
            ...
        ]
    }
  }
  ```

Uso
---

    python scripts/diagnosticar_linking.py [--grafo PATH] [--export-json PATH]

Sprint LINK-AUDIT-01 (2026-05-15). Script puramente diagnóstico: não escreve
no grafo, não modifica config nem cria arestas. Saída determinística.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Janelas e tolerâncias varridas (em ordem crescente: queremos o MENOR valor
# que já resolve o órfão para reportar como sugestão mínima de ajuste).
JANELAS_VARRIDAS: tuple[int, ...] = (1, 3, 7, 15, 30, 60, 90, 180)
TOLERANCIAS_VARRIDAS: tuple[float, ...] = (0.005, 0.01, 0.03, 0.05, 0.10, 0.20)


def carregar_documentos_e_transacoes(
    grafo_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[int]]:
    """Lê o grafo e retorna (documentos, transacoes_parsadas, ids_linkados).

    `documentos` é lista de dicts com chaves `id`, `nome`, `metadata`.
    `transacoes_parsadas` é lista de dicts com `id`, `data_iso`, `valor_abs`,
    `metadata`. Apenas transações com data e valor válidos entram.
    `ids_linkados` é o set de `documento.id` que já tem aresta `documento_de`.
    """
    if not grafo_path.exists():
        raise FileNotFoundError(f"Grafo não encontrado em {grafo_path}")

    conn = sqlite3.connect(str(grafo_path))
    cur = conn.cursor()
    documentos: list[dict[str, Any]] = []
    for did, nome, meta_json in cur.execute(
        "SELECT id, nome_canonico, metadata FROM node WHERE tipo='documento'"
    ).fetchall():
        try:
            meta = json.loads(meta_json)
        except json.JSONDecodeError:
            meta = {}
        documentos.append({"id": did, "nome": nome, "metadata": meta})

    transacoes: list[dict[str, Any]] = []
    for tid, meta_json in cur.execute(
        "SELECT id, metadata FROM node WHERE tipo='transacao'"
    ).fetchall():
        try:
            meta = json.loads(meta_json)
        except json.JSONDecodeError:
            continue
        data_raw = str(meta.get("data", ""))[:10]
        try:
            data_iso = date.fromisoformat(data_raw)
        except (ValueError, TypeError):
            continue
        try:
            valor_abs = abs(float(meta.get("valor", 0.0)))
        except (TypeError, ValueError):
            continue
        transacoes.append(
            {
                "id": tid,
                "data": data_iso,
                "valor": valor_abs,
                "metadata": meta,
            }
        )

    ids_linkados: set[int] = set()
    for (src,) in cur.execute("SELECT src_id FROM edge WHERE tipo='documento_de'").fetchall():
        ids_linkados.add(src)

    conn.close()
    return documentos, transacoes, ids_linkados


def _ancora_temporal_para_tipo(metadata: dict[str, Any], tipo: str | None) -> str | None:
    """Retorna a data iso usada como centro da janela.

    Espelha a regra do motor (`linking_config.yaml`): DAS_PARCSN usa
    `vencimento`; o resto usa `data_emissao`.
    """
    if tipo == "das_parcsn_andre":
        return metadata.get("vencimento") or metadata.get("data_emissao")
    return metadata.get("data_emissao")


def encontrar_candidatas(
    doc: dict[str, Any],
    transacoes: list[dict[str, Any]],
    janela_dias: int,
    tolerancia_pct: float,
) -> list[dict[str, Any]]:
    """Lista candidatas para um documento dentro de janela/tolerância dados.

    Devolve dicts com `tid`, `delta_dias` (assinado, transação-doc), `valor`,
    `diff_pct`. Lista ordenada por menor `diff_pct` e depois menor |delta|.
    """
    meta = doc["metadata"]
    tipo = meta.get("tipo_documento")
    ancora_iso = _ancora_temporal_para_tipo(meta, tipo)
    total = meta.get("total")
    if not ancora_iso or total is None:
        return []
    try:
        ancora = date.fromisoformat(str(ancora_iso)[:10])
        total_f = float(total)
    except (ValueError, TypeError):
        return []
    if abs(total_f) <= 0.01:
        return []

    referencia = max(abs(total_f), 1.0)
    candidatas: list[dict[str, Any]] = []
    for tx in transacoes:
        delta = (tx["data"] - ancora).days
        if abs(delta) > janela_dias:
            continue
        diff_abs = abs(tx["valor"] - abs(total_f))
        diff_pct = diff_abs / referencia
        if diff_pct > tolerancia_pct:
            continue
        candidatas.append(
            {
                "tid": tx["id"],
                "delta_dias": delta,
                "valor_transacao": round(tx["valor"], 2),
                "diff_valor": round(diff_abs, 2),
                "diff_pct": round(diff_pct, 4),
            }
        )

    candidatas.sort(key=lambda c: (c["diff_pct"], abs(c["delta_dias"])))
    return candidatas


def menor_combinacao_que_resolve(
    doc: dict[str, Any],
    transacoes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Para um órfão, varre janelas e tolerâncias crescentes e devolve a
    primeira combinação (menor janela, menor tolerância dentro dela) que
    devolve pelo menos 1 candidata.

    Retorna `None` quando nem 180 dias + 20% bastam.
    """
    for janela in JANELAS_VARRIDAS:
        for tol in TOLERANCIAS_VARRIDAS:
            cands = encontrar_candidatas(doc, transacoes, janela, tol)
            if cands:
                return {
                    "janela_dias_minima": janela,
                    "tolerancia_pct_minima": tol,
                    "qtd_candidatas": len(cands),
                    "candidatas": cands[:3],
                }
    return None


def gerar_diagnostico(grafo_path: Path) -> dict[str, Any]:
    """Roda o diagnóstico completo e devolve dict estruturado."""
    documentos, transacoes, ids_linkados = carregar_documentos_e_transacoes(grafo_path)

    orfaos_por_tipo: dict[str, int] = {}
    linkados_por_tipo: dict[str, int] = {}
    candidatos_por_tipo: dict[str, list[dict[str, Any]]] = {}

    for doc in documentos:
        tipo = doc["metadata"].get("tipo_documento") or "?"
        if doc["id"] in ids_linkados:
            linkados_por_tipo[tipo] = linkados_por_tipo.get(tipo, 0) + 1
            continue
        orfaos_por_tipo[tipo] = orfaos_por_tipo.get(tipo, 0) + 1

        analise = menor_combinacao_que_resolve(doc, transacoes)
        entrada: dict[str, Any] = {
            "doc_id": doc["id"],
            "doc_nome": doc["nome"],
            "data_emissao": doc["metadata"].get("data_emissao"),
            "vencimento": doc["metadata"].get("vencimento"),
            "total": doc["metadata"].get("total"),
        }
        if analise is None:
            entrada["resolvivel"] = False
        else:
            entrada["resolvivel"] = True
            entrada.update(analise)
        candidatos_por_tipo.setdefault(tipo, []).append(entrada)

    total_docs = len(documentos)
    total_linkados = sum(linkados_por_tipo.values())
    total_transacoes = len(transacoes)
    pct_docs_linkados = (total_linkados / total_docs * 100) if total_docs else 0.0
    pct_transacoes_com_doc = (
        (total_linkados / total_transacoes * 100) if total_transacoes else 0.0
    )

    return {
        "total_documentos": total_docs,
        "total_linkados": total_linkados,
        "total_orfaos": total_docs - total_linkados,
        "total_transacoes": total_transacoes,
        "linking_pct_docs": round(pct_docs_linkados, 4),
        "linking_pct_transacoes": round(pct_transacoes_com_doc, 4),
        "linkados_por_tipo": linkados_por_tipo,
        "orfaos_por_tipo": orfaos_por_tipo,
        "candidatos_por_tipo": candidatos_por_tipo,
    }


def imprimir_relatorio(diag: dict[str, Any]) -> None:
    """Imprime resumo legível no stdout."""
    print("=" * 78)
    print("DIAGNOSTICO DE LINKING -- LINK-AUDIT-01")  # noqa: accent
    print("=" * 78)
    print(f"Total documentos:           {diag['total_documentos']}")
    print(f"Total transações:           {diag['total_transacoes']}")
    print(f"Documentos linkados:        {diag['total_linkados']}")
    print(f"Documentos órfãos:          {diag['total_orfaos']}")
    print(f"Linking pct (documentos):   {diag['linking_pct_docs']:.2f}%")
    print(f"Linking pct (transações):   {diag['linking_pct_transacoes']:.4f}%")
    print()
    print("--- Linkados por tipo ---")
    for tipo, n in sorted(diag["linkados_por_tipo"].items()):
        print(f"  {tipo}: {n}")
    print()
    print("--- Órfãos por tipo ---")
    for tipo, n in sorted(diag["orfaos_por_tipo"].items()):
        print(f"  {tipo}: {n}")
    print()
    print("--- Detalhe por tipo (menor janela/tol que resolveria) ---")
    for tipo, items in sorted(diag["candidatos_por_tipo"].items()):
        print(f"\n[{tipo}] {len(items)} orfao(s)")  # noqa: accent
        for it in items:
            if not it.get("resolvivel"):
                print(
                    f"  doc_id={it['doc_id']} total={it.get('total')} "
                    f"data={it.get('data_emissao')} venc={it.get('vencimento')}: "
                    "SEM CANDIDATA ate 180d/20%"  # noqa: accent
                )
                continue
            cs = it["candidatas"]
            primeira = cs[0] if cs else {}
            print(
                f"  doc_id={it['doc_id']} total={it.get('total')} "
                f"data={it.get('data_emissao')} venc={it.get('vencimento')}: "
                f"janela_min={it['janela_dias_minima']}d "
                f"tol_min={it['tolerancia_pct_minima']*100:.1f}% "
                f"qtd={it['qtd_candidatas']} "
                f"top=(tid={primeira.get('tid')}, delta={primeira.get('delta_dias')}d, "
                f"diff_v={primeira.get('diff_valor')})"
            )


def main(argv: list[str] | None = None) -> int:
    """Entrypoint CLI."""
    parser = argparse.ArgumentParser(
        description="Diagnóstico empírico do linking documento -> transação"
    )
    parser.add_argument(
        "--grafo",
        type=Path,
        default=Path("data/output/grafo.sqlite"),
        help="Caminho do grafo SQLite (default: data/output/grafo.sqlite)",
    )
    parser.add_argument(
        "--export-json",
        type=Path,
        default=None,
        help="Caminho de saída JSON estruturado (opcional)",
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Suprime relatório textual no stdout",
    )
    args = parser.parse_args(argv)

    if not args.grafo.exists():
        print(
            f"ERRO: grafo não encontrado em {args.grafo}. "
            "Rode `./run.sh --tudo` no repo principal antes.",
            file=sys.stderr,
        )
        return 2

    diag = gerar_diagnostico(args.grafo)
    if not args.silent:
        imprimir_relatorio(diag)
    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_json.write_text(
            json.dumps(diag, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        if not args.silent:
            print(f"\nJSON exportado em {args.export_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Diagnóstico honesto é a metade do remédio." -- princípio hipocrático paraphrase
