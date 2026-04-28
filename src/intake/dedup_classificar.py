"""Sprint INFRA-DEDUP-CLASSIFICAR: dedup automático de PDFs bit-a-bit em
data/raw/_classificar/.

Detecta arquivos com SHA-256 idêntico (cópias bit-a-bit) e remove fósseis,
mantendo o canônico (sem sufixo _N) quando existe -- senão o de menor
lexicografia.

Causa raiz tratada: Sprint 97 (page-split heterogêneo) faz tentativa
+ reversão. Quando reverte para single envelope, o arquivo original e N
cópias com sufixo `_1`, `_2` ficam todos em `_classificar/`.

Uso:
    from src.intake.dedup_classificar import deduplicar_classificar
    rel = deduplicar_classificar(Path('data/raw/_classificar'), dry_run=True)
    # rel = {'removidos': 0, 'preservados': 3, 'grupos': [...]}
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from src.utils.logger import configurar_logger

logger = configurar_logger("intake.dedup_classificar")

# Pattern para identificar sufixo _<N> antes da extensão.
_SUFIXO_NUM = re.compile(r"_\d+(?=\.[^.]+$)")


def _sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(65536), b""):
            h.update(bloco)
    return h.hexdigest()


def _eh_canonico(nome: str) -> bool:
    """True se o nome NÃO tem sufixo `_<N>` antes da extensão."""
    return _SUFIXO_NUM.search(nome) is None


def _escolher_canonico(arquivos: list[Path]) -> Path:
    """Dado um grupo de arquivos com mesmo hash, escolhe qual preservar.

    Prioridade:
      1. O que tem nome canônico (sem `_<N>`).
      2. O de menor lexicografia (estável entre runs).
    """
    canonicos = [a for a in arquivos if _eh_canonico(a.name)]
    if canonicos:
        return sorted(canonicos)[0]
    return sorted(arquivos)[0]


def deduplicar_classificar(pasta: Path, dry_run: bool = True) -> dict:
    """Detecta e remove cópias bit-a-bit em ``pasta``.

    Args:
        pasta: caminho para data/raw/_classificar/ (ou outra pasta).
        dry_run: quando True, só reporta sem deletar.

    Returns:
        dict com chaves:
          - 'removidos': int (apagados ou marcados em dry_run)
          - 'preservados': int (canônicos mantidos)
          - 'grupos': list[dict] com {hash, canonico, descartados}
    """
    if not pasta.exists() or not pasta.is_dir():
        logger.info("pasta inexistente ou não-diretório: %s", pasta)
        return {"removidos": 0, "preservados": 0, "grupos": []}

    arquivos = sorted([p for p in pasta.iterdir() if p.is_file()])
    if not arquivos:
        return {"removidos": 0, "preservados": 0, "grupos": []}

    por_hash: dict[str, list[Path]] = {}
    for arq in arquivos:
        try:
            h = _sha256_arquivo(arq)
        except OSError as exc:
            logger.warning("falha ao calcular sha256 de %s: %s", arq, exc)
            continue
        por_hash.setdefault(h, []).append(arq)

    grupos: list[dict] = []
    removidos = 0
    preservados = 0
    for h, grupo in por_hash.items():
        if len(grupo) == 1:
            preservados += 1
            continue
        canonico = _escolher_canonico(grupo)
        descartados = [a for a in grupo if a != canonico]
        grupos.append(
            {
                "hash": h,
                "canonico": str(canonico),
                "descartados": [str(a) for a in descartados],
            }
        )
        preservados += 1
        for desc in descartados:
            if dry_run:
                logger.info("[dry-run] removeria %s (cópia de %s)", desc, canonico)
            else:
                try:
                    desc.unlink()
                    logger.info("removido %s (cópia bit-a-bit de %s)", desc, canonico)
                except OSError as exc:
                    logger.error("falha ao remover %s: %s", desc, exc)
                    continue
            removidos += 1

    return {"removidos": removidos, "preservados": preservados, "grupos": grupos}


# "Onde havia três, fique um -- três cópias do nada não são herança."
# -- princípio do dedup honesto
