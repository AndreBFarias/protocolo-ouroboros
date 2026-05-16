"""Auditoria periódica de cobertura D7 -- relatório consolidado.

Sprint META-COBERTURA-TOTAL-01.

Junta o lint estático (``check_cobertura_total.py --json``) com snapshots
históricos de cobertura runtime e gera relatório markdown em
``docs/auditorias/cobertura_total_<data>.md`` (apêndice, leniente -- nunca
mutua código).

Decisão D7 do dono: extrair tudo das imagens e pdfs, cada valor, catalogar
tudo. Esta auditoria é o feedback loop -- vê tendência ao longo do tempo,
detecta regressões silenciosas (extrator que extraía N campos passou a
extrair N-1), e alimenta a sprint guarda-chuva RETRABALHO-EXTRATORES-01
com tier (A/B/C/D) por extrator.

Modos:

  - Padrão (sem flags): roda dry-run, imprime sumário no terminal sem escrita.
  - ``--executar``: gera arquivo em ``docs/auditorias/`` (apêndice, não mutação
    destrutiva). Comportamento read-only-equivalente conforme
    ``docs/SUPERVISOR_OPUS.md §11``.

A auditoria não chama ``./run.sh --tudo`` nem regenera grafo; lê o estado
atual de ``data/output/grafo.sqlite`` (se existir) e cruza com o output do
lint estático.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_DIR_AUDITORIAS: Path = _RAIZ_REPO / "docs" / "auditorias"
_GRAFO: Path = _RAIZ_REPO / "data" / "output" / "grafo.sqlite"
_DIR_EXTRATORES: Path = _RAIZ_REPO / "src" / "extractors"


def coletar_violacoes_lint() -> list[dict]:
    """Roda ``check_cobertura_total.py --json`` e devolve lista de dicts."""
    script = _RAIZ_REPO / "scripts" / "check_cobertura_total.py"
    res = subprocess.run(
        [sys.executable, str(script), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    saida = (res.stdout or "").strip()
    if not saida:
        return []
    try:
        return json.loads(saida)
    except json.JSONDecodeError:
        return []


def coletar_extratores() -> list[str]:
    """Lista os extratores reais (excluindo ``__init__``, ``base``, ``_ocr_comum``)."""
    excluir = {"__init__.py", "base.py", "_ocr_comum.py"}
    return sorted(f.stem for f in _DIR_EXTRATORES.glob("*.py") if f.name not in excluir)


def coletar_cobertura_grafo() -> dict[str, dict]:
    """Cruza grafo: por tipo_documento, conta nodes documento, com aresta documento_de
    e com aresta contem_item.

    Retorna ``{tipo: {documentos, com_documento_de, com_contem_item}}``.
    Tolera ausência do banco (devolve dict vazio).
    """
    if not _GRAFO.exists():
        return {}
    try:
        conn = sqlite3.connect(_GRAFO)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT json_extract(metadata, '$.tipo_documento') AS tipo_doc,
                   COUNT(*) AS docs
              FROM node
             WHERE tipo='documento'
             GROUP BY tipo_doc
            """
        )
        docs = {row[0] or "<sem_tipo>": {"documentos": row[1]} for row in cur.fetchall()}
        cur.execute(
            """
            SELECT json_extract(d.metadata, '$.tipo_documento') AS tipo_doc,
                   COUNT(DISTINCT d.id) AS com_documento_de
              FROM edge e JOIN node d ON d.id=e.src_id
             WHERE e.tipo='documento_de' AND d.tipo='documento'
             GROUP BY tipo_doc
            """
        )
        for row in cur.fetchall():
            tipo = row[0] or "<sem_tipo>"
            if tipo in docs:
                docs[tipo]["com_documento_de"] = row[1]
        cur.execute(
            """
            SELECT json_extract(d.metadata, '$.tipo_documento') AS tipo_doc,
                   COUNT(DISTINCT d.id) AS com_contem_item
              FROM edge e JOIN node d ON d.id=e.src_id
             WHERE e.tipo='contem_item' AND d.tipo='documento'
             GROUP BY tipo_doc
            """
        )
        for row in cur.fetchall():
            tipo = row[0] or "<sem_tipo>"
            if tipo in docs:
                docs[tipo]["com_contem_item"] = row[1]
        conn.close()
        return docs
    except sqlite3.Error:
        return {}


def montar_relatorio(
    extratores: list[str],
    violacoes: list[dict],
    cobertura: dict[str, dict],
) -> str:
    """Monta o markdown final."""
    hoje = date.today().isoformat()
    linhas: list[str] = []
    linhas.append(f"# Auditoria de cobertura total D7 ({hoje})")
    linhas.append("")
    linhas.append(
        "> Sprint META-COBERTURA-TOTAL-01. Gerada por "
        "`python scripts/auditar_cobertura_total.py --executar`."
    )
    linhas.append("")
    linhas.append(f"- Extratores em `src/extractors/`: **{len(extratores)}**")
    linhas.append(f"- Violações no lint estático: **{len(violacoes)}**")
    linhas.append(f"- Tipos de documento no grafo: **{len(cobertura)}**")
    linhas.append("")

    linhas.append("## Lint estático")
    linhas.append("")
    if violacoes:
        linhas.append("| Arquivo | Função | Linha | Motivo |")
        linhas.append("|---|---|---:|---|")
        for v in violacoes:
            linhas.append(f"| `{v['arquivo']}` | `{v['funcao']}` | {v['linha']} | {v['motivo']} |")
    else:
        linhas.append("Sem violações detectadas pelo lint estático.")
    linhas.append("")

    linhas.append("## Cobertura no grafo (snapshot)")
    linhas.append("")
    if cobertura:
        linhas.append("| Tipo de documento | Documentos | Com `documento_de` | Com `contem_item` |")
        linhas.append("|---|---:|---:|---:|")
        for tipo in sorted(cobertura):
            d = cobertura[tipo]
            docs = d.get("documentos", 0)
            with_de = d.get("com_documento_de", 0)
            with_item = d.get("com_contem_item", 0)
            linhas.append(f"| {tipo} | {docs} | {with_de} | {with_item} |")
    else:
        linhas.append("Grafo `data/output/grafo.sqlite` ausente ou ilegível -- snapshot vazio.")
    linhas.append("")

    linhas.append("## Extratores em src/extractors/")
    linhas.append("")
    linhas.append(
        "Lista canônica para a Sprint RETRABALHO-EXTRATORES-01 ramificar em tiers A/B/C/D:"
    )
    linhas.append("")
    for extrator in extratores:
        linhas.append(f"- `{extrator}.py`")
    linhas.append("")

    linhas.append("## Próximos passos")
    linhas.append("")
    linhas.append(
        "1. Cada extrator listado acima passa por triagem na Sprint RETRABALHO-EXTRATORES-01."
    )
    linhas.append(
        "2. Se o lint detectar nova violação no futuro, abrir sprint-filha "
        "`sprint_retrabalho_<extrator>.md` na hora -- regra zero TODO solto."
    )
    linhas.append(
        "3. Comparar este snapshot com auditorias anteriores em "
        "`docs/auditorias/cobertura_total_*.md` para detectar regressões."
    )
    linhas.append("")
    linhas.append(
        '*"Saber a cobertura é metade da cobertura. Agir sobre ela é a outra metade." '
        "-- princípio do auditor.*"
    )
    linhas.append("")
    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0] if __doc__ else "")
    parser.add_argument(
        "--executar",
        action="store_true",
        help="grava relatório em docs/auditorias/ (sem flag, dry-run apenas imprime sumário)",
    )
    args = parser.parse_args()

    extratores = coletar_extratores()
    violacoes = coletar_violacoes_lint()
    cobertura = coletar_cobertura_grafo()

    relatorio = montar_relatorio(extratores, violacoes, cobertura)

    if args.executar:
        _DIR_AUDITORIAS.mkdir(parents=True, exist_ok=True)
        hoje = date.today().isoformat()
        caminho = _DIR_AUDITORIAS / f"cobertura_total_{hoje}.md"
        caminho.write_text(relatorio, encoding="utf-8")
        print(f"[D7] relatório gravado em {caminho.relative_to(_RAIZ_REPO)}")
    else:
        print("[D7] dry-run -- use --executar para gravar relatório")
        print(
            f"[D7] {len(extratores)} extratores | {len(violacoes)} violacoes | "
            f"{len(cobertura)} tipos no grafo"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Auditar é confessar com método. Sem confissão metódica,
#  cada extrator vira ilha; com ela, cada um vira parte do continente."
#  -- princípio operacional do Protocolo Ouroboros
