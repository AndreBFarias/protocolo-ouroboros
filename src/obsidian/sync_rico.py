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
import os
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
    mocs_gerados: int = 0  # MOCs mensais escritos em Meses/YYYY-MM.md
    notas_preservadas: int = 0  # usuário editou manualmente
    inalteradas: int = 0  # hash igual → nada mudou
    erros: list[str] = field(default_factory=list)

    def total_escritas(self) -> int:
        return self.documentos_escritos + self.fornecedores_escritos + self.mocs_gerados


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
        f'nome_canonico: "{doc_nome}"\n'
        f"tipo_documento: {tipo_doc}\n"
        f"data: {data}\n"
        f'fornecedor: "[[Fornecedores/{slugify(fornecedor)}]]"\n'
        f"valor: {valor:.2f}\n"
        f'arquivo_original: "[[{arquivo_attach}]]"\n'
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
    categoria = str(meta.get("categoria", "nao-classificado"))  # noqa: accent
    cnpj = str(meta.get("cnpj") or meta.get("cpf_cnpj") or "")

    frontmatter = (
        "---\n"
        "tipo: fornecedor\n"
        f'nome_canonico: "{nome}"\n'
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
# MOC mensal (Sprint 87.6)
# ============================================================================


_NOMES_MESES_PT: dict[str, str] = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Março",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}


def _agregar_docs_por_mes(
    documentos: list[Any],
) -> dict[str, dict[str, Any]]:
    """Agrupa nodes de documento por `YYYY-MM` extraído de `data_emissao`.

    Retorna `{mes_ref: {"docs": [...], "fornecedores": set[str], "total": float}}`.
    Docs sem `data_emissao` vão para a chave sentinela ``"sem-data"`` (para que o
    chamador possa descartar ou logar antes de renderizar a MOC).
    """
    agregado: dict[str, dict[str, Any]] = {}
    for doc in documentos:
        if getattr(doc, "nome_canonico", None) is None:
            continue
        meta = doc.metadata or {}
        mes_ref = _yyyymm(meta.get("data_emissao"))
        bucket = agregado.setdefault(
            mes_ref,
            {"docs": [], "fornecedores": set(), "total": 0.0},
        )
        bucket["docs"].append(doc)
        fornecedor = str(meta.get("fornecedor") or "").strip()
        if fornecedor:
            bucket["fornecedores"].add(fornecedor)
        try:
            bucket["total"] += float(meta.get("total") or 0.0)
        except (TypeError, ValueError):
            # valor corrompido no metadata — ignorar em silêncio; vai
            # refletir como subestimativa no "total" da MOC.
            pass
    return agregado


def _label_mes_humano(mes_ref: str) -> str:
    """Traduz 'YYYY-MM' em 'Nome AAAA' (ex: '2026-04' → 'Abril 2026')."""
    partes = mes_ref.split("-")
    if len(partes) != 2:
        return mes_ref
    ano, mm = partes
    nome = _NOMES_MESES_PT.get(mm, mm)
    return f"{nome} {ano}"


def _render_moc_mensal(mes_ref: str, agregado: dict[str, Any]) -> str:
    """Gera o Markdown da MOC mensal em `Meses/YYYY-MM.md`.

    Inclui frontmatter, tabela de documentos, lista de fornecedores únicos e
    uma consulta Dataview viva para navegação dentro do Obsidian. A query
    Dataview é escrita com aspas triplas para não colidir com o parser do
    Python — os backticks são literais no Markdown final.
    """
    docs: list[Any] = agregado.get("docs", [])
    fornecedores: set[str] = agregado.get("fornecedores", set())
    total_valor: float = float(agregado.get("total", 0.0))
    total_docs = len(docs)
    total_fornecedores = len(fornecedores)
    label_humano = _label_mes_humano(mes_ref)

    # Frontmatter
    frontmatter = (
        "---\n"
        "tipo: moc\n"
        f'mes: "{mes_ref}"\n'
        f"total_documentos: {total_docs}\n"
        f"total_fornecedores: {total_fornecedores}\n"
        f"total_valor: {total_valor:.2f}\n"
        f"tags: [sincronizado-automaticamente, moc, mes-{mes_ref}]\n"
        f'aliases: ["{label_humano}", "{mes_ref}"]\n'
        "sincronizado: true\n"
        "gerado_por: ouroboros.sync_rico\n"
        "---\n\n"
    )

    # Tabela de documentos (ordenada por data)
    def _chave_ordenacao(doc: Any) -> str:
        return str((doc.metadata or {}).get("data_emissao") or "")

    docs_ordenados = sorted(docs, key=_chave_ordenacao)

    linhas_tabela: list[str] = []
    linhas_tabela.append("| Data | Tipo | Fornecedor | Valor | Nota |")
    linhas_tabela.append("|---|---|---|---|---|")
    for doc in docs_ordenados:
        meta = doc.metadata or {}
        data = str(meta.get("data_emissao") or "sem-data")[:10]
        tipo_doc = str(meta.get("tipo_documento") or "documento")
        fornecedor = str(meta.get("fornecedor") or "desconhecido")
        valor = _formatar_valor_br(meta.get("total"))
        slug = slugify(doc.nome_canonico)
        link = f"[[Documentos/{mes_ref}/{slug}]]"
        linhas_tabela.append(f"| {data} | {tipo_doc} | {fornecedor} | R$ {valor} | {link} |")

    tabela_docs = "\n".join(linhas_tabela)

    # Lista de fornecedores únicos
    if fornecedores:
        linhas_forn = [
            f"- [[Fornecedores/{slugify(nome)}|{nome}]]" for nome in sorted(fornecedores)
        ]
        lista_fornecedores = "\n".join(linhas_forn)
    else:
        lista_fornecedores = "_Nenhum fornecedor identificado._"

    # Consulta Dataview viva. Usamos `chr(96) * 3` para compor os três
    # backticks sem ambiguidade na leitura do código-fonte.
    tripla = chr(96) * 3
    query_dataview = (
        f"{tripla}dataview\n"
        'TABLE file.link as "Nota", tipo_documento, valor as "Valor"\n'
        f'FROM "Pessoal/Casal/Financeiro/Documentos/{mes_ref}"\n'
        'WHERE tipo = "documento"\n'
        "SORT data_emissao ASC\n"
        f"{tripla}"
    )

    corpo = (
        f"# {label_humano}\n\n"
        f"## Documentos ({total_docs})\n\n"
        f"{tabela_docs}\n\n"
        f"## Fornecedores únicos ({total_fornecedores})\n\n"
        f"{lista_fornecedores}\n\n"
        "## Dataview — consulta viva\n\n"
        f"{query_dataview}\n\n"
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
    elif categoria == "moc":
        report.mocs_gerados += 1
    return True


# ============================================================================
# Sync principal
# ============================================================================


def _gravar_last_sync(
    raiz_projeto: Path,
    *,
    n_arquivos: int,
    duracao_segundos: float,
    vault_path: str,
    erros: list[str] | None = None,
) -> None:
    """Grava ``.ouroboros/cache/last_sync.json`` para observabilidade UI.

    Lido por ``src.dashboard.componentes.ui.ler_sync_info`` (UX-V-03)
    e renderizado como sync-indicator pelo dashboard (UX-V-04).

    Isolamento de testes (INFRA-TEST-ISOLAR-LAST-SYNC): se a variável
    de ambiente ``OUROBOROS_CACHE_DIR`` estiver setada, escreve nela
    em vez de ``raiz_projeto / .ouroboros / cache``. Permite que testes
    apontem o destino para ``tmp_path`` via ``monkeypatch.setenv``.

    Resiliente a falhas (ADR-10): qualquer exceção é capturada e logada,
    nunca propaga — observabilidade não pode quebrar o sync.
    """
    import json
    from datetime import datetime
    try:
        override = os.environ.get("OUROBOROS_CACHE_DIR")
        if override:
            cache_dir = Path(override)
        else:
            cache_dir = raiz_projeto / ".ouroboros" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "data": datetime.now().astimezone().isoformat(timespec="seconds"),
            "n_arquivos": int(n_arquivos),
            "fonte": "vault_obsidian",
            "vault_path": str(vault_path),
            "duracao_segundos": round(float(duracao_segundos), 2),
            "erros": list(erros or []),
        }
        target = cache_dir / "last_sync.json"
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("last_sync.json gravado: %s", target)
    except Exception as exc:  # noqa: BLE001 -- ADR-10 resiliência
        logger.warning("falha ao gravar last_sync.json: %s", exc)


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
    import time as _time
    _inicio = _time.monotonic()
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
            destino = fin / "Documentos" / yyyymm / f"{slugify(doc.nome_canonico)}.md"
            conteudo = _render_documento(doc.metadata, doc.nome_canonico)
            try:
                _escrever_nota(destino, conteudo, dry_run, report, "documento")
                _copiar_original(doc.metadata, doc.nome_canonico, fin, dry_run)
            except Exception as exc:  # noqa: BLE001
                logger.error("erro ao escrever %s: %s", destino, exc)
                report.erros.append(f"doc:{doc.nome_canonico}:{exc}")

        # --- MOCs mensais (Sprint 87.6, resolve R71-2) ---
        agregado_por_mes = _agregar_docs_por_mes(documentos)
        for mes_ref, bucket in sorted(agregado_por_mes.items()):
            if mes_ref == "sem-data":
                logger.warning(
                    "MOC mensal: %d docs sem data_emissao — ignorados",
                    len(bucket.get("docs", [])),
                )
                continue
            destino_moc = fin / "Meses" / f"{mes_ref}.md"
            conteudo_moc = _render_moc_mensal(mes_ref, bucket)
            try:
                _escrever_nota(destino_moc, conteudo_moc, dry_run, report, "moc")
            except Exception as exc:  # noqa: BLE001
                logger.error("erro ao escrever MOC %s: %s", destino_moc, exc)
                report.erros.append(f"moc:{mes_ref}:{exc}")

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

    # Observabilidade UX-V-04: grava last_sync.json apenas em execução real
    # (dry_run pula para não poluir cache em testes/inspeções).
    if not dry_run:
        _gravar_last_sync(
            _RAIZ_REPO,
            n_arquivos=report.total_escritas(),
            duracao_segundos=_time.monotonic() - _inicio,
            vault_path=str(vault_root),
            erros=report.erros,
        )

    return report


def _contar_docs_do_fornecedor(db: GrafoDB, forn_id: int | None) -> int:
    """Conta arestas `fornecido_por` apontando para o fornecedor."""
    if forn_id is None:
        return 0
    return len(db.listar_edges(dst_id=forn_id, tipo="fornecido_por"))


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
    parser.add_argument("--vault", type=Path, default=None, help="Sobrescreve BORDO_DIR")
    args = parser.parse_args(argv)

    vault = args.vault or Path(os.environ.get("BORDO_DIR", Path.home() / "Controle de Bordo"))
    report = sincronizar_rico(vault, dry_run=not args.executar)
    logger.info(
        "sync rico: %d docs, %d fornecedores, %d MOCs, %d preservadas, %d inalteradas, %d erros",
        report.documentos_escritos,
        report.fornecedores_escritos,
        report.mocs_gerados,
        report.notas_preservadas,
        report.inalteradas,
        len(report.erros),
    )
    return 0 if not report.erros else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())


# "O grafo do vault é o nosso dashboard sempre aberto." — princípio Sprint 71
