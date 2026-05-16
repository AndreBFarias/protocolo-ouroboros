"""Writer ao vault Bem-estar para diário emocional (Sprint UX-RD-18).

Complementa ``diario_emocional.py`` (read-only): aquele varre o vault e
gera o cache JSON; este aqui escreve um registro novo no vault em
formato compatível com o schema ``diario_emocional`` -- frontmatter com
``modo`` (trigger/vitoria), ``emocoes`` (lista), ``intensidade`` (1-5),
``com`` (lista) e ``texto``. Após gravar, regenera o cache imediatamente
chamando :func:`gerar_cache`, garantindo que a próxima varredura do
dashboard veja o novo dia sem reload manual.

Caminho canônico do arquivo: ``<vault>/inbox/mente/diario/<YYYY-MM-DD>/<slug>.md``.
O ``slug`` é derivado das primeiras 4 palavras de ``frase`` (sem
acentuação no nome do arquivo, ASCII-safe), prefixado por ``HHMM`` da
hora local quando disponível para evitar colisão entre múltiplos
registros do mesmo dia.

Idempotência: o caller que envia ``slug`` igual sobrescreve. Sem slug,
o timestamp HHMM corrente garante unicidade entre escritas distintas no
mesmo dia.

Lição UX-RD-17 herdada: identificador de pessoa SEMPRE canônico
(``pessoa_a``/``pessoa_b``/``casal``) -- ADR-23 / Regra -1. Aceita
rótulos legados via :func:`pessoa_id_de_legacy` antes de gravar.

Formato canônico do .md gravado::

    ---
    tipo: diario_emocional
    data: 2026-05-05T08:15:00-03:00
    autor: pessoa_a
    modo: trigger
    emocoes:
      - ansiedade
      - cansaco
    intensidade: 3
    com:
      - pessoa_b
    texto: reuniao chata logo cedo.
    ---

    reuniao chata logo cedo.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml

from src.mobile_cache.diario_emocional import gerar_cache as gerar_cache_diario
from src.utils.logger import configurar_logger
from src.utils.pessoas import pessoa_id_de_legacy

logger = configurar_logger("mobile_cache.escrever_diario")

TZ_LOCAL = timezone(timedelta(hours=-3))

MODOS_VALIDOS = {"trigger", "vitoria"}


def _normalizar_dia(valor: str | date) -> str:
    """Aceita ISO ``YYYY-MM-DD`` ou ``date``; devolve string ISO."""
    if isinstance(valor, date):
        return valor.isoformat()
    txt = str(valor).strip()
    return date.fromisoformat(txt).isoformat()


def _coerce_int_1_5(valor: int, nome: str) -> int:
    """Garante inteiro 1..5 para sliders. ``ValueError`` se inválido."""
    try:
        v = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nome}: esperado inteiro 1..5, recebido {valor!r}") from exc
    if not 1 <= v <= 5:
        raise ValueError(f"{nome}: fora do intervalo 1..5 ({v})")
    return v


def _agora_iso() -> str:
    """ISO 8601 truncado em segundos, fuso -03:00."""
    momento = datetime.now(TZ_LOCAL).replace(microsecond=0)
    return momento.isoformat()


def _ascii_slug(texto: str, *, max_palavras: int = 4) -> str:
    """Converte ``texto`` para slug ASCII curto (até ``max_palavras``)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    sem_acento = sem_acento.lower()
    palavras = re.findall(r"[a-z0-9]+", sem_acento)
    if not palavras:
        return ""
    return "-".join(palavras[:max_palavras])


def escrever_diario(
    vault_root: Path,
    dia: str | date,
    *,
    modo: str,
    emocoes: Iterable[str],
    intensidade: int,
    com_quem: Iterable[str] | None = None,
    frase: str = "",
    pessoa: str = "pessoa_a",
    slug: str | None = None,
    regenerar_cache: bool = True,
) -> Path:
    """Grava registro de diário emocional em ``<vault>/inbox/mente/diario/<dia>/<slug>.md``.

    Args:
        vault_root: raiz do vault Bem-estar. Subdir é criado se ausente.
        dia: data do registro (ISO string ou ``date``).
        modo: ``"trigger"`` ou ``"vitoria"``.
        emocoes: iterável de tags emocionais (livre).
        intensidade: inteiro 1..5 (slider).
        com_quem: iterável de identificadores ``pessoa_a/pessoa_b/casal/...``.
        frase: texto livre do registro (mockup chama de "frase do dia").
        pessoa: identificador legado/canônico, normalizado via
            :func:`pessoa_id_de_legacy`.
        slug: nome do arquivo dentro do dia. Quando ``None``, deriva de
            ``frase`` (4 primeiras palavras ASCII) prefixado por ``HHMM``.
        regenerar_cache: se ``True`` (default), invoca
            :func:`gerar_cache_diario` após gravar.

    Returns:
        ``Path`` do arquivo ``.md`` gravado.

    Raises:
        ValueError: se ``modo`` inválido, ``intensidade`` fora de 1..5,
            ``dia`` malformado, ou ``frase`` e ``slug`` ambos vazios.
    """
    vault_path = Path(vault_root).expanduser().resolve()
    dia_iso = _normalizar_dia(dia)
    pessoa_id = pessoa_id_de_legacy(pessoa)

    modo_norm = str(modo).strip().lower()
    if modo_norm not in MODOS_VALIDOS:
        raise ValueError(f"modo inválido: {modo!r}. Esperado um de {sorted(MODOS_VALIDOS)}")
    intens = _coerce_int_1_5(intensidade, "intensidade")

    emocoes_list = [str(e).strip() for e in (emocoes or []) if str(e).strip()]
    com_list = [str(c).strip() for c in (com_quem or []) if str(c).strip()]
    frase_strip = (frase or "").strip()

    base_slug = slug.strip() if slug else _ascii_slug(frase_strip)
    if not base_slug:
        base_slug = "registro"
    timestamp_atual = datetime.now(TZ_LOCAL).replace(microsecond=0)
    hhmm = timestamp_atual.strftime("%H%M")
    nome_arquivo = base_slug if slug else f"{hhmm}-{base_slug}"

    pasta_dia = vault_path / "inbox" / "mente" / "diario" / dia_iso
    pasta_dia.mkdir(parents=True, exist_ok=True)
    arquivo = pasta_dia / f"{nome_arquivo}.md"

    # Atenção: ``data`` é gravada como ``YYYY-MM-DD`` simples para que o
    # parser ``diario_emocional._parse_item`` (via ``_normalizar_data`` →
    # ``date.fromisoformat``) consiga ler. Strings ISO completas como
    # ``2026-05-05T02:38:46-03:00`` são rejeitadas por ``date.fromisoformat``
    # em Python 3.12. Precisão de hora vai em ``timestamp_criacao`` separado.
    frontmatter: dict = {
        "tipo": "diario_emocional",
        "data": dia_iso,
        "autor": pessoa_id,
        "modo": modo_norm,
        "emocoes": emocoes_list,
        "intensidade": intens,
        "com": com_list,
        "texto": frase_strip,
        "timestamp_criacao": timestamp_atual.isoformat(),
    }

    yaml_block = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    corpo = f"{frase_strip}\n" if frase_strip else ""
    conteudo = f"---\n{yaml_block}\n---\n\n{corpo}"
    arquivo.write_text(conteudo, encoding="utf-8")
    logger.info("registro de diário gravado: %s (autor=%s, modo=%s)", arquivo, pessoa_id, modo_norm)

    if regenerar_cache:
        try:
            gerar_cache_diario(vault_path)
        except OSError as exc:
            logger.warning("falha ao regenerar diario-emocional.json: %s", exc)

    return arquivo


# "O que se nomeia, se atravessa." -- princípio terapêutico
