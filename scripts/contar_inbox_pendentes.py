"""Conta arquivos pendentes em ``data/inbox/`` e imprime aviso visível.

Sprint HOOK-INBOX-01.

Invocado pelo hook ``.claude/hooks.json`` quando EU (Opus interativo)
chamo ``./run.sh --inbox``, ``--tudo`` ou ``--full-cycle``. Imprime aviso
em stderr se a fila estiver acima do threshold configurável.

Princípio D7 (cobertura observável, não-gate):

  - **Aviso, não bloqueio**. Exit code 0 sempre.
  - **Tolera ausência**. ``data/inbox/`` inexistente = 0 arquivos = silêncio.
  - **Configurável via env**:
    - ``OUROBOROS_INBOX_THRESHOLD=N`` (default 1) -- avisa se >= N.
    - ``OUROBOROS_AUTO_HINT_INBOX=0`` -- desativa totalmente.

Conforme ADR-13: nenhuma chamada Anthropic API. Apenas leitura de fs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[1]
_PATH_INBOX_PADRAO: Path = _RAIZ_REPO / "data" / "inbox"

ENV_DESATIVAR: str = "OUROBOROS_AUTO_HINT_INBOX"
ENV_THRESHOLD: str = "OUROBOROS_INBOX_THRESHOLD"
THRESHOLD_DEFAULT: int = 1


def _hook_desativado() -> bool:
    """Retorna True se a env var de desativacao foi setada para 0."""
    valor = os.environ.get(ENV_DESATIVAR, "1").strip()
    return valor in {"0", "false", "no", ""}


def _ler_threshold() -> int:
    """Le threshold via env, com fallback seguro."""
    bruto = os.environ.get(ENV_THRESHOLD, "").strip()
    if not bruto:
        return THRESHOLD_DEFAULT
    try:
        valor = int(bruto)
    except ValueError:
        return THRESHOLD_DEFAULT
    return max(1, valor)


def _contar_arquivos(inbox: Path) -> int:
    """Conta arquivos regulares em inbox (recursivo, ignora ocultos no nivel raiz)."""
    if not inbox.exists() or not inbox.is_dir():
        return 0
    total = 0
    for caminho in inbox.rglob("*"):
        # Ignora diretorios ocultos no primeiro nivel (ex: .agentic_only/ é
        # gerenciado por outra sprint).
        partes_relativas = caminho.relative_to(inbox).parts
        if partes_relativas and partes_relativas[0].startswith("."):
            continue
        if caminho.is_file():
            total += 1
    return total


def contar_pendentes(inbox: Path | None = None) -> int:
    """API publica testavel: número de arquivos pendentes em data/inbox/."""
    return _contar_arquivos(inbox or _PATH_INBOX_PADRAO)


def main() -> int:
    if _hook_desativado():
        return 0
    threshold = _ler_threshold()
    pendentes = contar_pendentes()
    if pendentes >= threshold:
        sufixo = "" if pendentes == 1 else "s"
        print(
            f"[INBOX] {pendentes} arquivo{sufixo} pendente{sufixo} em "
            f"data/inbox/. Considere /validar-inbox antes de prosseguir.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())


# "Fila visivel é fila gerenciavel. Fila invisivel é debito."
#  -- principio operacional do Protocolo Ouroboros
