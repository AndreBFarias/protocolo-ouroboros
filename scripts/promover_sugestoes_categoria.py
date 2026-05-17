"""Promove sugestões de categoria do TF-IDF para `mappings/overrides.yaml`.

Sprint CATEGORIZER-SUGESTAO-TFIDF (2026-05-16) — fase 2. Consome
``data/output/sugestoes_categoria.json`` gerado por
``scripts/sugerir_categorias.py`` e cria entries em
``mappings/overrides.yaml`` para sugestões acima de um threshold de
confiança.

Cada promoção:
- Adiciona entry com ``match`` (descrição exata da transação), ``categoria``
  (categoria sugerida) e ``origem: CATEGORIZER-SUGESTAO-TFIDF``.
- Idempotente: não duplica entry com mesmo match.
- Log estruturado em ``data/output/promocoes_categoria_log.json``.

Uso:

    python -m scripts.promover_sugestoes_categoria                  # dry-run
    python -m scripts.promover_sugestoes_categoria --apply          # executa
    python -m scripts.promover_sugestoes_categoria --apply --threshold 0.9
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
PATH_SUGESTOES = _RAIZ / "data" / "output" / "sugestoes_categoria.json"
PATH_OVERRIDES = _RAIZ / "mappings" / "overrides.yaml"
PATH_LOG = _RAIZ / "data" / "output" / "promocoes_categoria_log.json"

THRESHOLD_DEFAULT = 0.85


def _ler_sugestoes(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _ler_overrides_existentes(path: Path) -> set[str]:
    """Lê matches já presentes em overrides.yaml (parser textual simples).

    Não usa PyYAML porque overrides tem comentários inline + estrutura
    flexível. Heurística: linhas começando com ``- match:`` ou ``  match:``
    extraem o valor entre aspas duplas ou simples.
    """
    if not path.exists():
        return set()
    matches: set[str] = set()
    import re
    pat = re.compile(r'^[-\s]*match:\s*(?P<v>".*?"|\'.*?\'|\S.*)\s*$')
    for linha in path.read_text(encoding="utf-8").splitlines():
        m = pat.match(linha)
        if not m:
            continue
        val = m.group("v").strip()
        if val.startswith(('"', "'")) and val.endswith(('"', "'")):
            val = val[1:-1]
        matches.add(val.strip())
    return matches


def _filtrar_candidatos(
    sugestoes: dict,
    threshold: float,
    existentes: set[str],
) -> list[dict]:
    """Devolve lista de sugestões elegíveis ordenada por confiança decrescente."""
    sug = sugestoes.get("sugestoes", {})
    candidatos = []
    for tx_id, item in sug.items():
        conf = float(item.get("confianca_top1", 0))
        if conf < threshold:
            continue
        desc = (item.get("descricao") or "").strip()
        if not desc or desc in existentes:
            continue
        categoria = item.get("top1", "")
        if not categoria or categoria == "Outros":
            continue
        candidatos.append(
            {
                "tx_id": tx_id,
                "descricao": desc,
                "categoria": categoria,
                "confianca": conf,
            }
        )
    candidatos.sort(key=lambda c: -c["confianca"])
    return candidatos


def _apendar_em_overrides(
    candidatos: list[dict],
    path_yaml: Path,
) -> str:
    """Apenda entries em batch em overrides.yaml. Retorna conteúdo apendado."""
    data_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cabecalho = (
        f"\n# CATEGORIZER-SUGESTAO-TFIDF: promocao em lote de {len(candidatos)}\n"
        f"# sugestoes alta confianca em {data_iso}\n"
    )
    blocos = []
    for c in candidatos:
        match_safe = json.dumps(c["descricao"])
        blocos.append(
            f'- match: {match_safe}\n'
            f'  categoria: {c["categoria"]}\n'
            f'  origem: CATEGORIZER-SUGESTAO-TFIDF\n'
            f'  confianca_origem: {c["confianca"]}\n'
        )
    bloco_completo = cabecalho + "".join(blocos)
    if path_yaml.exists():
        atual = path_yaml.read_text(encoding="utf-8")
        path_yaml.write_text(atual.rstrip() + "\n" + bloco_completo, encoding="utf-8")
    else:
        path_yaml.write_text(bloco_completo.lstrip(), encoding="utf-8")
    return bloco_completo


def executar(
    threshold: float = THRESHOLD_DEFAULT,
    apply: bool = False,
    path_sugestoes: Path | None = None,
    path_overrides: Path | None = None,
    path_log: Path | None = None,
) -> dict:
    sugestoes = _ler_sugestoes(path_sugestoes or PATH_SUGESTOES)
    if not sugestoes:
        return {"erro": "sem_sugestoes", "candidatos": [], "promovidos": 0}

    existentes = _ler_overrides_existentes(path_overrides or PATH_OVERRIDES)
    candidatos = _filtrar_candidatos(sugestoes, threshold, existentes)

    resultado = {
        "modo": "apply" if apply else "dry-run",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "n_candidatos": len(candidatos),
        "n_existentes_em_overrides": len(existentes),
        "n_promovidos": 0,
        "candidatos": candidatos[:50],
    }

    if apply and candidatos:
        _apendar_em_overrides(candidatos, path_overrides or PATH_OVERRIDES)
        resultado["n_promovidos"] = len(candidatos)
        log = path_log or PATH_LOG
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promove sugestoes TF-IDF para overrides.yaml")
    parser.add_argument("--apply", action="store_true", help="Executa (default: dry-run)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=THRESHOLD_DEFAULT,
        help=f"Confianca minima (default: {THRESHOLD_DEFAULT})",
    )
    args = parser.parse_args(argv)

    r = executar(threshold=args.threshold, apply=args.apply)
    if "erro" in r:
        sys.stderr.write(f"Erro: {r['erro']}\n")
        return 1
    sys.stdout.write(f"Modo: {r['modo']}\n")
    sys.stdout.write(f"Threshold: {r['threshold']}\n")
    sys.stdout.write(f"Existentes em overrides.yaml: {r['n_existentes_em_overrides']}\n")
    sys.stdout.write(f"Candidatos elegiveis: {r['n_candidatos']}\n")
    if args.apply:
        sys.stdout.write(f"Promovidos: {r['n_promovidos']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Promocao em lote tem economia de escala; revisao posterior corrige residuos." -- principio
