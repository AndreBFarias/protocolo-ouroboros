"""Writer ao vault Bem-estar: grava ``daily/<YYYY-MM-DD>.md`` (UX-RD-17).

Complementa ``humor_heatmap.py`` (read-only): aquele varre o vault e
gera o cache JSON; este aqui escreve um registro novo no vault em
formato compatível com ``CAMPOS_OBRIGATORIOS`` (data, autor, humor,
energia, ansiedade, foco). Após gravar, regenera o cache imediatamente
chamando :func:`gerar_humor_heatmap`, garantindo que a próxima
varredura do dashboard veja o novo dia sem reload manual.

Idempotência: gravações no mesmo ``(dia, pessoa)`` sobrescrevem o
arquivo. ``timestamp_criacao`` no frontmatter é preservado se o
arquivo já existia (apenas o ``timestamp_atualizacao`` muda) -- assim
historiamos a primeira vez que o humor foi capturado naquele dia,
útil para a métrica "tempo até registrar < 30 segundos" do mockup 17.

Lição UX-RD-17: identificador de pessoa SEMPRE canônico
(``pessoa_a``/``pessoa_b``/``casal``) -- ADR-23 / Regra -1. Aceita
rótulos legados via :func:`pessoa_id_de_legacy` antes de gravar.

Formato canônico do .md gravado::

    ---
    tipo: humor
    data: 2026-05-05
    autor: pessoa_a
    humor: 4
    energia: 3
    ansiedade: 2
    foco: 4
    medicacao_tomada: true
    horas_sono: 6.5
    tags:
      - calma
      - foco
    timestamp_criacao: 2026-05-05T08:15:00-03:00
    timestamp_atualizacao: 2026-05-05T08:15:00-03:00
    ---

    Frase do dia: manhã produtiva, sono ok 6h.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import yaml

from src.mobile_cache.humor_heatmap import gerar_humor_heatmap
from src.utils.logger import configurar_logger
from src.utils.pessoas import pessoa_id_de_legacy

logger = configurar_logger("mobile_cache.escrever_humor")

TZ_LOCAL = timezone(timedelta(hours=-3))

_RE_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)

# Tags canônicas oferecidas no mockup 17 -- chips multi-seleção.
TAGS_CANONICAS: tuple[str, ...] = (
    "alegria",
    "ansiedade",
    "calma",
    "cansaço",
    "foco",
    "irritação",
    "tranquilidade",
    "gratidão",
)


def _normalizar_dia(valor: str | date) -> str:
    """Aceita ISO ``YYYY-MM-DD`` ou ``date``; devolve string ISO."""
    if isinstance(valor, date):
        return valor.isoformat()
    txt = str(valor).strip()
    # Valida o parse para evitar paths absurdos no nome do arquivo.
    return date.fromisoformat(txt).isoformat()


def _coerce_int_1_5(valor: int, nome: str) -> int:
    """Garante inteiro 1..5 para sliders. Estoura ``ValueError`` se inválido."""
    try:
        v = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nome}: esperado inteiro 1..5, recebido {valor!r}") from exc
    if not 1 <= v <= 5:
        raise ValueError(f"{nome}: fora do intervalo 1..5 ({v})")
    return v


def _ler_timestamp_criacao_existente(arquivo: Path) -> str | None:
    """Lê ``timestamp_criacao`` do frontmatter, se arquivo já existe."""
    if not arquivo.exists():
        return None
    try:
        texto = arquivo.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _RE_FRONTMATTER.match(texto)
    if not match:
        return None
    try:
        dados = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(dados, dict):
        return None
    valor = dados.get("timestamp_criacao")
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    if isinstance(valor, datetime):
        return valor.isoformat()
    return None


def _agora_iso() -> str:
    """ISO 8601 truncado em segundos, fuso -03:00."""
    momento = datetime.now(TZ_LOCAL).replace(microsecond=0)
    return momento.isoformat()


def escrever_registro(
    vault_root: Path,
    dia: str | date,
    *,
    humor: int,
    energia: int,
    ansiedade: int,
    foco: int,
    medicacao: bool = False,
    horas_sono: float | None = None,
    tags: Iterable[str] | None = None,
    frase: str = "",
    pessoa: str = "pessoa_a",
    regenerar_cache: bool = True,
) -> Path:
    """Grava registro de humor em ``<vault>/daily/<YYYY-MM-DD>.md``.

    Args:
        vault_root: raiz do vault Bem-estar. Diretório ``daily/`` é criado
            se não existir.
        dia: data do registro (string ISO ou ``date``).
        humor, energia, ansiedade, foco: inteiros 1..5 (sliders do mockup 17).
        medicacao: se a medicação foi tomada hoje.
        horas_sono: horas de sono (float). ``None`` para omitir do frontmatter.
        tags: iterável de tags livres (não restritas a ``TAGS_CANONICAS``).
        frase: nota textual livre (mockup chama de "frase do dia").
        pessoa: identificador legado/canônico; é normalizado via
            :func:`pessoa_id_de_legacy`.
        regenerar_cache: se ``True`` (default), chama
            :func:`gerar_humor_heatmap` após gravar.

    Returns:
        ``Path`` do arquivo ``.md`` gravado.

    Raises:
        ValueError: se algum slider estiver fora de 1..5 ou ``dia`` inválido.
    """
    vault_path = Path(vault_root).expanduser().resolve()
    dia_iso = _normalizar_dia(dia)
    pessoa_id = pessoa_id_de_legacy(pessoa)

    # Validação imperativa dos sliders (1..5 inclusive).
    h = _coerce_int_1_5(humor, "humor")
    e = _coerce_int_1_5(energia, "energia")
    a = _coerce_int_1_5(ansiedade, "ansiedade")
    f = _coerce_int_1_5(foco, "foco")

    daily_dir = vault_path / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    arquivo = daily_dir / f"{dia_iso}.md"

    timestamp_atual = _agora_iso()
    timestamp_criacao = _ler_timestamp_criacao_existente(arquivo) or timestamp_atual

    frontmatter: dict = {
        "tipo": "humor",
        "data": dia_iso,
        "autor": pessoa_id,
        "humor": h,
        "energia": e,
        "ansiedade": a,
        "foco": f,
        "medicacao_tomada": bool(medicacao),
        "timestamp_criacao": timestamp_criacao,
        "timestamp_atualizacao": timestamp_atual,
    }
    if horas_sono is not None:
        try:
            frontmatter["horas_sono"] = float(horas_sono)
        except (TypeError, ValueError):
            logger.warning("horas_sono inválido (%r) -- ignorado", horas_sono)

    tags_list: list[str] = []
    if tags is not None:
        for t in tags:
            if not isinstance(t, str):
                continue
            t_strip = t.strip()
            if t_strip:
                tags_list.append(t_strip)
    if tags_list:
        frontmatter["tags"] = tags_list

    yaml_block = yaml.safe_dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()

    corpo = ""
    if frase and frase.strip():
        corpo = f"Frase do dia: {frase.strip()}\n"

    conteudo = f"---\n{yaml_block}\n---\n\n{corpo}"
    arquivo.write_text(conteudo, encoding="utf-8")
    logger.info("registro de humor gravado: %s (autor=%s)", arquivo, pessoa_id)

    if regenerar_cache:
        try:
            gerar_humor_heatmap(vault_path)
        except OSError as exc:
            # Cache pode falhar (permissões, FS read-only) sem invalidar
            # a gravação principal. Logamos e seguimos.
            logger.warning("falha ao regenerar humor-heatmap.json: %s", exc)

    return arquivo


# "Escreve, escreve, escreve -- o registro é a memória futura." -- Marco Aurélio
