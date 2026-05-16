"""Sprint LLM-04-V2 -- Auditor de cobertura disparado pelo supervisor humano.

Rodado pelo Opus principal (Claude Code interativo) quando o dono digita
`/auditar-cobertura` na sessao. **NÃO eh cron, NÃO eh automacao
programatica via Anthropic API.** Conforme ADR-13: o supervisor sou eu,
sessao a sessao, sem chamada paga.

Le `data/output/grafo.sqlite` + `mappings/categorias.yaml` e gera
`docs/auditorias/cobertura_<periodo>.md` com:
- % transações categorizadas vs `OUTROS` (cobertura efetiva).
- Top fornecedores cuja maioria das transações cai em `OUTROS`.
- Cobertura por pessoa (André/Vitória/Casal).
- Documentos com aresta `documento_de` vs orfaos.

Uso:

    python scripts/auditar_cobertura.py                    # dry-run
    python scripts/auditar_cobertura.py --executar         # grava .md
    python scripts/auditar_cobertura.py --periodo 2026-04  # mes especifico

Relatório gerado vira ponto de partida para conversa com o dono na
sessao: o que vira regra nova em `mappings/`, o que vira sprint, o que
fica como `OUTROS` legitimo.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
GRAFO_DEFAULT: Path = RAIZ / "data" / "output" / "grafo.sqlite"
DESTINO_DIR: Path = RAIZ / "docs" / "auditorias"
LIMITE_TOP_FORNECEDORES = 15


def _categoria_outros_existe(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(*) FROM node WHERE tipo='categoria' AND UPPER(nome_canonico)='OUTROS'"
    ).fetchone()
    return bool(row and row[0])


def contagem_categorias(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    sql = (
        "SELECT n2.nome_canonico AS cat, COUNT(*) AS n "
        "FROM edge e "
        "JOIN node n1 ON e.src_id = n1.id AND n1.tipo='transacao' "
        "JOIN node n2 ON e.dst_id = n2.id AND n2.tipo='categoria' "
        "WHERE e.tipo='categoria_de' "
        "GROUP BY n2.nome_canonico "
        "ORDER BY n DESC"
    )
    return [(row[0], int(row[1])) for row in conn.execute(sql)]


def fornecedores_em_outros(conn: sqlite3.Connection, limite: int) -> list[tuple[str, int]]:
    """Top fornecedores cuja maioria das transações (`contraparte`) cai em
    categoria=OUTROS. São os candidatos a regra nova em `mappings/categorias.yaml`."""
    sql = (
        "SELECT n_forn.nome_canonico AS forn, COUNT(*) AS n "
        "FROM edge e_cont "
        "JOIN node n_tx ON e_cont.src_id = n_tx.id AND n_tx.tipo='transacao' "
        "JOIN node n_forn ON e_cont.dst_id = n_forn.id AND n_forn.tipo='fornecedor' "
        "JOIN edge e_cat ON e_cat.src_id = n_tx.id AND e_cat.tipo='categoria_de' "
        "JOIN node n_cat ON e_cat.dst_id = n_cat.id "
        "WHERE e_cont.tipo='contraparte' AND UPPER(n_cat.nome_canonico)='OUTROS' "
        "GROUP BY n_forn.nome_canonico "
        "ORDER BY n DESC LIMIT ?"
    )
    return [(row[0], int(row[1])) for row in conn.execute(sql, (limite,))]


def cobertura_por_pessoa(conn: sqlite3.Connection) -> list[tuple[str, int, int, float]]:
    """Para cada pessoa, retorna (quem, total, em_outros, pct_categorizado)."""
    sql_total = (
        "SELECT json_extract(metadata, '$.quem') AS quem, COUNT(*) "
        "FROM node WHERE tipo='transacao' GROUP BY quem"
    )
    sql_outros = (
        "SELECT json_extract(n_tx.metadata, '$.quem') AS quem, COUNT(*) "
        "FROM edge e "
        "JOIN node n_tx ON e.src_id = n_tx.id AND n_tx.tipo='transacao' "
        "JOIN node n_cat ON e.dst_id = n_cat.id AND n_cat.tipo='categoria' "
        "WHERE e.tipo='categoria_de' AND UPPER(n_cat.nome_canonico)='OUTROS' "
        "GROUP BY quem"
    )
    totais = {row[0] or "(sem-quem)": int(row[1]) for row in conn.execute(sql_total)}
    outros = {row[0] or "(sem-quem)": int(row[1]) for row in conn.execute(sql_outros)}
    resultado = []
    for quem, total in sorted(totais.items()):
        em_outros = outros.get(quem, 0)
        pct = (1.0 - em_outros / total) * 100 if total else 0.0
        resultado.append((quem, total, em_outros, pct))
    return resultado


def documentos_orfaos(conn: sqlite3.Connection) -> tuple[int, int]:
    """Retorna (total_documentos, documentos_sem_aresta_documento_de)."""
    total = int(conn.execute("SELECT COUNT(*) FROM node WHERE tipo='documento'").fetchone()[0])
    orfaos = int(
        conn.execute(
            "SELECT COUNT(*) FROM node WHERE tipo='documento' AND id NOT IN "
            "(SELECT src_id FROM edge WHERE tipo='documento_de')"
        ).fetchone()[0]
    )
    return total, orfaos


def regras_yaml_carregadas(caminho_yaml: Path) -> int:
    if not caminho_yaml.exists():
        return 0
    import yaml

    try:
        cfg = yaml.safe_load(caminho_yaml.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return 0
    regras = cfg.get("regras") or cfg.get("categorias") or []
    if isinstance(regras, list):
        return len(regras)
    if isinstance(regras, dict):
        return len(regras)
    return 0


def montar_relatorio(grafo: Path, periodo: str, total_regras_yaml: int) -> str:
    if not grafo.exists():
        return (
            f"# Auditoria de cobertura ({periodo})\n\n"
            f"Grafo ausente em `{grafo}`. Rode `./run.sh --tudo` antes.\n"
        )

    with sqlite3.connect(f"file:{grafo}?mode=ro", uri=True) as conn:
        cats = contagem_categorias(conn)
        fornecedores_outros = fornecedores_em_outros(conn, LIMITE_TOP_FORNECEDORES)
        cobertura_pessoa = cobertura_por_pessoa(conn)
        total_docs, docs_orfaos = documentos_orfaos(conn)
        outros_qtd = next((n for c, n in cats if c.upper() == "OUTROS"), 0)

    total_tx = sum(n for _, n in cats)
    pct_cobertos = (1.0 - outros_qtd / total_tx) * 100 if total_tx else 0.0

    cabecalho_origem = (
        "> Gerado pelo Opus principal (Claude Code interativo) via skill "
        f"`/auditar-cobertura` em sessão de {date.today().isoformat()}."
    )
    cabecalho_fonte = (
        f"> Fonte: `{grafo.relative_to(RAIZ)}`. Regras carregadas: {total_regras_yaml}."
    )
    linhas = [
        f"# Auditoria de cobertura — {periodo}",
        "",
        cabecalho_origem,
        cabecalho_fonte,
        "",
        "## Sumário executivo",
        "",
        f"- Transações no grafo: **{total_tx:,}**",
        f"- Categorizadas (não-OUTROS): **{total_tx - outros_qtd:,} ({pct_cobertos:.1f}%)**",
        f"- Em OUTROS (cabem regra nova): **{outros_qtd:,} ({100 - pct_cobertos:.1f}%)**",
        f"- Documentos no grafo: {total_docs:,} ({docs_orfaos} órfãos sem aresta `documento_de`)",
        "",
        "## Distribuição de categorias",
        "",
        "| Categoria | Transações |",
        "|-----------|-----------:|",
    ]
    for cat, n in cats[:20]:
        linhas.append(f"| {cat} | {n:,} |")
    linhas.append("")

    linhas += [
        f"## Top {LIMITE_TOP_FORNECEDORES} fornecedores em OUTROS (candidatos a regra nova)",
        "",
        "| Fornecedor | Tx em OUTROS |",
        "|------------|-------------:|",
    ]
    if not fornecedores_outros:
        linhas.append("| _(nenhum)_ | 0 |")
    for forn, n in fornecedores_outros:
        linhas.append(f"| {forn} | {n:,} |")
    linhas.append("")

    linhas += [
        "## Cobertura por pessoa",
        "",
        "| Pessoa | Total | Em OUTROS | % categorizado |",
        "|--------|------:|----------:|---------------:|",
    ]
    for quem, total, em_outros, pct in cobertura_pessoa:
        linhas.append(f"| {quem} | {total:,} | {em_outros:,} | {pct:.1f}% |")
    linhas.append("")

    proximos_passos = [
        ("Revisar top fornecedores em OUTROS — os 5 primeiros tipicamente concentram >30% do gap."),
        (
            "Para cada fornecedor recorrente, decidir: criar regra em "
            "`mappings/categorias.yaml` OU usar `/propor-extrator` se faltar "
            "extrator dedicado."
        ),
        (
            "Documentos órfãos (sem aresta `documento_de`): rodar "
            "`LINK-AUDIT-01` (Onda 4) ou ajustar tolerância temporal em "
            "`mappings/linking_config.yaml`."
        ),
        (
            "Se cobertura por pessoa diverge muito entre André/Vitória, "
            "suspeitar de regra que só pega nome de uma das contas."
        ),
    ]
    linhas += [
        "## Próximos passos sugeridos pelo supervisor",
        "",
    ]
    for i, passo in enumerate(proximos_passos, start=1):
        linhas.append(f"{i}. {passo}")
    linhas += [
        "",
        "---",
        "",
        '*"O que se mede sem padrão é palpite com etiqueta." — princípio do auditor manual*',
        "",
    ]
    return "\n".join(linhas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--periodo",
        default=None,
        help="Período do relatório (default: data ISO de hoje, formato YYYY-MM-DD).",
    )
    parser.add_argument(
        "--grafo",
        type=Path,
        default=GRAFO_DEFAULT,
        help=f"SQLite do grafo (default: {GRAFO_DEFAULT}).",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Sem flag: imprime no stdout. Com flag: grava em docs/auditorias/.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    periodo = args.periodo or date.today().isoformat()
    total_regras = regras_yaml_carregadas(RAIZ / "mappings" / "categorias.yaml")
    relatorio = montar_relatorio(args.grafo, periodo, total_regras)

    if args.executar:
        DESTINO_DIR.mkdir(parents=True, exist_ok=True)
        destino = DESTINO_DIR / f"cobertura_{periodo}.md"
        destino.write_text(relatorio, encoding="utf-8")
        logger.info("[OK] Relatório gravado em %s", destino)
        print(destino)
    else:
        sys.stdout.write(relatorio)
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Auditar manualmente é o preço da soberania sobre as regras." -- princípio ADR-13
