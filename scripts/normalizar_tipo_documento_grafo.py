"""Migração retroativa de `metadata.tipo_documento` no grafo SQLite.

Sprint META-NORMALIZAR-TIPO-DOCUMENTO-ETL (2026-05-16). Auditoria empírica
do grafo mostrou que `metadata.tipo_documento` está com nomes divergentes
do YAML canônico (``mappings/tipos_documento.yaml``):

| Atual no grafo | Canônico do YAML |
|---|---|
| ``cupom_fiscal`` (3) | ``cupom_fiscal_foto`` |
| ``das_parcsn_andre`` (19) | ``das_parcsn`` (+ ``metadata.pessoa: pessoa_a``) |
| ``nfce_modelo_65`` (2) | ``nfce_consumidor_eletronica`` |

Tipos que JÁ concordam (intactos): ``holerite``, ``boleto_servico``,
``comprovante_pix_foto``, ``dirpf_retif`` (este último não está no YAML
mas é nome válido — sprint paralela decide adicioná-lo).

Estratégia:
1. Lê todos os nodes ``tipo='documento'`` com ``tipo_documento`` no metadata.
2. Para cada um no MAPA_NORMALIZACAO, atualiza in-place via UPDATE SQL.
3. Para ``das_parcsn_andre`` especificamente: grava ``metadata.pessoa: pessoa_a``
   para preservar a discriminação atual (que estava codificada no nome do tipo).
4. Atualiza ``updated_at`` para auditoria.
5. Log estruturado em ``data/output/normalizar_tipo_documento_log.json``.

Idempotente: rodar 2× consecutivas não duplica trabalho.

Uso:

    python scripts/normalizar_tipo_documento_grafo.py            # dry-run
    python scripts/normalizar_tipo_documento_grafo.py --apply    # executa
    python scripts/normalizar_tipo_documento_grafo.py --reverter # reversão
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
PATH_GRAFO = _RAIZ / "data" / "output" / "grafo.sqlite"
PATH_LOG = _RAIZ / "data" / "output" / "normalizar_tipo_documento_log.json"

# Mapa canônico de migração. Chave = nome atual no grafo, valor = canônico do YAML.
MAPA_NORMALIZACAO: dict[str, str] = {
    "cupom_fiscal": "cupom_fiscal_foto",
    "das_parcsn_andre": "das_parcsn",
    "das_parcsn_vitoria": "das_parcsn",
    "nfce_modelo_65": "nfce_consumidor_eletronica",
}

# Metadata adicional a gravar quando migra de tipo discriminado para canônico.
# Preserva discriminação que estava codificada no nome do tipo.
MAPA_METADATA_EXTRA: dict[str, dict] = {
    "das_parcsn_andre": {"pessoa": "pessoa_a"},
    "das_parcsn_vitoria": {"pessoa": "pessoa_b"},
}


def _coletar_nodes_para_migrar(
    con: sqlite3.Connection,
) -> list[dict]:
    """Lista nodes documento que precisam de migração.

    Retorna lista de dicts com {id, tipo_atual, tipo_canonico, metadata, nome_canonico}.
    """
    cur = con.execute(
        "SELECT id, nome_canonico, metadata FROM node WHERE tipo='documento'"
    )
    candidatos = []
    for node_id, nome, meta_str in cur.fetchall():
        try:
            meta = json.loads(meta_str) if meta_str else {}
        except json.JSONDecodeError:
            continue
        tipo_atual = meta.get("tipo_documento", "")
        if tipo_atual in MAPA_NORMALIZACAO:
            candidatos.append(
                {
                    "id": node_id,
                    "nome_canonico": nome,
                    "tipo_atual": tipo_atual,
                    "tipo_canonico": MAPA_NORMALIZACAO[tipo_atual],
                    "metadata": meta,
                }
            )
    return candidatos


def _aplicar_migracao(
    con: sqlite3.Connection,
    candidatos: list[dict],
) -> list[dict]:
    """Aplica UPDATE in-place. Retorna lista de mudanças efetivas."""
    aplicados = []
    ts = datetime.now(timezone.utc).isoformat()
    for cand in candidatos:
        meta_novo = dict(cand["metadata"])
        meta_novo["tipo_documento"] = cand["tipo_canonico"]
        meta_novo["_normalizado_em"] = ts
        meta_novo["_tipo_anterior"] = cand["tipo_atual"]
        extras = MAPA_METADATA_EXTRA.get(cand["tipo_atual"], {})
        for k, v in extras.items():
            # Não sobrescreve se já está populado:
            if k not in meta_novo:
                meta_novo[k] = v
        con.execute(
            "UPDATE node SET metadata = ?, updated_at = ? WHERE id = ?",
            (json.dumps(meta_novo, ensure_ascii=False), ts, cand["id"]),
        )
        aplicados.append(
            {
                "node_id": cand["id"],
                "nome_canonico": cand["nome_canonico"],
                "tipo_anterior": cand["tipo_atual"],
                "tipo_canonico": cand["tipo_canonico"],
                "metadata_extras": list(extras.keys()),
            }
        )
    return aplicados


def _reverter_migracao(
    con: sqlite3.Connection,
) -> list[dict]:
    """Reverte usando `_tipo_anterior` gravado em runs anteriores. Idempotente."""
    cur = con.execute(
        "SELECT id, metadata FROM node WHERE tipo='documento'"
    )
    revertidos = []
    ts = datetime.now(timezone.utc).isoformat()
    for node_id, meta_str in cur.fetchall():
        try:
            meta = json.loads(meta_str) if meta_str else {}
        except json.JSONDecodeError:
            continue
        tipo_anterior = meta.get("_tipo_anterior")
        if not tipo_anterior:
            continue
        meta_novo = dict(meta)
        meta_novo["tipo_documento"] = tipo_anterior
        # Limpa marcadores:
        meta_novo.pop("_tipo_anterior", None)
        meta_novo.pop("_normalizado_em", None)
        con.execute(
            "UPDATE node SET metadata = ?, updated_at = ? WHERE id = ?",
            (json.dumps(meta_novo, ensure_ascii=False), ts, node_id),
        )
        revertidos.append({"node_id": node_id, "voltou_para": tipo_anterior})
    return revertidos


def executar(
    grafo: Path = PATH_GRAFO,
    apply: bool = False,
    reverter: bool = False,
    log: Path = PATH_LOG,
) -> dict:
    """Pipeline completo: coleta, exibe ou aplica, grava log."""
    if not grafo.exists():
        return {"erro": f"Grafo ausente: {grafo}", "candidatos": [], "aplicados": []}

    con = sqlite3.connect(str(grafo))
    try:
        if reverter:
            with con:
                aplicados = _reverter_migracao(con)
            resultado = {
                "modo": "reverter",
                "executado_em": datetime.now(timezone.utc).isoformat(),
                "n_revertidos": len(aplicados),
                "revertidos": aplicados,
            }
        else:
            candidatos = _coletar_nodes_para_migrar(con)
            if apply and candidatos:
                with con:
                    aplicados = _aplicar_migracao(con, candidatos)
            else:
                aplicados = []
            resultado = {
                "modo": "apply" if apply else "dry-run",
                "executado_em": datetime.now(timezone.utc).isoformat(),
                "mapa_normalizacao": MAPA_NORMALIZACAO,
                "n_candidatos": len(candidatos),
                "n_aplicados": len(aplicados),
                "candidatos": [
                    {
                        "node_id": c["id"],
                        "nome_canonico": c["nome_canonico"],
                        "tipo_atual": c["tipo_atual"],
                        "tipo_canonico": c["tipo_canonico"],
                    }
                    for c in candidatos
                ],
                "aplicados": aplicados,
            }
    finally:
        con.close()

    if apply or reverter:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normaliza tipo_documento no grafo")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa UPDATE (default: dry-run que apenas lista mudanças)",
    )
    parser.add_argument(
        "--reverter",
        action="store_true",
        help="Reverte usando _tipo_anterior gravado em runs anteriores",
    )
    args = parser.parse_args(argv)

    if args.apply and args.reverter:
        sys.stderr.write("Erro: --apply e --reverter sao mutuamente exclusivos.\n")
        return 1

    resultado = executar(apply=args.apply, reverter=args.reverter)

    if "erro" in resultado:
        sys.stderr.write(f"{resultado['erro']}\n")
        return 1

    sys.stdout.write(f"Modo: {resultado['modo']}\n")
    if args.reverter:
        sys.stdout.write(f"Revertidos: {resultado['n_revertidos']}\n")
    else:
        sys.stdout.write(f"Candidatos: {resultado['n_candidatos']}\n")
        sys.stdout.write(f"Aplicados:  {resultado['n_aplicados']}\n")
        # Resumo por tipo:
        por_tipo: dict[str, int] = {}
        for c in resultado["candidatos"]:
            chave = f"{c['tipo_atual']} -> {c['tipo_canonico']}"
            por_tipo[chave] = por_tipo.get(chave, 0) + 1
        for chave, n in sorted(por_tipo.items(), key=lambda kv: -kv[1]):
            sys.stdout.write(f"  {chave}: {n}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Duas fontes de verdade sao uma fonte e um boato." -- principio
