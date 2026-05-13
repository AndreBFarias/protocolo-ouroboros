r"""Sprint INFRA-LINKING-PROPOSTAS-GC -- garbage collection de propostas obsoletas.

Política
========

`docs/propostas/linking/` acumula propostas geradas a cada `./run.sh --tudo`
sem limpeza. Quando a execução posterior dedupa transações, renomeia
documentos ou atribui ids de grafo novos, as propostas antigas viram
resíduo que ofusca o supervisor. Este script classifica e arquiva.

Critério de obsolescência
=========================

Para cada `*.md` no diretório (exceto `_obsoletas/`, `_aprovadas/`,
`_rejeitadas/`):

  1. Extrai `id grafo` do corpo (linha `- id grafo: \`<id>\``).
  2. Consulta `node` (tabela canônica `src/graph/db.py`) por
     `id = <id grafo>` e `tipo = 'documento'`.
  3. Se nó existe -> proposta `atual`.
  4. Se nó não existe -> proposta `obsoleta` (documento sumiu por
     rename, dedup, ingestão limpa, etc.).

Arquivos sem `id grafo` no corpo (ex: propostas legadas com nome
`YYYY-MM-DD_<tema>.md`) são marcados como `indeterminado` e
preservados -- exigem revisão humana para arquivamento manual.

Saídas
======

`--auditar-atual`  imprime resumo por categoria e lista paths.
`--mover-obsoletos` move obsoletas para
                   `docs/propostas/linking/_obsoletas/<YYYY-MM-DD>-<nome>`.
                   Idempotente: prefixo de data garante unicidade entre
                   execuções do mesmo dia (sufixo `.N` se colidir).
`--dry-run`        (default) lista sem mover.

Idempotência
============

Re-rodar `--mover-obsoletos` só move o que ainda está na raiz do
diretório. Arquivos já em `_obsoletas/` não são reprocessados.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Permite executar como `python scripts/gc_propostas_linking.py` direto
# (sem -m) preservando imports relativos a src/.
_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
if str(_RAIZ_REPO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_REPO))

from src.graph.db import caminho_padrao  # noqa: E402
from src.utils.logger import configurar_logger  # noqa: E402

logger = configurar_logger("scripts.gc_propostas_linking")


# ============================================================================
# Constantes
# ============================================================================

PASTA_PROPOSTAS_PADRAO: Path = _RAIZ_REPO / "docs" / "propostas" / "linking"
SUBDIRS_IGNORADOS: tuple[str, ...] = ("_obsoletas", "_aprovadas", "_rejeitadas")
PADRAO_ID_GRAFO = re.compile(r"^\s*-\s*id\s+grafo\s*:\s*`?(\d+)`?", re.IGNORECASE | re.MULTILINE)


# ============================================================================
# Modelo
# ============================================================================


@dataclass(frozen=True)
class Classificacao:
    """Resultado da auditoria de uma proposta.

    estado in {"atual", "obsoleto", "indeterminado"}.
    id_grafo == None quando o arquivo não declara id grafo.
    """

    caminho: Path
    estado: str
    id_grafo: int | None
    motivo: str


# ============================================================================
# Leitura e classificação
# ============================================================================


def extrair_id_grafo(texto: str) -> int | None:
    r"""Lê o id do grafo no corpo da proposta.

    Aceita variações `- id grafo: \`7422\`` e `- id grafo: 7422`.
    Devolve None quando o padrão não casa.
    """
    match = PADRAO_ID_GRAFO.search(texto)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def listar_propostas(pasta: Path) -> list[Path]:
    """Lista `*.md` na raiz da pasta, ignorando subdiretórios reservados.

    Subdiretórios em SUBDIRS_IGNORADOS são puramente não-recursivos:
    `_obsoletas/`, `_aprovadas/`, `_rejeitadas/`.
    """
    if not pasta.is_dir():
        return []
    propostas: list[Path] = []
    for item in sorted(pasta.iterdir()):
        if item.is_dir():
            continue
        if item.suffix != ".md":
            continue
        propostas.append(item)
    return propostas


def carregar_ids_documento(caminho_db: Path) -> set[int]:
    """Lê todos os ids de nós `tipo='documento'` do grafo.

    Devolve set para lookup O(1). Quando o grafo não existe, devolve
    set vazio -- caller decide se isso é erro (auditoria sem grafo não
    pode classificar nada como atual).
    """
    if not caminho_db.exists():
        logger.warning("grafo SQLite ausente em %s -- nenhum id carregado", caminho_db)
        return set()
    conn = sqlite3.connect(str(caminho_db))
    try:
        cursor = conn.execute("SELECT id FROM node WHERE tipo = 'documento'")
        return {int(row[0]) for row in cursor.fetchall()}
    finally:
        conn.close()


def classificar(
    propostas: list[Path],
    ids_documento_vivos: set[int],
) -> list[Classificacao]:
    """Classifica cada proposta como atual / obsoleto / indeterminado.

    Sem id_grafo extraível -> `indeterminado` (preserva).
    id_grafo extraído e presente em ids_documento_vivos -> `atual`.
    id_grafo extraído e ausente do grafo -> `obsoleto`.
    """
    resultados: list[Classificacao] = []
    for caminho in propostas:
        try:
            texto = caminho.read_text(encoding="utf-8")
        except OSError as erro:
            logger.warning("falha ao ler %s: %s", caminho.name, erro)
            resultados.append(
                Classificacao(
                    caminho=caminho,
                    estado="indeterminado",
                    id_grafo=None,
                    motivo=f"erro_io: {erro}",
                )
            )
            continue

        id_grafo = extrair_id_grafo(texto)
        if id_grafo is None:
            resultados.append(
                Classificacao(
                    caminho=caminho,
                    estado="indeterminado",
                    id_grafo=None,
                    motivo="sem_id_grafo_no_corpo",
                )
            )
            continue

        if id_grafo in ids_documento_vivos:
            resultados.append(
                Classificacao(
                    caminho=caminho,
                    estado="atual",
                    id_grafo=id_grafo,
                    motivo="documento_no_grafo",
                )
            )
        else:
            resultados.append(
                Classificacao(
                    caminho=caminho,
                    estado="obsoleto",
                    id_grafo=id_grafo,
                    motivo="documento_ausente_no_grafo",
                )
            )
    return resultados


# ============================================================================
# Acao: mover para _obsoletas/
# ============================================================================


def mover_obsoletos(
    classificacoes: list[Classificacao],
    pasta_propostas: Path,
    hoje: date | None = None,
) -> list[tuple[Path, Path]]:
    """Move propostas classificadas como `obsoleto` para `_obsoletas/`.

    Nome destino: `<YYYY-MM-DD>-<nome_original>`. Se já existir
    (re-execução no mesmo dia), adiciona sufixo `.N` para preservar
    auditoria sem sobrescrever.

    Devolve lista de (origem, destino) realmente movidos.
    """
    dia = (hoje or date.today()).isoformat()
    destino_pasta = pasta_propostas / "_obsoletas"
    destino_pasta.mkdir(parents=True, exist_ok=True)

    movidos: list[tuple[Path, Path]] = []
    for cls in classificacoes:
        if cls.estado != "obsoleto":
            continue
        origem = cls.caminho
        if not origem.exists():
            # Pode ter sido movido em iteração concorrente; idempotência.
            continue
        nome_base = f"{dia}-{origem.name}"
        destino = destino_pasta / nome_base
        sufixo = 1
        while destino.exists():
            destino = destino_pasta / f"{nome_base}.{sufixo}"
            sufixo += 1
        origem.rename(destino)
        movidos.append((origem, destino))
        logger.info("movido %s -> _obsoletas/%s", origem.name, destino.name)
    return movidos


# ============================================================================
# Relatorio
# ============================================================================


def resumir(classificacoes: list[Classificacao]) -> dict[str, int]:
    """Conta classificações por estado."""
    contagem: dict[str, int] = {"atual": 0, "obsoleto": 0, "indeterminado": 0}
    for cls in classificacoes:
        contagem[cls.estado] = contagem.get(cls.estado, 0) + 1
    return contagem


def imprimir_relatorio(
    classificacoes: list[Classificacao],
    titulo: str,
    detalhar_obsoletos: bool = True,
) -> None:
    """Imprime resumo + listagem opcional.

    PII (nomes/CPFs em paths) não são logados em INFO; ficam apenas no
    arquivo, não no stdout estruturado. Aqui exibimos somente nomes de
    arquivo no terminal -- supervisor abre o md para detalhe sensível.
    """
    contagem = resumir(classificacoes)
    print(f"\n=== {titulo} ===")
    print(f"  atuais        : {contagem.get('atual', 0)}")
    print(f"  obsoletas     : {contagem.get('obsoleto', 0)}")
    print(f"  indeterminadas: {contagem.get('indeterminado', 0)}")
    print(f"  total         : {len(classificacoes)}")

    if detalhar_obsoletos:
        obsoletas = [c for c in classificacoes if c.estado == "obsoleto"]
        if obsoletas:
            print("\nObsoletas (id_grafo ausente no grafo):")
            for cls in obsoletas:
                print(f"  - {cls.caminho.name} (id_grafo={cls.id_grafo})")

    indeterminadas = [c for c in classificacoes if c.estado == "indeterminado"]
    if indeterminadas:
        print("\nIndeterminadas (preservadas, exigem revisao manual):")
        for cls in indeterminadas:
            print(f"  - {cls.caminho.name} ({cls.motivo})")


# ============================================================================
# CLI
# ============================================================================


def montar_parser() -> argparse.ArgumentParser:
    """Constrói argparse para a CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Garbage collection de propostas obsoletas em "
            "docs/propostas/linking/."
        ),
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--auditar-atual",
        action="store_true",
        help="Audita estado atual sem mover (sinônimo de --dry-run).",
    )
    grupo.add_argument(
        "--mover-obsoletos",
        action="store_true",
        help="Move propostas obsoletas para _obsoletas/<data>-<nome>.",
    )
    grupo.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista classificação sem mover (default).",
    )
    parser.add_argument(
        "--pasta",
        type=Path,
        default=PASTA_PROPOSTAS_PADRAO,
        help="Pasta de propostas (default: docs/propostas/linking).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Caminho do grafo SQLite (default: data/output/grafo.sqlite).",
    )
    return parser


def executar(argv: list[str] | None = None) -> int:
    """Entrada programática.

    Devolve exit code: 0 sempre que a execução completa sem erro de
    IO/SQL. Auditoria pura não falha apenas porque encontrou obsoletos
    -- isso é o resultado esperado.
    """
    parser = montar_parser()
    args = parser.parse_args(argv)

    caminho_db = args.db if args.db is not None else caminho_padrao()
    pasta = args.pasta

    if not pasta.is_dir():
        print(f"ERRO: pasta não encontrada: {pasta}", file=sys.stderr)
        return 2

    propostas = listar_propostas(pasta)
    ids_vivos = carregar_ids_documento(caminho_db)
    classificacoes = classificar(propostas, ids_vivos)

    if args.mover_obsoletos:
        imprimir_relatorio(classificacoes, titulo="ANTES da movimentação")
        movidos = mover_obsoletos(classificacoes, pasta)
        print(f"\nMovidas {len(movidos)} propostas para _obsoletas/.")
        propostas_pos = listar_propostas(pasta)
        classificacoes_pos = classificar(propostas_pos, ids_vivos)
        imprimir_relatorio(
            classificacoes_pos,
            titulo="DEPOIS da movimentação",
            detalhar_obsoletos=False,
        )
        return 0

    titulo = "Auditoria (dry-run)"
    imprimir_relatorio(classificacoes, titulo=titulo)
    return 0


def main() -> int:
    return executar(sys.argv[1:])


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


# "Acumular sem limpar é atalho para não ver o que já viu." -- princípio do arquivista
