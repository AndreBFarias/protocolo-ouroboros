"""Auto-detect de pessoa para arquivos da inbox (Sprint 41b).

Decisão ortogonal à classificação de tipo: cada arquivo é roteado para
`data/raw/<pessoa>/...`, e essa `<pessoa>` precisa vir de algum lugar.

Antes da Sprint 41b: parâmetro hardcoded `pessoa="andre"` no orquestrador.
Em produção isso é frágil -- documentos da Vitória chegando à inbox vão
pra pasta do André.

A Sprint 41b implementa detecção em 3 camadas, em ordem:

  1. CPF extraído do preview (texto extraído do arquivo) -> consulta
     `mappings/cpfs_pessoas.yaml` (usuário cadastra CPF -> pessoa). Se o
     CPF está mapeado, retorna a pessoa correspondente.
  2. Pasta-pai do arquivo (`andre`/`vitoria`) -> usa direto. Útil quando
     o usuário organizou manualmente em subpastas antes de processar.
  3. Fallback `casal` -- NUNCA chuta André ou Vitória sem evidência.
     Documentos compartilhados ou ambíguos vão para `data/raw/casal/`,
     onde o supervisor revisa.

API:

    pessoa, fonte = detectar_pessoa(caminho_arquivo, preview_texto)

Devolve uma tupla (pessoa, fonte_da_decisao). `fonte` é string humano-legível
para auditoria (ex.: "CPF 051.273.731-22", "path 'andre/'", "fallback").

LGPD: `mappings/cpfs_pessoas.yaml` contém CPFs reais -- está no `.gitignore`.
Repo carrega só `mappings/cpfs_pessoas.yaml.example` com placeholders.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml

from src.intake.glyph_tolerant import extrair_cpf
from src.utils.logger import configurar_logger

logger = configurar_logger("intake.pessoa")

Pessoa = Literal["andre", "vitoria", "casal", "_indefinida"]

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]
_PATH_MAPPING: Path = _RAIZ_REPO / "mappings" / "cpfs_pessoas.yaml"

_PESSOAS_VALIDAS: frozenset[str] = frozenset({"andre", "vitoria", "casal"})

# Cache do mapping carregado uma vez no primeiro uso (igual ao classifier).
_CACHE_CPFS: dict[str, str] | None = None


# ============================================================================
# API pública
# ============================================================================


def detectar_pessoa(
    caminho_arquivo: Path,
    preview_texto: str | None,
) -> tuple[Pessoa, str]:
    """Devolve (pessoa, fonte_da_decisao).

    Ordem (curta-circuito no primeiro hit):
      1. CPF do preview cadastrado em `mappings/cpfs_pessoas.yaml`
      2. Pasta-pai do arquivo é `andre` ou `vitoria`
      3. Fallback `casal`

    Nunca levanta. Mapping ausente -> camada 1 não casa, segue para 2/3.
    """
    if preview_texto:
        cpf = extrair_cpf(preview_texto)
        if cpf:
            mapeamento = _carregar_mapeamento_se_preciso()
            cpf_chave = _normalizar_cpf_chave(cpf)
            pessoa = mapeamento.get(cpf_chave)
            if pessoa in _PESSOAS_VALIDAS:
                return pessoa, f"CPF {cpf}"  # type: ignore[return-value]

    pasta_pai = caminho_arquivo.parent.name.lower()
    if pasta_pai in {"andre", "vitoria"}:
        return pasta_pai, f"path '{pasta_pai}/'"  # type: ignore[return-value]

    return "casal", "fallback (sem CPF mapeado + pasta-pai não-pessoa)"


def recarregar_mapeamento(path: Path | None = None) -> dict[str, str]:
    """Recarrega `mappings/cpfs_pessoas.yaml` (use em testes ou após editar).

    Schema esperado:

        cpfs:
          "00000000000": andre     # CPF sem pontuação como string
          "11111111111": vitoria
          "22222222222": casal     # MEI compartilhado, etc.

    Mapping ausente é OK -- detector simplesmente nunca casa pela camada 1.
    Mapping com schema inválido (não-dict, sem chave `cpfs`) levanta
    ValueError no carregamento (falha-cedo).
    """
    global _CACHE_CPFS
    arquivo = path or _PATH_MAPPING

    if not arquivo.exists():
        logger.info(
            "mappings/cpfs_pessoas.yaml ausente -- detector usará só path/fallback. "
            "Copie mappings/cpfs_pessoas.yaml.example e preencha para ativar camada 1."
        )
        _CACHE_CPFS = {}
        return _CACHE_CPFS

    with arquivo.open(encoding="utf-8") as f:
        dados = yaml.safe_load(f) or {}

    if not isinstance(dados, dict):
        raise ValueError(f"YAML em {arquivo} não é dict raiz -- esperado chave 'cpfs' no topo")
    cpfs_raw = dados.get("cpfs", {})
    if not isinstance(cpfs_raw, dict):
        raise ValueError(f"YAML em {arquivo}: chave 'cpfs' deve ser dict")

    mapeamento: dict[str, str] = {}
    for chave_bruta, valor in cpfs_raw.items():
        chave = _normalizar_cpf_chave(str(chave_bruta))
        if len(chave) != 11 or not chave.isdigit():
            logger.warning(
                "CPF inválido em mappings/cpfs_pessoas.yaml: %r (esperado 11 dígitos)",
                chave_bruta,
            )
            continue
        if valor not in _PESSOAS_VALIDAS:
            logger.warning(
                "valor inválido para CPF %r em mappings/cpfs_pessoas.yaml: %r "
                "(esperado andre|vitoria|casal)",
                chave_bruta,
                valor,
            )
            continue
        mapeamento[chave] = valor

    _CACHE_CPFS = mapeamento
    logger.info("cpfs_pessoas.yaml carregado: %d CPF(s) registrado(s)", len(_CACHE_CPFS))
    return _CACHE_CPFS


# ============================================================================
# Internals
# ============================================================================


def _carregar_mapeamento_se_preciso() -> dict[str, str]:
    if _CACHE_CPFS is None:
        recarregar_mapeamento()
    return _CACHE_CPFS or {}


def _normalizar_cpf_chave(cpf: str) -> str:
    """Remove pontuação e espaços, devolve só dígitos."""
    return re.sub(r"\D", "", cpf)


# "Onde não há prova, não há acusação." -- princípio do direito civilizado
