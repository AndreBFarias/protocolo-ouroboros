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


# ---------------------------------------------------------------------------
# Sprint INFRA-INBOX-OFX-READER -- scan recursivo + fila persistida
# ---------------------------------------------------------------------------
#
# Adições aditivas (padrão (o) retrocompatível): listar_inbox e companhia
# permanecem com contrato sha8 + sidecar; abaixo entra a camada de "fila"
# com sha256 completo, scan recursivo e schema JSON v1 da spec.
#
# - escanear_inbox(raiz): scan recursivo, devolve dicts schema v1.
# - persistir_fila(itens, destino): grava JSON com chave "itens".
# - carregar_fila(origem): leitura defensiva.
# - agrupar_duplicatas(itens): agrega contador por sha8.
# - processar_fila(raiz, destino, extrator): orquestra scan + dedup +
#   persistência. Extrator é hook opcional (default: marca aguardando).

# Mapeamento extensao -> tipo inferido (semantica de negocio).
# Diferente de _EXT_PARA_TIPO_VISUAL que devolve categoria visual.
_EXT_PARA_TIPO_INFERIDO: dict[str, str] = {
    ".pdf": "documento_pdf",
    ".csv": "extrato_csv",
    ".xlsx": "planilha_xlsx",
    ".xls": "planilha_xlsx",
    ".ofx": "extrato_ofx",
    ".jpg": "imagem",
    ".jpeg": "imagem",
    ".png": "imagem",
    ".heic": "imagem",
    ".heif": "imagem",
    ".webp": "imagem",
    ".xml": "xml_estruturado",
    ".eml": "email",
    ".zip": "compactado",
    ".txt": "texto_plano",
    ".html": "html_pagina",
    ".json": "json_estruturado",
}

# Schema v1 da fila persistida (constante exportada para validação externa).
SCHEMA_FILA_VERSAO: str = "1"


def _calcular_sha256_completo(arquivo: Path) -> str:
    """Sha256 completo (64 chars) do conteúdo binário.

    Usa o mesmo padrão de chunks de 64 KiB de ``_calcular_sha8``.
    """
    h = hashlib.sha256()
    with arquivo.open("rb") as fp:
        while True:
            chunk = fp.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _tipo_inferido(extensao: str) -> str:
    """Tipo semântico de negócio a partir da extensão.

    Fallback para ``desconhecido`` quando extensão não mapeada (defesa
    contra novas extensões adicionadas a EXTENSOES_ACEITAS sem updates).
    """
    return _EXT_PARA_TIPO_INFERIDO.get(extensao.lower(), "desconhecido")


def _raiz_inbox_padrao() -> Path:
    """Default da Sprint INFRA-INBOX-OFX-READER: ``<raiz>/data/raw/inbox/``.

    Específico do scan recursivo. NÃO confundir com ``_resolver_inbox_path``
    que continua atendendo a UI legada (``<raiz>/inbox/``).
    """
    return _raiz_projeto() / "data" / "raw" / "inbox"


def _destino_fila_padrao() -> Path:
    """Default da fila persistida: ``<raiz>/data/output/inbox_fila.json``."""
    return _raiz_projeto() / "data" / "output" / "inbox_fila.json"


def escanear_inbox(raiz: Path | None = None) -> list[dict]:
    """Scan recursivo da inbox devolvendo schema v1 da Sprint INFRA-OFX.

    Args:
        raiz: Diretório raiz da inbox. ``None`` -> ``<raiz>/data/raw/inbox/``.

    Returns:
        Lista de dicts com schema v1::

            {
              "sha256": "<64 chars>",
              "filename": "extrato.pdf",
              "tipo_inferido": "documento_pdf",
              "tamanho_kb": 182,
              "status": "aguardando",
              "ts_descoberto": "ISO",
              "ts_processado": None,
              "extractor_versao": None,
              "caminho_relativo": "subpasta/extrato.pdf",
            }

        Diretório inexistente devolve lista vazia (degradação graciosa).
    """
    diretorio = raiz if raiz is not None else _raiz_inbox_padrao()
    if not diretorio.exists() or not diretorio.is_dir():
        return []

    itens: list[dict] = []
    for arquivo in sorted(diretorio.rglob("*")):
        if not arquivo.is_file():
            continue
        ext = arquivo.suffix.lower()
        if ext not in EXTENSOES_ACEITAS:
            continue
        if arquivo.name.startswith("."):
            continue
        # Sidecars internos do listar_inbox legado não entram na fila.
        if ".extracted" in arquivo.parts:
            continue

        try:
            stat = arquivo.stat()
            sha256 = _calcular_sha256_completo(arquivo)
        except OSError:
            continue

        ts_iso, _ = _formatar_ts(datetime.fromtimestamp(stat.st_mtime))
        try:
            caminho_rel = str(arquivo.relative_to(diretorio))
        except ValueError:
            caminho_rel = arquivo.name

        itens.append(
            {
                "sha256": sha256,
                "filename": arquivo.name,
                "tipo_inferido": _tipo_inferido(ext),
                "tamanho_kb": round(stat.st_size / 1024.0, 1),
                "status": "aguardando",
                "ts_descoberto": ts_iso,
                "ts_processado": None,
                "extractor_versao": None,
                "caminho_relativo": caminho_rel,
            }
        )

    itens.sort(key=lambda i: i["ts_descoberto"], reverse=True)
    return itens


def agrupar_duplicatas(itens: list[dict]) -> dict[str, int]:
    """Conta ocorrências por sha8 (primeiros 8 chars do sha256).

    Returns:
        Dict ``{sha8: contador}`` apenas para sha8 com contador > 1.
        Sha8 com 1 ocorrência são omitidos (foco em duplicatas reais).
    """
    contagem: dict[str, int] = {}
    for it in itens:
        sha = it.get("sha256", "")
        if not sha:
            continue
        sha8 = sha[:8]
        contagem[sha8] = contagem.get(sha8, 0) + 1
    return {sha8: c for sha8, c in contagem.items() if c > 1}


def persistir_fila(itens: list[dict], destino: Path | None = None) -> Path:
    """Grava ``{"itens": itens, "schema": "1"}`` em JSON.

    Args:
        itens: Lista de dicts no schema v1 (ver ``escanear_inbox``).
        destino: Path do JSON. ``None`` -> ``<raiz>/data/output/inbox_fila.json``.

    Returns:
        Path absoluto do arquivo gravado.
    """
    caminho = destino if destino is not None else _destino_fila_padrao()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": SCHEMA_FILA_VERSAO, "itens": itens}
    caminho.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return caminho


def carregar_fila(origem: Path | None = None) -> list[dict]:
    """Lê ``inbox_fila.json`` e devolve a lista ``itens``.

    Returns:
        Lista de dicts (vazia se arquivo ausente, JSON malformado ou
        schema desconhecido). Padrão: degradação graciosa.
    """
    caminho = origem if origem is not None else _destino_fila_padrao()
    if not caminho.exists():
        return []
    try:
        payload = json.loads(caminho.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(payload, dict):
        return []
    itens = payload.get("itens")
    if not isinstance(itens, list):
        return []
    return itens


def processar_fila(
    raiz: Path | None = None,
    destino: Path | None = None,
    extrator=None,  # callable(item: dict) -> dict | None
) -> list[dict]:
    """Orquestra scan recursivo + dedup + persistência da fila.

    Fluxo:
      1. ``escanear_inbox(raiz)`` produz itens em status=aguardando.
      2. Mescla com fila anterior (preserva status já processados).
      3. Marca duplicatas (sha8 com contador > 1) com status=pulado para
         entradas além da primeira ocorrência.
      4. Quando ``extrator`` é callable, chama-o para cada item em
         aguardando; resultado atualiza status/ts_processado/extractor_versao.
      5. ``persistir_fila(itens, destino)`` grava JSON.

    Args:
        raiz: Inbox raiz. ``None`` -> ``data/raw/inbox/``.
        destino: Destino do JSON. ``None`` -> ``data/output/inbox_fila.json``.
        extrator: Callable opcional ``(item) -> dict | None``. Quando
            devolve dict, sobrescreve campos do item. Quando devolve
            ``None``, item permanece como detectado (aguardando ou pulado).

    Returns:
        Lista final dos itens persistidos.
    """
    itens_novos = escanear_inbox(raiz)

    # Mescla com fila anterior preservando estado.
    fila_anterior = carregar_fila(destino)
    estados_por_sha: dict[str, dict] = {it["sha256"]: it for it in fila_anterior if "sha256" in it}

    fundidos: list[dict] = []
    for novo in itens_novos:
        anterior = estados_por_sha.get(novo["sha256"])
        if anterior is None:
            fundidos.append(novo)
            continue
        # Preserva status/ts_processado/extractor_versao quando ja processado.
        merged = dict(novo)
        if anterior.get("status") in {"extraido", "falhou", "pulado"}:
            merged["status"] = anterior["status"]
            merged["ts_processado"] = anterior.get("ts_processado")
            merged["extractor_versao"] = anterior.get("extractor_versao")
        fundidos.append(merged)

    # Duplicatas: mantem primeira ocorrencia, demais viram "pulado".
    vistos: set[str] = set()
    for item in fundidos:
        sha = item["sha256"]
        if sha in vistos:
            if item["status"] == "aguardando":
                item["status"] = "pulado"
                item["ts_processado"] = datetime.now().isoformat(timespec="seconds")
        else:
            vistos.add(sha)

    # Hook de extracao (opcional).
    if callable(extrator):
        for item in fundidos:
            if item["status"] != "aguardando":
                continue
            try:
                resultado = extrator(item)
            except Exception as exc:  # noqa: BLE001 -- isolamento de hook
                item["status"] = "falhou"
                item["ts_processado"] = datetime.now().isoformat(timespec="seconds")
                item["erro"] = str(exc)[:200]
                continue
            if isinstance(resultado, dict):
                item.update(resultado)
                if "ts_processado" not in resultado:
                    item["ts_processado"] = datetime.now().isoformat(timespec="seconds")

    persistir_fila(fundidos, destino)
    return fundidos


# "Antes de organizar a casa, é preciso saber o que há nela." -- Sêneca
