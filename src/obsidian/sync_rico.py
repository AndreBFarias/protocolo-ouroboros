"""Sync rico bidirecional com vault Controle de Bordo — Sprint 71 (ADR-18).

Complementa `src/obsidian/sync.py` (relatórios mensais agregados) gerando,
para cada node do grafo SQLite, uma nota Markdown estruturada no vault
Obsidian. Escrita acontece em:

    $BORDO_DIR/Pessoal/Casal/Financeiro/{Documentos,Fornecedores,Meses,_Attachments}/

Princípios:

  - **Soberania humana**: se a nota tiver frontmatter com `sincronizado: true`
    ou tag `#sincronizado-automaticamente`, é reescrita. Caso contrário, o
    adapter trata como edição manual e PULA (nunca sobrescreve).
  - **Idempotência**: timestamp do grafo vs timestamp da nota + hash do corpo
    impedem reescrita sem mudança.
  - **Local First**: usa apenas `data/output/grafo.sqlite` e o filesystem do
    vault. Nenhuma rede.
  - **Forbidden zones**: respeita `.sistema`, `Trabalho`, `Segredos`,
    `Arquivo`, `.obsidian`, `.git` (ADR-18; adapter nunca entra).

API:

    sincronizar_rico(vault_root, grafo_path, dry_run=True) -> SyncReport
    python -m src.obsidian.sync --rico
"""

from __future__ import annotations

import hashlib
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.graph.db import GrafoDB, caminho_padrao
from src.utils.logger import configurar_logger

logger = configurar_logger("obsidian.sync_rico")

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_DIR_ORIGINAIS: Path = _RAIZ_REPO / "data" / "raw" / "originais"

_TAG_SINCRONIZADO: str = "#sincronizado-automaticamente"
_FRONTMATTER_SINCRONIZADO_RE = re.compile(r"^sincronizado:\s*true\s*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

_SUBPASTAS_OUROBOROS: tuple[str, ...] = (
    "Documentos",
    "Fornecedores",
    "Meses",
    "_Attachments",
)


# ============================================================================
# Relatório
# ============================================================================


@dataclass
class SyncReport:
    """Sumário da execução do sync rico."""

    documentos_escritos: int = 0
    fornecedores_escritos: int = 0
    notas_preservadas: int = 0  # usuário editou manualmente
    inalteradas: int = 0  # hash igual → nada mudou
    erros: list[str] = field(default_factory=list)

    def total_escritas(self) -> int:
        return self.documentos_escritos + self.fornecedores_escritos


# ============================================================================
# Slug e caminhos
# ============================================================================


def slugify(texto: str, limite: int = 80) -> str:
    """Converte texto em slug ASCII seguro para nomes de arquivo no vault."""
    if not texto:
        return "sem-nome"
    # Remove acentos
    nfkd = unicodedata.normalize("NFKD", texto)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii").lower()
    # Troca não-alfanum por hífen
    out: list[str] = []
    for ch in ascii_str:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    slug = "".join(out).strip("-")
    return (slug[:limite] or "sem-nome").strip("-")


def _diretorio_financeiro(vault_root: Path) -> Path:
    """Raiz do hub Ouroboros dentro do vault."""
    return vault_root / "Pessoal" / "Casal" / "Financeiro"


def _yyyymm(data_iso: str | None) -> str:
    """Extrai 'YYYY-MM' de uma data ISO; fallback para 'sem-data'."""
    if not data_iso:
        return "sem-data"
    partes = str(data_iso)[:10].split("-")
    if len(partes) >= 2:
        return f"{partes[0]}-{partes[1]}"
    return "sem-data"


# ============================================================================
# Detecção de edição manual
# ============================================================================


def eh_seguro_sobrescrever(nota_path: Path) -> bool:
    """True se a nota pode ser reescrita sem perder edição do usuário.

    Nota nova: seguro (não há conteúdo).
    Nota existente: seguro apenas se houver marcador
    `#sincronizado-automaticamente` ou frontmatter `sincronizado: true`.
    """
    if not nota_path.exists():
        return True
    try:
        conteudo = nota_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if _TAG_SINCRONIZADO in conteudo:
        return True
    match = _FRONTMATTER_RE.match(conteudo)
    if not match:
        return False
    return bool(_FRONTMATTER_SINCRONIZADO_RE.search(match.group(1)))


# ============================================================================
# Escrita idempotente
# ============================================================================


def _hash_conteudo(conteudo: str) -> str:
    """Hash curto usado como marcador de idempotência (primeiros 12 chars)."""
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:12]


def _conteudo_mudou(nota_path: Path, novo_conteudo: str) -> bool:
    """True quando a nota não existe ou seu corpo difere do novo."""
    if not nota_path.exists():
        return True
    try:
        atual = nota_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True
    return atual != novo_conteudo


# ============================================================================
# Templates
# ============================================================================


def _formatar_valor_br(valor: float | int | None) -> str:
    if valor is None:
        return "0,00"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "0,00"
    s = f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _render_documento(doc_meta: dict[str, Any], doc_nome: str) -> str:
    """Gera o corpo Markdown de uma nota de documento."""
    data = str(doc_meta.get("data_emissao", "sem-data"))[:10]
    fornecedor = str(doc_meta.get("fornecedor", "desconhecido"))
    valor = float(doc_meta.get("total") or 0.0)
    tipo_doc = str(doc_meta.get("tipo_documento", "documento"))
    arquivo_original = str(doc_meta.get("arquivo_original", ""))
    arquivo_attach = (
        f"_Attachments/{slugify(doc_nome)}{Path(arquivo_original).suffix.lower() or ''}"
    )

    frontmatter = (
        "---\n"
        "tipo: documento\n"
        f"nome_canonico: \"{doc_nome}\"\n"
        f"tipo_documento: {tipo_doc}\n"
        f"data: {data}\n"
        f"fornecedor: \"[[Fornecedores/{slugify(fornecedor)}]]\"\n"
        f"valor: {valor:.2f}\n"
        f"arquivo_original: \"[[{arquivo_attach}]]\"\n"
        "tags: [sincronizado-automaticamente, documento, "
        f"{tipo_doc}]\n"
        "sincronizado: true\n"
        "gerado_por: ouroboros.sync_rico\n"
        "---\n\n"
    )

    corpo = (
        f"# {doc_nome}\n\n"
        f"**Data:** {data}  \n"
        f"**Fornecedor:** [[Fornecedores/{slugify(fornecedor)}|{fornecedor}]]  \n"
        f"**Valor:** R$ {_formatar_valor_br(valor)}  \n"
        f"**Tipo:** {tipo_doc}  \n\n"
        "## Arquivo original\n\n"
        f"![[{arquivo_attach}]]\n\n"
        f"## Sincronização\n\n"
        f"_Gerado automaticamente por Ouroboros._ {_TAG_SINCRONIZADO}  \n"
        "Para editar manualmente, remova a tag acima antes.\n"
    )

    return frontmatter + corpo


def _render_fornecedor(nome: str, meta: dict[str, Any], qtd_docs: int) -> str:
    """Gera o corpo Markdown de uma nota de fornecedor."""
    categoria = str(meta.get("categoria", "nao-classificado"))
    cnpj = str(meta.get("cnpj") or meta.get("cpf_cnpj") or "")

    frontmatter = (
        "---\n"
        "tipo: fornecedor\n"
        f"nome_canonico: \"{nome}\"\n"
        f"categoria: {categoria}\n"
        + (f'cnpj: "{cnpj}"\n' if cnpj else "")
        + f"qtd_documentos: {qtd_docs}\n"
        "tags: [sincronizado-automaticamente, fornecedor]\n"
        "sincronizado: true\n"
        "gerado_por: ouroboros.sync_rico\n"
        "---\n\n"
    )

    corpo = (
        f"# {nome}\n\n"
        f"**Categoria:** {categoria}  \n"
        + (f"**CNPJ:** `{cnpj}`  \n" if cnpj else "")
        + f"**Documentos vinculados:** {qtd_docs}  \n\n"
        "## Dataview — documentos deste fornecedor\n\n"
        "```dataview\n"
        "TABLE data, valor, tipo_documento\n"
        '  FROM "Pessoal/Casal/Financeiro/Documentos"\n'
        f'  WHERE fornecedor = "[[Fornecedores/{slugify(nome)}]]"\n'
        "  SORT data DESC\n"
        "```\n\n"
        f"_Gerado automaticamente por Ouroboros._ {_TAG_SINCRONIZADO}\n"
    )

    return frontmatter + corpo


# ============================================================================
# Escrita de notas
# ============================================================================


def _escrever_nota(
    destino: Path,
    conteudo: str,
    dry_run: bool,
    report: SyncReport,
    categoria: str,
) -> bool:
    """Escreve o conteúdo em `destino` se seguro. Atualiza `report`."""
    if not eh_seguro_sobrescrever(destino):
        report.notas_preservadas += 1
        logger.info("preservada (editada manualmente): %s", destino)
        return False

    if not _conteudo_mudou(destino, conteudo):
        report.inalteradas += 1
        return False

    if dry_run:
        logger.info("[dry-run] escreveria %s (%d bytes)", destino, len(conteudo))
    else:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(conteudo, encoding="utf-8")
        logger.info("escrita: %s", destino)

    if categoria == "documento":
        report.documentos_escritos += 1
    elif categoria == "fornecedor":
        report.fornecedores_escritos += 1
    return True


# ============================================================================
# Sync principal
# ============================================================================


def sincronizar_rico(
    vault_root: Path,
    grafo_path: Path | None = None,
    dry_run: bool = True,
    min_docs_por_fornecedor: int = 2,
) -> SyncReport:
    """Execução principal — varre grafo e escreve notas no vault.

    - vault_root: raiz do vault (ex: `Path.home() / "Controle de Bordo"`).
    - grafo_path: caminho do SQLite; default = `src.graph.db.caminho_padrao()`.
    - dry_run: se True, não escreve nada no filesystem.
    - min_docs_por_fornecedor: fornecedores com menos que isso são pulados
      (reduz ruído quando grafo tem muito fornecedor isolado).
    """
    grafo = grafo_path or caminho_padrao()
    report = SyncReport()

    if not grafo.exists():
        logger.warning("grafo ausente: %s — sync rico abortado", grafo)
        report.erros.append(f"grafo_ausente:{grafo}")
        return report

    fin = _diretorio_financeiro(vault_root)

    # Garante subpastas de destino (no dry-run também criamos — útil para
    # inspeção manual da estrutura planejada; é um diretório vazio, sem
    # efeito destrutivo).
    if not dry_run:
        for sub in _SUBPASTAS_OUROBOROS:
            (fin / sub).mkdir(parents=True, exist_ok=True)

    with GrafoDB(grafo) as db:
        documentos = db.listar_nodes(tipo="documento")
        for doc in documentos:
            if doc.nome_canonico is None:
                continue
            yyyymm = _yyyymm(doc.metadata.get("data_emissao"))
            destino = (
                fin / "Documentos" / yyyymm / f"{slugify(doc.nome_canonico)}.md"
            )
            conteudo = _render_documento(doc.metadata, doc.nome_canonico)
            try:
                _escrever_nota(destino, conteudo, dry_run, report, "documento")
                _copiar_original(doc.metadata, doc.nome_canonico, fin, dry_run)
            except Exception as exc:  # noqa: BLE001
                logger.error("erro ao escrever %s: %s", destino, exc)
                report.erros.append(f"doc:{doc.nome_canonico}:{exc}")

        fornecedores = db.listar_nodes(tipo="fornecedor")
        for forn in fornecedores:
            if forn.nome_canonico is None:
                continue
            # Contagem de documentos do fornecedor: arestas `fornecido_por`
            # podem ser (doc -> fornecedor) ou (fornecedor <- doc).
            qtd = _contar_docs_do_fornecedor(db, forn.id)
            if qtd < min_docs_por_fornecedor:
                continue
            destino = fin / "Fornecedores" / f"{slugify(forn.nome_canonico)}.md"
            conteudo = _render_fornecedor(forn.nome_canonico, forn.metadata, qtd)
            try:
                _escrever_nota(destino, conteudo, dry_run, report, "fornecedor")
            except Exception as exc:  # noqa: BLE001
                logger.error("erro ao escrever %s: %s", destino, exc)
                report.erros.append(f"forn:{forn.nome_canonico}:{exc}")

    return report


def _contar_docs_do_fornecedor(db: GrafoDB, forn_id: int | None) -> int:
    """Conta arestas `fornecido_por` apontando para o fornecedor."""
    if forn_id is None:
        return 0
    try:
        edges = db.listar_edges(dst_id=forn_id, tipo="fornecido_por")
    except Exception:  # noqa: BLE001 — tipo pode não existir no grafo vazio
        return 0
    return len(edges)


def _copiar_original(
    doc_meta: dict[str, Any],
    doc_nome: str,
    fin_dir: Path,
    dry_run: bool,
) -> None:
    """Copia o original preservado em `data/raw/originais/` para o vault.

    Usa o campo `arquivo_original` do metadata (se presente) como hint para
    obter a extensão. Se a cópia já existir com mesmo hash, não sobrescreve.
    """
    arquivo_original = str(doc_meta.get("arquivo_original") or "").strip()
    if not arquivo_original:
        return
    origem = Path(arquivo_original)
    if not origem.is_absolute():
        origem = _RAIZ_REPO / origem
    if not origem.exists():
        # tenta buscar em data/raw/originais/ via hash do arquivo no metadata
        return

    destino = fin_dir / "_Attachments" / f"{slugify(doc_nome)}{origem.suffix.lower()}"
    if destino.exists():
        return
    if dry_run:
        logger.info("[dry-run] copiaria %s -> %s", origem, destino)
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(origem, destino)
        logger.info("anexo copiado: %s", destino)
    except OSError as exc:
        logger.warning("falha ao copiar original %s: %s", origem, exc)


# ============================================================================
# CLI
# ============================================================================


def main(argv: list[str] | None = None) -> int:
    import argparse
    import os

    parser = argparse.ArgumentParser(
        prog="python -m src.obsidian.sync_rico",
        description="Sync rico: gera notas por documento/fornecedor no vault",
    )
    parser.add_argument("--executar", action="store_true", help="Efetua escritas")
    parser.add_argument(
        "--vault", type=Path, default=None, help="Sobrescreve BORDO_DIR"
    )
    args = parser.parse_args(argv)

    vault = args.vault or Path(
        os.environ.get("BORDO_DIR", Path.home() / "Controle de Bordo")
    )
    report = sincronizar_rico(vault, dry_run=not args.executar)
    logger.info(
        "sync rico: %d docs escritas, %d fornecedores, %d preservadas, %d inalteradas, %d erros",
        report.documentos_escritos,
        report.fornecedores_escritos,
        report.notas_preservadas,
        report.inalteradas,
        len(report.erros),
    )
    return 0 if not report.erros else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())


# "O grafo do vault é o nosso dashboard sempre aberto." — princípio Sprint 71
