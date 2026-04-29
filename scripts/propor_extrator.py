"""Sprint LLM-02-V2 -- Pre-popula proposta de extrator novo.

Quando o classifier retorna `tipo=None` para um arquivo do inbox e não
ha extrator dedicado, o supervisor (Opus principal interativo) usa este
script via skill `/propor-extrator` para gerar arquivo
`docs/propostas/extracao/<tipo>_<data>.md` baseado em
`docs/propostas/_template.md`. Humano revisa, aprova e dispara a
sub-sprint correspondente em `docs/sprints/backlog/sprint_doc_<X>_*.md`.

Uso CLI:

    python scripts/propor_extrator.py <tipo_canonico> [--amostra <caminho>]

Exemplo:

    python scripts/propor_extrator.py pix_foto_comprovante \\
        --amostra data/raw/_classificar/comprovante_pix.jpg --executar

Sai com path do arquivo gerado em stdout. Idempotente via SHA da
hipotese normalizada (Sprint LLM-06-V2 vai consumir).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import sys
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATE = RAIZ / "docs" / "propostas" / "_template.md"
DESTINO_DIR = RAIZ / "docs" / "propostas" / "extracao"


def slug_seguro(raw: str) -> str:
    """Normaliza tipo para slug compatível com filesystem."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in raw.lower())


def hipotese_padrao(tipo: str, amostra: Path | None) -> str:
    referencia = f" Amostra de referência: `{amostra}`." if amostra else ""
    return (
        f"Tipo de documento `{tipo}` aparece em data/raw/ ou inbox/ mas o classifier "
        f"retorna None. Propor extrator dedicado em `src/extractors/{slug_seguro(tipo)}.py` + "
        f"regra em `mappings/tipos_documento.yaml`.{referencia}"
    )


def gerar_sha_hipotese(hipotese: str) -> str:
    """SHA-256 da hipótese normalizada (Sprint LLM-06-V2 vai consumir)."""
    normalizado = " ".join(hipotese.lower().split())
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()[:16]


def montar_proposta(tipo: str, amostra: Path | None, hoje: str) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    hipotese = hipotese_padrao(tipo, amostra)
    sha = gerar_sha_hipotese(hipotese)
    referencia_evidencia = (
        f"\n    - amostra: {amostra}" if amostra else "\n    - amostra: <preencher>"
    )
    sub_spec = (
        "    - sub-spec sugerida: docs/sprints/backlog/sprint_doc_<X>_extrator_"
        + slug_seguro(tipo)
        + ".md"
    )
    placeholder_tipo = (
        "<regra_categoria | extracao | resolver | classificação | er_produtos"
        " | linking | outro>"
    )
    placeholder_sha = (
        "<sha256 da hipotese normalizada -- preencher antes de gerar; "
        "ver scripts/check_propostas_rejeitadas.py>"
    )
    substituicoes = {
        "<slug-curto-kebab-case>": slug_seguro(tipo),
        placeholder_tipo: "extracao",
        "2026-04-28": hoje,
        "Texto livre em uma frase: o que esta proposta resolveria.": hipotese,
        "    - <amostra ou query do grafo que motivou a proposta>": referencia_evidencia,
        "    - <link para arquivo em data/raw/ ou node id no grafo>": sub_spec,
        placeholder_sha: sha,
        "Proposta: <título humano>": f"Proposta: extrator para `{tipo}`",
        "Por que esta proposta surgiu? Qual a observação que motivou?": (
            f"O tipo `{tipo}` foi detectado em runtime (classifier retornou None) "
            f"e não tem extrator dedicado. Proposta gerada via "
            f"`scripts/propor_extrator.py` para iniciar o ciclo de revisao humana."
        ),
    }
    proposta = template
    for antigo, novo in substituicoes.items():
        proposta = proposta.replace(antigo, novo)
    return proposta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tipo", help="Identificador canônico do tipo (ex: pix_foto_comprovante).")
    parser.add_argument(
        "--amostra",
        type=Path,
        default=None,
        help="Caminho do arquivo bruto que motivou a proposta.",
    )
    parser.add_argument(
        "--data",
        default=None,
        help="Override de data ISO (default: hoje).",
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Sem flag, dry-run (imprime conteúdo). Com flag, escreve arquivo.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not TEMPLATE.exists():
        logger.error("Template ausente: %s", TEMPLATE)
        return 2

    hoje = args.data or date.today().isoformat()
    proposta = montar_proposta(args.tipo, args.amostra, hoje)

    DESTINO_DIR.mkdir(parents=True, exist_ok=True)
    destino = DESTINO_DIR / f"{slug_seguro(args.tipo)}_{hoje}.md"

    if args.executar:
        if destino.exists():
            logger.warning("Proposta ja existe: %s (sobrescrevendo).", destino)
        destino.write_text(proposta, encoding="utf-8")
        logger.info("[OK] Proposta gerada em %s", destino)
        print(destino)
    else:
        logger.info("[DRY-RUN] Conteúdo que seria escrito em %s:", destino)
        logger.info("---")
        logger.info(proposta)
        logger.info("---")
        logger.info("Use --executar para gravar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Quem propoe sem evidencia chuta com etiqueta." -- princípio do ciclo deliberativo
