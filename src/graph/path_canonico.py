"""AUDIT-PATH-RELATIVO: helpers para path canonico em metadata.

Paths em `metadata.arquivo_origem` SQLite são SEMPRE relativos a
`_RAIZ_REPO` quando dentro do repo. Resolução para absoluto eh runtime
via `to_absoluto`. Helpers existem para evitar gravacao acidental de
paths absolutos (`/home/andrefarias/...`) que não funcionam em outra
maquina.
"""

from __future__ import annotations

from pathlib import Path

_RAIZ_REPO: Path = Path(__file__).resolve().parents[2]


def to_relativo(p: Path | str) -> str:
    """Converte path absoluto para relativo a `_RAIZ_REPO` (string).

    Se `p` ja eh relativo, devolve como string. Se eh absoluto FORA do
    repo (raro), preserva absoluto -- não tenta forçar relativo via `..`.
    """
    pp = Path(p) if isinstance(p, str) else p
    if not pp.is_absolute():
        return str(pp)
    try:
        pp_resolvido = pp.resolve()
        return str(pp_resolvido.relative_to(_RAIZ_REPO))
    except ValueError:
        # Path fora do repo -- preserva absoluto (caso raro, ex: tmp_path em testes).
        return str(pp)


def to_absoluto(p: str | Path) -> Path:
    """Converte string (relativa ou absoluta) para Path absoluto resolvido.

    Inverso de `to_relativo`. String relativa eh resolvida contra `_RAIZ_REPO`.
    """
    pp = Path(p)
    if pp.is_absolute():
        return pp
    return (_RAIZ_REPO / pp).resolve()


# "Casa que muda de endereço precisa de mapa novo." -- princípio do path canônico
