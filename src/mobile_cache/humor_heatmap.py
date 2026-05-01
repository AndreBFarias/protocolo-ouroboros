"""Gerador do cache ``humor-heatmap.json`` consumido pelo Mobile.

Varre os arquivos ``.md`` em ``<vault_root>/daily/`` e
``<vault_root>/inbox/mente/humor/`` cuja data caia nos últimos
``periodo_dias`` (default 90) dias. Cada arquivo deve ter frontmatter
YAML com campos canônicos: ``data``, ``autor``, ``humor``, ``energia``,
``ansiedade``, ``foco``. Frontmatter incompleto é silenciosamente
pulado (não quebra a geração).

Schema do payload em ``Protocolo-Mob-Ouroboros/docs/ADRs/0012-cache-mobile-readonly.md``.
Identificador de pessoa é sempre ``pessoa_a``/``pessoa_b``/``casal``
(Regra -1, ADR-23).

Saída padrão: ``<vault_root>/.ouroboros/cache/humor-heatmap.json``.
Escrita atômica via ``write_json_atomic`` para que o app Mobile,
lendo via SAF concorrentemente, jamais veja arquivo parcial.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from src.mobile_cache.atomic import write_json_atomic
from src.utils.logger import configurar_logger
from src.utils.pessoas import pessoa_id_de_legacy

logger = configurar_logger("mobile_cache.humor_heatmap")

SCHEMA_VERSION = 1
PESSOAS_PADRAO: tuple[str, ...] = ("pessoa_a", "pessoa_b")
TZ_LOCAL = timezone(timedelta(hours=-3))

CAMPOS_OBRIGATORIOS = ("data", "autor", "humor", "energia", "ansiedade", "foco")

_RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)


def _ler_frontmatter(md_path: Path) -> dict[str, Any] | None:
    """Le bloco YAML de frontmatter de um .md. Retorna None se ausente/invalido."""
    try:
        texto = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("falha ao ler %s: %s", md_path, exc)
        return None
    match = _RE_FRONTMATTER.match(texto)
    if not match:
        return None
    try:
        dados = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.warning("frontmatter inválido em %s: %s", md_path, exc)
        return None
    if not isinstance(dados, dict):
        return None
    return dados


def _normalizar_data(valor: Any) -> str | None:
    """Aceita date, datetime ou string ISO; retorna 'YYYY-MM-DD' ou None."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str):
        candidato = valor.strip()
        try:
            return date.fromisoformat(candidato).isoformat()
        except ValueError:
            return None
    return None


def _coerce_int(valor: Any) -> int | None:
    """Converte valor numerico do frontmatter para int (humor/energia/etc)."""
    if valor is None:
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return int(round(valor))
    if isinstance(valor, str):
        try:
            return int(valor.strip())
        except ValueError:
            return None
    return None


def _listar_dailies(vault_root: Path, periodo_dias: int, hoje: date) -> list[Path]:
    """Lista .md candidatos em daily/ e inbox/mente/humor/ ordenados por nome."""
    diretorios = [
        vault_root / "daily",
        vault_root / "inbox" / "mente" / "humor",
    ]
    limite_inferior = hoje - timedelta(days=periodo_dias - 1)
    arquivos: list[Path] = []
    for d in diretorios:
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            data_no_nome = _data_no_nome(md.stem)
            if data_no_nome is not None:
                if not (limite_inferior <= data_no_nome <= hoje):
                    continue
            arquivos.append(md)
    return arquivos


def _data_no_nome(stem: str) -> date | None:
    """Tenta extrair YYYY-MM-DD do início do stem do arquivo."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None


def _parse_celula(
    md_path: Path,
    limite_inferior: date,
    hoje: date,
) -> dict[str, Any] | None:
    """Parseia um .md em uma celula do heatmap. Retorna None se incompleto."""
    fm = _ler_frontmatter(md_path)
    if fm is None:
        return None
    if str(fm.get("tipo", "")).strip().lower() not in {"", "humor", "daily"}:
        # Aceita tipo ausente, ``humor`` ou ``daily``; rejeita outros (treino, etc.).
        return None
    data_iso = _normalizar_data(fm.get("data"))
    if data_iso is None:
        return None
    try:
        data_obj = date.fromisoformat(data_iso)
    except ValueError:
        return None
    if not (limite_inferior <= data_obj <= hoje):
        return None
    autor = pessoa_id_de_legacy(fm.get("autor"))
    if autor not in {"pessoa_a", "pessoa_b", "casal"}:
        return None
    humor = _coerce_int(fm.get("humor"))
    energia = _coerce_int(fm.get("energia"))
    ansiedade = _coerce_int(fm.get("ansiedade"))
    foco = _coerce_int(fm.get("foco"))
    if any(v is None for v in (humor, energia, ansiedade, foco)):
        return None
    return {
        "data": data_iso,
        "autor": autor,
        "humor": humor,
        "energia": energia,
        "ansiedade": ansiedade,
        "foco": foco,
    }


def _calcular_estatisticas(
    celulas: list[dict[str, Any]],
    pessoas: tuple[str, ...],
    hoje: date,
) -> dict[str, dict[str, Any]]:
    """Calcula media_humor_30d, registros_30d, registros_total por pessoa."""
    limite_30d = hoje - timedelta(days=29)
    stats: dict[str, dict[str, Any]] = {}
    for pessoa in pessoas:
        registros_total = 0
        registros_30d = 0
        soma_humor_30d = 0
        for c in celulas:
            if c["autor"] != pessoa:
                continue
            registros_total += 1
            try:
                data_obj = date.fromisoformat(c["data"])
            except ValueError:
                continue
            if data_obj >= limite_30d:
                registros_30d += 1
                soma_humor_30d += int(c["humor"])
        if registros_30d > 0:
            media = round(soma_humor_30d / registros_30d, 2)
        else:
            media = 0.0
        stats[pessoa] = {
            "media_humor_30d": media,
            "registros_30d": registros_30d,
            "registros_total": registros_total,
        }
    return stats


def _gerado_em_iso(referencia: datetime | None = None) -> str:
    """Retorna ISO 8601 com timezone -03:00 (formato canonico do schema)."""
    momento = referencia or datetime.now(TZ_LOCAL)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=TZ_LOCAL)
    else:
        momento = momento.astimezone(TZ_LOCAL)
    # Trunca microsegundos para idempotencia segundo-a-segundo.
    momento = momento.replace(microsecond=0)
    return momento.isoformat()


def gerar_humor_heatmap(
    vault_root: Path,
    periodo_dias: int = 90,
    saida: Path | None = None,
    hoje: date | None = None,
    pessoas: tuple[str, ...] = PESSOAS_PADRAO,
    gerado_em: datetime | None = None,
) -> Path:
    """Gera ``humor-heatmap.json`` no Vault.

    Parametros:
        vault_root: raiz do vault Mobile (ex.: ``~/Protocolo-Ouroboros``).
        periodo_dias: quantos dias retroativos cobrir (default 90).
        saida: caminho final do JSON. Default
            ``<vault_root>/.ouroboros/cache/humor-heatmap.json``.
        hoje: ``date`` de referência para o período (default
            ``date.today()``). Usado em testes para isolar do relógio.
        pessoas: tupla de pessoas válidas no schema. Default
            ``("pessoa_a", "pessoa_b")``.
        gerado_em: timestamp ISO. Default ``datetime.now(-03:00)``.

    Retorna o ``Path`` do arquivo gravado.
    """
    vault_root = Path(vault_root).expanduser().resolve()
    if hoje is None:
        hoje = datetime.now(TZ_LOCAL).date()
    if saida is None:
        saida = vault_root / ".ouroboros" / "cache" / "humor-heatmap.json"
    else:
        saida = Path(saida)

    limite_inferior = hoje - timedelta(days=periodo_dias - 1)
    candidatos = _listar_dailies(vault_root, periodo_dias, hoje)
    celulas: list[dict[str, Any]] = []
    vistos: set[tuple[str, str]] = set()
    for md in candidatos:
        celula = _parse_celula(md, limite_inferior, hoje)
        if celula is None:
            continue
        chave = (celula["data"], celula["autor"])
        if chave in vistos:
            # Mesma data + autor pode aparecer em daily/ e inbox/.
            # Mantemos o primeiro (ordem alfabetica = daily/ antes de inbox/).
            continue
        vistos.add(chave)
        celulas.append(celula)

    celulas.sort(key=lambda c: (c["data"], c["autor"]))
    stats = _calcular_estatisticas(celulas, pessoas, hoje)

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "gerado_em": _gerado_em_iso(gerado_em),
        "periodo_dias": periodo_dias,
        "pessoas": list(pessoas),
        "celulas": celulas,
        "estatisticas": stats,
    }
    write_json_atomic(saida, payload)
    logger.info(
        "humor-heatmap.json gerado: %d células, %d pessoas, período=%dd",
        len(celulas),
        len(pessoas),
        periodo_dias,
    )
    return saida


# "Conhece-te a ti mesmo." -- Socrates
