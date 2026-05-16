"""Anti-órfão na inbox: detecta arquivos sem integração ao grafo.

Sprint ANTI-MIGUE-02 do plan pure-swinging-mitten. Cobre item 30 da auditoria
honesta 2026-04-29 (P0 perda silenciosa de dados): arquivo entra na zona de
estagiário (data/raw/_classificar/ ou data/raw/_conferir/) e nunca produz
node documento no grafo. Por padrão varre apenas essas duas zonas porque é
onde a perda silenciosa acontece -- arquivos já em pastas finais (holerites,
impostos, etc.) já passaram pelo pipeline.

Estados detectados por arquivo:
    integrado         documento no grafo + aresta documento_de presente
    catalogado_orfao  documento no grafo mas sem aresta documento_de
    orfao_total       arquivo no disco mas ausente no grafo

Uso:
    python -m src.intake.anti_orfao              # observador (sempre exit 0)
    python -m src.intake.anti_orfao --strict     # exit 1 se ha orfaos > 24h
    python -m src.intake.anti_orfao --threshold-horas 6
    python -m src.intake.anti_orfao --abrangente # varre data/raw/ inteiro
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ_REPO = Path(__file__).resolve().parent.parent.parent
DB_PADRAO = RAIZ_REPO / "data" / "output" / "grafo.sqlite"
RAW_PADRAO = RAIZ_REPO / "data" / "raw"
RELATORIO_PADRAO = RAIZ_REPO / "data" / "output" / "orfaos.md"

# Zona de estagiario: subpastas de data/raw/ onde arquivos chegam antes da
# catalogacao final. Se um arquivo persiste aqui alem do threshold, virou
# orfao silencioso (cenario P0 da auditoria 2026-04-29).
ZONA_ESTAGIARIO = ("_classificar", "_conferir")

# Pastas dentro de data/raw/ que não são varridas no modo abrangente:
# - originais/: cópia preservada por ADR-18 (intencionalmente fora do pipeline).
# - _envelopes/: envelopes já processados, não são documentos individuais.
PASTAS_IGNORADAS_ABRANGENTE = {"originais", "_envelopes"}

# Extensoes suportadas pelo pipeline (sincronizado com src/inbox_processor.py).
EXTENSOES_VALIDAS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".csv",
    ".xlsx",
    ".xls",
    ".ofx",
    ".xml",
    ".html",
    ".htm",
    ".docx",
    ".txt",
}


@dataclass
class Classificacao:
    integrado: list[Path] = field(default_factory=list)
    catalogado_orfao: list[Path] = field(default_factory=list)
    orfao_total: list[Path] = field(default_factory=list)
    orfao_total_antigo: list[Path] = field(default_factory=list)


def _normalizar(caminho: Path) -> str:
    """Retorna path relativo a raiz do repo, com separador POSIX."""
    try:
        rel = caminho.resolve().relative_to(RAIZ_REPO)
    except ValueError:
        rel = caminho
    return str(rel).replace("\\", "/")


def varrer_arquivos_inbox(raw: Path = RAW_PADRAO, abrangente: bool = False) -> list[Path]:
    """Lista arquivos suportados na zona de estagiario (default) ou em todo
    data/raw/ (modo abrangente).
    """
    if not raw.exists():
        return []
    arquivos: list[Path] = []
    if abrangente:
        for filho in raw.iterdir():
            if filho.is_dir() and filho.name in PASTAS_IGNORADAS_ABRANGENTE:
                continue
            if filho.is_dir():
                arquivos.extend(_listar_recursivo(filho))
            elif filho.is_file() and filho.suffix.lower() in EXTENSOES_VALIDAS:
                arquivos.append(filho)
    else:
        for nome in ZONA_ESTAGIARIO:
            zona = raw / nome
            if zona.is_dir():
                arquivos.extend(_listar_recursivo(zona))
    return arquivos


def _listar_recursivo(pasta: Path) -> list[Path]:
    return [c for c in pasta.rglob("*") if c.is_file() and c.suffix.lower() in EXTENSOES_VALIDAS]


def mapear_documentos_no_grafo(db: Path = DB_PADRAO) -> dict[str, dict]:
    """Indexa nodes tipo=documento por metadata.arquivo_origem.

    Retorna mapa {path_relativo: {"doc_id": int, "tem_aresta": bool}}.
    """
    if not db.exists():
        return {}
    mapa: dict[str, dict] = {}
    with sqlite3.connect(db) as con:
        # 1. Coleta documentos
        for doc_id, metadata_json in con.execute(
            "SELECT id, metadata FROM node WHERE tipo='documento'"
        ):
            try:
                meta = json.loads(metadata_json or "{}")
            except json.JSONDecodeError:
                continue
            path = meta.get("arquivo_origem")
            if not path:
                continue
            mapa[path] = {"doc_id": doc_id, "tem_aresta": False}
        # 2. Marca quem tem aresta documento_de
        if mapa:
            ids = ",".join(str(d["doc_id"]) for d in mapa.values())
            for (src_id,) in con.execute(
                f"SELECT DISTINCT src_id FROM edge WHERE tipo='documento_de' AND src_id IN ({ids})"
            ):
                for path, info in mapa.items():
                    if info["doc_id"] == src_id:
                        info["tem_aresta"] = True
                        break
    return mapa


def classificar(
    arquivos: list[Path],
    mapa_grafo: dict[str, dict],
    threshold_horas: int = 24,
) -> Classificacao:
    """Distribui arquivos entre os 4 estados anti-orfao."""
    resultado = Classificacao()
    limite = datetime.now() - timedelta(hours=threshold_horas)
    for arq in arquivos:
        chave = _normalizar(arq)
        info = mapa_grafo.get(chave)
        if info is None:
            mtime = datetime.fromtimestamp(arq.stat().st_mtime)
            if mtime < limite:
                resultado.orfao_total_antigo.append(arq)
            else:
                resultado.orfao_total.append(arq)
        elif info["tem_aresta"]:
            resultado.integrado.append(arq)
        else:
            resultado.catalogado_orfao.append(arq)
    return resultado


def gerar_relatorio(c: Classificacao, saida: Path = RELATORIO_PADRAO) -> None:
    """Escreve relatório Markdown em data/output/orfaos.md."""
    saida.parent.mkdir(parents=True, exist_ok=True)
    total = (
        len(c.integrado) + len(c.catalogado_orfao) + len(c.orfao_total) + len(c.orfao_total_antigo)
    )
    linhas: list[str] = [
        "# Relatório Anti-Órfão",
        "",
        f"Gerado em {datetime.now().isoformat(timespec='seconds')}.",
        "",
        "## Resumo",
        "",
        f"- Total de arquivos varridos: **{total}**",
        f"- Integrados (documento no grafo + aresta documento_de): **{len(c.integrado)}**",
        f"- Catalogados órfãos (documento no grafo, sem aresta): **{len(c.catalogado_orfao)}**",
        f"- Órfãos totais recentes (<24h, ainda processando): **{len(c.orfao_total)}**",
        f"- Órfãos totais antigos (>24h, ALERTA): **{len(c.orfao_total_antigo)}**",
        "",
    ]
    if c.orfao_total_antigo:
        linhas.append("## Órfãos antigos (ação requerida)")
        linhas.append("")
        for arq in sorted(c.orfao_total_antigo):
            linhas.append(f"- `{_normalizar(arq)}`")
        linhas.append("")
    if c.catalogado_orfao:
        linhas.append("## Catalogados órfãos (linking falhou)")
        linhas.append("")
        for arq in sorted(c.catalogado_orfao):
            linhas.append(f"- `{_normalizar(arq)}`")
        linhas.append("")
    if c.orfao_total:
        linhas.append("## Órfãos recentes (ainda em janela de processamento)")
        linhas.append("")
        for arq in sorted(c.orfao_total):
            linhas.append(f"- `{_normalizar(arq)}`")
        linhas.append("")
    saida.write_text("\n".join(linhas), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anti-órfão na inbox")
    parser.add_argument("--strict", action="store_true", help="Exit 1 se há órfãos > threshold")
    parser.add_argument(
        "--threshold-horas",
        type=int,
        default=24,
        help="Idade em horas a partir da qual órfão total vira alerta (padrão: 24)",
    )
    parser.add_argument(
        "--abrangente",
        action="store_true",
        help="Varre data/raw/ inteiro (excluindo originais/, _envelopes/) em vez "
        "de apenas a zona de estagiário",
    )
    parser.add_argument("--db", type=Path, default=DB_PADRAO)
    parser.add_argument("--raw", type=Path, default=RAW_PADRAO)
    parser.add_argument("--saida", type=Path, default=RELATORIO_PADRAO)
    args = parser.parse_args(argv)

    arquivos = varrer_arquivos_inbox(args.raw, abrangente=args.abrangente)
    mapa = mapear_documentos_no_grafo(args.db)
    classif = classificar(arquivos, mapa, threshold_horas=args.threshold_horas)
    gerar_relatorio(classif, args.saida)

    total_orfaos_antigos = len(classif.orfao_total_antigo)
    print(
        f"[ANTI-ORFAO] {len(classif.integrado)} integrados | "
        f"{len(classif.catalogado_orfao)} catalogados órfãos | "
        f"{len(classif.orfao_total)} órfãos recentes | "
        f"{total_orfaos_antigos} órfãos antigos (>{args.threshold_horas}h) | "
        f"relatório: {_normalizar(args.saida)}"
    )

    if args.strict and total_orfaos_antigos > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "O que entra e não sai vira sombra; o que entra e fica registrado vira luz."
# -- princípio do anti-órfão
