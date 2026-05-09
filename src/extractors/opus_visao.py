"""Opus multimodal como OCR canônico para imagens (Sprint INFRA-OCR-OPUS-VISAO).

Promove o modelo Claude Opus a OCR canônico para cupons fotografados,
comprovantes e recibos físicos. Validação de 2026-05-08 mostrou que o OCR
local erra texto óbvio (ex.: "P55" em vez de "PS5") e que cupons JPEG têm
0/5 cobertura — enquanto o supervisor humano lendo via Read multimodal
extrai 52 itens de cupom degradado sem erro perceptível.

Modos de operação
-----------------

1. **Modo supervisor artesanal** (ADR-13, default desta sprint):

   A função NÃO chama Anthropic API. Quando recebe uma imagem nova,
   registra um pedido em ``data/output/opus_ocr_pendentes/<sha256>.txt``
   contendo o caminho absoluto da imagem. O supervisor humano (Claude Code)
   processa esse pedido manualmente: lê a imagem via Read multimodal,
   transcreve para o schema canônico e grava em
   ``data/output/opus_ocr_cache/<sha256>.json``. Na próxima invocação a
   função encontra o cache e retorna direto.

2. **Modo produção** (futuro, gated por ``OPUS_API_KEY``):

   Stub neste commit. Levanta ``NotImplementedError`` com mensagem clara
   de que o caminho API ainda não foi implementado. Sprint futura tratará.

Schema canônico
---------------

Documentado em ``mappings/schema_opus_ocr.json``. Campos obrigatórios:
``sha256``, ``tipo_documento``, ``estabelecimento``, ``data_emissao``,
``itens``, ``total``, ``extraido_via``, ``ts_extraido``.

Cache idempotente
-----------------

A chave é o sha256 do conteúdo da imagem (não do nome). Mesma imagem
renomeada bate o mesmo cache. Padrão alinhado a ``_ocr_comum.cache_key``
mas usa o hash hex completo (não truncado) por consistência com o nome
do pedido pendente.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from src.utils.logger import configurar_logger

logger: logging.Logger = configurar_logger("extrator_opus_visao")


# ---------------------------------------------------------------------------
# Constantes de path (overridáveis por argumento; default produção)
# ---------------------------------------------------------------------------

_RAIZ_PROJETO: Path = Path(__file__).resolve().parent.parent.parent
DIR_CACHE_PADRAO: Path = _RAIZ_PROJETO / "data" / "output" / "opus_ocr_cache"
DIR_PENDENTES_PADRAO: Path = _RAIZ_PROJETO / "data" / "output" / "opus_ocr_pendentes"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def calcular_sha256(caminho: Path) -> str:
    """Hash SHA-256 hex completo do conteúdo da imagem.

    Igual ao adotado em ``_ocr_comum.cache_key`` exceto pela truncagem:
    aqui o hex completo (64 chars) é usado para casar com o nome do
    arquivo de pedido pendente, que precisa ser único globalmente.
    """
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def _registrar_pendente(
    sha: str,
    caminho_imagem: Path,
    dir_pendentes: Path,
) -> Path:
    """Grava pedido para o supervisor humano em ``<dir_pendentes>/<sha>.txt``.

    O txt contém o caminho absoluto da imagem; o supervisor lê via Read
    multimodal e gera o JSON canônico no diretório de cache.
    """
    dir_pendentes.mkdir(parents=True, exist_ok=True)
    arquivo_pedido = dir_pendentes / f"{sha}.txt"
    arquivo_pedido.write_text(str(caminho_imagem.resolve()), encoding="utf-8")
    logger.info(
        "pedido OCR Opus registrado: %s (sha=%s...)",
        arquivo_pedido.name,
        sha[:8],
    )
    return arquivo_pedido


def _ler_cache(sha: str, dir_cache: Path) -> dict | None:
    """Retorna o JSON canônico do cache se já existir, senão None."""
    arquivo_cache = dir_cache / f"{sha}.json"
    if not arquivo_cache.exists():
        return None
    try:
        dados = json.loads(arquivo_cache.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        logger.warning(
            "cache Opus corrompido em %s: %s — tratando como cache miss",
            arquivo_cache,
            erro,
        )
        return None
    logger.debug("cache Opus hit: %s", arquivo_cache.name)
    return dados


def _resultado_aguardando(sha: str, caminho_imagem: Path) -> dict:
    """Resultado provisório quando o pedido foi registrado mas o supervisor
    ainda não processou. Marcado com ``aguardando_supervisor=True``.

    A escolha de devolver dict (em vez de levantar) preserva o pipeline
    que chama em loop sobre a inbox: o leitor pode pular este arquivo e
    seguir para o próximo, e numa próxima rodada o cache estará pronto.
    """
    return {
        "sha256": sha,
        "tipo_documento": "pendente",
        "aguardando_supervisor": True,
        "caminho_imagem": str(caminho_imagem),
        "extraido_via": "opus_supervisor_artesanal",
        "ts_extraido": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def extrair_via_opus(
    caminho: Path,
    *,
    dir_cache: Path | None = None,
    dir_pendentes: Path | None = None,
) -> dict:
    """Lê imagem via Opus multimodal e retorna schema canônico.

    Modo supervisor artesanal (ADR-13)
    ----------------------------------
    Se ``OPUS_API_KEY`` não está no ambiente:

    1. Calcula sha256 da imagem.
    2. Se ``<dir_cache>/<sha>.json`` existe, parsea e retorna.
    3. Caso contrário, grava pedido em ``<dir_pendentes>/<sha>.txt`` e
       retorna stub ``aguardando_supervisor=True`` (sem levantar). O
       supervisor humano deve transcrever a imagem para o cache na
       próxima passagem.

    Modo produção (futuro)
    ----------------------
    Se ``OPUS_API_KEY`` está no ambiente: levanta ``NotImplementedError``.
    Stub registrado para sprint futura cuidar da chamada API.

    Parâmetros
    ----------
    caminho:
        Caminho da imagem (.jpg, .jpeg, .png, .heic).
    dir_cache:
        Diretório de cache JSON. Default ``data/output/opus_ocr_cache``.
    dir_pendentes:
        Diretório de pedidos pendentes. Default
        ``data/output/opus_ocr_pendentes``.

    Retorno
    -------
    dict no schema canônico (``mappings/schema_opus_ocr.json``) ou stub
    ``aguardando_supervisor=True`` quando o pedido está em fila.
    """
    if not caminho.exists():
        raise FileNotFoundError(f"Imagem inexistente: {caminho}")

    cache = dir_cache if dir_cache is not None else DIR_CACHE_PADRAO
    pendentes = dir_pendentes if dir_pendentes is not None else DIR_PENDENTES_PADRAO

    if os.environ.get("OPUS_API_KEY"):
        logger.warning(
            "modo API ainda não implementado — sprint futura. "
            "Caindo em modo supervisor artesanal."
        )
        raise NotImplementedError(
            "Modo produção (chamada Anthropic API) não implementado nesta sprint. "
            "Remover OPUS_API_KEY ou aguardar sprint INFRA-OCR-OPUS-API."
        )

    sha = calcular_sha256(caminho)

    cached = _ler_cache(sha, cache)
    if cached is not None:
        return cached

    _registrar_pendente(sha, caminho, pendentes)
    return _resultado_aguardando(sha, caminho)


# "Onde modelo fraco erra, modelo forte vê com olho humano." -- Heráclito de Éfeso
