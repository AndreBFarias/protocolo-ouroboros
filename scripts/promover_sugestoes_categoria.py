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
    """Lê descrições já presentes como chaves em overrides.yaml.

    Schema canônico do projeto (chaves YAML em ASCII por convenção legada):
    ```yaml
    overrides:
      "WANDERSON RAMOS":
        categoria: "Pessoal"
        classificacao: "Questionavel"  # noqa: accent -- chave YAML canônica
    ```

    Parser leve via PyYAML: lê estrutura, devolve set de chaves do dict
    ``overrides``. Falha-soft em qualquer erro.
    """
    if not path.exists():
        return set()
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        return set()
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return set()
    overrides = doc.get("overrides", {}) or {}
    return set(overrides.keys()) if isinstance(overrides, dict) else set()


def _deduplicar_por_descricao(candidatos: list[dict]) -> list[dict]:
    """Mantém apenas 1 candidato por descrição (maior confiança vence).

    O sugestor pode produzir múltiplas linhas com mesma descrição (PIX
    recorrente para mesma pessoa, "Pagamento da fatura - Cartão Nubank"
    repetido em transações distintas). YAML não aceita chaves duplicadas
    no mesmo dict — deduplicação no batch evita "última vence" silenciosa.
    """
    melhor_por_desc: dict[str, dict] = {}
    for c in candidatos:
        desc = c["descricao"]
        atual = melhor_por_desc.get(desc)
        if atual is None or c["confianca"] > atual["confianca"]:
            melhor_por_desc[desc] = c
    return sorted(melhor_por_desc.values(), key=lambda c: -c["confianca"])


def _filtrar_candidatos(
    sugestoes: dict,
    threshold: float,
    existentes: set[str],
    riscos_aceitos: tuple[str, ...] = ("BAIXO",),
) -> list[dict]:
    """Devolve lista de sugestões elegíveis ordenada por confiança decrescente.

    Sprint CATEGORIZER-SUGESTAO-AUDITORIA-RUIDO: aceita apenas sugestões
    com ``risco_estimado`` em ``riscos_aceitos`` (default BAIXO). Sugestões
    sem campo de risco (versão antiga do JSON) ficam DESCONHECIDO e são
    rejeitadas por default.
    """
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
        risco = item.get("risco_estimado", "DESCONHECIDO")
        if risco not in riscos_aceitos:
            continue
        candidatos.append(
            {
                "tx_id": tx_id,
                "descricao": desc,
                "categoria": categoria,
                "confianca": conf,
                "risco_estimado": risco,
            }
        )
    candidatos.sort(key=lambda c: -c["confianca"])
    return _deduplicar_por_descricao(candidatos)


def _apendar_em_overrides(
    candidatos: list[dict],
    path_yaml: Path,
) -> str:
    """Apenda entries no formato canonico dict de overrides.yaml.

    Schema esperado pelo categorizer:
    ```yaml
    overrides:
      "DESCRICAO EXATA":
        categoria: "Pessoal"
        classificacao: "Questionável"  # noqa: accent -- chave YAML canônica
    ```

    A versão batch grava no FIM da seção ``overrides:`` (não cria seção
    nova). Garante alinhamento de indentação com 2 espaços (padrão YAML
    do projeto). Retorna conteúdo apendado para audit.
    """
    data_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cabecalho_comentario = (
        f"\n  # CATEGORIZER-SUGESTAO-TFIDF: promocao em lote {data_iso} "
        f"({len(candidatos)} entries)\n"
    )
    blocos = [cabecalho_comentario]
    for c in candidatos:
        # Escapa aspas duplas para inserir como chave YAML:
        chave_yaml = json.dumps(c["descricao"])  # ja envolve em ""
        chave_classif = "classificacao"  # noqa: accent -- chave YAML canônica
        blocos.append(
            f"  {chave_yaml}:\n"
            f'    categoria: "{c["categoria"]}"\n'
            f'    {chave_classif}: "Questionável"\n'
            f"    origem: CATEGORIZER-SUGESTAO-TFIDF\n"
            f"    confianca_origem: {c['confianca']}\n"
        )
    bloco_completo = "".join(blocos)

    if not path_yaml.exists():
        path_yaml.write_text(
            "# Correcoes manuais de categorizacao\noverrides:\n" + bloco_completo,
            encoding="utf-8",
        )
        return bloco_completo

    # Apenda DENTRO da seção overrides:, no final do arquivo.
    # Se o arquivo já termina com newline, mantém; senão adiciona.
    atual = path_yaml.read_text(encoding="utf-8")
    if not atual.endswith("\n"):
        atual += "\n"
    path_yaml.write_text(atual + bloco_completo, encoding="utf-8")
    return bloco_completo


def executar(
    threshold: float = THRESHOLD_DEFAULT,
    apply: bool = False,
    riscos_aceitos: tuple[str, ...] = ("BAIXO",),
    path_sugestoes: Path | None = None,
    path_overrides: Path | None = None,
    path_log: Path | None = None,
) -> dict:
    sugestoes = _ler_sugestoes(path_sugestoes or PATH_SUGESTOES)
    if not sugestoes:
        return {"erro": "sem_sugestoes", "candidatos": [], "promovidos": 0}

    existentes = _ler_overrides_existentes(path_overrides or PATH_OVERRIDES)
    candidatos = _filtrar_candidatos(sugestoes, threshold, existentes, riscos_aceitos)

    resultado = {
        "modo": "apply" if apply else "dry-run",
        "executado_em": datetime.now(timezone.utc).isoformat(),
        "threshold": threshold,
        "riscos_aceitos": list(riscos_aceitos),
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
    parser.add_argument(
        "--riscos",
        type=str,
        default="BAIXO",
        help=(
            "Riscos aceitos separados por vírgula (default: BAIXO). "
            "Opções: BAIXO, MEDIO, ALTO, DESCONHECIDO."
        ),
    )
    args = parser.parse_args(argv)
    riscos_aceitos = tuple(r.strip() for r in args.riscos.split(",") if r.strip())

    r = executar(threshold=args.threshold, apply=args.apply, riscos_aceitos=riscos_aceitos)
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
