"""Gerador do índice de extratores em docs/extractors/_INDEX.md.

Complementa (não substitui) os docs curados por extrator: lê cada módulo,
extrai classe e docstring, confere cobertura de documentação manual e
produz uma visão geral navegável.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger("doc_generator")

RAIZ = Path(__file__).parent.parent.parent
DIR_EXTRATORES = RAIZ / "src" / "extractors"
DIR_DOCS = RAIZ / "docs" / "extractors"
ARQUIVO_INDICE = DIR_DOCS / "_INDEX.md"

IGNORAR_MODULOS: frozenset[str] = frozenset({"__init__", "base"})

MAPA_DOC_CURADO: dict[str, str] = {
    "nubank_cartao": "nubank_cartao.md",
    "nubank_cc": "nubank_cc.md",
    "c6_cartao": "c6_cartao.md",
    "c6_cc": "c6_cc.md",
    "itau_pdf": "itau_cc.md",
    "santander_pdf": "santander_cartao.md",
    "energia_ocr": "energia_neoenergia.md",
    "ofx_parser": "ofx_parser.md",
}


@dataclass(frozen=True)
class InfoExtrator:
    """Metadados de um extrator extraídos via AST."""

    modulo: str
    classes: list[str]
    docstring_modulo: str
    docstring_classe: str
    doc_curado: str | None


def _extrair_docstring(node: ast.AST) -> str:
    """Retorna docstring do nó ou string vazia."""
    doc = ast.get_docstring(node)
    return (doc or "").strip()


def _analisar_arquivo(caminho: Path) -> InfoExtrator:
    """Extrai classes e docstrings de um módulo extrator via AST."""
    conteudo = caminho.read_text(encoding="utf-8")
    arvore = ast.parse(conteudo, filename=str(caminho))

    classes: list[str] = []
    doc_classe = ""

    for node in arvore.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
            if not doc_classe:
                doc_classe = _extrair_docstring(node)

    modulo = caminho.stem
    doc_curado_nome = MAPA_DOC_CURADO.get(modulo)
    if doc_curado_nome and (DIR_DOCS / doc_curado_nome).exists():
        doc_curado = doc_curado_nome
    else:
        doc_curado = None

    return InfoExtrator(
        modulo=modulo,
        classes=classes,
        docstring_modulo=_extrair_docstring(arvore),
        docstring_classe=doc_classe,
        doc_curado=doc_curado,
    )


def _descobrir_extratores() -> list[Path]:
    """Lista arquivos .py em src/extractors/ ignorando base e __init__."""
    if not DIR_EXTRATORES.exists():
        raise FileNotFoundError(f"Diretório {DIR_EXTRATORES} não existe")
    return sorted(p for p in DIR_EXTRATORES.glob("*.py") if p.stem not in IGNORAR_MODULOS)


def _render_indice(infos: list[InfoExtrator]) -> str:
    """Monta o Markdown do índice de extratores."""
    linhas: list[str] = []
    linhas.append("# Extratores -- Índice gerado")
    linhas.append("")
    linhas.append(
        "Gerado automaticamente por `src/utils/doc_generator.py`. "
        "Não edite manualmente; atualize via `make docs`."
    )
    linhas.append("")
    linhas.append(
        "Os arquivos `.md` deste diretório (fora este) são curados à mão e "
        "descrevem o formato de cada fonte bancária."
    )
    linhas.append("")

    linhas.append("## Cobertura")
    linhas.append("")
    linhas.append("| Módulo | Classe principal | Doc curado |")
    linhas.append("|--------|------------------|------------|")
    for info in infos:
        classe = info.classes[0] if info.classes else "-"
        if info.doc_curado:
            doc_link = f"[`{info.doc_curado}`]({info.doc_curado})"
        else:
            doc_link = "**ausente**"
        linhas.append(f"| `{info.modulo}` | `{classe}` | {doc_link} |")
    linhas.append("")

    linhas.append("## Descrição por módulo")
    linhas.append("")
    for info in infos:
        linhas.append(f"### `{info.modulo}`")
        linhas.append("")
        if info.docstring_modulo:
            linhas.append(info.docstring_modulo)
            linhas.append("")
        if info.classes:
            linhas.append(f"**Classe principal:** `{info.classes[0]}`")
            linhas.append("")
        if info.docstring_classe:
            linhas.append("**Docstring da classe:**")
            linhas.append("")
            linhas.append("```")
            linhas.append(info.docstring_classe)
            linhas.append("```")
            linhas.append("")
        if info.doc_curado:
            linhas.append(f"Documentação detalhada: [`{info.doc_curado}`]({info.doc_curado})")
        else:
            linhas.append("_Sem documentação curada -- criar arquivo dedicado recomendado._")
        linhas.append("")

    return "\n".join(linhas).rstrip() + "\n"


def gerar_indice() -> Path:
    """Orquestra a coleta e escrita do índice. Retorna o caminho do arquivo."""
    arquivos = _descobrir_extratores()
    logger.info("Encontrados %d extratores em %s", len(arquivos), DIR_EXTRATORES)

    infos = [_analisar_arquivo(a) for a in arquivos]

    sem_doc = [i.modulo for i in infos if i.doc_curado is None]
    if sem_doc:
        logger.warning("Extratores sem doc curado: %s", ", ".join(sem_doc))

    DIR_DOCS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_INDICE.write_text(_render_indice(infos), encoding="utf-8")
    logger.info("Índice gerado em %s", ARQUIVO_INDICE)
    return ARQUIVO_INDICE


def main() -> None:
    """Entrypoint CLI para geração do índice."""
    try:
        gerar_indice()
    except Exception as err:
        logger.error("Falha ao gerar índice: %s", err)
        sys.exit(1)


if __name__ == "__main__":
    main()


# "Um livro deve ser o machado que quebra o mar de gelo dentro de nós." -- Franz Kafka
