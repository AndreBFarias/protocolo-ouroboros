"""Helper comum para fallback Opus em extratores específicos.

Sprint INFRA-EXTRATORES-USAR-OPUS (2026-05-08).

Refutação empírica do plano original
------------------------------------
A spec original (sprint_INFRA_extratores_usar_opus.md) descrevia os
extratores como retornando ``erro=campos_insuficientes``. A verificação
``rg "campos_insuficientes" src/extractors/`` provou o contrário: nenhum
dos 5 extratores alvo emite essa string -- todos falham silenciosamente
(retornam ``[]``, ``{}`` ou ``documento`` vazio).

Estratégia adotada (Opção B, validada pelo supervisor humano)
-------------------------------------------------------------
1. Adicionar fallback DENTRO de cada método público (``extrair_cupom``,
   ``extrair_bilhetes``, ``extrair_danfes``, ``extrair_receitas``,
   ``extrair_nfces``). NÃO mexer em ``ExtratorBase.extrair`` -- mudaria
   o contrato base e cascataria nos demais extratores.

2. Cada extrator detecta sua própria falha local (heurística simples:
   resultado vazio ou sem campo crítico) e, quando aplicável, chama
   ``extrair_via_opus(caminho)``.

3. O resultado do Opus é mapeado para o schema interno de cada extrator
   pela função ``_mapear_schema_canonico_opus`` específica da classe.

Cobertura efetiva nesta sprint
------------------------------
Apenas ``cupom_termico_foto`` tem mapeamento real Opus->schema interno,
porque o schema canônico Opus (cupom de consumo: ``estabelecimento``,
``itens``, ``total``) só cobre cupons fiscais. Para garantia estendida,
DANFE, receita médica e NFC-e, o gancho fica registrado mas o mapper
retorna estrutura vazia + log explicativo: o cache canônico Opus
correspondente teria que ter schema próprio dessas classes, e nenhum
deles existe hoje. Promove-se assim a integração honesta sem fingir
funcionalidade.

Quando o cache canônico Opus existir no schema correto destes outros
4 tipos, os respectivos ``_mapear_schema_canonico_opus`` desbloqueiam
imediatamente sem precisar tocar mais nada.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger: logging.Logger = logging.getLogger("opus_fallback_comum")


# Sufixos que o Opus visão hoje processa (calcula sha256 e busca cache).
# PDFs também passam (sha256 do binário), mas cache canônico Opus para
# PDFs não foi populado em modo supervisor artesanal nesta fase.
SUFIXOS_IMAGEM_OPUS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".heic", ".heif"})


def tentar_fallback_opus(caminho: Path) -> dict[str, Any] | None:
    """Chama ``extrair_via_opus`` e devolve payload válido ou ``None``.

    Devolve ``None`` em qualquer um destes casos (sem propagar exceção):

    - arquivo inexistente;
    - resposta com ``aguardando_supervisor=True`` (cache ainda não foi
      preenchido pelo supervisor humano artesanal);
    - qualquer ``Exception`` durante a chamada (fail-safe: o caller mantém
      o resultado local original).

    Devolve ``dict`` com payload canônico apenas quando o cache Opus
    está pronto e o schema é completo.
    """
    try:
        # Import local para evitar custo de import quando o fallback
        # nunca é exercitado.
        from src.extractors.opus_visao import extrair_via_opus
    except ImportError as erro:
        logger.warning("opus_visao indisponível: %s", erro)
        return None

    if not caminho.exists():
        logger.debug("fallback Opus: arquivo inexistente %s", caminho)
        return None

    try:
        payload = extrair_via_opus(caminho)
    except Exception as erro:  # noqa: BLE001 -- fallback nunca derruba pipeline
        logger.warning("fallback Opus falhou em %s: %s", caminho.name, erro)
        return None

    if not isinstance(payload, dict):
        logger.warning(
            "fallback Opus retornou tipo inesperado %s para %s",
            type(payload).__name__,
            caminho.name,
        )
        return None

    if payload.get("aguardando_supervisor"):
        logger.info(
            "fallback Opus pendente: %s (sha=%s) -- supervisor artesanal ainda não preencheu cache",
            caminho.name,
            (payload.get("sha256") or "")[:8],
        )
        return None

    return payload


# "A ferramenta certa para o trabalho errado e o trabalho certo
#  para a ferramenta errada produzem o mesmo nada." -- Sêneca
