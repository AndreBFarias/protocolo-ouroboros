"""Leitura observacional da inbox para a página UI (UX-RD-15).

Este módulo é PURO LEITOR -- não move, não classifica, não toca em
``data/raw/``. A lógica canônica de roteamento permanece em
``src.inbox_processor`` e ``src.intake.orchestrator`` (proibido tocar
nesses arquivos pela spec UX-RD-15).

Contrato:

    listar_inbox(inbox_path: Path | None = None) -> list[dict]

Para cada arquivo elegível em ``inbox_path`` (default ``<raiz>/inbox/``),
calcula sha8, detecta formato pela extensão, busca sidecar JSON em
``<inbox_path>/.extracted/<sha8>.json`` e devolve dict no shape esperado
pelo render da página::

    {
      "sha8": "a3f9c1e2",
      "filename": "extrato.pdf",
      "tipo": "pdf",            # categoria visual: pdf|csv|xlsx|ofx|img|html
      "tipo_arquivo": "extrato_cc",  # tipo semântico (do sidecar)
      "estado": "extraido",     # aguardando|extraido|falhou|duplicado
      "tamanho_humano": "182 KB",
      "ts_iso": "2026-04-29T14:32:11",
      "ts_humano": "2026-04-29 14:32",
      "sidecar": {...} | None,
      "erro": "..." | None,
      "duplicado_de": "..." | None,
      "caminho": "inbox/extrato.pdf",
    }

Estados derivados:

* sem sidecar e sem erro -> ``aguardando``
* sidecar com ``duplicado_de`` -> ``duplicado``
* sidecar com ``erro`` -> ``falhou``
* sidecar com ``tipo`` ou ``tipo_arquivo`` -> ``extraido``

Default ordering: por ``ts`` decrescente (mais recente primeiro).

Decisão de path (ADR-15 + cobertura legada): o repo já tem
``<raiz>/inbox/`` canônico (referenciado por ``src/inbox_processor.py``
e ``src/integrations/gmail_csv.py``). Mantemos como default. Aceita
override explícito para testes e para alinhamento futuro com
``data/inbox/`` se a infraestrutura migrar.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

# Extensões aceitas pela inbox real (espelha EXTENSOES_SUPORTADAS de
# ``src/inbox_processor.py`` -- mantido por valor para evitar import
# circular, deve ser revisado se ``inbox_processor`` mudar).
EXTENSOES_ACEITAS: set[str] = {
    ".pdf",
    ".csv",
    ".xlsx",
    ".xls",
    ".ofx",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".heif",
    ".webp",
    ".xml",
    ".eml",
    ".zip",
    ".txt",
    ".html",
    ".json",
}

# Mapeamento extensão -> categoria visual usada pelo glyph e pelo render.
_EXT_PARA_TIPO_VISUAL: dict[str, str] = {
    ".pdf": "pdf",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".ofx": "ofx",
    ".jpg": "img",
    ".jpeg": "img",
    ".png": "img",
    ".heic": "img",
    ".heif": "img",
    ".webp": "img",
    ".xml": "xml",
    ".eml": "eml",
    ".zip": "zip",
    ".txt": "txt",
    ".html": "html",
    ".json": "json",
}


def _raiz_projeto() -> Path:
    """Resolve a raiz do projeto a partir deste arquivo.

    ``src/intake/inbox_reader.py`` -> três níveis acima é a raiz.
    """
    return Path(__file__).resolve().parents[2]


def _resolver_inbox_path(inbox_path: Path | None) -> Path:
    """Resolve o diretório efetivo da inbox.

    Ordem de prioridade:
      1. ``inbox_path`` explícito (testes, integrações).
      2. ``<raiz>/inbox/`` (canônico do codebase atual).
      3. ``<raiz>/data/inbox/`` (alvo futuro -- spec menciona).
    """
    if inbox_path is not None:
        return inbox_path
    raiz = _raiz_projeto()
    canonico = raiz / "inbox"
    futuro = raiz / "data" / "inbox"
    if canonico.exists():
        return canonico
    if futuro.exists():
        return futuro
    return canonico


def _calcular_sha8(arquivo: Path) -> str:
    """Primeiros 8 chars do sha256 do conteúdo binário.

    Lê em chunks de 64 KiB para tolerar arquivos grandes sem estourar RAM.
    """
    h = hashlib.sha256()
    with arquivo.open("rb") as fp:
        while True:
            chunk = fp.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()[:8]


def _formatar_tamanho(bytes_: int) -> str:
    """Tamanho humano em KB/MB com 1 casa.

    Usa base 1024 (consistente com ``ls -h``).
    """
    if bytes_ < 1024:
        return f"{bytes_} B"
    kb = bytes_ / 1024.0
    if kb < 1024:
        return f"{kb:.0f} KB"
    mb = kb / 1024.0
    return f"{mb:.1f} MB"


def _ler_sidecar(diretorio_sidecar: Path, sha8: str) -> dict | None:
    """Lê sidecar JSON ``<dir>/<sha8>.json`` quando existe.

    Retorna ``None`` em ausência ou JSON malformado (degradação graciosa).
    """
    caminho = diretorio_sidecar / f"{sha8}.json"
    if not caminho.exists():
        return None
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _derivar_estado(sidecar: dict | None) -> str:
    """Estado derivado a partir do sidecar (ou ausência dele).

    Regras (ordem de avaliação):
      1. sidecar ausente -> ``aguardando``
      2. ``sidecar["duplicado_de"]`` truthy -> ``duplicado``
      3. ``sidecar["erro"]`` truthy -> ``falhou``
      4. ``sidecar["tipo"]`` ou ``sidecar["tipo_arquivo"]`` truthy -> ``extraido``
      5. fallback -> ``aguardando``
    """
    if sidecar is None:
        return "aguardando"
    if sidecar.get("duplicado_de"):
        return "duplicado"
    if sidecar.get("erro"):
        return "falhou"
    if sidecar.get("tipo") or sidecar.get("tipo_arquivo"):
        return "extraido"
    return "aguardando"


def _tipo_visual(extensao: str) -> str:
    """Categoria visual usada pelo glyph na fila."""
    return _EXT_PARA_TIPO_VISUAL.get(extensao.lower(), "txt")


def _formatar_ts(ts: datetime) -> tuple[str, str]:
    return ts.isoformat(timespec="seconds"), ts.strftime("%Y-%m-%d %H:%M")


def listar_inbox(inbox_path: Path | None = None) -> list[dict]:
    """Lista arquivos da inbox + estado derivado por sidecar.

    Args:
        inbox_path: Diretório da inbox. ``None`` -> resolução automática
            (``<raiz>/inbox/`` ou fallback ``data/inbox/``).

    Returns:
        Lista de dicts, ordenada por ``ts_iso`` decrescente. Diretório
        inexistente ou vazio retorna lista vazia.
    """
    diretorio = _resolver_inbox_path(inbox_path)
    if not diretorio.exists() or not diretorio.is_dir():
        return []

    sidecar_dir = diretorio / ".extracted"

    itens: list[dict] = []
    for arquivo in sorted(diretorio.iterdir()):
        if not arquivo.is_file():
            continue
        ext = arquivo.suffix.lower()
        if ext not in EXTENSOES_ACEITAS:
            continue
        if arquivo.name.startswith("."):
            continue

        try:
            stat = arquivo.stat()
            sha8 = _calcular_sha8(arquivo)
        except OSError:
            # Arquivo sumiu entre iterdir e stat -- ignorar silenciosamente.
            continue

        sidecar = _ler_sidecar(sidecar_dir, sha8)
        estado = _derivar_estado(sidecar)
        ts_iso, ts_humano = _formatar_ts(datetime.fromtimestamp(stat.st_mtime))

        itens.append(
            {
                "sha8": sha8,
                "filename": arquivo.name,
                "tipo": _tipo_visual(ext),
                "tipo_arquivo": (sidecar or {}).get("tipo_arquivo")
                or (sidecar or {}).get("tipo")
                or None,
                "estado": estado,
                "tamanho_bytes": stat.st_size,
                "tamanho_humano": _formatar_tamanho(stat.st_size),
                "ts_iso": ts_iso,
                "ts_humano": ts_humano,
                "sidecar": sidecar,
                "erro": (sidecar or {}).get("erro"),
                "duplicado_de": (sidecar or {}).get("duplicado_de"),
                "caminho": str(arquivo),
            }
        )

    # Ordem decrescente por ts; estável (sorted Python é estável) preserva
    # ordem alfabética secundária pra arquivos com mesmo mtime.
    itens.sort(key=lambda i: i["ts_iso"], reverse=True)
    return itens


def contar_estados(itens: list[dict]) -> dict[str, int]:
    """Soma por estado para a barra de status.

    Estados conhecidos: aguardando, extraido, falhou, duplicado. Total
    derivado por ``len(itens)``.
    """
    contagens: dict[str, int] = {
        "aguardando": 0,
        "extraido": 0,
        "falhou": 0,
        "duplicado": 0,
    }
    for it in itens:
        estado = it.get("estado", "aguardando")
        if estado in contagens:
            contagens[estado] += 1
    return contagens


def gravar_arquivo_inbox(
    nome_original: str,
    conteudo: bytes,
    inbox_path: Path | None = None,
) -> Path:
    """Grava conteúdo subido pelo dropzone em ``<inbox>/<nome>``.

    Cria o diretório se ausente. Se houver colisão de nome, prefixa o
    sha8 ao filename (``<sha8>_<nome>``) para preservar o original sem
    sobrescrever.
    """
    diretorio = _resolver_inbox_path(inbox_path)
    diretorio.mkdir(parents=True, exist_ok=True)

    destino = diretorio / nome_original
    if destino.exists():
        sha8 = hashlib.sha256(conteudo).hexdigest()[:8]
        destino = diretorio / f"{sha8}_{nome_original}"
    destino.write_bytes(conteudo)
    return destino


# "Antes de organizar a casa, é preciso saber o que há nela." -- Sêneca
