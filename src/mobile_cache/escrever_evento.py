"""Writer ao vault Bem-estar para eventos (Sprint UX-RD-18).

Complementa ``eventos.py`` (read-only): aquele varre o vault e gera o
cache JSON; este aqui escreve um registro novo em formato compatível
com o schema ``eventos`` -- frontmatter com ``modo``
(positivo/negativo), ``lugar``, ``bairro``, ``com``, ``categoria``,
``fotos`` e ``intensidade``. Após gravar, regenera o cache imediatamente
chamando :func:`gerar_cache`.

Caminho canônico do arquivo: ``<vault>/eventos/<YYYY-MM-DD>/<slug>.md``.
``slug`` é derivado de ``lugar`` (4 primeiras palavras ASCII) prefixado
por ``HHMM`` quando o caller não fornece slug explícito, evitando
colisão entre múltiplos eventos do mesmo dia.

Lição UX-RD-17 herdada: identificador de pessoa SEMPRE canônico
(``pessoa_a``/``pessoa_b``/``casal``) -- ADR-23 / Regra -1. Aceita
rótulos legados via :func:`pessoa_id_de_legacy` antes de gravar.

Formato canônico do .md gravado::

    ---
    tipo: evento
    data: 2026-05-05T20:00:00-03:00
    autor: casal
    modo: positivo
    lugar: padaria do bairro
    bairro: bela vista
    com:
      - pessoa_b
    categoria: rolezinho
    intensidade: 4
    fotos:
      - foto_padaria.jpg
    ---

    cafe da manha sem pressa.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml

from src.mobile_cache.eventos import gerar_cache as gerar_cache_eventos
from src.utils.logger import configurar_logger
from src.utils.pessoas import pessoa_id_de_legacy

logger = configurar_logger("mobile_cache.escrever_evento")

TZ_LOCAL = timezone(timedelta(hours=-3))

MODOS_VALIDOS = {"positivo", "negativo"}


def _normalizar_dia(valor: str | date) -> str:
    if isinstance(valor, date):
        return valor.isoformat()
    txt = str(valor).strip()
    return date.fromisoformat(txt).isoformat()


def _coerce_int_1_5(valor: int, nome: str) -> int:
    try:
        v = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nome}: esperado inteiro 1..5, recebido {valor!r}") from exc
    if not 1 <= v <= 5:
        raise ValueError(f"{nome}: fora do intervalo 1..5 ({v})")
    return v


def _ascii_slug(texto: str, *, max_palavras: int = 4) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    sem_acento = sem_acento.lower()
    palavras = re.findall(r"[a-z0-9]+", sem_acento)
    if not palavras:
        return ""
    return "-".join(palavras[:max_palavras])


def escrever_evento(
    vault_root: Path,
    dia: str | date,
    *,
    modo: str,
    lugar: str,
    bairro: str = "",
    com_quem: Iterable[str] | None = None,
    categoria: str = "",
    fotos: Iterable[str] | None = None,
    intensidade: int = 3,
    pessoa: str = "pessoa_a",
    texto: str = "",
    slug: str | None = None,
    regenerar_cache: bool = True,
) -> Path:
    """Grava registro de evento em ``<vault>/eventos/<dia>/<slug>.md``.

    Args:
        vault_root: raiz do vault Bem-estar.
        dia: data do registro (ISO string ou ``date``).
        modo: ``"positivo"`` ou ``"negativo"``.
        lugar: nome do estabelecimento ou local. Usado como base do slug
            quando ``slug`` não é fornecido.
        bairro: bairro associado (usado pela coluna lateral "Bairros
            frequentes" da página).
        com_quem: iterável de identificadores ``pessoa_a/pessoa_b/casal/...``.
        categoria: rótulo livre (rolezinho, jantar, cinema, ...).
        fotos: iterável de paths/nomes de fotos anexadas.
        intensidade: inteiro 1..5 (slider).
        pessoa: identificador legado/canônico do autor, normalizado via
            :func:`pessoa_id_de_legacy`.
        texto: corpo do registro (memória subjetiva do evento).
        slug: nome do arquivo dentro do dia. Default deriva de ``lugar``.
        regenerar_cache: se ``True`` (default), invoca
            :func:`gerar_cache_eventos` após gravar.

    Returns:
        ``Path`` do arquivo ``.md`` gravado.

    Raises:
        ValueError: se ``modo`` inválido, ``intensidade`` fora de 1..5,
            ``dia`` malformado, ou ``lugar`` vazio (sem material para slug).
    """
    vault_path = Path(vault_root).expanduser().resolve()
    dia_iso = _normalizar_dia(dia)
    pessoa_id = pessoa_id_de_legacy(pessoa)

    modo_norm = str(modo).strip().lower()
    if modo_norm not in MODOS_VALIDOS:
        raise ValueError(
            f"modo inválido: {modo!r}. Esperado um de {sorted(MODOS_VALIDOS)}"
        )
    intens = _coerce_int_1_5(intensidade, "intensidade")

    lugar_strip = (lugar or "").strip()
    if not lugar_strip and not slug:
        raise ValueError("lugar não pode ser vazio quando slug não é fornecido")

    com_list = [str(c).strip() for c in (com_quem or []) if str(c).strip()]
    fotos_list = [str(f).strip() for f in (fotos or []) if str(f).strip()]

    base_slug = slug.strip() if slug else _ascii_slug(lugar_strip)
    if not base_slug:
        base_slug = "evento"
    timestamp_atual = datetime.now(TZ_LOCAL).replace(microsecond=0)
    hhmm = timestamp_atual.strftime("%H%M")
    nome_arquivo = base_slug if slug else f"{hhmm}-{base_slug}"

    pasta_dia = vault_path / "eventos" / dia_iso
    pasta_dia.mkdir(parents=True, exist_ok=True)
    arquivo = pasta_dia / f"{nome_arquivo}.md"

    # Mesmo motivo do escrever_diario: ``data`` simples para o parser
    # via ``date.fromisoformat`` (Python 3.12 não aceita ISO completo).
    frontmatter: dict = {
        "tipo": "evento",
        "data": dia_iso,
        "autor": pessoa_id,
        "modo": modo_norm,
        "lugar": lugar_strip,
        "bairro": (bairro or "").strip(),
        "com": com_list,
        "categoria": (categoria or "").strip(),
        "intensidade": intens,
        "fotos": fotos_list,
        "timestamp_criacao": timestamp_atual.isoformat(),
    }

    yaml_block = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    corpo = f"{texto.strip()}\n" if texto and texto.strip() else ""
    conteudo = f"---\n{yaml_block}\n---\n\n{corpo}"
    arquivo.write_text(conteudo, encoding="utf-8")
    logger.info(
        "registro de evento gravado: %s (autor=%s, modo=%s, lugar=%s)",
        arquivo, pessoa_id, modo_norm, lugar_strip,
    )

    if regenerar_cache:
        try:
            gerar_cache_eventos(vault_path)
        except OSError as exc:
            logger.warning("falha ao regenerar eventos.json: %s", exc)

    return arquivo


# "O lugar é onde o tempo se atravessa em memória." -- Gaston Bachelard
